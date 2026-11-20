#!/usr/bin/env python3
# REMURA v0.8.80 LAB — 14/11/2026 18:30 CET
"""Private in-memory TEST collection, no raw artifact, disk dump or DB writes.
One inventory read, up to eight SELECT pages. Never fetch production rows.
Public workflow logs can contain only fixed aggregates, not raw envelopes.
"""
import json
from urllib.parse import quote
from cvd_pilot_analytic_reader_v1 import SQL,SYMBOL,VERSION,M5,MAX_SLOTS,LIMIT,MIN_CLOSE_MS,utc_ms
from cloudflare_d1_readonly_audit import AuditError,api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from cvd_archive_preview_v2 import assemble
MAX_PAGES=8

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

def read_batch(account_id,token,*,start,end,now,explicit=False):
    if explicit is not True:
        raise AuditError("explicit_batch_read_required")
    pages=plan(start,end,now)
    account=quote(require_account_id(account_id),safe="")
    token=require_account_token(token)
    base=f"/accounts/{account}/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    windows=[]; met=[]
    for a,b in pages:
        response=api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,
            {"sql":SQL,"params":[SYMBOL,"5",VERSION,a,b,now,LIMIT+1]})
        rows,stats=unpack(response)
        windows.append({"start_ms":a,"end_ms":b,"rows":rows})
        met.append(stats)
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
    a=p.parse_args()
    try:
        r=read_batch(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                     start=utc_ms(a.start_utc),end=utc_ms(a.end_utc),now=time.time_ns()//1000000,explicit=True)
        print("REMURA_CVD_TEST_BATCH_V2="+json.dumps(r,sort_keys=True,allow_nan=False))
        return 0
    except Exception:
        print("REMURA_CVD_TEST_BATCH_V2=UNKNOWN_FAIL_CLOSED")
        return 2
if __name__=="__main__":
    raise SystemExit(main())
