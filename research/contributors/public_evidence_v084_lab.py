# REMURA Contributors v0.84 LAB — 21/11/2026 Europe/Rome
# Strict, identifier-free offline evidence export. NO network, Secrets or staging.
"""Accept only an allowlisted, sanitized evidence snapshot; refuse all deployment.

The caller is untrusted. Empty/null D1 counters are UNKNOWN, never zero.
These counters are adaptive estimates, not billing or provider attestations.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import sys

INPUT_KEYS = frozenset({
    "source", "utc_day", "observed_utc", "d1_rows_read_estimate",
    "d1_rows_written_estimate", "workers_requests_estimate",
    "d1_account_storage_bytes", "d1_database_count",
    "access_plan", "access_seats_used", "access_seats_total",
})
D1_READ_REFERENCE = 5_000_000
D1_WRITE_REFERENCE = 100_000
WORKERS_REFERENCE = 100_000
STORAGE_REFERENCE = 5_000_000_000
D1_COUNT_REFERENCE = 10
CAUTION_PERCENT = 70
MAX_AGE = timedelta(hours=4)
SKEW = timedelta(minutes=2)

class PublicEvidenceError(ValueError):
    pass

def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise PublicEvidenceError("timestamp_invalid")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicEvidenceError("timestamp_invalid") from exc
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise PublicEvidenceError("timestamp_not_utc")
    return t.astimezone(timezone.utc)

def optional_int(value: object, *, ceiling: int) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0 or value > ceiling:
        raise PublicEvidenceError("counter_invalid")
    return value

def level(value: int, limit: int) -> str:
    if value >= limit:
        return "AT_OR_OVER_REFERENCE_LIMIT"
    if value * 100 >= limit * CAUTION_PERCENT:
        return "NEAR_REFERENCE_LIMIT"
    return "ESTIMATE_BELOW_CAUTION_NOT_BILLING"

def review(snapshot: object, *, now_utc: datetime) -> dict[str, object]:
    # Never serialize the input or any part of an unexpected field.
    result: dict[str, object] = {
        "schema": "remura.contributors.public_evidence.v084.lab",
        "version": "0.84",
        "source_trust": "OFFLINE_UNVERIFIED",
        "status": "INVALID_OR_UNKNOWN",
        "d1_daily": "UNKNOWN_NOT_ZERO",
        "workers_daily": "UNKNOWN_NOT_ZERO",
        "d1_storage": "UNKNOWN",
        "access_seats": "UNKNOWN_NOT_ATTESTED",
        "d1_rows_read_estimate": None,
        "d1_rows_written_estimate": None,
        "workers_requests_estimate": None,
        "d1_account_storage_bytes": None,
        "d1_database_count": None,
        "real_provider_attested": False,
        "billing_attested": False,
        "automatic_deploy_allowed": False,
        "decision": "NO_GO",
    }
    try:
        if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
            raise PublicEvidenceError("clock_invalid")
        now = now_utc.astimezone(timezone.utc)
        if not isinstance(snapshot, dict) or set(snapshot) != INPUT_KEYS:
            raise PublicEvidenceError("unexpected_input_key")
        if snapshot["source"] != "OFFLINE_SUPPLIED_UNVERIFIED":
            raise PublicEvidenceError("input_source_not_allowed")
        observed = timestamp(snapshot["observed_utc"])
        if (snapshot["utc_day"] != now.date().isoformat() or
                observed.date() != now.date() or
                not now - MAX_AGE <= observed <= now + SKEW):
            raise PublicEvidenceError("snapshot_stale_or_future")
        fields = {
            "d1_rows_read_estimate": optional_int(snapshot["d1_rows_read_estimate"], ceiling=10**12),
            "d1_rows_written_estimate": optional_int(snapshot["d1_rows_written_estimate"], ceiling=10**12),
            "workers_requests_estimate": optional_int(snapshot["workers_requests_estimate"], ceiling=10**12),
            "d1_account_storage_bytes": optional_int(snapshot["d1_account_storage_bytes"], ceiling=10**13),
            "d1_database_count": optional_int(snapshot["d1_database_count"], ceiling=10**3),
        }
        if ((fields["d1_rows_read_estimate"] is None) !=
                (fields["d1_rows_written_estimate"] is None)):
            raise PublicEvidenceError("partial_d1_counters")
        if ((fields["d1_account_storage_bytes"] is None) !=
                (fields["d1_database_count"] is None)):
            raise PublicEvidenceError("partial_storage")
        if snapshot["access_plan"] not in ("UNKNOWN", "FREE_MANUAL_UNVERIFIED"):
            raise PublicEvidenceError("access_plan_invalid")
        used = optional_int(snapshot["access_seats_used"], ceiling=1000)
        total = optional_int(snapshot["access_seats_total"], ceiling=1000)
        if (used is None) != (total is None):
            raise PublicEvidenceError("partial_access")
        if used is not None and (total == 0 or used > total):
            raise PublicEvidenceError("invalid_access_seats")
        # This still does not certify Access Free seats, even when counts are supplied.
        result.update(fields)
        reads = fields["d1_rows_read_estimate"]
        writes = fields["d1_rows_written_estimate"]
        if reads is not None and writes is not None:
            grades = (level(reads, D1_READ_REFERENCE), level(writes, D1_WRITE_REFERENCE))
            result["d1_daily"] = (
                "AT_OR_OVER_REFERENCE_LIMIT" if "AT_OR_OVER_REFERENCE_LIMIT" in grades else
                "NEAR_REFERENCE_LIMIT" if "NEAR_REFERENCE_LIMIT" in grades else
                "ADAPTIVE_ESTIMATE_BELOW_CAUTION_NOT_BILLING"
            )
        requests = fields["workers_requests_estimate"]
        if requests is not None:
            result["workers_daily"] = level(requests, WORKERS_REFERENCE)
        storage = fields["d1_account_storage_bytes"]
        count = fields["d1_database_count"]
        if storage is not None and count is not None:
            grades = (level(storage, STORAGE_REFERENCE), level(count, D1_COUNT_REFERENCE))
            result["d1_storage"] = (
                "AT_OR_OVER_REFERENCE_LIMIT" if "AT_OR_OVER_REFERENCE_LIMIT" in grades else
                "NEAR_REFERENCE_LIMIT" if "NEAR_REFERENCE_LIMIT" in grades else
                "METADATA_BELOW_CAUTION_NOT_BILLING"
            )
        result["status"] = "OFFLINE_SNAPSHOT_CLASSIFIED"
    except (PublicEvidenceError, TypeError, ValueError, OverflowError):
        # Invalid inputs produce zero numeric fields and never expose raw input.
        result["status"] = "INVALID_OR_UNKNOWN"
    return result

def demo() -> tuple[dict[str, object], datetime]:
    now = datetime(2026, 11, 21, 17, 30, tzinfo=timezone.utc)
    return {
        "source": "OFFLINE_SUPPLIED_UNVERIFIED",
        "utc_day": "2026-11-21", "observed_utc": "2026-11-21T17:30:00Z",
        "d1_rows_read_estimate": None, "d1_rows_written_estimate": None,
        "workers_requests_estimate": 199,
        "d1_account_storage_bytes": 6557696, "d1_database_count": 4,
        "access_plan": "UNKNOWN", "access_seats_used": None,
        "access_seats_total": None,
    }, now

def main(argv: list[str]) -> int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_V084_PUBLIC_EVIDENCE=NO_GO_BAD_ARGUMENTS")
        return 2
    sample, now = demo()
    result = review(sample, now_utc=now)
    if result["d1_daily"] != "UNKNOWN_NOT_ZERO" or result["automatic_deploy_allowed"]:
        print("REMURA_V084_PUBLIC_EVIDENCE=NO_GO_UNEXPECTED")
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
