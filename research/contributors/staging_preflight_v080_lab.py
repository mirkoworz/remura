# REMURA Contributors v0.80 LAB — 21/11/2026 17:22 CET
# Offline-only merging of D1 adaptive dataset, Access user inventory, prior quota
# monitor evidence and irreversible staging blockers. No Cloudflare APIs or secrets.
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from free_quota_evidence_v079_lab import classify as classify_quota
from access_seat_inventory_v080_lab import inventory_summary
from d1_two_day_visibility_v080_lab import inspect_window


REQUIRED_MANUAL_GATES = (
    "CONFIRM_ACCESS_FREE_PLAN_AND_BILLABLE_SEATS",
    "CONFIRM_D1_ACCOUNT_DAILY_ROWS_CURRENT",
    "CONFIRM_DIRECT_WORKER_ACCESS_CONTEXT",
    "APPROVE_ISOLATED_STAGING_D1_AND_SECRET_HANDLING",
    "APPROVE_PRIVATE_ACCESS_POLICY_AND_TEST_IDENTITIES",
    "VERIFY_SAFARI_LOGIN_LOGOUT_REVOKE",
    "AUTHORIZE_STAGING_DEPLOY_SEPARATELY",
)


def build_preflight(*, existing_monitor_logs: dict[str, str],
                    access_users_pages: object,
                    d1_today: object,
                    d1_yesterday: object,
                    now_utc: datetime) -> dict[str, Any]:
    """All inputs must be explicit; this function CANNOT contact the provider."""
    # IMPORTANT: do not substitute an access_seat boolean as a dashboard
    # billing attestation; the v0.79 classifier remains NO_GO in that case.
    budget = classify_quota(existing_monitor_logs, now_utc=now_utc,
                            access_seats_attested=False).public_dict()
    access = inventory_summary(access_users_pages)
    d1 = inspect_window(d1_today, d1_yesterday, utc_day=now_utc.date())
    blockers = list(REQUIRED_MANUAL_GATES)
    if budget["d1_daily"] != "ADAPTIVE_ESTIMATE_PRESENT":
        blockers.append("D1_DAILY_DATASET_MISSING_OR_UNVERIFIED")
    if budget["workers_daily"] != "ADAPTIVE_ESTIMATE_PRESENT":
        blockers.append("WORKERS_DAILY_DATASET_MISSING_OR_UNVERIFIED")
    if budget["d1_storage"] != "METADATA_SNAPSHOT_PRESENT":
        blockers.append("D1_ACCOUNT_METADATA_UNVERIFIED")
    if access["status"] in ("UNKNOWN_INCOMPLETE_OR_INVALID", "EMPTY_NOT_SEAT_ATTESTATION"):
        blockers.append("ACCESS_USERS_INVENTORY_UNKNOWN_OR_EMPTY")
    if d1["status"] in ("UNKNOWN_OR_INVALID_DATASET", "TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO",
                       "BOTH_DAYS_EMPTY_NOT_ZERO"):
        blockers.append("D1_TWO_DAY_ADAPTIVE_DATASET_INCOMPLETE")
    # No automatic GO, regardless of user-supplied inputs.
    return {
        "schema": "remura.contributors.staging_preflight.v080.lab",
        "version": "0.80",
        "updated_local": "21/11/2026 17:22 CET",
        "mode": "OFFLINE_REVIEW_ONLY",
        "decision": "NO_GO",
        "automatic_deploy_allowed": False,
        "production_budget_attested": False,
        "cloudflare_access_real_session_attested": False,
        "d1_daily": budget["d1_daily"],
        "workers_daily": budget["workers_daily"],
        "d1_storage": budget["d1_storage"],
        "access_inventory_status": access["status"],
        "access_authenticated_flags": access["access_authenticated_flags"],
        "access_billing_seats_available": None,
        "d1_window_status": d1["status"],
        "pending_gates": blockers,
    }
