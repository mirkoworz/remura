#!/usr/bin/env python3
# REMURA v0.8.52 LAB — 14/11/2026 11:00 CET
"""Explicit bounded EURUSD TEST read. No BTC, writes, predictions or raw logs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

from cloudflare_d1_readonly_audit import AuditError, api_request, require_account_id, require_account_token
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB, inspect_verified_inventory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from volume_features_v1 import analyze_export, decode, BTC_END, M5
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS
from volume_sequence_v1 import sequential_diagnostics
from fx_pilot_config_v1 import REFERENCE, compare_v1_fields, inspect_declared_config

VERSION = "0.8.52-lab"
SYMBOL = "FXCM:EURUSD"
MAX_SLOTS = 72
LIMIT = 100
SQL = (
    "SELECT event_key, received_at_ms, bar_close_ms, symbol, timeframe, "
    "event_type, version, is_timely, raw_json FROM tv_flow_events "
    "WHERE symbol = ? AND timeframe = ? AND bar_close_ms >= ? AND bar_close_ms <= ? "
    "AND received_at_ms <= ? ORDER BY bar_close_ms ASC, event_key ASC LIMIT ?"
)

def utc_ms(text):
    # Explicit UTC, no locale or timezone guesses. Minute resolution.
    if not isinstance(text, str) or len(text) != 17:
        raise AuditError("invalid_utc_format")
    try:
        dt = datetime.strptime(text, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise AuditError("invalid_utc_format") from None
    if dt.strftime("%Y-%m-%dT%H:%MZ") != text:
        raise AuditError("invalid_utc_format")
    return int(dt.timestamp()) * 1000

def check_window(start, end, now_ms):
    if (any(type(x) is not int for x in (start, end, now_ms))
        or start < BTC_END or start % M5 or end % M5
        or start > end or end - start >= MAX_SLOTS * M5
        or end + 120_000 > now_ms):
        raise AuditError("invalid_mature_fx_window")

def aggregate(response, start, end, now_ms):
    check_window(start, end, now_ms)
    if not isinstance(response, dict) or response.get("success") is not True:
        raise AuditError("query_failed")
    batches = response.get("result")
    if (not isinstance(batches, list) or len(batches) != 1
        or not isinstance(batches[0], dict) or batches[0].get("success") is not True):
        raise AuditError("invalid_batch")
    rows = batches[0].get("results")
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise AuditError("incomplete_or_invalid_page")
    for r in rows:
        if (not isinstance(r, dict) or set(r) != EXPECTED_COLUMNS
            or r["symbol"] != SYMBOL or r["timeframe"] != "5"
            or type(r["bar_close_ms"]) is not int or not start <= r["bar_close_ms"] <= end
            or type(r["received_at_ms"]) is not int or r["received_at_ms"] > now_ms):
            raise AuditError("unexpected_row_scope")
    parsed = analyze_export(rows)
    obs = parsed["observations"]
    config = {}
    accepted = {(v["bar_close_ms"],v["received_at_ms"]) for v in obs}
    for r in rows:
        key = (r["bar_close_ms"],r["received_at_ms"])
        if key not in accepted or key in config:
            continue
        p,_ = decode(r)
        config[key] = compare_v1_fields(p, REFERENCE)["v1_difference_fields"]
    if len(config) != len(obs) or any(v["cohort"] != "FX_RESEARCH_PREVIEW" for v in obs):
        raise AuditError("cohort_or_config_invariant")
    labels, missing, checks, differences = Counter(), Counter(), Counter(), Counter()
    for v in obs:
        labels.update(v["observed_labels"])
        missing.update(v["missing_fields"])
        checks.update(v["diagnostic_checks"].values())
        differences.update(config[(v["bar_close_ms"],v["received_at_ms"])])
    expected = (end-start)//M5+1
    invalid = parsed["counts"].get("INVALID_ROW",0)
    conflicts = parsed["quarantined_bars"]
    status = ("NO_MATCHING_ROWS" if not rows else
              "INVALID_OR_CONFLICTING_ROWS" if invalid or conflicts else
              "CONFIG_METADATA_MISMATCH" if differences else
              "INCOMPLETE_REQUESTED_WINDOW" if len(obs)!=expected else
              "COMPLETE_REQUESTED_WINDOW")
    return {
        "schema":"remura.tv.fx.test.aggregate.v1","version":VERSION,
        "status":status,"window_start_ms":start,"window_end_ms":end,
        "requested_slots":expected,"rows_read":len(rows),"valid_unique_bars":len(obs),
        "unobserved_requested_slots":expected-len(obs),
        "coverage_basis":"REQUESTED_SLOTS_NOT_MARKET_CALENDAR",
        "bar_events":sum(v["event_type"]=="BAR_EVENT" for v in obs),
        "heartbeats":sum(v["event_type"]=="HEARTBEAT" for v in obs),
        "timely_bars":sum(v["fx_timeliness_eligible"] for v in obs),
        "footprint_available_bars":sum(v["observed"]["footprint"]["available"] for v in obs),
        "invalid_rows":invalid,"quarantined_bars":conflicts,
        "duplicate_rows":parsed["counts"].get("DUPLICATE_ROW",0),
        "max_lag_ms":max((v["latency_ms"] for v in obs),default=None),
        "label_counts":dict(sorted(labels.items())),"missing_field_counts":dict(sorted(missing.items())),
        "diagnostic_counts":dict(sorted(checks.items())),
        "sequence_diagnostics":sequential_diagnostics(obs),
        "reference_config_sha256":inspect_declared_config(REFERENCE)["declared_config_sha256"],
        "v1_config_matching_bars":sum(not x for x in config.values()),
        "v1_config_difference_counts":dict(sorted(differences.items())),
        "effective_alert_inputs_attested":False,"scientific_admission":False,
        "target":"EU_D1_TEST_ONLY","raw_json_logged":False,"orders_enabled":False,
    }

def read_live(account_id,token,*,start,end,now_ms,explicit=False):
    if explicit is not True:
        raise AuditError("explicit_read_required")
    check_window(start,end,now_ms)
    account=quote(require_account_id(account_id),safe="")
    token=require_account_token(token)
    base=f"/accounts/{account}/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[TEST_DB]==ids[MAIN_DB]:
        raise AuditError("test_db_not_isolated")
    response=api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,
                         {"sql":SQL,"params":[SYMBOL,"5",start,end,now_ms,LIMIT+1]})
    return aggregate(response,start,end,now_ms)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--live-read",action="store_true",required=True)
    parser.add_argument("--start-utc",required=True)
    parser.add_argument("--end-utc",required=True)
    args=parser.parse_args()
    try:
        r=read_live(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                    start=utc_ms(args.start_utc),end=utc_ms(args.end_utc),
                    now_ms=time.time_ns()//1_000_000,explicit=True)
        print("REMURA_FX_TEST_ANALYTIC="+json.dumps(r,sort_keys=True,allow_nan=False))
        return 2 if r["status"] in ("INVALID_OR_CONFLICTING_ROWS","CONFIG_METADATA_MISMATCH") else 0
    except Exception:
        print("REMURA_FX_TEST_ANALYTIC=UNKNOWN_READ_FAILED")
        return 2

if __name__=="__main__":
    raise SystemExit(main())
