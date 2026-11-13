#!/usr/bin/env python3
# REMURA TradingView LAB v0.8.35 — 13/11/2026 CET
# GET-only preflight and post-deploy metadata checks, no mutation or secrets in logs.
"""Recognize precisely scoped TEST Worker state for an emergency inert-code stop.

This tool NEVER deploys or sends a webhook. A separate owner-only manual workflow
must provide the decision to deploy a reviewed, inert bootstrap version.
The Cloudflare secret can persist when code is redeployed; a remaining *named*
secret is not proof of active ingest. Never inspect, copy, print or accept its text.
"""
from __future__ import annotations

import os
import re

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import TEST_DB, inspect_verified_inventory
from gateway_off_candidate_v1 import choose_candidate_namespace
from bootstrap_postdeploy_audit_v1 import api_get

WORKER = "remura-tv-webhook-test"
SECRET = "WEBHOOK_TOKEN_SHA256"
UUID = re.compile(r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$", re.I)
NAMESPACE = re.compile(r"^[1-9][0-9]{0,14}$")


class StopUnsafe(ValueError):
    """Unrecognized settings. Do not deploy even in an emergency."""


def binding_map(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise StopUnsafe("invalid_settings_envelope")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise StopUnsafe("missing_settings")
    if "name" in result and result["name"] != WORKER:
        raise StopUnsafe("wrong_worker")
    bindings = result.get("bindings")
    if not isinstance(bindings, list) or len(bindings) > 4:
        raise StopUnsafe("bindings_unknown")
    if any(not isinstance(item, dict) or
           not isinstance(item.get("name"), str) or
           not isinstance(item.get("type"), str) for item in bindings):
        raise StopUnsafe("binding_shape")
    names = [item["name"] for item in bindings]
    if len(set(names)) != len(names):
        raise StopUnsafe("duplicate_binding")
    return {item["name"]: item for item in bindings}


def inspect_before_stop(payload: object, *, test_uuid: str,
                        namespace: str) -> str:
    if not isinstance(test_uuid, str) or not UUID.fullmatch(test_uuid):
        raise StopUnsafe("test_uuid_unknown")
    if not isinstance(namespace, str) or not NAMESPACE.fullmatch(namespace):
        raise StopUnsafe("namespace_unknown")
    bindings = binding_map(payload)
    if not bindings:
        return "ALREADY_EMPTY_BOOTSTRAP"
    base = {"TELEMETRY_DB", "INGEST_RATE_LIMITER", "INGEST_ENABLED"}
    if set(bindings) not in (base, base | {SECRET}):
        raise StopUnsafe("unexpected_bindings")
    db = bindings["TELEMETRY_DB"]
    if db.get("type") != "d1" or db.get("id") != test_uuid:
        raise StopUnsafe("wrong_database")
    rl = bindings["INGEST_RATE_LIMITER"]
    if (rl.get("type") != "ratelimit" or
            rl.get("namespace_id") != namespace or
            rl.get("simple") != {"limit": 20, "period": 60}):
        raise StopUnsafe("limiter_untrusted")
    flag = bindings["INGEST_ENABLED"]
    if flag.get("type") != "plain_text" or flag.get("text") not in ("true", "false"):
        raise StopUnsafe("unknown_ingest_flag")
    if SECRET in bindings and bindings[SECRET].get("type") != "secret_text":
        raise StopUnsafe("unexpected_secret_type")
    suffix = "WITH_HASH_SECRET" if SECRET in bindings else "NO_SECRET"
    state = "ON" if flag["text"] == "true" else "OFF"
    return "TEST_GATEWAY_" + state + "_" + suffix


def inspect_after_inert_deploy(payload: object) -> str:
    """Wrangler preserves existing secrets; bootstrap must have no DB/limiter/ON."""
    bindings = binding_map(payload)
    if not bindings:
        return "INERT_NO_BINDINGS"
    if set(bindings) == {SECRET} and bindings[SECRET].get("type") == "secret_text":
        return "INERT_SECRET_STILL_STORED"
    raise StopUnsafe("unexpected_remaining_binding")


def preflight(account_id: str, d1_read: str, test_editor: str) -> str:
    account = require_account_id(account_id)
    read_token = require_account_token(d1_read)
    if (not isinstance(test_editor, str) or len(test_editor) < 24 or
            any(c.isspace() for c in test_editor)):
        raise StopUnsafe("editor_token_unknown")
    # Two read-only GETs; no API call to Worker Production or a D1 SQL endpoint.
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100", read_token)
    ids = inspect_verified_inventory(inventory)
    worker_settings = api_get(account, test_editor, "/settings")
    return inspect_before_stop(
        worker_settings, test_uuid=ids[TEST_DB],
        namespace=choose_candidate_namespace(account))


def postdeploy(account_id: str, test_editor: str) -> str:
    account = require_account_id(account_id)
    if (not isinstance(test_editor, str) or len(test_editor) < 24 or
            any(c.isspace() for c in test_editor)):
        raise StopUnsafe("editor_token_unknown")
    return inspect_after_inert_deploy(api_get(account, test_editor, "/settings"))


def main() -> int:
    try:
        result = preflight(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
        )
    except (StopUnsafe, AuditError, TypeError, ValueError):
        print("REMURA_TEST_EMERGENCY_PREFLIGHT=BLOCKED_FAIL_CLOSED")
        print("MUTATION=NONE; SECRETS_LOGGED=NO")
        return 2
    print("REMURA_TEST_EMERGENCY_PREFLIGHT=" + result)
    print("TARGET=TEST_WORKER_ONLY; PRODUCTION=NOT_TARGETED; MUTATION=NONE")
    return 0


def after_main() -> int:
    try:
        state = postdeploy(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
        )
    except (StopUnsafe, AuditError, TypeError, ValueError):
        print("REMURA_TEST_EMERGENCY_POSTDEPLOY=UNVERIFIED_FAIL_CLOSED")
        return 2
    print("REMURA_TEST_EMERGENCY_POSTDEPLOY=" + state)
    print("NO_D1_OR_RATE_LIMITER=VERIFIED_SETTINGS; SECRET_VALUE=NEVER_READ")
    print("EDGE_TRAFFIC_ALLOCATION=NOT_VERIFIED; HTTP_HEALTH=NOT_VERIFIED")
    return 0


if __name__ == "__main__":
    import sys
    if sys.argv == ["%s" % sys.argv[0]]:
        raise SystemExit(main())
    if sys.argv[1:] == ["--postdeploy"]:
        raise SystemExit(after_main())
    print("REMURA_TEST_EMERGENCY=INVALID_OPERATION")
    raise SystemExit(2)
