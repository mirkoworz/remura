# REMURA Contributors v0.92 LAB — 21/11/2026 Europe/Rome
"""Manual aggregate-only budget preflight for a future 1–2 person pilot.

Does not call Cloudflare, inspect credentials, certify account billing, grant
staging, or substitute for explicit authorization. 2026 Free limits below are
PLANNING constants and must be reconfirmed in the live provider dashboard.
Missing/UNKNOWN usage is never zero.
"""
from __future__ import annotations
from datetime import datetime, timezone
import re

SCHEMA = "remura.contributors.manual_free_gate.v092.lab"
SOURCE = "MANUAL_CLOUDFLARE_DASHBOARD_AGGREGATES"
# Nominal Workers/D1 Free planning ceilings, NOT an observed account balance.
NOMINAL_LIMITS = {
    "requests_today": 100_000,
    "rows_read_today": 5_000_000,
    "rows_written_today": 100_000,
    "d1_storage_bytes": 5 * 1024 ** 3,
    "d1_database_count": 10,
}
INTERNAL_BUDGET_PERCENT = 70
MAX_AGE_SECONDS = 3600
REQUIRED = frozenset({
    "source", "observed_utc", "daily_utc",
    "free_workers_confirmed", "free_d1_confirmed", "access_free_confirmed",
    "coverage_all_workers", "coverage_all_d1_databases",
    "requests_today", "rows_read_today", "rows_written_today",
    "d1_storage_bytes", "d1_database_count",
    "access_seats_in_use", "access_seats_limit",
})
PLAN = frozenset({
    "pilot_users", "extra_requests", "extra_rows_read",
    "extra_rows_written", "extra_storage_bytes", "extra_databases",
})
DELTA = {
    "requests_today": "extra_requests",
    "rows_read_today": "extra_rows_read",
    "rows_written_today": "extra_rows_written",
    "d1_storage_bytes": "extra_storage_bytes",
    "d1_database_count": "extra_databases",
}
STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def timestamp(raw: object) -> datetime:
    if not isinstance(raw, str) or not STAMP.fullmatch(raw):
        raise ValueError("invalid_utc")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_utc") from exc
    if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError("invalid_utc")
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != raw:
        raise ValueError("invalid_utc")
    return dt


def count(x: object) -> bool:
    return type(x) is int and 0 <= x <= 10**12


def result(status: str, reasons: list[str]) -> dict[str, object]:
    return {
        "schema": SCHEMA, "version": "0.92",
        "status": status, "reasons": sorted(set(reasons)),
        "values_retrieved_from_provider": False,
        "provider_account_verified_by_tool": False,
        "billing_and_access_seats_independently_attested": False,
        "nominal_limits_must_be_rechecked": True,
        "daily_usage_unknown_when_missing": True,
        "zero_inferred_from_empty_response": False,
        "cloudflare_api_calls": 0, "d1_sql_calls": 0,
        "secrets_used": False, "users_registered": 0,
        "staging_allowed": False, "deploy_allowed": False,
        "additional_spending_allowed": False,
        "pilot_allowed": False,
    }


def review(aggregates: object, proposed: object, *, now_utc: str) -> dict[str, object]:
    """Conservative evidence-shape/nominal-headroom screen, not an activation gate."""
    try:
        now = timestamp(now_utc)
    except ValueError:
        return result("UNKNOWN_OR_INCOMPLETE", ["invalid_audit_clock"])
    if (type(aggregates) is not dict or set(aggregates) != REQUIRED or
            type(proposed) is not dict or set(proposed) != PLAN):
        return result("UNKNOWN_OR_INCOMPLETE", ["missing_or_unknown_required_fields"])
    errors = []
    if aggregates["source"] != SOURCE:
        errors.append("aggregate_origin_unverified")
    try:
        seen = timestamp(aggregates["observed_utc"])
        if not 0 <= (now - seen).total_seconds() <= MAX_AGE_SECONDS:
            errors.append("stale_or_future_snapshot")
        if seen.strftime("%Y-%m-%d") != aggregates["daily_utc"] or now.strftime("%Y-%m-%d") != aggregates["daily_utc"]:
            errors.append("wrong_utc_day")
    except ValueError:
        errors.append("bad_observation_time")
    for k in ("free_workers_confirmed", "free_d1_confirmed", "access_free_confirmed",
              "coverage_all_workers", "coverage_all_d1_databases"):
        if aggregates[k] is not True:
            errors.append(k + "_unknown_or_false")
    for field in (*NOMINAL_LIMITS, "access_seats_in_use", "access_seats_limit"):
        if not count(aggregates[field]):
            errors.append(field + "_unknown")
    for field in PLAN:
        if not count(proposed[field]):
            errors.append(field + "_unknown")
    if errors:
        return result("UNKNOWN_OR_INCOMPLETE", errors)
    if proposed["pilot_users"] not in (1, 2):
        return result("NO_GO_INTERNAL_BUDGET", ["pilot_size_not_1_or_2"])
    if proposed["extra_requests"] == 0 or proposed["extra_rows_read"] == 0:
        return result("UNKNOWN_OR_INCOMPLETE", ["future_usage_not_planned"])
    if aggregates["access_seats_limit"] == 0 or aggregates["access_seats_in_use"] > aggregates["access_seats_limit"]:
        return result("NO_GO_INTERNAL_BUDGET", ["access_seat_limit_invalid_or_exceeded"])
    if aggregates["access_seats_in_use"] + proposed["pilot_users"] > aggregates["access_seats_limit"]:
        return result("NO_GO_INTERNAL_BUDGET", ["insufficient_access_seats"])
    for name, cap in NOMINAL_LIMITS.items():
        planned = aggregates[name] + proposed[DELTA[name]]
        if name == "d1_database_count":
            if planned > cap:
                errors.append(name + "_nominal_limit")
        elif planned * 100 > cap * INTERNAL_BUDGET_PERCENT:
            errors.append(name + "_internal_70_percent_ceiling")
    if errors:
        return result("NO_GO_INTERNAL_BUDGET", errors)
    return result(
        "MANUAL_SHAPE_AND_PLANNING_HEADROOM_ONLY_NO_GO",
        ["requires_dashboard_recheck_and_separate_user_authorization",
         "manual_values_not_independent_provider_attestation"]
    )
