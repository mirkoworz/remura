# REMURA Contributors v0.86 LAB — 21/11/2026 18:22 CET Europe/Rome
# REVIEW an explicitly bounded future read-only probe; this file NEVER does HTTP.
"""Generate a public-safe, authorization-gated plan for reviewing D1 telemetry.

Do not confuse a review plan with approval to execute it. A future action
must be approved separately, with controls for secret and Free usage.
"""
from __future__ import annotations
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
PIN = "08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8"
QUERY_FIXTURE = ROOT / "research/contributors/monitor_query_reference_v086_lab.graphql"
AUDITED_HISTORICAL_GUARD_BLOB = "af89df266d25541fc474b4d13536f61d2d77022a"
EXPECTED_QUERY_SHA256 = "483e14a113af7841fb69bdfdb7ea3fa3ee616b74f4f28b9cbc509b29d022754a"
DOC_URL = "https://developers.cloudflare.com/d1/observability/metrics-analytics/"
GRAPHQL_ENDPOINT = "https://api.cloudflare.com/client/v4/graphql"
MAX_ADDITIONAL_GRAPHQL_POST = 2
EXPECTED_FIELDS = (
    "d1AnalyticsAdaptiveGroups", "dimensions { date databaseId }",
    "sum { rowsRead rowsWritten }",
    "date_geq: $day", "date_leq: $day",
)
class ProbeError(ValueError):
    pass

def pinned_query() -> tuple[str,str]:
    # Historical monitor runs from a separate checkout at an audited SHA.
    # This branch intentionally includes ONLY its query text, not the HTTP client.
    if not QUERY_FIXTURE.is_file() or QUERY_FIXTURE.is_symlink():
        raise ProbeError("query_reference_missing")
    content = QUERY_FIXTURE.read_bytes()
    if not content or len(content) > 5000:
        raise ProbeError("query_reference_unbounded")
    try:
        query = content.decode("utf-8").removesuffix("\n")
    except UnicodeError as exc:
        raise ProbeError("query_reference_invalid") from exc
    if sha256(query.encode("utf-8")).hexdigest() != EXPECTED_QUERY_SHA256:
        raise ProbeError("query_reference_drift")
    if not all(fragment in query for fragment in EXPECTED_FIELDS):
        raise ProbeError("query_fields_missing")
    if "mutation" in query.lower() or "subscription" in query.lower():
        raise ProbeError("unsafe_graphql_operation")
    if "limit: 100" not in query:
        raise ProbeError("query_not_bounded")
    return query, EXPECTED_QUERY_SHA256

def plan(day: object) -> dict[str,object]:
    result: dict[str,object] = {
        "schema":"remura.contributors.readonly_probe_plan.v086.lab",
        "version":"0.86",
        "status":"INVALID_OR_UNVERIFIED",
        "approved_to_execute":False,
        "execution_mode":"OFFLINE_PLAN_ONLY",
        "http_calls_performed":0,
        "additional_graphql_calls_max_after_separate_approval":MAX_ADDITIONAL_GRAPHQL_POST,
        "access_users_api_calls":0,
        "d1_sql_calls":0,
        "provider_secrets_accessed":False,
        "auto_retry_allowed":False,
        "workflow_dispatch_triggered":False,
        "deployment_allowed":False,
        "query_sha256":None,
        "day_scopes_utc":None,
        "access_seats": "MANUAL_DASHBOARD_CHECK_REQUIRED",
        "same_day_billing_attested":False,
        "d1_rows_today_attested":False,
        "decision":"NO_GO",
    }
    try:
        if type(day) is not date or not date(2026,11,1) <= day <= date(2026,12,31):
            raise ProbeError("day_outside_boundaries")
        _, queryhash = pinned_query()
        result.update(
            status="PINNED_QUERY_REVIEWED_NO_EXECUTION",
            query_sha256=queryhash,
            day_scopes_utc=[day.isoformat(),(day-timedelta(days=1)).isoformat()],
        )
    except (ProbeError,ValueError,OSError,UnicodeError):
        pass
    return result

def main(argv:list[str])->int:
    if argv != ["--review-synthetic-plan"]:
        print("REMURA_V086_READONLY_PLAN=NO_GO_BAD_ARGUMENTS")
        return 2
    result=plan(date(2026,11,21))
    if result["status"]!="PINNED_QUERY_REVIEWED_NO_EXECUTION":
        print("REMURA_V086_READONLY_PLAN=NO_GO_GUARD_DRIFT")
        return 3
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
