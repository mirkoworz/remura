# REMURA Contributors v0.80 LAB — 21/11/2026 17:22 CET
# Offline-only D1 GraphQL two-day dataset presence/quality audit. NO API calls.
"""Inspect synthetic or previously supplied D1 GraphQL aggregate responses.

d1AnalyticsAdaptiveGroups is adaptive analytics. Empty groups are never
converted to zero; a nonempty group is not independent proof of billing.
No raw database/account IDs are emitted or committed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite
from re import fullmatch
from typing import Any
import json
import sys

UUID_RE = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
MAX_D1_DATABASES_FREE_REFERENCE = 10
MAX_TOTAL_SAMPLE_ROWS = 10

class D1EvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class D1Window:
    day: str
    groups: int
    aggregate_read_estimate: int | None
    aggregate_write_estimate: int | None
    dataset_state: str


def _nonnegative_integral(value: object) -> int:
    if type(value) not in (int, float) or not isfinite(value) or value < 0 or int(value) != value:
        raise D1EvidenceError("invalid_graphql_rows_counter")
    if int(value) > 1_000_000_000_000:
        raise D1EvidenceError("graphql_counter_outside_safe_bound")
    return int(value)


def inspect_day(payload: object, expected_day: date) -> D1Window:
    if not isinstance(expected_day, date) or type(expected_day) is not date:
        raise D1EvidenceError("invalid_requested_utc_day")
    if not isinstance(payload, dict) or payload.get("errors") not in (None, []):
        raise D1EvidenceError("graphql_error_or_invalid_response")
    view = payload.get("data")
    if not isinstance(view, dict) or not isinstance(view.get("viewer"), dict):
        raise D1EvidenceError("graphql_missing_viewer")
    accounts = view["viewer"].get("accounts")
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        raise D1EvidenceError("graphql_account_mismatch")
    data = accounts[0].get("d1AnalyticsAdaptiveGroups")
    if not isinstance(data, list) or len(data) > MAX_TOTAL_SAMPLE_ROWS:
        raise D1EvidenceError("graphql_missing_or_excessive_groups")
    seen = set()
    reads = writes = 0
    for row in data:
        if not isinstance(row, dict):
            raise D1EvidenceError("graphql_invalid_group")
        dimensions, sums = row.get("dimensions"), row.get("sum")
        if not isinstance(dimensions, dict) or not isinstance(sums, dict):
            raise D1EvidenceError("graphql_group_columns_missing")
        dbid = dimensions.get("databaseId")
        if not isinstance(dbid, str) or not fullmatch(UUID_RE, dbid):
            raise D1EvidenceError("graphql_database_identity_invalid")
        if dimensions.get("date") != expected_day.isoformat():
            raise D1EvidenceError("graphql_day_mismatch")
        if dbid.lower() in seen:
            raise D1EvidenceError("graphql_duplicate_database")
        seen.add(dbid.lower())
        reads += _nonnegative_integral(sums.get("rowsRead"))
        writes += _nonnegative_integral(sums.get("rowsWritten"))
    # Empty is NOT 0 row usage; unknown data availability/propagation.
    return D1Window(expected_day.isoformat(), len(data), reads if data else None,
                    writes if data else None,
                    "ADAPTIVE_GROUPS_PRESENT_ESTIMATE_ONLY" if data else "UNKNOWN_NO_GRAPHQL_GROUPS")


def inspect_window(today: object, yesterday: object, *, utc_day: date) -> dict[str, Any]:
    try:
        if not isinstance(utc_day, date) or type(utc_day) is not date:
            raise D1EvidenceError("invalid_utc_day")
        current = inspect_day(today, utc_day)
        past = inspect_day(yesterday, utc_day - timedelta(days=1))
    except (D1EvidenceError, OverflowError, ValueError):
        return {
            "schema": "remura.contributors.d1_two_day.v080.lab", "version": "0.80",
            "mode": "OFFLINE_FIXTURE_ONLY", "status": "UNKNOWN_OR_INVALID_DATASET",
            "today_group_count": None, "prior_group_count": None,
            "today_rows_read_estimate": None, "today_rows_written_estimate": None,
            "automatic_deploy_allowed": False,
        }
    if current.groups == 0 and past.groups > 0:
        condition = "TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO"
    elif current.groups == 0:
        condition = "BOTH_DAYS_EMPTY_NOT_ZERO"
    else:
        condition = "TODAY_GROUPS_PRESENT_STILL_ADAPTIVE"
    return {
        "schema": "remura.contributors.d1_two_day.v080.lab", "version": "0.80",
        "mode": "OFFLINE_FIXTURE_ONLY", "status": condition,
        "today_group_count": current.groups, "prior_group_count": past.groups,
        # Presence and counts are informative, not evidence of all account activity.
        "today_rows_read_estimate": current.aggregate_read_estimate,
        "today_rows_written_estimate": current.aggregate_write_estimate,
        "automatic_deploy_allowed": False,
    }


def main(argv: list[str]) -> int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_V080_D1=NO_GO")
        return 2
    day = date(2026, 11, 21)
    def sample(day: date, n: int) -> dict[str, Any]:
        return {"data": {"viewer": {"accounts": [{"d1AnalyticsAdaptiveGroups": [
            {"dimensions": {"date": day.isoformat(),
                            "databaseId": "11111111-1111-4111-8111-111111111111"},
             "sum": {"rowsRead": 3, "rowsWritten": 0}}
        ] if n else []}]}}}
    result = inspect_window(sample(day, 0), sample(day - timedelta(days=1), 1), utc_day=day)
    assert result["status"] == "TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO"
    assert result["today_rows_read_estimate"] is None
    assert not result["automatic_deploy_allowed"]
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
