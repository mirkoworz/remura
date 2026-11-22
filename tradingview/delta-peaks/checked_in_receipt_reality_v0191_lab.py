#!/usr/bin/env python3
# REMURA TV v0.8.191 LAB — audit ACTUAL checked-in, sanitized TEST metadata.
"""Read-only repository inventory; NOT a Cloudflare/TradingView status check.

No network, Secrets, D1, request dispatch, market data or activated capture.
Pinned Git blobs make accidental evidence edits visible *inside this checkout*.
Neither Git hash nor GitHub Actions run number proves original first-seen.
A snapshot of checked-in TEST evidence cannot prove absence of external data.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from holdout_freeze_v0182_lab import ROOT, guard, git_blob_hash, H1_START

SCHEMA="remura.tv.checked_in_test_reality.v0191.lab"
M5=300_000
EVIDENCE=ROOT/"tradingview/delta-peaks/evidence"
WORKFLOWS=ROOT/".github/workflows"
MAX_BYTES=100_000

PINNED={
    "fx_first_receipt_20261116.json":"e163dbb141a33c812c3b675c342377d24a84c42c",
    "fx_second_receipt_20261116.json":"dcf911b3e5bb3903d60f36cf0a1314a015a5e052",
    "fx_third_receipt_20261118.json":"ba82c13a61e467112257978a5a287e792ea85148",
    "fx_fourth_receipt_20261118.json":"f5880168dc6f019cc0dff01f5e5d2e4bd71abb8a",
}
# Exactly the 16 pre-existing TV workflows seen on main at the V10 inspection.
# This is NOT an inventory of Cloudflare schedules, user TradingView alerts,
# provider delivery, or whether workflow_dispatch has been used.
TV_WORKFLOWS=(
    "remura-tv-bootstrap-test-only-manual.yml",
    "remura-tv-btc-analytic-readonly-manual.yml",
    "remura-tv-btc-weekend-test-manual.yml",
    "remura-tv-cvd-analytic-readonly-manual.yml",
    "remura-tv-cvd-batch-readonly-manual.yml",
    "remura-tv-cvd-fold-readonly-manual.yml",
    "remura-tv-cvd-transition-manual.yml",
    "remura-tv-emergency-stop-test-manual.yml",
    "remura-tv-fx-analytic-readonly-manual.yml",
    "remura-tv-gateway-test-off-manual.yml",
    "remura-tv-rollback-test-manual.yml",
    "remura-tv-test-first-receipt-readonly.yml",
    "remura-tv-test-hash-secret-manual.yml",
    "remura-tv-test-ingest-on-manual.yml",
    "remura-tv-test-rotate-hash-manual.yml",
    "remura-tv-test-worker-editor-readonly.yml",
)
DISPATCH=re.compile(r"(?m)^\s+workflow_dispatch\s*:")
SCHEDULE=re.compile(r"(?m)^\s+schedule\s*:")
ON=re.compile(r"(?m)^on\s*:")
class InventoryError(ValueError):
    pass

def _strict_pairs(pairs):
    val={}
    for key,value in pairs:
        if key in val:raise InventoryError("duplicate_json_key")
        val[key]=value
    return val

def _read(path,base):
    if path.parent!=base or path.is_symlink() or not path.is_file():
        raise InventoryError("source_file_absent_or_symlink")
    if path.stat().st_size>MAX_BYTES or path.stat().st_size<8:
        raise InventoryError("source_size_invalid")
    return path.read_bytes()

def _utc(ms):
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def audit_checked_in(*, evidence_dir=EVIDENCE, workflow_dir=WORKFLOWS):
    """Only supplied local repository paths, no direct API calls."""
    guard()
    if not isinstance(evidence_dir,Path) or not isinstance(workflow_dir,Path):
        raise InventoryError("path_object_required")
    issues=[]
    records=[]
    runs=set()
    windows=[]
    for name,expected in PINNED.items():
        try:
            raw=_read(evidence_dir/name,evidence_dir)
            if git_blob_hash(raw)!=expected:
                raise InventoryError("source_git_blob_drift")
            item=json.loads(raw,object_pairs_hook=_strict_pairs)
            report=item["report"]
            collection=report["collection"]
            start,end,observed=(item[k] for k in ("start_ms","end_ms","observed_ms"))
            if any(type(x) is not int for x in (start,end,observed,item["run_id"])):
                raise InventoryError("noninteger_receipt_metadata")
            if not (0<start<=end<=observed and start%M5==0 and end%M5==0):
                raise InventoryError("invalid_or_backdated_receipt_window")
            if item["run_id"] in runs:
                raise InventoryError("duplicate_test_run_id")
            if not (report["requested_slots"]==report["valid_unique_bars"]+
                    report["missing_requested_slots"] and
                    report["requested_slots"]==(end-start)//M5+1 and
                    report["duplicate_rows"]==0):
                raise InventoryError("test_window_count_mismatch")
            if (report["symbol"]!="FX:EURUSD" or
                    collection["target"]!="EU_D1_TEST_ONLY" or
                    collection["account_quota_utilization"] is not None or
                    report["scope"]!="REQUESTED_SLOTS_NOT_MARKET_CALENDAR" or
                    report["conflict_ledger_available"] is not False or
                    report["independent_provenance"] is not False or
                    report["scientific_admission"] is not False or
                    report["orders_enabled"] is not False):
                raise InventoryError("test_scope_or_attestation_claim_changed")
            if datetime.fromtimestamp(end/1000,timezone.utc)>=H1_START:
                raise InventoryError("pinned_test_receipt_in_holdout")
            runs.add(item["run_id"])
            windows.append((start,end))
            records.append({"filename":name,"run_id":item["run_id"],
                            "window_start_utc":_utc(start),"window_end_utc":_utc(end),
                            "source_is_test":True,"requested_slots":report["requested_slots"],
                            "unique_bars":report["valid_unique_bars"],
                            "missing_slots_in_requested_window":report["missing_requested_slots"],
                            "external_first_seen_verified":False})
        except (InventoryError,KeyError,TypeError,ValueError,UnicodeError,OverflowError,
                OSError,AttributeError) as exc:
            issues.append(name+":"+type(exc).__name__)
    if any(a[1]>=b[0] for a,b in zip(sorted(windows),sorted(windows)[1:])):
        issues.append("overlapping_pinned_test_windows")
    manual=scheduled=unknown=0
    for name in TV_WORKFLOWS:
        try:
            text=_read(workflow_dir/name,workflow_dir).decode("utf-8")
            if not ON.search(text):
                raise InventoryError("workflow_missing_on")
            has_schedule=bool(SCHEDULE.search(text))
            scheduled+=int(has_schedule)
            manual+=int(bool(DISPATCH.search(text)) and not has_schedule)
        except (InventoryError,OSError,UnicodeError):
            issues.append(name+":workflow_unverified")
            unknown+=1
    if len(records)!=len(PINN):
        issues.append("checked_in_evidence_inventory_incomplete")
    if scheduled:
        issues.append("schedule_present_in_snapshot_requires_external_review")
    if unknown:
        issues.append("workflow_inventory_incomplete")
    total=sum(x["unique_bars"] for x in records)
    last=max((x["window_end_utc"] for x in records),default=None)
    return {
        "schema":SCHEMA,
        "status":("QUARANTINE_SOURCE_OR_WORKFLOW_DRIFT" if issues
                  else "VERIFIED_PINNED_HISTORICAL_TEST_METADATA_ONLY"),
        "issues":sorted(set(issues)),
        "pinned_test_receipts_expected":len(PINN),
        "pinned_test_receipts_read":len(records),
        "pinned_test_window_bars":total,
        "last_pinned_test_window_close_utc":last,
        "pinned_test_windows":sorted(records,key=lambda x:x["window_start_utc"]),
        "github_main_tv_workflow_names_checked":len(TV_WORKFLOWS),
        "workflow_dispatch_without_schedule_in_checkout":manual,
        "workflows_with_schedule_in_checkout":scheduled,
        "workflows_unknown_in_checkout":unknown,
        "pinned_receipts_in_holdout":0 if not issues else None,
        "pinned_receipts_outside_test_files_not_inspected":True,
        "real_cloudflare_worker_or_alert_status": "UNKNOWN_NOT_QUERIED",
        "full_market_m5_denominator":None,
        "current_cvd_capture_operational":None,
        "provider_publication_or_first_seen_verified":False,
        "evidence_independently_attested":False,
        "historical_test_not_promoted_to_holdout":True,
        "live_alpha_go":False,
        "next_action":"OBTAIN_AUTHORIZED_REAL_PROSPECTIVE_CAPTURE_AND_INDEPENDENT_RECEIPT",
        "cloudflare_api_calls":0,"github_api_calls_by_script":0,
        "d1_calls":0,"secrets_used":False,"deploy_performed":False,
    }
