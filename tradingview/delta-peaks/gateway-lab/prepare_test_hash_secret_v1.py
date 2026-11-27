#!/usr/bin/env python3
# REMURA TradingView LAB v0.8.36 — 13/11/2026 CET
# GET-only D1/Worker preflight plus temporary bundle. No secret write or deploy.
"""Prepare a TEST-only, OFF-only bundle for later owner-run Wrangler secret put.

A strong URL token must be generated on the user's own device. ONLY its SHA-256
hex digest is stored as an encrypted GitHub Actions secret and later as a
Cloudflare Worker secret. Never print or save the raw URL token here.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import shutil

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import TEST_DB, inspect_verified_inventory
from gateway_off_candidate_v1 import EXAMPLE, choose_candidate_namespace, make_candidate
from emergency_stop_test_guard_v1 import inspect_before_stop, StopUnsafe
from bootstrap_postdeploy_audit_v1 import api_get
from prepare_test_off_bundle_v1 import create_ephemeral_bundle

HASH_RE = re.compile(r"^[a-f0-9]{64}$")
GITHUB_SECRET_NAME = "REMURA_CF_TV_TEST_WEBHOOK_SHA256"


def validate_hash_secret(value: object) -> None:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise AuditError("missing_or_invalid_test_hash")


def prepare(account_id: str, d1_token: str, editor_token: str, template: object) -> dict:
    account = require_account_id(account_id)
    read_token = require_account_token(d1_token)
    if (not isinstance(editor_token, str) or len(editor_token) < 24 or
            any(c.isspace() for c in editor_token)):
        raise AuditError("editor_missing")
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100", read_token)
    ids = inspect_verified_inventory(inventory)
    metadata = api_get(account, editor_token, "/settings")
    try:
        status = inspect_before_stop(
            metadata, test_uuid=ids[TEST_DB],
            namespace=choose_candidate_namespace(account))
    except StopUnsafe:
        raise AuditError("current_test_state_unsafe") from None
    if status != "TEST_GATEWAY_OFF_NO_SECRET":
        raise AuditError("secret_setup_requires_off_without_secret")
    return make_candidate(template, ids, account)


def main() -> int:
    path = None
    try:
        validate_hash_secret(os.getenv(GITHUB_SECRET_NAME, ""))
        envfile = os.getenv("GITHUB_ENV", "")
        runner = os.getenv("RUNNER_TEMP", "")
        if not envfile or not Path(envfile).is_file() or not runner:
            raise AuditError("github_runner_required")
        template = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        cfg = prepare(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""), template)
        path = create_ephemeral_bundle(cfg, runner)
        print("::add-mask::" + cfg["d1_databases"][0]["database_id"])
        print("::add-mask::" + cfg["ratelimits"][0]["namespace_id"])
        with open(envfile, "a", encoding="utf-8") as f:
            f.write("REMURA_TEST_SECRET_BUNDLE=" + str(path) + "\n")
    except (AuditError, StopUnsafe, OSError, TypeError, ValueError):
        if path is not None:
            shutil.rmtree(path, ignore_errors=True)
        print("REMURA_TEST_HASH_SECRET_PREFLIGHT=BLOCKED_FAIL_CLOSED")
        print("CLOUDFLARE_MUTATION=NONE; SECRET_VALUE_NOT_PRINTED=YES")
        return 2
    print("REMURA_TEST_HASH_SECRET_PREFLIGHT=OFF_NO_SECRET_VERIFIED")
    print("WORKER=TEST_ONLY; D1=EU_TEST_ONLY; INGEST=false; PREVIEW=false")
    print("HASH=FORMAT_CHECKED_NOT_ECHOED; RAW_TOKEN=NOT_RECEIVED")
    print("UPLOAD=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
