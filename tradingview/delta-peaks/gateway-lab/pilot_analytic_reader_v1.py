#!/usr/bin/env python3
# REMURA v0.8.48 LAB — 14/11/2026 09:38 CET
"""Bounded diagnostic BTC pilot read: TEST D1 only, aggregate output only.
No writes, exports, trading decisions, production access or FX research.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import quote

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB, inspect_verified_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from volume_features_v1 import analyze_export, BTC_START, BTC_END, M5
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS

VERSION = "0.8.48-lab"
SYMBOL = "BINANCE:BTCUSDT"
FIRST_CLOSE = BTC_START + (7 * 60 + 10) * 60_000
MAX_SLOTS = 72
LIMIT = 100
SQL = (
    "SELECT event_key, received_at_ms, bar_close_ms, symbol, timeframe, "
    "event_type, version, is_timely, raw_json FROM tv_flow_events "
    "WHERE symbol = ? AND timeframe = ? AND bar_close_ms >= ? AND bar_close_ms <= ? "
    "AND received_at_ms <= ? AND version = ? "
    "ORDER BY bar_close_ms ASC, event_key ASC LIMIT ?"
)


def window(now_ms):
    if type(now_ms) is not int or now_ms < FIRST_CLOSE + 120_000:
        raise AuditError("window_not_ready")
    end = min((now_ms - 120_000) // M5 * M5, BTC_END - M5)
    start = max(FIRST_CLOSE, end - (MAX_SLOTS - 1) * M5)
    if start > end:
        raise AuditError("window_not_ready")
    return start, end


def aggregate(payload, start, end, now_ms):
    if (type(start) is not int or type(end) is not int or type(now_ms) is not int
            or start % M5 or end % M5
            or not FIRST_CLOSE <= start <= end < BTC_END
            or end - start >= MAX_SLOTS * M5 or end + 120_000 > now_ms):
        raise AuditError("invalid_window")
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("query_failed")
    batches = payload.get("result")
    if (not isinstance(batches, list) or len(batches) != 1
            or not isinstance(batches[0], dict) or batches[0].get("success") is not True):
        raise AuditError("invalid_batch")
    rows = batches[0].get("results")
    if not isinstance(rows, list) or len(rows) > LIMIT:
        raise AuditError("incomplete_or_invalid_page")
    for row in rows:
        if (not isinstance(row, dict) or set(row) != EXPECTED_COLUMNS
                or row["symbol"] != SYMBOL or row["timeframe"] != "5"
                or row["version"] != "0.8.1-lab"
                or type(row["bar_close_ms"]) is not int
                or not start <= row["bar_close_ms"] <= end
                or type(row["received_at_ms"]) is not int or row["received_at_ms"] > now_ms):
            raise AuditError("unexpected_row_scope")
    parsed = analyze_export(rows)
    observations = parsed["observations"]
    if any(v["cohort"] != "BTC_TRANSPORT_ONLY" or v["fx_timeliness_eligible"]
           or v["hypotheses"] or v["orders_enabled"] for v in observations):
        raise AuditError("cohort_violation")
    labels, missing = Counter(), Counter()
    checks = {}
    for v in observations:
        labels.update(v["observed_labels"])
        missing.update(v["missing_fields"])
        for name, value in v["diagnostic_checks"].items():
            checks.setdefault(name, Counter())[value] += 1
    expected = (end - start) // M5 + 1
    counts = parsed["counts"]
    status = ("NO_MATCHING_ROWS" if not rows else
              "INVALID_OR_CONFLICTING_ROWS" if counts.get("INVALID_ROW") or counts.get("CONFLICT_ROW") else
              "INCOMPLETE_WINDOW" if len(observations) != expected else "COMPLETE_WINDOW")
    return {
        "schema": "remura.tv.test.aggregate.v1", "version": VERSION,
        "status": status, "window_start_ms": start, "window_end_ms": end,
        "expected_slots": expected, "rows_read": len(rows),
        "valid_unique_bars": len(observations),
        "unobserved_valid_slots": expected - len(observations),
        "heartbeats": sum(v["event_type"] == "HEARTBEAT" for v in observations),
        "bar_events": sum(v["event_type"] == "BAR_EVENT" for v in observations),
        "transport_within_120s": sum(v["transport_timely"] for v in observations),
        "max_lag_ms": max((v["latency_ms"] for v in observations), default=None),
        "invalid_rows": counts.get("INVALID_ROW", 0),
        "duplicate_rows": counts.get("DUPLICATE_ROW", 0),
        "conflict_rows": counts.get("CONFLICT_ROW", 0),
        "quarantined_bars": parsed["quarantined_bars"],
        "footprint_available_bars": sum(v["observed"]["footprint"]["available"] for v in observations),
        "partial_bars": sum(v["quality"] == "PARTIAL" for v in observations),
        "observed_label_counts": dict(sorted(labels.items())),
        "missing_field_counts": dict(sorted(missing.items())),
        "diagnostic_check_counts": {k: dict(sorted(v.items())) for k,v in sorted(checks.items())},
        "diagnostic_tolerances": "PROVISIONAL_NOT_CALIBRATED",
        "target": "EU_D1_TEST_ONLY", "cohort": "BTC_TRANSPORT_ONLY",
        "raw_json_logged": False, "signal_validation": "NOT_PERFORMED",
        "orders_enabled": False,
    }


def read_live(account_id, token, *, now_ms, explicit=False):
    if explicit is not True:
        raise AuditError("explicit_read_required")
    start, end = window(now_ms)
    account = quote(require_account_id(account_id), safe="")
    token = require_account_token(token)
    base = f"/accounts/{account}/d1/database"
    ids = inspect_verified_inventory(api_request("GET", base + "?page=1&per_page=100", token))
    if ids[TEST_DB] == ids[MAIN_DB]:
        raise AuditError("test_db_not_isolated")
    endpoint = base + "/" + quote(ids[TEST_DB], safe="") + "/query"
    response = api_request("POST", endpoint, token, {"sql": SQL, "params": [
        SYMBOL, "5", start, end, now_ms, "0.8.1-lab", LIMIT + 1]})
    return aggregate(response, start, end, now_ms)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-read", action="store_true", required=True)
    parser.parse_args()
    try:
        result = read_live(os.getenv("REMURA_CF_ACCOUNT_ID", ""),
                           os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
                           now_ms=time.time_ns() // 1_000_000, explicit=True)
        # Only the fixed aggregate schema is emitted. No raw/row-level data or exceptions.
        print("REMURA_TV_TEST_ANALYTIC=" + json.dumps(result, sort_keys=True, allow_nan=False))
        return 2 if result["status"] == "INVALID_OR_CONFLICTING_ROWS" else 0
    except Exception:
        print("REMURA_TV_TEST_ANALYTIC=UNKNOWN_READ_FAILED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
