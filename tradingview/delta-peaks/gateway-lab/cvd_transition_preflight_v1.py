#!/usr/bin/env python3
# REMURA v0.8.63 LAB — 14/11/2026 CET
"""Read-only transition preflight. No deploy, SQL, secret value read or mutation.
Only known TEST Worker settings and the isolated EU D1 identity are queried.
A successful result is NOT authorization, traffic verification or billing proof.
"""
import os
from cloudflare_d1_readonly_audit import api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from gateway_off_candidate_v1 import choose_candidate_namespace
from bootstrap_postdeploy_audit_v1 import api_get
from cvd_transition_bundle_v1 import inspect_state,StopUnsafe

def preflight(account,read_token,editor_token):
    account=require_account_id(account)
    read_token=require_account_token(read_token)
    if type(editor_token) is not str or len(editor_token)<24 or any(c.isspace() for c in editor_token):
        raise StopUnsafe("editor_missing")
    ids=inspect_verified_inventory(api_request("GET",f"/accounts/{account}/d1/database?page=1&per_page=100",read_token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise StopUnsafe("main_alias")
    state,mode=inspect_state(api_get(account,editor_token,"/settings"),test_uuid=ids[TEST_DB],
                            namespace=choose_candidate_namespace(account))
    if state!="TEST_GATEWAY_ON_WITH_HASH_SECRET" or mode!="LEGACY":
        raise StopUnsafe("not_expected_legacy_on")
    return "LEGACY_TEST_ON_VERIFIED_NO_MUTATION"

def main():
    try:
        status=preflight(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),
                         os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN",""))
    except Exception:
        print("REMURA_CVD_TRANSITION_PREFLIGHT=BLOCKED_FAIL_CLOSED")
        return 2
    print("REMURA_CVD_TRANSITION_PREFLIGHT="+status)
    print("TEST_SETTINGS_ONLY=YES; D1_SQL=NO; DEPLOY=NO; EDGE_TRAFFIC=UNVERIFIED; BILLING=UNVERIFIED")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
