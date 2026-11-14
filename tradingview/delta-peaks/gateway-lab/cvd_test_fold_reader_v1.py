#!/usr/bin/env python3
# REMURA v0.8.72 LAB — 14/11/2026 16:59 CET
"""One fixed closed calendar fold, private memory, bounded SELECT only.
No raw data files, uploads, scheduler, production reads or write queries.
A completed query calendar is not attested market coverage.
"""
import json
from urllib.parse import quote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from cvd_test_batch_reader_v1 import unpack,SQL,SYMBOL,VERSION,M5,MAX_SLOTS,LIMIT
from cloudflare_d1_readonly_audit import (AuditError,API_ORIGIN,api_request,
    require_account_id,require_account_token,UUID_RE)
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from cvd_archive_preview_v1 import assemble
from cvd_oos_protocol_preview_v1 import FOLDS,clock,digest
MAX_PAGES=28
MAX_RESPONSE_BYTES=4500000
MAX_READS_OBSERVED=100000  # research circuit breaker, not an account quota or hard server-side cap

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def plan(fold,now):
    matches=[(clock(s),clock(e)) for name,s,e in FOLDS if name==fold]
    if len(matches)!=1 or type(now) is not int:
        raise AuditError("unknown_fold")
    start,end=matches[0]
    if now<end:
        raise AuditError("fold_not_closed")
    pages=[(t,min(end-M5,t+(MAX_SLOTS-1)*M5)) for t in range(start,end,MAX_SLOTS*M5)]
    if len(pages)!=MAX_PAGES:
        raise AuditError("unexpected_fold_scope")
    return end,pages

def fetch_page(account,uid,token,a,b,cutoff):
    # Larger bounded response ONLY for the fixed SELECT path, no generic POST,
    # no redirect of credentials; original generic helper remains unchanged.
    if not UUID_RE.fullmatch(uid):
        raise AuditError("invalid_test_id")
    url=API_ORIGIN+"/accounts/"+quote(account,safe="")+"/d1/database/"+quote(uid,safe="")+"/query"
    body=json.dumps({"sql":SQL,"params":[SYMBOL,"5",VERSION,a,b,cutoff,LIMIT+1]}).encode()
    req=Request(url,data=body,method="POST",headers={"Authorization":"Bearer "+token,
        "Accept":"application/json","Content-Type":"application/json"})
    try:
        with build_opener(NoRedirect()).open(req,timeout=15) as r:
            raw=r.read(MAX_RESPONSE_BYTES+1)
        if len(raw)>MAX_RESPONSE_BYTES:
            raise AuditError("fold_response_cap")
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise AuditError("fold_select_failed") from None

def read_fold(account_id,token,*,fold,now,explicit=False):
    if explicit is not True:
        raise AuditError("explicit_fold_read_required")
    end,pages=plan(fold,now)
    account=require_account_id(account_id); token=require_account_token(token)
    base="/accounts/"+quote(account,safe="")+"/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    windows=[]; reads=0
    for a,b in pages:
        rows,stats=unpack(fetch_page(account,ids[TEST_DB],token,a,b,end-1))
        if stats[0] is None or stats[1]!=0:
            raise AuditError("fold_query_usage_unknown")
        reads+=stats[0]
        if reads>MAX_READS_OBSERVED:
            raise AuditError("fold_observed_read_budget_exceeded")
        if any(type(r) is not dict or type(r.get("received_at_ms")) is not int or
               r["received_at_ms"]>=end for r in rows):
            raise AuditError("fold_future_receipt")
        windows.append({"start_ms":a,"end_ms":b,"rows":rows})
    # Query receipt cutoff end-1. Evaluate at closed boundary with validated rows.
    report=assemble(windows,as_of_ms=end)
    return {"schema":"remura.tv.cvd.fold.collection.preview.v1","fold":fold,
            "protocol_sha256":digest(),"fold_result":report["prospective_folds"]["folds"][fold],
            "coverage":{"requested_slots":report["requested_slots"],"valid_unique_bars":report["valid_unique_bars"],
                        "missing_requested_slots":report["missing_requested_slots"]},
            "collection":{"inventory_requests":1,"select_requests":len(pages),"query_rows_read":reads,
                          "query_rows_written":0,"account_quota_utilization":None,
                          "scope":"THIS_RUN_ONLY_NOT_ACCOUNT_BILLING","raw_persisted":False,"raw_logged":False,
                          "snapshot_atomic_across_pages":False},
            "scientific_admission":False,"edge":"NOT_ESTABLISHED","orders_enabled":False}

def main():
    import argparse,os,time
    p=argparse.ArgumentParser()
    p.add_argument("--live-read",action="store_true",required=True)
    p.add_argument("--fold",choices=[x[0] for x in FOLDS],required=True)
    a=p.parse_args()
    try:
        r=read_fold(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                    fold=a.fold,now=time.time_ns()//1000000,explicit=True)
        print("REMURA_CVD_TEST_FOLD="+json.dumps(r,sort_keys=True,allow_nan=False))
        return 0
    except Exception:
        print("REMURA_CVD_TEST_FOLD=UNKNOWN_FAIL_CLOSED")
        return 2
if __name__=="__main__":
    raise SystemExit(main())
