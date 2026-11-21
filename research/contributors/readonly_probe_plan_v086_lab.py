# REMURA Contributors v0.86 LAB — 21/11/2026 18:22 CET Europe/Rome
# REVIEW an explicitly bounded future read-only probe; this file NEVER does HTTP.
"""Generate a public-safe, authorization-gated plan for reviewing D1 telemetry.

Do not confuse a review plan with approval to execute it. A future action
must be approved separately, with controls for secret and Free usage.
"""
from __future__ import annotations
import ast
from datetime import date, timedelta
from hashlib import sha1, sha256
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
PIN = "08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8"
GUARD = ROOT / "tradingview/delta-peaks/gateway-lab/cloudflare_account_quota_guard.py"
GUARD_BLOB = "af89df266d25541fc474b4d13536f61d2d77022a"
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

def git_blob(content: bytes) -> str:
    return sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def pinned_query() -> tuple[str,str]:
    if not GUARD.is_file() or GUARD.is_symlink():
        raise ProbeError("pinned_monitor_source_missing")
    content = GUARD.read_bytes()
    if len(content) > 20_000 or git_blob(content) != GUARD_BLOB:
        raise ProbeError("pinned_monitor_source_drift")
    try:
        tree = ast.parse(content.decode("utf-8"))
    except (SyntaxError, UnicodeError) as e:
        raise ProbeError("monitor_source_invalid") from e
    candidates = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "QUERY" for t in node.targets)
    ]
    if len(candidates) != 1 or not isinstance(candidates[0], str):
        raise ProbeError("query_missing_or_ambiguous")
    query = candidates[0]
    if not all(fragment in query for fragment in EXPECTED_FIELDS):
        raise ProbeError("query_drift")
    if "mutation" in query.lower() or "subscription" in query.lower():
        raise ProbeError("not_read_only_query")
    if "limit: 100" not in query:
        raise ProbeError("query_not_bounded")
    return query, sha256(query.encode("utf-8")).hexdigest()

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
