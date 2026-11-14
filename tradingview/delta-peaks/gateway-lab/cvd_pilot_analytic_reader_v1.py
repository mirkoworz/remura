#!/usr/bin/env python3
# REMURA v0.8.68 LAB — 14/11/2026 16:46 CET
"""Dedicated CVD TEST reader; no order calls, writes, raw payload or prices in logs."""
import json
from collections import Counter,defaultdict
from urllib.parse import quote
from fx_pilot_analytic_reader_v1 import LIMIT, M5, MAX_SLOTS, utc_ms
from cloudflare_d1_readonly_audit import AuditError,api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB,inspect_verified_inventory
from cvd_telemetry_preview_v1 import validate,VERSION,SYMBOL
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS
from volume_quality_v1 import diagnose
from cvd_outcome_readiness_v1 import summarize
from cvd_radar_preview_v1 import aggregate_radar

# First aligned M5 close after actual successful TEST deployment at 12:36:36 UTC.
MIN_CLOSE_MS=utc_ms("2026-11-14T12:40Z")

def check_window(start,end,now):
    if (any(type(x) is not int for x in (start,end,now)) or start<MIN_CLOSE_MS
        or start%M5 or end%M5 or start>end or end-start>=MAX_SLOTS*M5
        or end+120000>now):
        raise AuditError("invalid_mature_cvd_window")

SQL=("SELECT event_key, received_at_ms, bar_close_ms, symbol, timeframe, event_type, version, is_timely, raw_json "
     "FROM tv_flow_events WHERE symbol = ? AND timeframe = ? AND version = ? "
     "AND bar_close_ms >= ? AND bar_close_ms <= ? AND received_at_ms <= ? "
     "ORDER BY bar_close_ms ASC, event_key ASC LIMIT ?")

def aggregate(response,start,end,now):
    check_window(start,end,now)
    if not isinstance(response,dict) or response.get("success") is not True:
        raise AuditError("query_failed")
    batch=response.get("result")
    if not isinstance(batch,list) or len(batch)!=1 or not isinstance(batch[0],dict) or batch[0].get("success") is not True:
        raise AuditError("query_batch")
    rows=batch[0].get("results")
    if not isinstance(rows,list) or len(rows)>LIMIT:
        raise AuditError("query_limit")
    groups=defaultdict(list)
    counts=Counter()
    for row in rows:
        if not isinstance(row,dict) or set(row)!=EXPECTED_COLUMNS or row["symbol"]!=SYMBOL or row["version"]!=VERSION or row["timeframe"]!="5":
            raise AuditError("wrong_row_scope")
        t=row["bar_close_ms"]; received=row["received_at_ms"]
        if type(t) is not int or not start<=t<=end or type(received) is not int or received>now:
            raise AuditError("wrong_row_clock")
        try:
            if type(row["raw_json"]) is not str or len(row["raw_json"].encode())>20000:
                raise ValueError("bad_payload")
            envelope=json.loads(row["raw_json"])
            v=validate(envelope,received_ms=received)
            if type(row["is_timely"]) is not int or row["is_timely"]!=0 or v["event_key"]!=row["event_key"] or v["bar_close_ms"]!=t or envelope["snapshot"]["event_type"]!=row["event_type"]:
                raise ValueError("row_identity")
            groups[t].append((row,envelope,v))
        except (ValueError,TypeError,KeyError,OverflowError):
            counts["invalid_rows"]+=1
    valid=[]
    for group in groups.values():
        original=group[0]
        if any(x[0]!=original[0] for x in group[1:]):
            counts["conflicted_bars"]+=1
            continue
        counts["duplicate_rows"]+=len(group)-1
        valid.append(original)
    labels=Counter(); quality=Counter(); math_checks=Counter(); differences=[]
    for row,e,v in valid:
        c=e["cvd"]; p=e["snapshot"]
        quality.update({"complete":int(c["complete"]),"continuous":int(c["continuous"] is True),
                        "day_valid":int(c["day_valid"]),"eligible":int(c["eligible"]),
                        "footprint_available":int(p["footprint"]["available"])})
        for name in ("price_bull","price_bear","cvd_bull","cvd_bear"):
            labels[name]+=int(c[name])
        for name in ("peak","er_positive","er_negative","retest_day1","retest_day2","retest_day3","retest_previous_day"):
            labels[name]+=int(p["events"][name])
        math_checks.update(diagnose(p).values())
        if v["delta_difference"] is not None:
            differences.append(abs(v["delta_difference"]))
    expected=(end-start)//M5+1
    status=("INVALID_OR_CONFLICTING_ROWS" if counts["invalid_rows"] or counts["conflicted_bars"] else
            "NO_MATCHING_ROWS" if not rows else "COMPLETE_REQUESTED_WINDOW" if len(valid)==expected
            else "INCOMPLETE_REQUESTED_WINDOW")
    return {"schema":"remura.tv.cvd.test.aggregate.preview.v1","version":"0.8.68-lab",
            "status":status,"symbol":SYMBOL,"window_start_ms":start,"window_end_ms":end,
            "requested_slots":expected,"valid_unique_bars":len(valid),"missing_requested_slots":expected-len(valid),
            "coverage_basis":"REQUESTED_SLOTS_NOT_MARKET_CALENDAR","row_counts":dict(counts),
            "quality_counts":dict(quality),"event_counts":dict(labels),"math_check_counts":dict(math_checks),
            "delta_comparable_bars":len(differences),"delta_exact_matches":sum(x==0 for x in differences),
            "delta_max_abs_difference":max(differences,default=None),
            "max_lag_ms":max((x[2]["lag_ms"] for x in valid),default=None),
            "target":"EU_D1_TEST_ONLY","raw_json_logged":False,"conflict_ledger_available":False,
            "radar":({"status":"BLOCKED_INVALID_OR_CONFLICT"} if counts["invalid_rows"] or counts["conflicted_bars"] else aggregate_radar(valid,as_of_ms=now)),
            "outcome_readiness":({"status":"BLOCKED_INVALID_OR_CONFLICT"} if counts["invalid_rows"] or counts["conflicted_bars"] else summarize(valid,as_of_ms=min(now,end+120000))),
            "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False}

def read_live(account_id,token,*,start,end,now,explicit=False):
    if explicit is not True:
        raise AuditError("explicit_read_required")
    check_window(start,end,now)
    account=quote(require_account_id(account_id),safe="")
    token=require_account_token(token)
    base=f"/accounts/{account}/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    response=api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,
        {"sql":SQL,"params":[SYMBOL,"5",VERSION,start,end,now,LIMIT+1]})
    return aggregate(response,start,end,now)

def main():
    import argparse,os,time
    from fx_pilot_analytic_reader_v1 import utc_ms
    parser=argparse.ArgumentParser()
    parser.add_argument("--live-read",action="store_true",required=True)
    parser.add_argument("--start-utc",required=True)
    parser.add_argument("--end-utc",required=True)
    args=parser.parse_args()
    try:
        r=read_live(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                    start=utc_ms(args.start_utc),end=utc_ms(args.end_utc),
                    now=time.time_ns()//1000000,explicit=True)
        print("REMURA_CVD_TEST_ANALYTIC="+json.dumps(r,sort_keys=True,allow_nan=False))
        return 2 if r["status"]=="INVALID_OR_CONFLICTING_ROWS" else 0
    except Exception:
        print("REMURA_CVD_TEST_ANALYTIC=UNKNOWN_READ_FAILED")
        return 2

if __name__=="__main__":
    raise SystemExit(main())
