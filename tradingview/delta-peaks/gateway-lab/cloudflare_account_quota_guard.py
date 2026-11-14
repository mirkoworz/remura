# REMURA Account Quota Guard v0.1 — aggiornamento 13/11/2026 ore 06:53 CET
# Sola lettura GraphQL Analytics, TOKEN SEPARATO: Account Analytics -> Read.
# Non richiede D1 Edit, Workers Edit, deploy, webhook, o modifica database.
"""Preflight for account-wide D1 daily usage, strictly opt-in via a new read-only token.

The Analytics API exposes sampled/adaptive data; results are an observability
estimate, not an exact live billing assertion. Free quota resets midnight UTC.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cloudflare_d1_readonly_audit import (
    AuditError, require_account_id, require_account_token,
)

GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
FREE_ROWS_READ = 5_000_000
FREE_ROWS_WRITTEN = 100_000
WARNING_PERCENT = 70
CRITICAL_PERCENT = 90

# One day UTC only: bounded to maximum 10 Free-plan D1 databases.
# Values represent the D1 Adaptive Analytics dataset, not an exact D1 bill.
QUERY = """query RemuraD1AccountUsage($accountTag: string!, $day: Date!) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      d1AnalyticsAdaptiveGroups(
        limit: 100
        filter: { date_geq: $day, date_leq: $day }
      ) {
        dimensions { date databaseId }
        sum { rowsRead rowsWritten }
      }
    }
  }
}"""


def assessment(reads: int, writes: int) -> str:
    if any(type(n) is not int or n < 0 for n in (reads, writes)):
        raise AuditError("invalid_usage_counter")
    if (reads * 100 >= FREE_ROWS_READ * CRITICAL_PERCENT or
            writes * 100 >= FREE_ROWS_WRITTEN * CRITICAL_PERCENT):
        return "CRITICAL"
    if (reads * 100 >= FREE_ROWS_READ * WARNING_PERCENT or
            writes * 100 >= FREE_ROWS_WRITTEN * WARNING_PERCENT):
        return "WARNING"
    return "OK"


def parse_analytics(payload: object, day: str) -> tuple[int, int] | None:
    if not isinstance(payload, dict) or payload.get("errors"):
        raise AuditError("graphql_errors_or_invalid_response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AuditError("graphql_data_missing")
    viewer = data.get("viewer")
    if not isinstance(viewer, dict):
        raise AuditError("graphql_viewer_missing")
    accounts = viewer.get("accounts")
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        raise AuditError("graphql_account_count_mismatch")
    groups = accounts[0].get("d1AnalyticsAdaptiveGroups")
    if not isinstance(groups, list) or len(groups) > 10:
        raise AuditError("graphql_groups_missing_or_unbounded")
    if not groups:
        return None  # Missing metrics is NOT a genuine zero.
    reads = writes = 0
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            raise AuditError("graphql_bad_group")
        dims = group.get("dimensions")
        counts = group.get("sum")
        if not isinstance(dims, dict) or not isinstance(counts, dict):
            raise AuditError("graphql_group_fields_missing")
        database_id = dims.get("databaseId")
        if dims.get("date") != day or not isinstance(database_id, str):
            raise AuditError("graphql_unexpected_day_or_db")
        if database_id in seen:
            raise AuditError("graphql_duplicate_database")
        seen.add(database_id)
        for label in ("rowsRead", "rowsWritten"):
            val = counts.get(label)
            if (type(val) not in (int, float)
                    or not math.isfinite(val) or val < 0
                    or (type(val) is float and not val.is_integer())):
                raise AuditError("graphql_invalid_counter")
        reads += int(counts["rowsRead"])
        writes += int(counts["rowsWritten"])
    return reads, writes


def query_account_analytics(account_id: str, token: str, day: str) -> tuple[int, int] | None:
    account = require_account_id(account_id)
    token = require_account_token(token)
    request = Request(GRAPHQL_URL, method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json", "Accept": "application/json"},
        data=json.dumps({"query": QUERY, "variables": {
            "accountTag": account, "day": day}}).encode("utf-8"))
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(100_001)
    except (HTTPError, URLError, TimeoutError) as e:
        status = e.code if isinstance(e, HTTPError) else "network"
        raise AuditError(f"graphql_http_error_{status}") from None
    if len(raw) > 100_000:
        raise AuditError("graphql_response_too_large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise AuditError("graphql_invalid_json") from None
    return parse_analytics(payload, day)


def main() -> int:
    token = os.environ.get("REMURA_CF_ANALYTICS_READ_TOKEN", "").strip()
    if not token:
        print("REMURA_CF_ACCOUNT_QUOTA=SKIPPED_NO_ANALYTICS_READ_TOKEN")
        print("REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED")
        return 0
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    try:
        rows = query_account_analytics(
            os.environ.get("REMURA_CF_ACCOUNT_ID", ""), token, day)
        if rows is None:
            print("REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA")
            print("REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED")
            return 0
        reads, writes = rows
        level = assessment(reads, writes)
    except AuditError as error:
        print("REMURA_CF_ACCOUNT_QUOTA=ERROR:" + str(error))
        return 1
    print("REMURA_CF_ACCOUNT_QUOTA=" + level)
    print("UTC_DAY=" + day + "; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING")
    print("D1_ACCOUNT_ROWS_READ_ESTIMATE=" + str(reads))
    print("D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=" + str(writes))
    print("D1_FREE_READ_LIMIT=" + str(FREE_ROWS_READ))
    print("D1_FREE_WRITE_LIMIT=" + str(FREE_ROWS_WRITTEN))
    return 2 if level == "CRITICAL" else 0


if __name__ == "__main__":
    sys.exit(main())
