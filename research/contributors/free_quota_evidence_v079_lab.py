# REMURA Contributors v0.79 LAB — 21/11/2026 17:15 CET.
# Offline evidence classifier ONLY. No network, no Cloudflare credentials, no deploy GO.
"""Classify Cloudflare Free monitoring evidence without converting UNKNOWN to zero.

Inputs are public-safe, allowlisted metrics emitted by the existing account read-only
workflow. They are not signed nor exact billing proofs: the highest possible result
is LAB_REVIEW_ONLY. Never use this module as an automatic deployment permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import sys

D1_READ_LIMIT = 5_000_000
D1_WRITE_LIMIT = 100_000
WORKER_REQUEST_LIMIT = 100_000
D1_DB_COUNT_LIMIT = 10
D1_ACCOUNT_STORAGE_LIMIT = 5_000_000_000
D1_SINGLE_DB_LIMIT = 500_000_000
CAUTION_PERCENT = 70
MAX_BYTES_PER_LOG = 40_000
ALLOWED = frozenset({
    "REMURA_CF_ACCOUNT_QUOTA", "UTC_DAY", "D1_ACCOUNT_ROWS_READ_ESTIMATE",
    "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE", "D1_FREE_READ_LIMIT",
    "D1_FREE_WRITE_LIMIT", "REAL_ACCOUNT_DAILY_USAGE",
    "REMURA_CF_WORKERS_USAGE", "WORKERS_UTC_DAY",
    "WORKERS_ACCOUNT_REQUESTS_ESTIMATE", "WORKERS_ACCOUNT_ERRORS_ESTIMATE",
    "WORKERS_FREE_DAILY_REQUEST_LIMIT", "REMURA_D1_TEST_STORAGE",
    "REMURA_D1_TEST_STORAGE_BYTES", "REMURA_D1_TEST_STORAGE_LIMIT_BYTES",
    "REMURA_D1_ACCOUNT_STORAGE", "D1_ACCOUNT_DATABASE_COUNT",
    "D1_ACCOUNT_STORAGE_BYTES", "D1_ACCOUNT_LARGEST_DB_BYTES",
    "D1_ACCOUNT_FREE_STORAGE_LIMIT_BYTES",
    "D1_ACCOUNT_FREE_SINGLE_DB_LIMIT_BYTES",
    "D1_ACCOUNT_FREE_DB_COUNT_LIMIT",
})
STATUS = frozenset({"OK", "WARNING", "CRITICAL"})
LINE_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.+)$")
UINT_RE = re.compile(r"^(?:0|[1-9][0-9]{0,16})$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class EvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class Verdict:
    decision: str
    d1_daily: str
    workers_daily: str
    d1_storage: str
    access: str
    observed_utc_day: str
    reason_codes: tuple[str, ...]
    # No raw telemetry, secret, account ID, email or hostname is exposed.
    def public_dict(self) -> dict[str, object]:
        return {
            "schema": "remura.contributors.free_visibility.v079.lab",
            "version": "0.79",
            "mode": "OFFLINE_ADVISORY_ONLY",
            "decision": self.decision,
            "d1_daily": self.d1_daily,
            "workers_daily": self.workers_daily,
            "d1_storage": self.d1_storage,
            "access": self.access,
            "observed_utc_day": self.observed_utc_day,
            "reasons": list(self.reason_codes),
            "automatic_deploy_allowed": False,
        }


def parse_log(text: str) -> dict[str, str]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES_PER_LOG:
        raise EvidenceError("oversized_or_invalid_log")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if len(line) > 1000:
            raise EvidenceError("oversized_log_line")
        match = LINE_RE.fullmatch(line.strip())
        if not match:
            continue
        key, value = match.groups()
        if key not in ALLOWED:
            continue  # Ignore and never echo unrelated fields or possible secrets.
        if key in values:
            raise EvidenceError("duplicate_known_field")
        if not value.isascii() or len(value) > 200:
            raise EvidenceError("unsafe_known_value")
        values[key] = value
    return values


def integer_field(data: dict[str, str], key: str, limit: int) -> int:
    value = data.get(key, "")
    if not UINT_RE.fullmatch(value):
        raise EvidenceError("invalid_or_missing_counter")
    count = int(value)
    if count > limit:
        raise EvidenceError("counter_exceeds_supported_bounds")
    return count


def parse_day(value: str, field: str, expected: str) -> bool:
    if not isinstance(value, str):
        return False
    # The original monitor emits "UTC_DAY=YYYY-MM-DD; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING".
    parts = [x.strip() for x in value.split(";")]
    if len(parts) != 3 or parts[1:] != ["SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE", "NOT_EXACT_BILLING"]:
        return False
    if not DATE_RE.fullmatch(parts[0]):
        return False
    try:
        parsed = datetime.strptime(parts[0], "%Y-%m-%d").date()
    except ValueError:
        return False
    return parsed.isoformat() == expected


def under_caution(count: int, limit: int) -> bool:
    return count * 100 < limit * CAUTION_PERCENT


def classify(logs: dict[str, str], *, now_utc: datetime,
             access_seats_attested: bool = False) -> Verdict:
    if not isinstance(logs, dict) or set(logs) != {"d1", "workers", "test_storage", "account_storage"}:
        raise EvidenceError("missing_or_extra_log_categories")
    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise EvidenceError("utc_clock_required")
    if now_utc.utcoffset().total_seconds() != 0:
        raise EvidenceError("clock_must_be_utc")
    if type(access_seats_attested) is not bool:
        raise EvidenceError("invalid_access_attestation")
    day = now_utc.date().isoformat()
    metrics = {key: parse_log(value) for key, value in logs.items()}
    d, w, t, a = (metrics[k] for k in ("d1", "workers", "test_storage", "account_storage"))
    reasons: set[str] = set()
    d1_state = "UNKNOWN"
    if d.get("REMURA_CF_ACCOUNT_QUOTA") not in STATUS:
        reasons.add("D1_DAILY_UNKNOWN_NOT_ZERO")
    elif not parse_day(d.get("UTC_DAY", ""), "UTC_DAY", day):
        reasons.add("D1_DAILY_NOT_FRESH")
    else:
        try:
            read = integer_field(d, "D1_ACCOUNT_ROWS_READ_ESTIMATE", 10**12)
            written = integer_field(d, "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE", 10**12)
            if (integer_field(d, "D1_FREE_READ_LIMIT", 10**12) != D1_READ_LIMIT
                    or integer_field(d, "D1_FREE_WRITE_LIMIT", 10**12) != D1_WRITE_LIMIT):
                reasons.add("D1_REFERENCE_LIMIT_CHANGED")
            elif (d["REMURA_CF_ACCOUNT_QUOTA"] != "OK"
                    or not under_caution(read, D1_READ_LIMIT)
                    or not under_caution(written, D1_WRITE_LIMIT)):
                reasons.add("D1_DAILY_TOO_CLOSE_TO_FREE_CAP")
            else:
                d1_state = "ADAPTIVE_ESTIMATE_PRESENT"
        except EvidenceError:
            reasons.add("D1_DAILY_INVALID_COUNTERS")
    workers_state = "UNKNOWN"
    if w.get("REMURA_CF_WORKERS_USAGE") not in STATUS:
        reasons.add("WORKERS_DAILY_UNKNOWN")
    elif not parse_day(w.get("WORKERS_UTC_DAY", ""), "WORKERS_UTC_DAY", day):
        reasons.add("WORKERS_DAILY_NOT_FRESH")
    else:
        try:
            requests = integer_field(w, "WORKERS_ACCOUNT_REQUESTS_ESTIMATE", 10**12)
            errors = integer_field(w, "WORKERS_ACCOUNT_ERRORS_ESTIMATE", 10**12)
            if integer_field(w, "WORKERS_FREE_DAILY_REQUEST_LIMIT", 10**12) != WORKER_REQUEST_LIMIT:
                reasons.add("WORKERS_REFERENCE_LIMIT_CHANGED")
            elif w["REMURA_CF_WORKERS_USAGE"] != "OK" or errors > requests or not under_caution(requests, WORKER_REQUEST_LIMIT):
                reasons.add("WORKERS_DAILY_INVALID_OR_NEAR_CAP")
            else:
                workers_state = "ADAPTIVE_ESTIMATE_PRESENT"
        except EvidenceError:
            reasons.add("WORKERS_DAILY_INVALID_COUNTERS")
    storage_state = "UNKNOWN"
    if t.get("REMURA_D1_TEST_STORAGE") not in STATUS or a.get("REMURA_D1_ACCOUNT_STORAGE") not in STATUS:
        reasons.add("D1_STORAGE_METADATA_UNKNOWN")
    else:
        try:
            test_bytes = integer_field(t, "REMURA_D1_TEST_STORAGE_BYTES", 10**13)
            test_limit = integer_field(t, "REMURA_D1_TEST_STORAGE_LIMIT_BYTES", 10**13)
            count = integer_field(a, "D1_ACCOUNT_DATABASE_COUNT", 10**5)
            total = integer_field(a, "D1_ACCOUNT_STORAGE_BYTES", 10**13)
            largest = integer_field(a, "D1_ACCOUNT_LARGEST_DB_BYTES", 10**13)
            reference = (
                integer_field(a, "D1_ACCOUNT_FREE_STORAGE_LIMIT_BYTES", 10**13),
                integer_field(a, "D1_ACCOUNT_FREE_SINGLE_DB_LIMIT_BYTES", 10**13),
                integer_field(a, "D1_ACCOUNT_FREE_DB_COUNT_LIMIT", 10**5),
            )
            if test_limit != D1_SINGLE_DB_LIMIT or reference != (
                D1_ACCOUNT_STORAGE_LIMIT, D1_SINGLE_DB_LIMIT, D1_DB_COUNT_LIMIT
            ):
                reasons.add("D1_STORAGE_REFERENCE_LIMIT_CHANGED")
            elif (a["REMURA_D1_ACCOUNT_STORAGE"] != "OK" or t["REMURA_D1_TEST_STORAGE"] != "OK"
                  or count < 1 or test_bytes > largest or largest > total
                  or not all((under_caution(count, D1_DB_COUNT_LIMIT),
                              under_caution(total, D1_ACCOUNT_STORAGE_LIMIT),
                              under_caution(largest, D1_SINGLE_DB_LIMIT),
                              under_caution(test_bytes, D1_SINGLE_DB_LIMIT)))):
                reasons.add("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP")
            else:
                storage_state = "METADATA_SNAPSHOT_PRESENT"
        except EvidenceError:
            reasons.add("D1_STORAGE_INVALID_COUNTERS")
    access_state = "SEATS_ATTESTED_INPUT_UNVERIFIED" if access_seats_attested else "NOT_MEASURED"
    if not access_seats_attested:
        reasons.add("ACCESS_FREE_SEATS_NOT_ATTESTED")
    # Even a perfect synthetic input only reaches review. No self-authorizing GO.
    decision = "LAB_REVIEW_ONLY" if not reasons else "NO_GO"
    return Verdict(decision, d1_state, workers_state, storage_state, access_state,
                   day, tuple(sorted(reasons)))


def diagnostic(d1_today: dict, d1_yesterday: dict | None) -> str:
    """Classify *synthetic supplied* GraphQL dataset presence, not daily usage."""
    def group_count(value: dict | None) -> int | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise EvidenceError("invalid_graphql_diagnostic")
        data = value.get("data")
        if value.get("errors") or not isinstance(data, dict) or not isinstance(data.get("viewer"), dict):
            raise EvidenceError("graphql_failure")
        accounts = data["viewer"].get("accounts")
        if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
            raise EvidenceError("graphql_account_mismatch")
        rows = accounts[0].get("d1AnalyticsAdaptiveGroups")
        if not isinstance(rows, list) or len(rows) > 10:
            raise EvidenceError("graphql_rows_invalid")
        return len(rows)
    today = group_count(d1_today)
    yesterday = group_count(d1_yesterday)
    if today == 0 and yesterday is None:
        return "UNKNOWN_EMPTY_TODAY_WITHOUT_CONTROL"
    if today == 0 and yesterday == 0:
        return "UNKNOWN_EMPTY_BOTH_DAYS"
    if today == 0 and yesterday > 0:
        return "UNKNOWN_EMPTY_TODAY_PRIOR_HAS_ACTIVITY"
    if today > 0:
        return "GROUPS_PRESENT_VALUES_STILL_NEED_VALIDATION"
    raise EvidenceError("unreachable")


def main(argv: list[str]) -> int:
    # OFFLINE only: no API token, URL, action or deploy arguments.
    if len(argv) != 6 or argv[1] != "--offline-logs":
        print("REMURA_V079_GATE=NO_GO_BAD_ARGUMENTS")
        return 2
    from pathlib import Path
    try:
        paths = [Path(x) for x in argv[2:]]
        if any(not p.is_file() or p.stat().st_size > MAX_BYTES_PER_LOG for p in paths):
            raise EvidenceError("missing_or_large_input")
        logs = {k: p.read_text(encoding="utf-8") for k, p in zip(
            ("d1", "workers", "test_storage", "account_storage"), paths)}
        verdict = classify(logs, now_utc=datetime.now(timezone.utc))
        print(json.dumps(verdict.public_dict(), sort_keys=True, separators=(",", ":")))
        return 0 if verdict.decision == "LAB_REVIEW_ONLY" else 3
    except (EvidenceError, OSError, UnicodeError):
        print("REMURA_V079_GATE=NO_GO_UNVERIFIABLE_EVIDENCE")
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
