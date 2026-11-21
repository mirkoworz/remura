# REMURA Contributors v0.82 LAB — 21/11/2026 Europe/Rome
# OFFLINE supplied-envelope audit ONLY: no HTTP requests, URLs, credentials or deploy.
"""Review two user-supplied GraphQL transport envelopes without trusting their provenance.

This is NOT a Cloudflare API client; it never performs GraphQL calls or reads tokens.
HTTP 200 is not proof of complete D1 usage. Empty adaptive groups are UNKNOWN.
Only allowlisted, identifier-free status codes leave this process.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import json
import re
import sys
from readiness_dossier_v080_lab import triage, DossierError

MAX_BODY_BYTES = 64_000
MAX_AGE = timedelta(hours=4)
SKEW = timedelta(minutes=2)
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")

class BoundaryError(ValueError):
    pass

def utc(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise BoundaryError("invalid_utc_timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise BoundaryError("invalid_utc_timestamp") from None
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise BoundaryError("timestamp_not_utc")
    return stamp.astimezone(timezone.utc)

def _timestamp_ok(value: object, now: datetime) -> bool:
    stamp = utc(value)
    return now - MAX_AGE <= stamp <= now + SKEW and stamp.date() == now.date()

def validate_envelope(value: object, *, day: str, now: datetime) -> tuple[str, object | None]:
    if not isinstance(value, dict) or set(value) != {
        "day", "observed_utc", "transport", "http_status", "content_type",
        "body_bytes", "graphql"
    }:
        raise BoundaryError("envelope_shape_invalid")
    if value["day"] != day or not _timestamp_ok(value["observed_utc"], now):
        raise BoundaryError("window_or_freshness_invalid")
    state = value["transport"]
    if state in ("TIMEOUT", "NETWORK_ERROR"):
        if (value["http_status"] is not None or value["content_type"] is not None
                or value["graphql"] is not None or value["body_bytes"] != 0):
            raise BoundaryError("transport_error_has_response")
        return state, None
    if state != "HTTP":
        raise BoundaryError("unknown_transport_state")
    code = value["http_status"]
    size = value["body_bytes"]
    if type(code) is not int or type(size) is not int or not 0 <= size <= MAX_BODY_BYTES:
        raise BoundaryError("invalid_http_fields")
    if code == 401 or code == 403:
        return "AUTH_DENIED", None
    if code == 429:
        return "RATE_LIMITED", None
    if 500 <= code < 600:
        return "PROVIDER_ERROR", None
    if code != 200:
        return "HTTP_ERROR", None
    mime = value["content_type"]
    if mime != "application/json" or size < 2 or not isinstance(value["graphql"], dict):
        raise BoundaryError("unusable_graphql_response")
    return "HTTP_JSON_SUPPLIED", value["graphql"]

def audit(batch: object, *, now_utc: datetime) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "remura.contributors.d1_transport_boundary.v082.lab",
        "version": "0.82",
        "mode": "OFFLINE_SUPPLIED_UNVERIFIED",
        "today": "UNKNOWN",
        "prior": "UNKNOWN",
        "status": "NO_EVIDENCE",
        "d1_daily_usage_attested": False,
        "exact_billing_attested": False,
        "automatic_deploy_allowed": False,
        "decision": "NO_GO",
    }
    try:
        if not isinstance(now_utc, datetime) or now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
            raise BoundaryError("invalid_clock")
        if not isinstance(batch, dict) or set(batch) != {
            "source", "run_id", "query_digest", "inventory_digest", "inventory",
            "today", "prior"
        }:
            raise BoundaryError("batch_shape_invalid")
        if (batch["source"] != "OFFLINE_SUPPLIED_FIXTURE"
                or type(batch["run_id"]) is not int or not 0 < batch["run_id"] < 10**16
                or not all(isinstance(batch[k], str) and HEX_SHA256.fullmatch(batch[k])
                           for k in ("query_digest", "inventory_digest"))):
            raise BoundaryError("lineage_unverified")
        today_day = now_utc.date().isoformat()
        prior_day = (now_utc.date() - timedelta(days=1)).isoformat()
        today, p_today = validate_envelope(batch["today"], day=today_day, now=now_utc)
        prior, p_prior = validate_envelope(batch["prior"], day=prior_day, now=now_utc)
        result["today"], result["prior"] = today, prior
        if today != "HTTP_JSON_SUPPLIED" or prior != "HTTP_JSON_SUPPLIED":
            result["status"] = "TRANSPORT_OR_HTTP_UNAVAILABLE"
            return result
        # v0.80 triage is reused; its historical test suites are NOT rerun.
        inspected = triage(p_today, p_prior, day=today_day, inventory=batch["inventory"])
        result["status"] = {
            "TODAY_EMPTY_PRIOR_PRESENT": "TODAY_EMPTY_PRIOR_PRESENT_UNKNOWN_NOT_ZERO",
            "BOTH_DAYS_EMPTY": "BOTH_DAYS_EMPTY_UNKNOWN_NOT_ZERO",
            "TODAY_GROUPS_PRESENT_OFFLINE_ONLY": "TODAY_ADAPTIVE_ESTIMATE_ONLY",
        }[inspected["state"]]
        result["today"] = "UNKNOWN_NOT_ZERO" if inspected["today"] == "UNKNOWN_NOT_ZERO" else "ADAPTIVE_ONLY"
        result["prior"] = "UNKNOWN_NOT_ZERO" if inspected["prior"] == "UNKNOWN_NOT_ZERO" else "ADAPTIVE_ONLY"
    except (BoundaryError, DossierError, ValueError, TypeError, KeyError, OverflowError):
        result["today"] = "UNKNOWN"
        result["prior"] = "UNKNOWN"
        result["status"] = "INVALID_OR_UNVERIFIABLE"
    return result

def _demo() -> dict[str, Any]:
    today = "2026-11-21"
    prior = "2026-11-20"
    uid = "11111111-1111-4111-8111-111111111111"
    def envelope(day: str, rows: list) -> dict[str, Any]:
        return {"day": day, "observed_utc": "2026-11-21T17:00:00Z", "transport": "HTTP",
                "http_status": 200, "content_type": "application/json", "body_bytes": 75,
                "graphql": {"data": {"viewer": {"accounts": [{"d1AnalyticsAdaptiveGroups": rows}]}}}}
    return {
        "source": "OFFLINE_SUPPLIED_FIXTURE", "run_id": 1234567,
        "query_digest": "a" * 64, "inventory_digest": "b" * 64,
        "inventory": [{"uuid": uid}],
        "today": envelope(today, []),
        "prior": envelope(prior, [{
            "dimensions": {"date": prior, "databaseId": uid},
            "sum": {"rowsRead": 7, "rowsWritten": 0}
        }]),
    }

def main(argv: list[str]) -> int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_V082_D1=NO_GO_BAD_ARGUMENTS")
        return 2
    verdict = audit(_demo(), now_utc=datetime(2026, 11, 21, 17, 0, tzinfo=timezone.utc))
    if verdict["status"] != "TODAY_EMPTY_PRIOR_PRESENT_UNKNOWN_NOT_ZERO":
        print("REMURA_V082_D1=NO_GO_UNEXPECTED_FIXTURE")
        return 3
    print(json.dumps(verdict, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
