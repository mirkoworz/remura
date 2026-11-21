# REMURA Contributors v0.80 LAB — 21/11/2026 17:30 CET (Europe/Rome)
# Evidence dossier: OFFLINE only, no network/Cloudflare credentials/deploy.
"""Cross-check D1 GraphQL presence, monitor provenance, Access seats and pinned sources.

This program does not attest a real account. Its input is untrusted and supplied
offline; even valid data cannot authorize deployment, change Cloudflare or
prove exact billing. Never include identifiers, raw GraphQL, tokens or emails
in the public output.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import re
import sys

from free_quota_evidence_v079_lab import classify, EvidenceError
from staging_source_lock_v079_lab import verify_contract, SourceLockError

UUID = re.compile(r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
MAX_DATABASES = 10
MAX_GROUPS = 10
MAX_AGE = timedelta(hours=4)
MAX_FUTURE_SKEW = timedelta(minutes=2)
MAX_ROWS = 10**12


class DossierError(ValueError):
    pass


def utc_time(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise DossierError("invalid_timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DossierError("invalid_timestamp") from None
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise DossierError("timestamp_not_utc")
    return stamp.astimezone(timezone.utc)


def strict_number(value: object) -> int:
    if type(value) is int and 0 <= value <= MAX_ROWS:
        return value
    if type(value) is float and math.isfinite(value) and value.is_integer() and 0 <= value <= MAX_ROWS:
        return int(value)
    raise DossierError("invalid_counter")


def inventory_ids(items: object) -> frozenset[str]:
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_DATABASES:
        raise DossierError("inventory_unavailable_or_over_free_limit")
    ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"uuid"}:
            raise DossierError("inventory_record_unexpected")
        uid = item["uuid"]
        if not isinstance(uid, str) or not UUID.fullmatch(uid) or uid in ids:
            raise DossierError("inventory_id_invalid_or_duplicate")
        ids.add(uid)
    return frozenset(ids)


def graphql_day(payload: object, day: str, inventory: frozenset[str]) -> tuple[int, int, int]:
    """Returns (group_count, rows_read_estimate, rows_written_estimate).

    This is only a fixture parser; rows are *adaptive estimates* and never
    proof of real usage or billing. Empty groups remain UNKNOWN, not zero.
    """
    if not isinstance(payload, dict) or payload.get("errors") or not isinstance(payload.get("data"), dict):
        raise DossierError("graphql_errors_or_missing_data")
    viewer = payload["data"].get("viewer")
    if not isinstance(viewer, dict):
        raise DossierError("graphql_viewer_missing")
    accounts = viewer.get("accounts")
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        raise DossierError("graphql_account_ambiguous")
    groups = accounts[0].get("d1AnalyticsAdaptiveGroups")
    if not isinstance(groups, list) or len(groups) > MAX_GROUPS:
        raise DossierError("graphql_groups_missing_or_over_cap")
    seen: set[str] = set()
    reads = writes = 0
    for row in groups:
        if not isinstance(row, dict):
            raise DossierError("graphql_row_invalid")
        dims, values = row.get("dimensions"), row.get("sum")
        if not isinstance(dims, dict) or not isinstance(values, dict):
            raise DossierError("graphql_columns_missing")
        uid = dims.get("databaseId")
        if (dims.get("date") != day or not isinstance(uid, str) or
                uid not in inventory or uid in seen):
            raise DossierError("graphql_wrong_day_or_database")
        seen.add(uid)
        reads += strict_number(values.get("rowsRead"))
        writes += strict_number(values.get("rowsWritten"))
        if reads > MAX_ROWS or writes > MAX_ROWS:
            raise DossierError("graphql_aggregate_overflow")
    return len(groups), reads, writes


def triage(today: object, yesterday: object, *, day: str, inventory: object) -> dict[str, object]:
    """Compare two user-supplied read-only GraphQL fixture responses.

    Do not infer exact zero or fill today's missing groups with yesterday's.
    """
    try:
        target = datetime.strptime(day, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise DossierError("invalid_day") from None
    if target.isoformat() != day:
        raise DossierError("invalid_day")
    ids = inventory_ids(inventory)
    current = graphql_day(today, day, ids)
    prior = graphql_day(yesterday, (target - timedelta(days=1)).isoformat(), ids)
    if current[0] == 0:
        state = "TODAY_EMPTY_PRIOR_PRESENT" if prior[0] else "BOTH_DAYS_EMPTY"
        # NO today counts exposed, even if yesterday has counts.
        return {"state": state, "today": "UNKNOWN_NOT_ZERO",
                "prior": "ADAPTIVE_GROUPS_PRESENT" if prior[0] else "UNKNOWN_NOT_ZERO",
                "today_group_count": 0, "prior_group_count": prior[0],
                "usage_attested": False}
    return {"state": "TODAY_GROUPS_PRESENT_OFFLINE_ONLY",
            "today": "ADAPTIVE_GROUPS_PRESENT_NOT_BILLING",
            "prior": "ADAPTIVE_GROUPS_PRESENT" if prior[0] else "UNKNOWN_NOT_ZERO",
            "today_group_count": current[0], "prior_group_count": prior[0],
            "usage_attested": False}


def access_snapshot(value: object, *, now_utc: datetime) -> tuple[str, str]:
    """Manual dashboard observation, NOT an independently verified seat audit."""
    if value is None:
        return "UNKNOWN", "ACCESS_SEATS_UNMEASURED"
    if not isinstance(value, dict) or set(value) != {
        "plan", "seats_used", "seats_total", "observed_utc", "source"
    }:
        return "INVALID", "ACCESS_EVIDENCE_INVALID"
    try:
        observed = utc_time(value["observed_utc"])
        used, total = strict_number(value["seats_used"]), strict_number(value["seats_total"])
    except DossierError:
        return "INVALID", "ACCESS_EVIDENCE_INVALID"
    if value["source"] != "MANUAL_ZERO_TRUST_DASHBOARD" or value["plan"] != "FREE":
        return "INVALID", "ACCESS_PLAN_OR_SOURCE_UNVERIFIED"
    if not 0 < total <= 50 or used > total:
        return "INVALID", "ACCESS_SEATS_OUTSIDE_FREE_REFERENCE"
    if observed > now_utc + MAX_FUTURE_SKEW or now_utc - observed > MAX_AGE:
        return "STALE", "ACCESS_SNAPSHOT_NOT_FRESH"
    if observed.date() != now_utc.date():
        return "STALE", "ACCESS_SNAPSHOT_NOT_TODAY"
    if used == total:
        return "NO_CAPACITY", "ACCESS_SEATS_NO_FREE_MARGIN"
    return "MANUAL_ONLY", "ACCESS_SEATS_MANUAL_NOT_PROVIDER_ATTESTED"


def monitor_provenance(value: object, *, now_utc: datetime) -> tuple[str, str]:
    """Check public workflow run metadata only; never infer Cloudflare correctness."""
    if not isinstance(value, dict) or set(value) != {
        "run_id", "head_branch", "conclusion", "started_utc", "source"
    }:
        return "INVALID", "MONITOR_PROVENANCE_MISSING"
    if (type(value["run_id"]) is not int or not 1 <= value["run_id"] < 10**16
            or value["head_branch"] != "main"
            or value["source"] != "GITHUB_ACTIONS_PUBLIC_RUN"
            or value["conclusion"] not in ("success", "failure")):
        return "INVALID", "MONITOR_PROVENANCE_INVALID"
    try:
        stamp = utc_time(value["started_utc"])
    except DossierError:
        return "INVALID", "MONITOR_PROVENANCE_INVALID"
    if stamp > now_utc + MAX_FUTURE_SKEW or now_utc - stamp > MAX_AGE:
        return "STALE", "MONITOR_PROVENANCE_STALE"
    if stamp.date() != now_utc.date():
        return "STALE", "MONITOR_PROVENANCE_WRONG_DAY"
    if value["conclusion"] != "success":
        return "INCOMPLETE", "MONITOR_RUN_FAILED_OR_INCOMPLETE"
    # 'success' is not proof that logs are truthful or actual billing.
    return "PUBLIC_METADATA_ONLY", "MONITOR_METADATA_NOT_PROVIDER_ATTESTATION"


@dataclass(frozen=True)
class Dossier:
    schema: str
    version: str
    observed_day: str
    decision: str
    d1_daily: str
    workers_daily: str
    d1_storage: str
    access: str
    monitor: str
    graphql_triage: str
    source_lock: str
    reasons: tuple[str, ...]
    def public_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema, "version": self.version,
            "observed_utc_day": self.observed_day, "decision": self.decision,
            "d1_daily": self.d1_daily, "workers_daily": self.workers_daily,
            "d1_storage": self.d1_storage, "access": self.access,
            "monitor": self.monitor, "graphql_triage": self.graphql_triage,
            "source_lock": self.source_lock, "reasons": list(self.reasons),
            "input_trust": "OFFLINE_SUPPLIED_UNVERIFIED",
            "real_cloudflare_quotas_attested": False,
            "automatic_deploy_allowed": False,
            "requires_explicit_staging_authorization": True,
        }


def dossier(*, logs: dict[str, str], now_utc: datetime, monitor: object,
            access: object = None, graphql_today: object = None,
            graphql_yesterday: object = None, inventory: object = None,
            verify_sources: bool = True) -> Dossier:
    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
        raise DossierError("now_must_be_utc")
    if type(verify_sources) is not bool:
        raise DossierError("verify_sources_not_boolean")
    reasons: set[str] = set()
    try:
        # Never turn a manual seat count into a real Access attestation.
        budget = classify(logs, now_utc=now_utc, access_seats_attested=False)
        reasons.update(budget.reason_codes)
        d1_state, workers_state, storage_state = budget.d1_daily, budget.workers_daily, budget.d1_storage
    except (EvidenceError, TypeError, ValueError):
        reasons.add("BUDGET_LOGS_INVALID")
        d1_state = workers_state = storage_state = "UNKNOWN"
    access_state, access_reason = access_snapshot(access, now_utc=now_utc)
    reasons.add(access_reason)
    monitor_state, monitor_reason = monitor_provenance(monitor, now_utc=now_utc)
    reasons.add(monitor_reason)
    if graphql_today is None or graphql_yesterday is None or inventory is None:
        triage_state = "NOT_AVAILABLE"
        reasons.add("D1_GRAPHQL_TRIAGE_NOT_AVAILABLE")
    else:
        try:
            result = triage(graphql_today, graphql_yesterday,
                            day=now_utc.date().isoformat(), inventory=inventory)
            triage_state = str(result["state"])
            if result["today"] == "UNKNOWN_NOT_ZERO":
                reasons.add("D1_TODAY_EMPTY_NOT_ZERO")
            else:
                reasons.add("D1_GRAPHQL_OFFLINE_INPUT_NOT_PROVIDER_PROOF")
        except DossierError:
            triage_state = "INVALID"
            reasons.add("D1_GRAPHQL_TRIAGE_INVALID")
    if verify_sources:
        try:
            source_lock = str(verify_contract()["status"])
        except (SourceLockError, OSError, UnicodeError):
            source_lock = "DRIFT_OR_MISSING"
            reasons.add("SOURCE_LOCK_FAILED")
    else:
        source_lock = "NOT_CHECKED"
        reasons.add("SOURCE_LOCK_NOT_CHECKED")
    # No untrusted offline input can authorize real staging.
    return Dossier("remura.contributors.readiness.v080.lab", "0.80",
                   now_utc.date().isoformat(), "NO_GO",
                   d1_state, workers_state, storage_state,
                   access_state, monitor_state, triage_state,
                   source_lock, tuple(sorted(reasons)))


def main(argv: list[str]) -> int:
    # This module intentionally accepts no external endpoint, account ID or secret.
    if argv != ["--offline-help"]:
        print("REMURA_V080_READINESS=NO_GO_NO_LIVE_RUNNER")
        return 3
    print("REMURA_V080_READINESS=OFFLINE_ONLY; no Cloudflare calls; no deploy")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
