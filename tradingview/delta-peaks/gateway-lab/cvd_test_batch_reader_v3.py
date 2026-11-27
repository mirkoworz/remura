#!/usr/bin/env python3
# REMURA v0.8.88 LAB — 14/11/2026 21:16 CET
"""Private in-memory TEST collection, no raw artifact, disk dump or DB writes.
One inventory read, up to eight SELECT pages. Never fetch production rows.
Public workflow logs can contain only fixed aggregates, not raw envelopes.
"""
import json
from cvd_test_fold_reader_v2 import fetch_page
from cvd_archive_preview_v1 import validate_windows
from cvd_radar_preview_v1 import aggregate_radar
from cvd_oos_protocol_preview_v2 import digest
from urllib.parse import quote
from cvd_pilot_analytic_reader_v1 import SQL,SYMBOL,VERSION,M5,MAX_SLOTS,LIMIT,MIN_CLOSE_MS,utc_ms
from cloudflare_d1_readonly_audit import AuditError,api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from cvd_archive_preview_v2 import assemble
MAX_PAGES=8
MAX_OBSERVED_READS=20000
MAX_RECEIPT_SLOTS=12

def plan(start,end,now):
    if (any(type(x) is not int for x in (start,end,now)) or start<MIN_CLOSE_MS or
        start%M5 or end%M5 or start>end or end+120000>now or
        end-start>=MAX_PAGES*MAX_SLOTS*M5):
        raise AuditError("invalid_batch_scope")
    return [(t,min(end,t+(MAX_SLOTS-1)*M5)) for t in range(start,end+1,MAX_SLOTS*M5)]

def unpack(response):
    if type(response) is not dict or response.get("success") is not True:
        raise AuditError("batch_query_failed")
    batches=response.get("result")
    if type(batches) is not list or len(batches)!=1 or type(batches[0]) is not dict or batches[0].get("success") is not True:
        raise AuditError("batch_query_shape")
    b=batches[0]; rows=b.get("results")
    if type(rows) is not list or len(rows)>LIMIT:
        raise AuditError("batch_limit_or_sentinel")
    meta=b.get("meta")
    if meta is not None and type(meta) is not dict:
        raise AuditError("batch_meta_invalid")
    meta=meta or {}
    values=[]
    for key in ("rows_read","rows_written"):
        x=meta.get(key)
        if x is not None and (type(x) is not int or x<0):
            raise AuditError("batch_meta_count")
        values.append(x)
    if values[1] not in (None,0):
        raise AuditError("unexpected_write_metadata")
    return rows,values

def read_batch(account_id,token,*,start,end,now,explicit=False,receipt_only=False):
    if explicit is not True:
        raise AuditError("explicit_batch_read_required")
    pages=plan(start,end,now)
    if type(receipt_only) is not bool or receipt_only and (end-start)//M5+1>MAX_RECEIPT_SLOTS:
        raise AuditError("receipt_scope")
    account=require_account_id(account_id)
    token=require_account_token(token)
    base="/accounts/"+quote(account,safe="")+"/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    windows=[]; met=[]; reads=0
    for a,b in pages:
        response=fetch_page(account,ids[TEST_DB],token,a,b,now)
        rows,stats=unpack(response)
        if stats[0] is None or stats[1]!=0:
            raise AuditError("batch_query_usage_unknown")
        reads+=stats[0]
        if reads>MAX_OBSERVED_READS:
            raise AuditError("batch_observed_read_budget_exceeded")
        windows.append({"start_ms":a,"end_ms":b,"rows":rows})
        met.append(stats)
    if receipt_only:
        valid,stats=validate_windows(windows,as_of_ms=now)
        report={"schema":"remura.tv.cvd.first.receipt.preview.v1","version":"0.8.88-lab",
                **stats,"symbol":SYMBOL,"sender_version":VERSION,"protocol_sha256":digest(),
                "scope":"REQUESTED_SLOTS_NOT_MARKET_CALENDAR",
                "status":"NO_MATCHING_ROWS" if not valid else "COMPLETE_REQUESTED_WINDOW" if not stats["missing_requested_slots"] else "PARTIAL_REQUESTED_WINDOW",
                "max_lag_ms":max((v["lag_ms"] for _,_,v in valid),default=None),
                "radar":aggregate_radar(valid,as_of_ms=now),"outcomes_computed":False,
                "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False,
                "conflict_ledger_available":False,"independent_provenance":False}
    else:
        report=assemble(windows,as_of_ms=now)
    report["collection"]={"target":"EU_D1_TEST_ONLY","inventory_requests":1,"select_requests":len(pages),
        "raw_persisted":False,"raw_logged":False,"account_quota_utilization":None,
        "query_rows_read":sum(x[0] for x in met) if all(x[0] is not None for x in met) else None,
        "query_rows_written":sum(x[1] for x in met) if all(x[1] is not None for x in met) else None,
        "query_meta_scope":"THIS_COLLECTION_ONLY_NOT_ACCOUNT_USAGE",
        "snapshot_atomic_across_pages":False}
    return report

def main():
    import argparse,os,time
    p=argparse.ArgumentParser()
    p.add_argument("--live-read",action="store_true",required=True)
    p.add_argument("--start-utc",required=True)
    p.add_argument("--end-utc",required=True)
    p.add_argument("--receipt-only",action="store_true")
    a=p.parse_args()
    try:
        r=read_batch(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                     start=utc_ms(a.start_utc),end=utc_ms(a.end_utc),now=time.time_ns()//1000000,explicit=True,receipt_only=a.receipt_only)
        print("REMURA_CVD_TEST_BATCH_V3="+json.dumps(r,sort_keys=True,allow_nan=False))
        return 0
    except Exception:
        print("REMURA_CVD_TEST_BATCH_V2=UNKNOWN_FAIL_CLOSED")
        return 2
if __name__=="__main__":
    raise SystemExit(main())
