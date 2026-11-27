#!/usr/bin/env python3
# REMURA Worker Settings Probe v0.8.18 — 13/11/2026, ore 14:00 CET
# Solo GET autenticati API Cloudflare; mai GET al workers.dev pubblico, POST o deploy.
"""One-shot Workers metadata check using EXISTING D1 Read token.

An HTTP 403/401 is UNKNOWN, *never* proof of disabled/active ingestion.
The returned settings can contain plaintext variable values or sensitive
metadata. Never log the envelope, headers, exceptions, token or URLs.
"""
from __future__ import annotations

import os
import sys

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
    verify_account_token,
)

SCRIPT = "remura-tv-ingest-lab"
PATH_SUFFIX = "/workers/scripts/" + SCRIPT + "/settings"
REQUIRED = {
    "INGEST_ENABLED": "plain_text",
    "TELEMETRY_DB": "d1",
    "WEBHOOK_TOKEN_SHA256": "secret_text",
    "INGEST_RATE_LIMITER": "ratelimit",
}
# Named allowlist: never print unexpected binding names, values or identifiers.
PRINT_FIELDS = ("INGEST_FLAG", "D1_BINDING", "TOKEN_HASH_BINDING",
                "RATE_LIMIT_BINDING")


def inspect_settings(response: object) -> dict[str, str]:
    if not isinstance(response, dict) or response.get("success") is not True:
        raise AuditError("settings_envelope_unknown")
    result = response.get("result")
    if not isinstance(result, dict):
        raise AuditError("settings_result_unknown")
    bindings = result.get("bindings")
    if not isinstance(bindings, list):
        raise AuditError("bindings_not_reported")
    seen: dict[str, dict] = {}
    for item in bindings:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise AuditError("binding_invalid_shape")
        name = item["name"]
        if name in seen:
            raise AuditError("binding_duplicate_name")
        seen[name] = item
    verdict = {}
    for name, kind in REQUIRED.items():
        b = seen.get(name)
        if b is None:
            verdict[name] = "ABSENT"
        elif b.get("type") != kind:
            verdict[name] = "UNEXPECTED_TYPE"
        else:
            verdict[name] = "PRESENT"
    flag = seen.get("INGEST_ENABLED")
    if flag is None:
        flag_status = "ABSENT"
    elif flag.get("type") != "plain_text":
        flag_status = "UNKNOWN_TYPE"
    else:
        value = flag.get("text")
        flag_status = "ON" if value == "true" else (
            "OFF" if isinstance(value, str) else "UNKNOWN_VALUE"
        )
    # Only presence can be proven here; D1 UUID, secret value, limiter budget,
    # Worker deployed code, and Access account-wide remain UNKNOWN.
    return {
        "INGEST_FLAG": flag_status,
        "D1_BINDING": verdict["TELEMETRY_DB"],
        "TOKEN_HASH_BINDING": verdict["WEBHOOK_TOKEN_SHA256"],
        "RATE_LIMIT_BINDING": verdict["INGEST_RATE_LIMITER"],
    }


def audit(account_id: str, token: str) -> dict[str, str]:
    account = require_account_id(account_id)
    token = require_account_token(token)
    verify_account_token(api_request(
        "GET", "/accounts/" + account + "/tokens/verify", token))
    payload = api_request("GET", "/accounts/" + account + PATH_SUFFIX, token)
    return inspect_settings(payload)


def classify_failure(error: AuditError) -> str:
    # Do not return the API error string, token, endpoint or server body.
    code = str(error)
    if code == "cloudflare_http_error_403":
        return "INCONCLUSIVE_HTTP_403"
    if code == "cloudflare_http_error_401":
        return "INCONCLUSIVE_HTTP_401"
    if code == "cloudflare_http_error_404":
        return "INCONCLUSIVE_HTTP_404"
    if code in {
        "settings_envelope_unknown", "settings_result_unknown",
        "bindings_not_reported", "binding_invalid_shape",
        "binding_duplicate_name",
    }:
        return "INCONCLUSIVE_INCOMPLETE_SETTINGS"
    return "INCONCLUSIVE_OTHER"


def main() -> int:
    try:
        result = audit(os.getenv("REMURA_CF_ACCOUNT_ID", ""),
                       os.getenv("REMURA_CF_D1_READ_TOKEN", ""))
    except AuditError as error:
        print("REMURA_WORKER_SETTINGS=" + classify_failure(error))
        print("SOURCE=GET_API_ONLY; NO_EDGE_PROBE; NO_MUTATION")
        return 0  # Job classification SUCCESS != metadata VERIFIED.
    print("REMURA_WORKER_SETTINGS=METADATA_READ_SUCCEEDED")
    for key in PRINT_FIELDS:
        print(key + "=" + result[key])
    print("D1_TARGET_UUID=UNVERIFIED; DEPLOYED_CODE=UNVERIFIED")
    print("WORKERS_DEV_EDGE_POLICY=UNVERIFIED; RATE_LIMIT_COST=UNVERIFIED")
    print("SOURCE=GET_API_ONLY; NO_EDGE_PROBE; NO_MUTATION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
