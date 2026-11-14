#!/usr/bin/env python3
# REMURA TradingView LAB v0.8.37 — 14/11/2026, ore 01:55 CET
# MANIFEST BUILD ONLY. No Worker deploy, API POST, D1 SQL, secret access, or alerts.
"""Prepare only an ephemeral TEST gateway ON bundle from authenticated OFF+Secret.

This script DOES NOT authorize ON. Future owner-only manual workflow must run
a fresh preflight, dry-run and explicit dispatch before any Cloudflare deploy.
The existing Cloudflare secret's value is never read, printed or copied.
"""
from __future__ import annotations
from copy import deepcopy
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB, inspect_verified_inventory
from emergency_stop_test_guard_v1 import inspect_before_stop, StopUnsafe
from gateway_off_candidate_v1 import EXAMPLE, make_candidate, choose_candidate_namespace
from predeploy_test_manifest_guard_v1 import verify_manifest
from prepare_test_off_bundle_v1 import create_ephemeral_bundle
from bootstrap_postdeploy_audit_v1 import api_get

ON_FLAG = {"INGEST_ENABLED": "true"}


def build_on_candidate(account_id: str, d1_read: str, test_editor: str,
                       template: object, *, weekend_refresh: bool = False) -> dict:
    account = require_account_id(account_id)
    read_token = require_account_token(d1_read)
    if (not isinstance(test_editor, str) or len(test_editor) < 24 or
            any(c.isspace() for c in test_editor)):
        raise AuditError("editor_token_missing")
    # Two metadata GET calls only. Production Worker and D1 queries are prohibited.
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100", read_token)
    ids = inspect_verified_inventory(inventory)
    current = api_get(account, test_editor, "/settings")
    try:
        state = inspect_before_stop(
            current, test_uuid=ids[TEST_DB],
            namespace=choose_candidate_namespace(account))
    except StopUnsafe:
        raise AuditError("worker_test_settings_unsafe") from None
    # A refresh may ONLY replace the already ON isolated TEST Worker.
    expected = ("TEST_GATEWAY_ON_WITH_HASH_SECRET" if weekend_refresh
                else "TEST_GATEWAY_OFF_WITH_HASH_SECRET")
    if state != expected:
        raise AuditError("unexpected_test_ingest_state")
    off = make_candidate(template, ids, account)
    if verify_manifest(off) != "STRUCTURALLY_READY_OFFLINE_ONLY":
        raise AuditError("off_candidate_not_verified")
    if off["d1_databases"][0]["database_id"] == ids[MAIN_DB]:
        raise AuditError("main_db_forbidden")
    # Change EXACTLY the OFF flag; never put raw or hashed secret into manifest.
    on = deepcopy(off)
    on["vars"] = dict(ON_FLAG)
    return on


def validate_on_candidate(candidate: object) -> dict:
    if not isinstance(candidate, dict) or candidate.get("vars") != ON_FLAG:
        raise AuditError("ingest_not_explicitly_on")
    # The verified OFF configuration is reused as the structural reference.
    equivalent_off = deepcopy(candidate)
    equivalent_off["vars"] = {"INGEST_ENABLED": "false"}
    if verify_manifest(equivalent_off) != "STRUCTURALLY_READY_OFFLINE_ONLY":
        raise AuditError("manifest_not_test_isolated")
    if "WEBHOOK_TOKEN_SHA256" in json.dumps(candidate):
        raise AuditError("secret_must_remain_external")
    if candidate.get("preview_urls") is not False:
        raise AuditError("preview_must_be_disabled")
    # '$comment' belongs only to the EXAMPLE schema and causes Wrangler warnings.
    # Strip it only from the temporary runtime deploy manifest, not from the source.
    runtime = deepcopy(candidate)
    runtime.pop("$comment", None)
    if set(runtime) != set(candidate) - {"$comment"}:
        raise AuditError("unexpected_runtime_manifest")
    return runtime


def make_private_on_bundle(candidate: dict, runner_temp: str) -> Path:
    runtime = validate_on_candidate(candidate)
    off = deepcopy(candidate)
    off["vars"] = {"INGEST_ENABLED": "false"}
    folder = create_ephemeral_bundle(off, runner_temp)
    try:
        # Write the ON config as a private temp file, then atomically replace
        # the earlier OFF config; no secret values are written.
        tmp = folder / "wrangler-next.json"
        with open(tmp, "x", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(json.dumps(runtime, separators=(",", ":")) + "\n")
        tmp.replace(folder / "wrangler.json")
        if {p.name for p in folder.iterdir()} != {"worker.mjs", "wrangler.json"}:
            raise AuditError("unexpected_files_in_bundle")
        if json.loads((folder / "wrangler.json").read_text("utf-8")) != runtime:
            raise AuditError("bundle_roundtrip_error")
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return folder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend-refresh", action="store_true")
    args = parser.parse_args()
    bundle = None
    try:
        if args.weekend_refresh:
            now = datetime.datetime.now(datetime.timezone.utc)
            start = datetime.datetime(2026, 11, 14, tzinfo=datetime.timezone.utc)
            end = datetime.datetime(2026, 11, 16, tzinfo=datetime.timezone.utc)
            if not start <= now < end:
                raise AuditError("weekend_refresh_expired")
        envfile = os.getenv("GITHUB_ENV", "")
        runner = os.getenv("RUNNER_TEMP", "")
        if not envfile or not Path(envfile).is_file() or not runner:
            raise AuditError("github_runner_required")
        candidate = build_on_candidate(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
            os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", ""),
            json.loads(EXAMPLE.read_text(encoding="utf-8")),
            weekend_refresh=args.weekend_refresh)
        bundle = make_private_on_bundle(candidate, runner)
        print("::add-mask::" + candidate["d1_databases"][0]["database_id"])
        print("::add-mask::" + candidate["ratelimits"][0]["namespace_id"])
        with open(envfile, "a", encoding="utf-8") as f:
            f.write("REMURA_TEST_ON_BUNDLE=" + str(bundle) + "\n")
    except (AuditError, StopUnsafe, OSError, TypeError, ValueError):
        if bundle is not None:
            shutil.rmtree(bundle, ignore_errors=True)
        print("REMURA_TEST_INGEST_ON_PREPARE=BLOCKED_FAIL_CLOSED")
        print("DEPLOY=NO; TOKEN_READ=NO; WORKER_PRODUCTION=NOT_TARGETED")
        return 2
    print("REMURA_TEST_INGEST_ON_PREPARE=EPHEMERAL_ONLY_READY")
    print("TARGET=TEST_WORKER_ONLY; DATABASE=EU_TEST_ONLY; SOURCE=PINNED")
    print("INGEST_ON=ONLY_FUTURE_OWNER_MANUAL; SECRET=NAME_VERIFIED_NOT_READ")
    print("DEPLOY=NOT_PERFORMED; DATA_WRITES=NONE; COST_APPROVAL=NOT_ASSUMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
