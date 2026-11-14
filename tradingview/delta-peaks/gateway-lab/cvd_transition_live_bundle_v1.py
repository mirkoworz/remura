#!/usr/bin/env python3
# REMURA v0.8.65 LAB — 14/11/2026 CET
"""Prepare and recheck the isolated TEST transition. No remote mutations here."""
import argparse,json,os,shutil
from pathlib import Path
from cloudflare_d1_readonly_audit import api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from gateway_off_candidate_v1 import choose_candidate_namespace,make_candidate,EXAMPLE
from bootstrap_postdeploy_audit_v1 import api_get
from cvd_transition_bundle_v1 import inspect_state,build_pair,StopUnsafe,HERE,CVD_FLAG
from copy import deepcopy

OPERATIONS=("DEPLOY_CVD_TEST","ROLLBACK_LEGACY_TEST","STOP_CVD_TEST")
ON="TEST_GATEWAY_ON_WITH_HASH_SECRET"
OFF="TEST_GATEWAY_OFF_WITH_HASH_SECRET"

def inspect(account,read_token,editor):
    account=require_account_id(account)
    read_token=require_account_token(read_token)
    if type(editor) is not str or len(editor)<24 or any(c.isspace() for c in editor):
        raise StopUnsafe("editor_missing")
    ids=inspect_verified_inventory(api_request("GET",f"/accounts/{account}/d1/database?page=1&per_page=100",read_token))
    state,mode=inspect_state(api_get(account,editor,"/settings"),test_uuid=ids[TEST_DB],namespace=choose_candidate_namespace(account))
    return state,mode,make_candidate(json.loads(EXAMPLE.read_text()),ids,account)

def gate(operation,state,mode,*,post=False):
    if operation not in OPERATIONS:
        raise StopUnsafe("unknown_operation")
    if post:
        expected={"DEPLOY_CVD_TEST":(ON,"CVD_TRUE"),"ROLLBACK_LEGACY_TEST":(ON,"LEGACY"),
                  "STOP_CVD_TEST":(OFF,"LEGACY")}[operation]
        if (state,mode)!=expected:
            raise StopUnsafe("unexpected_post_state")
    elif operation=="DEPLOY_CVD_TEST":
        if (state,mode)!=(ON,"LEGACY"):
            raise StopUnsafe("not_legacy_on")
    elif operation=="ROLLBACK_LEGACY_TEST":
        if state!=ON or mode not in ("CVD_TRUE","CVD_FALSE"):
            raise StopUnsafe("not_cvd_on")
    elif state not in (ON,OFF) or mode not in ("CVD_TRUE","CVD_FALSE","LEGACY"):
        raise StopUnsafe("unknown_stop_state")

def prepare(operation,account,read_token,editor,runner):
    state,mode,cfg=inspect(account,read_token,editor)
    gate(operation,state,mode)
    folders=build_pair(cfg,runner,enable_cvd=operation!="STOP_CVD_TEST")
    return folders,cfg

def verify_target(operation,cfg,runner,target):
    root=Path(runner)
    folder=Path(target)
    if not root.is_absolute() or not folder.is_absolute() or folder.parent!=root or not folder.name.startswith("remura-test-off-") or folder.is_symlink() or not folder.is_dir():
        raise StopUnsafe("bad_private_target")
    if {x.name for x in folder.iterdir()}!={"worker.mjs","wrangler.json"}:
        raise StopUnsafe("bad_bundle_files")
    expected=deepcopy(cfg)
    expected.pop("$comment")
    expected["vars"]={"INGEST_ENABLED":"false" if operation=="STOP_CVD_TEST" else "true"}
    source="worker.mjs"
    if operation=="DEPLOY_CVD_TEST":
        expected["vars"][CVD_FLAG]="true"
        source="worker_cvd_candidate.mjs"
    for path in (folder/"wrangler.json",folder/"worker.mjs"):
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600:
            raise StopUnsafe("bundle_file_not_private")
    if json.loads((folder/"wrangler.json").read_text())!=expected or (folder/"worker.mjs").read_bytes()!=(HERE/source).read_bytes():
        raise StopUnsafe("bundle_changed_since_prepare")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("operation",choices=OPERATIONS)
    parser.add_argument("phase",choices=("prepare","precheck","postcheck"))
    args=parser.parse_args()
    creds=(os.getenv("REMURA_CF_ACCOUNT_ID",""),os.getenv("REMURA_CF_D1_READ_TOKEN",""),os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN",""))
    folders=()
    try:
        if args.phase=="prepare":
            runner=os.getenv("RUNNER_TEMP","")
            envfile=os.getenv("GITHUB_ENV","")
            if not runner or not envfile or not Path(envfile).is_file():
                raise StopUnsafe("private_runner_required")
            folders,cfg=prepare(args.operation,*creds,runner)
            print("::add-mask::"+cfg["d1_databases"][0]["database_id"])
            print("::add-mask::"+cfg["ratelimits"][0]["namespace_id"])
            target=folders[0] if args.operation=="DEPLOY_CVD_TEST" else folders[1]
            with open(envfile,"a",encoding="utf-8") as f:
                f.write(f"REMURA_CVD_CANDIDATE={folders[0]}\nREMURA_CVD_ROLLBACK={folders[1]}\nREMURA_CVD_TARGET={target}\n")
            print("REMURA_CVD_LIVE_BUNDLES=PRIVATE_READY")
        else:
            state,mode,cfg=inspect(*creds)
            gate(args.operation,state,mode,post=args.phase=="postcheck")
            if args.phase=="precheck":
                verify_target(args.operation,cfg,os.getenv("RUNNER_TEMP",""),os.getenv("REMURA_CVD_TARGET",""))
            print("REMURA_CVD_TRANSITION_"+args.phase.upper()+"=SETTINGS_VERIFIED")
    except Exception as exc:
        # Only allow fixed, known internal reason codes, never API text or paths.
        allowed={"bad_private_target","bad_bundle_files","bundle_file_not_private",
                 "bundle_changed_since_prepare","not_legacy_on","not_cvd_on",
                 "unknown_stop_state","unexpected_post_state","editor_missing",
                 "private_runner_required","cvd_flag_invalid","cvd_state_not_known"}
        reason=str(exc) if isinstance(exc,StopUnsafe) and str(exc) in allowed else "UNCLASSIFIED_SANITIZED"
        print("REMURA_CVD_BLOCK_REASON="+reason)
        for folder in folders:
            shutil.rmtree(folder,ignore_errors=True)
        print("REMURA_CVD_TRANSITION=BLOCKED_FAIL_CLOSED")
        return 2
    print("TARGET=TEST_ONLY; REMOTE_MUTATION_BY_THIS_SCRIPT=NONE; EDGE_TRAFFIC=UNVERIFIED")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
