#!/usr/bin/env python3
# REMURA v0.8.82 LAB — 14/11/2026 20:28 CET
"""V2 guarded collection, fixed cutoff, same bounded TEST SELECTs.
Guard at each network boundary and before/after local render. No retry.
V1 remains available for offline historical reproducibility.
"""
from urllib.parse import quote
from cvd_private_runtime_preview_v1 import (validate_inputs,plan,preview,MAX_OBSERVED_READS,
    unpack,fetch_page,AuditError,api_request,require_account_id,require_account_token,
    MAIN_DB,TEST_DB,inspect_verified_inventory)
def collect_guarded(core,account_id,token,*,now,explicit=False,private=None,secret=None,
                         retail_root=None,authorized_at=None,guard=None,origin="LOCAL_SNAPSHOT"):
    if explicit is not True or not callable(guard):
        raise AuditError("explicit_runtime_test_read_required")
    validate_inputs(core,private,secret,retail_root,authorized_at)
    pages=plan(now)
    account=require_account_id(account_id); token=require_account_token(token)
    base="/accounts/"+quote(account,safe="")+"/d1/database"
    guard()
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    windows=[]; reads=0
    for a,b in pages:
        guard()
        rows,stats=unpack(fetch_page(account,ids[TEST_DB],token,a,b,now))
        if stats[0] is None or stats[1]!=0:
            raise AuditError("runtime_query_usage_unknown")
        reads+=stats[0]
        if reads>MAX_OBSERVED_READS:
            raise AuditError("runtime_observed_budget_exceeded")
        windows.append({"start_ms":a,"end_ms":b,"rows":rows})
    guard()
    result=preview(core,windows,now=now,origin=origin,private=private,secret=secret,retail_root=retail_root,authorized_at=authorized_at)
    result["collection"]={"target":"EU_D1_TEST_ONLY","inventory_requests":1,"select_requests":len(pages),
        "rows_read":reads,"rows_written":0,"account_quota_utilization":None,
        "snapshot_atomic_across_pages":False,"raw_persisted":False,"raw_logged":False}
    guard()
    return result
