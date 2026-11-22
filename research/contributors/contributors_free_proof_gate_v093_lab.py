# REMURA Contributors v0.93 LAB — Cloudflare Free evidence gap preflight.
# 22 Nov 2026 Europe/Rome. Offline review ONLY, no provider calls or signup.
"""Fail closed on incomplete Free budget evidence. Report 'OK' from old
partial GitHub logs does not mean live seats, quota or billing headroom.

This module cannot establish authenticity of externally supplied counters;
therefore it NEVER grants remote staging, user invitations, or pilot GO.
Only read sanitized known status lines; never copy credentials to output.
"""
from __future__ import annotations
from datetime import datetime
import re

SCHEMA="remura.contributors.free_proof_gate.v093.lab"
RUN_ID=44919682812 # Existing 21 Nov 2026 Actions run read separately.
PINNED_CREATED_UTC="2026-11-21T15:32:05Z"
EXPECTED_KEYS=frozenset((
    "REMURA_CF_ACCOUNT_QUOTA",
    "REMURA_CF_WORKERS_USAGE",
    "REMURA_D1_TEST_STORAGE",
    "REMURA_D1_ACCOUNT_STORAGE",
    "REMURA_DAILY_BUDGET",
))
STATES=frozenset(("OK","WARNING","CRITICAL",
    "UNKNOWN_NO_GRAPHQL_DATA","UNKNOWN_NO_DATA",
    "SKIPPED_NO_ANALYTICS_READ_TOKEN",
    "SKIPPED_MISSING_ANALYTICS_TOKEN"))
BUDGET_STATES=frozenset(("READ_ONLY_COMPLETE","INCOMPLETE_OR_CRITICAL",
                        "INCOMPLETE_MISSING_SECRETS"))
STAMP=re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
KEY_STATUS=re.compile(r"^([A-Z0-9_]+)=([A-Z0-9_]+)$")
REDACTED_RUN_STATUS=(
    "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\n"
    "REMURA_CF_WORKERS_USAGE=OK\n"
    "REMURA_D1_TEST_STORAGE=OK\n"
    "REMURA_D1_ACCOUNT_STORAGE=OK\n"
    "REMURA_DAILY_BUDGET=INCOMPLETE_OR_CRITICAL\n"
)

class EvidenceError(ValueError):
    pass

def utc(iso):
    if type(iso) is not str or not STAMP.fullmatch(iso):
        raise EvidenceError("noncanonical_utc")
    try:
        out=datetime.fromisoformat(iso.replace("Z","+00:00"))
    except ValueError as exc:
        raise EvidenceError("noncanonical_utc") from exc
    if out.strftime("%Y-%m-%dT%H:%M:%SZ")!=iso:
        raise EvidenceError("noncanonical_utc")
    return out

def sanitize_status_lines(text):
    if type(text) is not str or len(text)>4000:
        raise EvidenceError("bounded_sanitized_report_required")
    statuses={}
    for line in text.splitlines():
        if not line:
            continue
        found=KEY_STATUS.fullmatch(line)
        if not found:
            # No credential fields, URLs, or arbitrary log text.
            raise EvidenceError("unexpected_or_unsafe_report_line")
        k,v=found.groups()
        if k not in EXPECTED_KEYS or k in statuses:
            raise EvidenceError("unknown_or_duplicate_status_key")
        if v not in (BUDGET_STATES if k=="REMURA_DAILY_BUDGET" else STATES):
            raise EvidenceError("unknown_status_value")
        statuses[k]=v
    if set(statuses)!=EXPECTED_KEYS:
        raise EvidenceError("incomplete_budget_status_keys")
    return statuses

def evaluate(*, sanitized_status_text, observed_run_id, observed_run_created_utc,
             reviewed_at_utc, plan_verified=False,
             access_seat_headroom_verified=False,
             github_actions_headroom_verified=False,
             independent_provider_receipt_verified=False):
    statuses=sanitize_status_lines(sanitized_status_text)
    if type(observed_run_id) is not int or observed_run_id!=RUN_ID:
        raise EvidenceError("unrecognized_historical_run")
    if observed_run_created_utc!=PINNED_CREATED_UTC:
        raise EvidenceError("historical_run_clock_mismatch")
    t0=utc(observed_run_created_utc)
    t1=utc(reviewed_at_utc)
    if t1<t0:
        raise EvidenceError("review_before_history")
    flags=(plan_verified, access_seat_headroom_verified,
           github_actions_headroom_verified, independent_provider_receipt_verified)
    if any(type(x) is not bool for x in flags):
        raise EvidenceError("boolean_claim_invalid")
    blocks=[]
    sections={}
    for k in sorted(EXPECTED_KEYS-{"REMURA_DAILY_BUDGET"}):
        status=statuses[k]
        sections[k]=status
        if status!="OK":
            blocks.append(k+":"+status)
    overall=statuses["REMURA_DAILY_BUDGET"]
    if overall!="READ_ONLY_COMPLETE":
        blocks.append("DAILY_REPORT_INCOMPLETE")
    if any(value!="OK" for value in sections.values()) and overall=="READ_ONLY_COMPLETE":
        blocks.append("DAILY_SUMMARY_CONFLICT")
    if (t1-t0).total_seconds()>12*3600:
        blocks.append("OBSERVATION_OVER_12H_OLD")
    for flag,meaning in zip(flags,(
        "CURRENT_CF_PLAN_NOT_INDEPENDENTLY_PROVEN",
        "CURRENT_ACCESS_SEAT_HEADROOM_NOT_INDEPENDENTLY_PROVEN",
        "GITHUB_ACTIONS_FREE_HEADROOM_NOT_INDEPENDENTLY_PROVEN",
        "PROVIDER_RECEPTION_NOT_INDEPENDENTLY_ATTESTED",
    )):
        if flag is not True:
            blocks.append(meaning)
    if not blocks:
        # Even all supplied flags are unauthenticated caller claims.
        blocks.append("SELF_REPORTED_GATES_NOT_A_PROVIDER_AUTHORIZATION")
    return {
        "schema":SCHEMA,
        "reviewed_run_id":RUN_ID,
        "run_observation_utc":PINNED_CREATED_UTC,
        "budget_checks":sections,
        "daily_report":overall,
        "status":"NO_GO_REAL_CONTRIBUTOR_PILOT",
        "blocking_reasons":sorted(set(blocks)),
        "confirmed_billable_headroom":False,
        "access_user_seats_currently_verified":False,
        "cloudflare_live_query_performed":False,
        "user_invitation_or_staging_enabled":False,
        "payment_authorized":False,
    }
