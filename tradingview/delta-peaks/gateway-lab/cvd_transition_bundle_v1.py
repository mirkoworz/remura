#!/usr/bin/env python3
# REMURA v0.8.62 LAB — 14/11/2026 12:52 CET
"""Offline build and state guards for a future CVD TEST transition.
No deploy, live API, credentials, database changes or auto-activation.
Runtime configuration still requires fresh authenticated metadata and owner approval.
"""
from copy import deepcopy
from pathlib import Path
import argparse,json,os,shutil,tempfile
from predeploy_test_manifest_guard_v1 import verify_manifest,ManifestError
from prepare_test_off_bundle_v1 import create_ephemeral_bundle
from emergency_stop_test_guard_v1 import inspect_before_stop,StopUnsafe
from cloudflare_d1_readonly_audit import AuditError

HERE=Path(__file__).resolve().parent
CVD_FLAG="CVD_PREVIEW_ENABLED"

def inspect_state(payload,*,test_uuid,namespace):
    # Old emergency guard accepts at most four bindings; recognize only our
    # exact fifth plain-text flag, then run the original identity checks.
    if not isinstance(payload,dict) or not isinstance(payload.get("result"),dict):
        raise StopUnsafe("unknown_settings")
    view=deepcopy(payload)
    bindings=view["result"].get("bindings")
    if not isinstance(bindings,list):
        raise StopUnsafe("unknown_bindings")
    flags=[b for b in bindings if isinstance(b,dict) and b.get("name")==CVD_FLAG]
    if not flags:
        return inspect_before_stop(payload,test_uuid=test_uuid,namespace=namespace),"LEGACY"
    if len(flags)!=1 or flags[0].get("type")!="plain_text" or flags[0].get("text") not in ("true","false"):
        raise StopUnsafe("cvd_flag_invalid")
    view["result"]["bindings"]=[b for b in bindings if b is not flags[0]]
    state=inspect_before_stop(view,test_uuid=test_uuid,namespace=namespace)
    if state not in ("TEST_GATEWAY_ON_WITH_HASH_SECRET","TEST_GATEWAY_OFF_WITH_HASH_SECRET"):
        raise StopUnsafe("cvd_state_not_known")
    return state,"CVD_"+flags[0]["text"].upper()

def build_pair(off,runner_temp,*,enable_cvd=False):
    """Build candidate and rollback in distinct private folders.
    Input must be a structurally resolved OFF TEST manifest.
    This function does not attest its IDs; CI uses synthetic IDs only.
    """
    if type(enable_cvd) is not bool or verify_manifest(off)!="STRUCTURALLY_READY_OFFLINE_ONLY":
        raise AuditError("unsafe_bundle_inputs")
    folders=[]
    try:
        for name,source in (("candidate","worker_cvd_candidate.mjs"),("rollback","worker.mjs")):
            folder=create_ephemeral_bundle(off,runner_temp,source=HERE/source)
            folders.append(folder)
            runtime=deepcopy(off)
            runtime.pop("$comment")
            # Only the future explicitly approved activation path may set ON.
            # CI always builds with both ingestion and CVD OFF.
            runtime["vars"]={"INGEST_ENABLED":"true" if enable_cvd else "false"}
            if name=="candidate":
                runtime["vars"][CVD_FLAG]="true" if enable_cvd else "false"
            # Rollback includes no CVD flag and uses exact prior legacy code.
            path=folder/"wrangler.json"
            path.write_text(json.dumps(runtime,separators=(",",":"))+"\n",encoding="utf-8")
            if json.loads(path.read_text())!=runtime or path.stat().st_mode & 0o777 != 0o600:
                raise AuditError("private_manifest_mismatch")
            if (folder/"worker.mjs").read_bytes()!=(HERE/source).read_bytes():
                raise AuditError("source_mismatch")
        return tuple(folders)
    except BaseException:
        for folder in folders:
            shutil.rmtree(folder,ignore_errors=True)
        raise

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--synthetic-dry-run",action="store_true",required=True)
    parser.add_argument("--outdir",required=True)
    args=parser.parse_args()
    root=Path(args.outdir)
    if not root.is_absolute() or root.exists() or not root.parent.is_dir() or root.parent.is_symlink():
        raise SystemExit("synthetic_output_must_be_new_absolute_directory")
    root.mkdir(mode=0o700)
    cfg=json.loads((HERE/"wrangler.webhook-test.EXAMPLE.json").read_text())
    cfg["d1_databases"][0]["database_id"]="00000000-0000-4000-8000-000000000002"
    cfg["ratelimits"][0]["namespace_id"]="812345678901"
    try:
        candidate,rollback=build_pair(cfg,str(root))
        candidate.rename(root/"candidate")
        rollback.rename(root/"rollback")
    except BaseException:
        shutil.rmtree(root,ignore_errors=True)
        raise
    print("REMURA_CVD_AND_ROLLBACK_BUNDLES=SYNTHETIC_ONLY; INGEST=OFF; CVD=OFF; NO_DEPLOY")
if __name__=="__main__":
    main()
