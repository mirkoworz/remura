#!/usr/bin/env python3
# REMURA TV v0.8.192 LAB — inspect CVD TEST implementation, not live state.
"""Source-locked, no-provider-calls preparation of the 23 Nov prospective gate.

The historical TEST deployment described in PILOT-CVD-EURUSD-RUNBOOK.md and
stored TEST receipts prove prior activity, not present TradingView/Worker state.
Manual assertions, even every answer TRUE, are never an independent audit.
This module cannot set ingest flags, build/deploy a Worker, or read Secrets.
"""
from __future__ import annotations
from datetime import timedelta
from pathlib import Path
import re

from holdout_freeze_v0182_lab import ROOT,guard,git_blob_hash,H1_START,H2_START
from holdout_evidence_ledger_v0187_lab import instant
from checked_in_receipt_reality_v0191_lab import audit_checked_in

SCHEMA="remura.tv.cvd.test_runtime_evidence_gap.v0192.lab"
BASE=ROOT/"tradingview/delta-peaks/gateway-lab"
LOCKED={
    "worker_cvd_candidate.mjs":"3562a38e224552a8a67987c4bb043dd8200c6355",
    "worker.mjs":"bfd5e228c962110b80acc9e6d74bd5ebd28d92bd",
}
MAX_BYTES=30000
MAX_AGE_SECONDS=3600
FIELDS=frozenset(("observed_utc","worker_flag_claim","cvd_flag_claim",
                  "correct_test_d1_claim","tradingview_alert_active_claim",
                  "recent_cvd_receipts_claim","independent_receipt_verified_claim",
                  "m5_coverage_verified_claim","price_comparator_verified_claim",
                  "spot_futures_mapping_verified_claim","free_margin_verified_claim"))
FLAGS=frozenset(("ON","OFF","UNKNOWN"))
BOOL_FIELDS=FIELDS-{"observed_utc","worker_flag_claim","cvd_flag_claim",
                    "recent_cvd_receipts_claim"}
class LiveGateError(ValueError):
    pass

def inspect_checked_in_sources(*, source_dir=BASE):
    guard()
    if not isinstance(source_dir,Path):
        raise LiveGateError("path_required")
    errors=[]
    sources={}
    for name,pinned in LOCKED.items():
        try:
            path=source_dir/name
            if path.is_symlink() or not path.is_file():
                raise LiveGateError("missing_or_linked_source")
            data=path.read_bytes()
            if len(data)==0 or len(data)>MAX_BYTES or git_blob_hash(data)!=pinned:
                raise LiveGateError("source_blob_drift")
            sources[name]=data.decode("utf-8")
        except (LiveGateError,OSError,UnicodeError,ValueError):
            errors.append(name+"_NOT_PINNED")
    if len(sources)==len(LOCKED):
        candidate=sources["worker_cvd_candidate.mjs"]
        prior=sources["worker.mjs"]
        for needle in (
            'env?.INGEST_ENABLED === "true"',
            'env.CVD_PREVIEW_ENABLED !== "true"',
            "validateCvdEnvelope(payload, receivedMs)",
            "INSERT OR IGNORE INTO tv_flow_events",
            "SELECT raw_json FROM tv_flow_events WHERE event_key = ?",
            'reply(409, "conflicting_retry")',
            "url.pathname.match(",
            "WEBHOOK_TOKEN_SHA256",
            "INGEST_RATE_LIMITER",
            "TELEMETRY_DB",
        ):
            if needle not in candidate:
                errors.append("CVD_CANDIDATE_GUARD_MISSING")
        if 'env.CVD_PREVIEW_ENABLED !== "true"' in prior:
            errors.append("ROLLBACK_CANDIDATE_NOT_LEGACY")
        if "INSERT OR IGNORE INTO tv_flow_events" not in prior:
            errors.append("LEGACY_RECEIVER_SOURCE_NOT_RECOGNIZED")
    receipt=audit_checked_in()
    if receipt["status"]!="VERIFIED_PINNED_HISTORICAL_TEST_METADATA_ONLY":
        errors.append("PINNED_HISTORICAL_TEST_RECEIPTS_DRIFT")
    return {
        "schema":SCHEMA,
        "source_status":"PINNED_TEST_GATEWAY_SOURCES_CONSISTENT"
                        if not errors else "SOURCE_REVIEW_REQUIRED",
        "issues":sorted(set(errors)),
        "checked_in_test_receiver_files":len(LOCKED),
        "historical_test_receipt_bars":receipt["pinned_test_window_bars"],
        "historical_gateway_deploy_documented":"2026-11-14",
        "historical_deploy_verification_run":"43595646049",
        "actual_worker_deployed_source_sha":"UNKNOWN_NOT_QUERIED",
        "current_ingest_state":"UNKNOWN_NOT_QUERIED",
        "current_cvd_flag":"UNKNOWN_NOT_QUERIED",
        "real_tv_alert_running":"UNKNOWN_NOT_QUERIED",
        "current_d1_test_rows":"UNKNOWN_NOT_QUERIED",
        "external_first_seen_verified":False,
        "market_coverage_verified":False,
        "cloudflare_quota_free_margin_verified":False,
        "historical_test_is_not_future_holdout":True,
        "can_activate_anything":False,
        "provider_calls":0,"d1_requests":0,"secrets_used":False,
        "live_alpha_go":False,
    }

def review_manual_claims(claims=None, *, evaluated_utc, source_dir=BASE):
    """Operator-claimed checklist; never returns GO or calls providers."""
    check=inspect_checked_in_sources(source_dir=source_dir)
    when=instant(evaluated_utc)
    unknown=set()
    if claims is None:
        unknown.add("LIVE_CHECKPOINT_NOT_COLLECTED")
    elif type(claims) is not dict or set(claims)!=FIELDS:
        raise LiveGateError("required_claim_schema_incomplete")
    else:
        observed=instant(claims["observed_utc"])
        if observed>when or (when-observed).total_seconds()>MAX_AGE_SECONDS:
            unknown.add("STALE_OR_FUTURE_MANUAL_CHECKPOINT")
        if any(type(claims[k]) is not bool for k in BOOL_FIELDS):
            raise LiveGateError("tri_state_or_boolean_required")
        if type(claims["recent_cvd_receipts_claim"]) is not int or claims["recent_cvd_receipts_claim"]<0:
            raise LiveGateError("receipt_count_claim_invalid")
        if claims["worker_flag_claim"] not in FLAGS or claims["cvd_flag_claim"] not in FLAGS:
            raise LiveGateError("flag_claim_invalid")
        if claims["worker_flag_claim"]!="ON":
            unknown.add("INGEST_NOT_CLAIMED_ON")
        if claims["cvd_flag_claim"]!="ON":
            unknown.add("CVD_NOT_CLAIMED_ON")
        if claims["recent_cvd_receipts_claim"]==0:
            unknown.add("NO_RECENT_CVD_RECEIPTS_CLAIMED")
        for field in BOOL_FIELDS:
            if claims[field] is not True:
                unknown.add(field.upper()+"_NOT_CLAIMED")
    if check["source_status"]!="PINNED_TEST_GATEWAY_SOURCES_CONSISTENT":
        unknown.add("CHECKED_IN_SOURCES_DRIFT")
    # Even a perfect manual checklist is NOT independent Cloudflare/provider
    # evidence; only a separately consented live READ could verify some gaps.
    unknown.add("MANUAL_CLAIMS_NOT_INDEPENDENT_ATTESTATION")
    unknown.add("NO_SIGNED_SOURCE_RECEIPT_OR_VERIFIED_MARKET_M5_DENOMINATOR")
    unknown.add("NO_PROVIDER_VALIDATED_CURRENT_CAPTURE")
    return {
        "schema":SCHEMA,
        "status":"NO_GO_PROSPECTIVE_HOLDOUT_UNVERIFIED",
        "as_of_utc":evaluated_utc,
        "historical_test_bars":check["historical_test_receipt_bars"],
        "source_status":check["source_status"],
        "blocking_reasons":sorted(unknown),
        "holdout1_start_utc":H1_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "holdout1_end_exclusive_utc":H2_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_manual_claims_are_not_provider_proof":True,
        "scientific_admission":False,
        "live_alpha_go":False,
        "capture_auto_enabled":False,
        "cloudflare_called":False,"new_costs_incurred":False,
        "next_verification_requires_separate_owner_consent":True,
    }
