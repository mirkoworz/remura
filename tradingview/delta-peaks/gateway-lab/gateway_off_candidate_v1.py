#!/usr/bin/env python3
# REMURA v0.8.31 — 13/11/2026, ore 21:13 CET
# PREP ONLY. No deployment, webhook, worker settings edit or database SQL.
"""Prepare an OFF-only TEST gateway binding *in memory* from authenticated D1 metadata.

No IDs are written to git, disk or logs. The candidate is NOT a deploy
authorization, and this script has no CLI path to upload or deploy it.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id,
    require_account_token, verify_account_token,
)
from d1_test_target_preflight_v1 import (
    MAIN_DB, TEST_DB, inspect_verified_inventory,
)
from predeploy_test_manifest_guard_v1 import verify_manifest, ManifestError

EXAMPLE = Path(__file__).with_name("wrangler.webhook-test.EXAMPLE.json")
WORKER = "remura-tv-webhook-test"


def choose_candidate_namespace(account: str) -> str:
    """12-digit deterministic candidate. Uniqueness against other namespaces UNKNOWN."""
    if not isinstance(account, str) or len(account) != 32:
        raise AuditError("account_invalid")
    source = (account + "|remura-tv-webhook-test|limiter-v1").encode("ascii")
    n = int.from_bytes(hashlib.sha256(source).digest()[:8], "big") % 10**11
    return "8" + str(n).zfill(11)


def make_candidate(template: object, ids: dict[str, str], account: str) -> dict:
    try:
        if verify_manifest(template) != "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS":
            raise AuditError("template_not_undeployable")
    except ManifestError:
        raise AuditError("template_guard_failed") from None
    main_id, test_id = ids.get(MAIN_DB), ids.get(TEST_DB)
    if not (isinstance(main_id, str) and isinstance(test_id, str)
            and main_id != test_id):
        raise AuditError("db_test_identity_unverified")
    cfg = deepcopy(template)
    cfg["d1_databases"][0]["database_id"] = test_id
    cfg["ratelimits"][0]["namespace_id"] = choose_candidate_namespace(account)
    try:
        if verify_manifest(cfg) != "STRUCTURALLY_READY_OFFLINE_ONLY":
            raise AuditError("candidate_guard_failed")
    except ManifestError:
        raise AuditError("candidate_guard_failed") from None
    if (cfg["name"] != WORKER or
            cfg["d1_databases"][0]["database_name"] != TEST_DB or
            cfg["d1_databases"][0]["database_id"] == main_id or
            cfg["preview_urls"] is not False or
            cfg["vars"] != {"INGEST_ENABLED": "false"}):
        raise AuditError("candidate_not_test_off")
    return cfg


def audit(account_id: str, token: str, template: object) -> dict[str, str]:
    account = require_account_id(account_id)
    token = require_account_token(token)
    verify_account_token(api_request(
        "GET", f"/accounts/{account}/tokens/verify", token))
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100", token)
    identities = inspect_verified_inventory(inventory)
    _ = make_candidate(template, identities, account)
    return {
        "TARGET_WORKER": "remura-tv-webhook-test",
        "TARGET_D1": "EU_TEST_IDENTITY_MATCHED",
        "D1_MAIN": "NOT_TARGETED",
        "INGEST_ENABLED": "FALSE",
        "PREVIEW_URLS": "DISABLED_IN_CANDIDATE",
        "RATE_LIMITER": "SYNTACTICALLY_READY_NAMESPACE_COLLISION_UNKNOWN",
        "WEBHOOK_SECRET": "NOT_ATTACHED",
        "DEPLOY": "NOT_AUTHORIZED",
        "DATA_WRITES": "NONE",
    }


def main() -> int:
    try:
        template = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        result = audit(os.getenv("REMURA_CF_ACCOUNT_ID", ""),
                       os.getenv("REMURA_CF_D1_READ_TOKEN", ""), template)
    except (AuditError, TypeError, ValueError, OSError):
        print("REMURA_TEST_OFF_CANDIDATE=BLOCKED_FAIL_CLOSED")
        print("DEPLOY=NO; WRITES=NO; SECRETS_NOT_EXPOSED=YES")
        return 2
    print("REMURA_TEST_OFF_CANDIDATE=VERIFIED_IN_MEMORY_ONLY")
    for key, value in result.items():
        print(f"{key}={value}")
    print("NO_UUID_OR_NAMESPACE_LOGGED=YES; CLOUDFLARE_MUTATION=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
