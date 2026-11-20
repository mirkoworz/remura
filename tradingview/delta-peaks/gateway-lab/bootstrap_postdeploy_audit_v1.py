#!/usr/bin/env python3
# REMURA v0.8.31 — 13/11/2026 ore 20:58 CET — LIVE READ ONLY
# No Worker edge HTTP request, no POST, no D1, no mutation or secret disclosure.
"""Post-deployment read-only proof: expected TEST version exists and has NO bindings.

Checks the version recorded by the successful, previously authorized Wrangler
deployment. Does NOT prove its current traffic allocation or external reachability.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKER = "remura-tv-webhook-test"
EXPECTED_VERSION = "f5a43b49-f07f-404b-a9dd-4606a22afa3c"
ACCOUNT_RE = re.compile(r"^[a-f0-9]{32}$")


class AuditFailure(ValueError):
    pass


def verify_version(payload: object) -> str:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditFailure("version_api_unknown")
    version = payload.get("result")
    if not isinstance(version, dict) or version.get("id") != EXPECTED_VERSION:
        raise AuditFailure("unexpected_worker_version")
    resources = version.get("resources")
    if not isinstance(resources, dict):
        raise AuditFailure("version_resources_unreported")
    bindings = resources.get("bindings")
    if not isinstance(bindings, list) or bindings:
        raise AuditFailure("unexpected_or_unknown_version_bindings")
    return "EXPECTED_VERSION_NO_BINDINGS"


def verify_current_settings(payload: object) -> str:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditFailure("settings_api_unknown")
    settings = payload.get("result")
    if not isinstance(settings, dict):
        raise AuditFailure("settings_missing")
    bindings = settings.get("bindings")
    if not isinstance(bindings, list) or bindings:
        raise AuditFailure("settings_bindings_not_empty")
    return "CURRENT_SETTINGS_NO_BINDINGS"


def api_get(account: str, token: str, suffix: str) -> object:
    if not ACCOUNT_RE.fullmatch(account) or not isinstance(token, str) or (
        len(token) < 24 or any(ch.isspace() for ch in token)
    ):
        raise AuditFailure("missing_credentials")
    root = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{WORKER}"
    request = Request(
        root + suffix, method="GET", headers={
            "Authorization": "Bearer " + token, "Accept": "application/json",
        }
    )
    try:
        with urlopen(request, timeout=12) as response:
            if response.status != 200:
                raise AuditFailure("api_not_200")
            raw = response.read(300001)
            if len(raw) > 300000:
                raise AuditFailure("response_oversize")
    except (HTTPError, URLError, TimeoutError, OSError):
        raise AuditFailure("api_get_denied_or_failed") from None
    try:
        return json.loads(raw)
    except (UnicodeError, ValueError):
        raise AuditFailure("api_invalid_json") from None


def audit(account: str, token: str) -> dict[str, str]:
    version = api_get(account, token, "/versions/" + EXPECTED_VERSION)
    verify_version(version)
    settings = api_get(account, token, "/settings")
    verify_current_settings(settings)
    return {
        "BOOTSTRAP_VERSION": "EXISTS_NO_BINDINGS",
        "CURRENT_SETTINGS": "NO_BINDINGS",
        "CURRENT_TRAFFIC_ALLOCATION": "NOT_VERIFIED",
        "EDGE_HEALTH": "NOT_VERIFIED",
        "D1": "NOT_QUERIED",
    }


def main() -> int:
    try:
        statuses = audit(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
        )
    except (AuditFailure, TypeError):
        print("REMURA_POSTDEPLOY_AUDIT=INCONCLUSIVE_FAIL_CLOSED")
        print("MUTATION=NONE; DEPLOY=NO; WORKER=TEST_ONLY")
        return 2
    print("REMURA_POSTDEPLOY_AUDIT=EXPECTED_TEST_VERSION_CONFIRMED")
    for key, value in statuses.items():
        print(f"{key}={value}")
    print("MUTATION=NONE; DEPLOY=NO; SECRET_VALUES=NOT_EXPOSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
