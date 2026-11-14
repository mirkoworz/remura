# REMURA Workers Analytics Guard v0.2 — aggiornamento 13/11/2026, ore 10:13 CET
# Solo lettura GraphQL con token Account Analytics Read già presente, no deploy.
"""Account-wide Workers daily invocation estimate, without any write or token logging.

GraphQL Workers Invocations Adaptive can be sampled/delayed. When there are
no records or the 1000-group cap is hit, do NOT report a misleading zero or
complete daily usage. This does not substitute for Cloudflare billing.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
import json
import math
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cloudflare_d1_readonly_audit import AuditError, require_account_id, require_account_token

GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
MAX_GROUPS = 1000
WORKERS_FREE_REQUESTS_PER_DAY = 100_000
WARNING_THRESHOLD_PERCENT = 70
CRITICAL_THRESHOLD_PERCENT = 90

# Matches official Workers GraphQL Metrics tutorial. No mutable operations.
# The dimension scriptName is used only in the parser, never published.
QUERY = """query RemuraWorkersDailyUsage($accountTag: String!, $start: Time!, $end: Time!) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      workersInvocationsAdaptive(limit: 1000,
        filter: { datetime_geq: $start, datetime_lt: $end }) {
        dimensions { scriptName status }
        sum { requests errors subrequests }
        quantiles { cpuTimeP99 }
      }
    }
  }
}"""


def nonnegative_int(value: object) -> int:
    if type(value) is int and value >= 0:
        return value
    if type(value) is float and math.isfinite(value) and value >= 0 and value.is_integer():
        return int(value)
    raise AuditError("workers_invalid_counter")


def parse_workers(payload: object) -> dict | None:
    if not isinstance(payload, dict) or payload.get("errors"):
        raise AuditError("workers_graphql_errors")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("viewer"), dict):
        raise AuditError("workers_graphql_missing_viewer")
    accounts = data["viewer"].get("accounts")
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        raise AuditError("workers_graphql_account_mismatch")
    rows = accounts[0].get("workersInvocationsAdaptive")
    if not isinstance(rows, list) or len(rows) > MAX_GROUPS:
        raise AuditError("workers_graphql_rows_unexpected")
    if not rows:
        return None  # Not proof of zero traffic.
    if len(rows) == MAX_GROUPS:
        raise AuditError("workers_graphql_truncated_at_1000")
    requests = errors = subrequests = 0
    script_names = set()
    worst_reported_p99 = None
    for row in rows:
        if not isinstance(row, dict):
            raise AuditError("workers_graphql_bad_row")
        dims, sums, quantiles = row.get("dimensions"), row.get("sum"), row.get("quantiles")
        if not isinstance(dims, dict) or not isinstance(sums, dict) or not isinstance(quantiles, dict):
            raise AuditError("workers_graphql_missing_columns")
        name = dims.get("scriptName")
        if not isinstance(name, str) or not name.strip():
            raise AuditError("workers_graphql_unknown_script")
        script_names.add(name)
        requests += nonnegative_int(sums.get("requests"))
        errors += nonnegative_int(sums.get("errors"))
        subrequests += nonnegative_int(sums.get("subrequests"))
        cpu_p99 = quantiles.get("cpuTimeP99")
        if cpu_p99 is not None:
            if type(cpu_p99) not in (int, float) or not math.isfinite(cpu_p99) or cpu_p99 < 0:
                raise AuditError("workers_graphql_invalid_cpu")
            worst_reported_p99 = max(worst_reported_p99 or 0.0, float(cpu_p99))
    if errors > requests:
        raise AuditError("workers_graphql_inconsistent_counts")
    return {
        "requests_estimate": requests,
        "errors_estimate": errors,
        "subrequests_estimate": subrequests,
        "script_count": len(script_names),
        "max_reported_cpu_p99_us": worst_reported_p99,
        "group_count": len(rows),
    }


def assess_requests(requests: int) -> str:
    requests = nonnegative_int(requests)
    if requests * 100 >= WORKERS_FREE_REQUESTS_PER_DAY * CRITICAL_THRESHOLD_PERCENT:
        return "CRITICAL"
    if requests * 100 >= WORKERS_FREE_REQUESTS_PER_DAY * WARNING_THRESHOLD_PERCENT:
        return "WARNING"
    return "OK"


def fetch_workers_analytics(account_id: str, token: str, now: datetime) -> dict | None:
    account_id = require_account_id(account_id)
    token = require_account_token(token)
    if now.tzinfo is None or now.utcoffset() is None:
        raise AuditError("workers_now_not_aware")
    now = now.astimezone(timezone.utc)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    variables = {
        "accountTag": account_id,
        "start": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    request = Request(
        GRAPHQL_URL, method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json", "Accept": "application/json"},
        data=json.dumps({"query": QUERY, "variables": variables}).encode("utf-8"),
    )
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(100_001)
    except (HTTPError, URLError, TimeoutError) as err:
        status = err.code if isinstance(err, HTTPError) else "network"
        raise AuditError(f"workers_graphql_http_error_{status}") from None
    if len(raw) > 100_000:
        raise AuditError("workers_graphql_too_large")
    try:
        return parse_workers(json.loads(raw))
    except (UnicodeError, ValueError):
        raise AuditError("workers_graphql_invalid_json") from None


def main() -> int:
    token = os.getenv("REMURA_CF_ANALYTICS_READ_TOKEN", "").strip()
    if not token:
        print("REMURA_CF_WORKERS_USAGE=SKIPPED_MISSING_ANALYTICS_TOKEN")
        return 0
    now = datetime.now(timezone.utc)
    try:
        metrics = fetch_workers_analytics(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""), token, now)
    except AuditError as err:
        print("REMURA_CF_WORKERS_USAGE=ERROR:" + str(err))
        return 1
    if metrics is None:
        print("REMURA_CF_WORKERS_USAGE=UNKNOWN_NO_DATA")
        return 0
    status = assess_requests(metrics["requests_estimate"])
    print("REMURA_CF_WORKERS_USAGE=" + status)
    print("WORKERS_UTC_DAY=" + now.date().isoformat() + "; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING")
    print("WORKERS_ACCOUNT_REQUESTS_ESTIMATE=" + str(metrics["requests_estimate"]))
    print("WORKERS_ACCOUNT_ERRORS_ESTIMATE=" + str(metrics["errors_estimate"]))
    print("WORKERS_ACCOUNT_SCRIPT_COUNT=" + str(metrics["script_count"]))
    print("WORKERS_MAX_REPORTED_CPU_P99_US=" +
          (str(metrics["max_reported_cpu_p99_us"])
           if metrics["max_reported_cpu_p99_us"] is not None else "NOT_AVAILABLE"))
    print("WORKERS_FREE_DAILY_REQUEST_LIMIT=" + str(WORKERS_FREE_REQUESTS_PER_DAY))
    print("WORKERS_CPU_AND_COST=NOT_VERIFIED_BY_BILLING")
    return 2 if status == "CRITICAL" else 0


if __name__ == "__main__":
    sys.exit(main())
