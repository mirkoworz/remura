#!/usr/bin/env python3
# REMURA D1 TEST TARGET PREFLIGHT v0.8.22 — 13/11/2026, ore 15:17 CET
# SOLO DUE GET Cloudflare API autenticati; mai POST, SQL, Worker deploy, Secrets in log.
"""Verify real D1 TEST identity against D1 main *without* persisting UUIDs.

This is a one-off pre-deployment metadata check, not an approval to deploy.
It reads only account-level D1 inventory and validates the immutable example
manifest is intentionally blocked. No credentials/identifiers are printed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
    verify_account_token,
)
from cloudflare_d1_account_storage_guard import parse_inventory
from predeploy_test_manifest_guard_v1 import verify_manifest, ManifestError

MAIN_DB = "remura-tv-lab"
TEST_DB = "remura-tv-lab-test"
TEMPLATE = Path(__file__).with_name("wrangler.webhook-test.EXAMPLE.json")


def inspect_verified_inventory(payload: object) -> dict[str, str]:
    entries = parse_inventory(payload)
    dbs = {name: (uid, region) for name, uid, region in entries}
    # parse_inventory already ensures unique ids/names, both databases,
    # required EU jurisdiction, pagination completeness and valid UUIDs.
    main_id, main_region = dbs[MAIN_DB]
    test_id, test_region = dbs[TEST_DB]
    if main_id == test_id or main_region != "eu" or test_region != "eu":
        raise AuditError("test_db_not_isolated_in_eu")
    return {MAIN_DB: main_id, TEST_DB: test_id}


def inspect_template(template: object, database_ids: dict[str, str]) -> str:
    try:
        status = verify_manifest(template)
    except ManifestError:
        raise AuditError("unresolved_manifest_invalid") from None
    if status != "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS":
        raise AuditError("template_must_remain_undeployable")
    # TEST UUID resolves only *in memory*, never to repository or logs.
    dbs = template.get("d1_databases")
    if not isinstance(dbs, list) or len(dbs) != 1:
        raise AuditError("template_d1_shape_wrong")
    if dbs[0].get("database_name") != TEST_DB or dbs[0].get("binding") != "TELEMETRY_DB":
        raise AuditError("template_test_binding_mismatch")
    if database_ids.get(TEST_DB) == database_ids.get(MAIN_DB):
        raise AuditError("test_uuid_aliases_main")
    return "VERIFIED_ISOLATED_BUT_UNRESOLVED"


def preflight(account_id: str, token: str, template: object) -> dict[str, str]:
    # Verify safe template before API calls; never resolve IDs into it.
    inspect_template(template, {MAIN_DB: "main", TEST_DB: "test"})
    account = require_account_id(account_id)
    token = require_account_token(token)
    verify_account_token(api_request("GET", f"/accounts/{account}/tokens/verify", token))
    inventory = api_request("GET", f"/accounts/{account}/d1/database?page=1&per_page=100", token)
    identities = inspect_verified_inventory(inventory)
    inspect_template(template, identities)
    return {
        "D1_MAIN_IDENTITY": "VERIFIED_EU",
        "D1_TEST_IDENTITY": "VERIFIED_EU_DIFFERENT_FROM_MAIN",
        "TEST_WORKER_MANIFEST": "BLOCKED_UNRESOLVED_IDS",
        "LIMITER_NAMESPACE": "UNASSIGNED",
        "WORKER_DEPLOY": "NOT_AUTHORIZED",
        "WORKER_INGEST": "NOT_ENABLED",
        "REAL_CLOUDFLARE_WORKER_SETTINGS": "NOT_READ",
    }


def main() -> int:
    try:
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        status = preflight(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""), template,
        )
    except (AuditError, OSError, ValueError, TypeError):
        print("REMURA_TEST_TARGET_PREFLIGHT=UNKNOWN_FAIL_CLOSED")
        print("DEPLOY=NO; DATABASE_WRITE=NO; HTTP_GET_D1_METADATA_ONLY=YES")
        return 2
    print("REMURA_TEST_TARGET_PREFLIGHT=VERIFIED_TEST_DB_IDENTITY_ONLY")
    for key, value in status.items():
        print(f"{key}={value}")
    print("PROVENANCE=D1_REAL_METADATA_ONLY; UUID_NOT_RECORDED_OR_PRINTED")
    print("DEPLOY=NO; DATABASE_WRITE=NO; WEBHOOK=OFF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
