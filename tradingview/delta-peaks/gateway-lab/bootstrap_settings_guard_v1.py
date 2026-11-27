#!/usr/bin/env python3
# REMURA v0.8.27 — 13/11/2026 ore 18:33 CET
# GET-only metadata preflight for single existing TEST Worker; no body/secrets logged.
"""Fail-closed Cloudflare TEST Worker bootstrap inspection.

Use only before manually approved, pinned-code bootstrap deployment.
Do not touch Production, log Cloudflare responses, or accept unknown bindings.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

NAME = "remura-tv-webhook-test"
ACCOUNT_RE = re.compile(r"^[a-f0-9]{32}$")


class UnsafeBootstrap(ValueError):
    pass


def inspect_settings(body: object) -> str:
    if not isinstance(body, dict) or body.get("success") is not True:
        raise UnsafeBootstrap("unverified_api_envelope")
    info = body.get("result")
    if not isinstance(info, dict):
        raise UnsafeBootstrap("worker_settings_unknown")
    if "name" in info and info["name"] != NAME:
        raise UnsafeBootstrap("unexpected_worker_name")
    bindings = info.get("bindings")
    if not isinstance(bindings, list):
        raise UnsafeBootstrap("worker_bindings_unknown")
    if bindings:
        raise UnsafeBootstrap("worker_not_empty")
    return "EXISTING_TEST_ONLY_NO_BINDINGS"


def check_existing_worker(account_id: str, token: str) -> str:
    if not isinstance(account_id, str) or not ACCOUNT_RE.fullmatch(account_id):
        raise UnsafeBootstrap("account_id_missing")
    if not isinstance(token, str) or len(token) < 24 or any(c.isspace() for c in token):
        raise UnsafeBootstrap("token_missing_or_invalid")
    req = Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{NAME}/settings",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=12) as resp:
            if resp.status != 200:
                raise UnsafeBootstrap("worker_metadata_not_200")
            raw = resp.read(524289)
            if len(raw) > 524288:
                raise UnsafeBootstrap("oversize_metadata")
    except (HTTPError, URLError, TimeoutError, OSError):
        raise UnsafeBootstrap("cloudflare_get_failed") from None
    try:
        response = json.loads(raw)
    except (ValueError, UnicodeError):
        raise UnsafeBootstrap("metadata_json_invalid") from None
    return inspect_settings(response)


def main() -> int:
    try:
        result = check_existing_worker(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
        )
    except UnsafeBootstrap:
        print("REMURA_BOOTSTRAP_PREFLIGHT=BLOCKED_UNKNOWN_OR_UNSAFE")
        print("DEPLOY=NO; LIVE_WORKER_NOT_VERIFIED")
        return 2
    print("REMURA_BOOTSTRAP_PREFLIGHT=" + result)
    print("WORKER=remura-tv-webhook-test; BINDINGS=NONE; DEPLOY=NOT_YET")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
