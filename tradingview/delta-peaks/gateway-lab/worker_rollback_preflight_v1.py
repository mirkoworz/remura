#!/usr/bin/env python3
# REMURA v0.8.32 — 13/11/2026 ore 21:06 CET
# GET-only future manual rollback preflight; never deploys, writes D1 or logs secrets.
"""Permit rollback ONLY from empty TEST bootstrap or strictly verified OFF TEST gateway.

Paired with an explicit, manually dispatched pinned-source rollback workflow.
Does not offer an endpoint to modify Cloudflare or query D1 rows.
"""
from __future__ import annotations

import os

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import TEST_DB, inspect_verified_inventory
from gateway_off_candidate_v1 import choose_candidate_namespace
from bootstrap_postdeploy_audit_v1 import api_get
from off_gateway_rollback_guard_v1 import inspect_worker_bindings, RollbackUnsafe


def preflight(account_id: str, d1_read_token: str, test_editor_token: str) -> str:
    account = require_account_id(account_id)
    read_token = require_account_token(d1_read_token)
    if (not isinstance(test_editor_token, str) or len(test_editor_token) < 24
            or any(ch.isspace() for ch in test_editor_token)):
        raise AuditError("editor_token_unavailable")
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100",
        read_token)
    identity = inspect_verified_inventory(inventory)
    current = api_get(account, test_editor_token, "/settings")
    try:
        return inspect_worker_bindings(
            current,
            verified_test_uuid=identity[TEST_DB],
            expected_namespace=choose_candidate_namespace(account),
        )
    except RollbackUnsafe:
        raise AuditError("worker_rollback_target_unsafe") from None


def main() -> int:
    try:
        state = preflight(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
        )
    except (AuditError, TypeError, ValueError):
        print("REMURA_TEST_ROLLBACK_PREFLIGHT=BLOCKED_FAIL_CLOSED")
        print("DEPLOY=NO; WRONG_WORKER_OR_BINDINGS=UNKNOWN")
        return 2
    print("REMURA_TEST_ROLLBACK_PREFLIGHT=" + state)
    print("TARGET=remura-tv-webhook-test; INGEST=OFF_OR_BOOTSTRAP_ONLY")
    print("D1_TEST_IDENTITY=VERIFIED_EU; MAIN_DB=NOT_TARGETED")
    print("TOKEN_OR_UUID_OUTPUT=NONE; DEPLOY=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
