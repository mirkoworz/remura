#!/usr/bin/env python3
# REMURA gateway TEST v0.8.33 — 13/11/2026 CET
# Build only. No deploy, SQL, webhook, Secret changes or automatic scheduling.
"""Prepare an ephemeral isolated OFF-only Wrangler bundle after strict LIVE GETs.

The destination Worker is immutable. This script cannot change Cloudflare.
All identities are taken from current authenticated metadata, never from chat.
The bundle remains inside RUNNER_TEMP, never a GitHub artifact or repository.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB, inspect_verified_inventory
from gateway_off_candidate_v1 import (
    EXAMPLE, WORKER, choose_candidate_namespace, make_candidate,
)
from predeploy_test_manifest_guard_v1 import verify_manifest
from off_gateway_rollback_guard_v1 import inspect_worker_bindings, RollbackUnsafe
from bootstrap_postdeploy_audit_v1 import api_get, AuditFailure

GATEWAY_SOURCE = Path(__file__).with_name("worker.mjs")
MAX_SOURCE_BYTES = 80_000


def verified_off_candidate(account_id: str, d1_token: str,
                           editor_token: str, template: object) -> dict:
    account = require_account_id(account_id)
    read_token = require_account_token(d1_token)
    if (not isinstance(editor_token, str) or len(editor_token) < 24
            or any(c.isspace() for c in editor_token)):
        raise AuditError("editor_token_unavailable")
    # Exactly two authenticated GETs. No Worker Production endpoint, D1 SQL or POST.
    inventory = api_request(
        "GET", f"/accounts/{account}/d1/database?page=1&per_page=100", read_token)
    identities = inspect_verified_inventory(inventory)
    settings = api_get(account, editor_token, "/settings")
    try:
        state = inspect_worker_bindings(
            settings, verified_test_uuid=identities[TEST_DB],
            expected_namespace=choose_candidate_namespace(account))
    except RollbackUnsafe:
        raise AuditError("worker_test_settings_unsafe") from None
    # Do not overwrite a configured Worker, even a previously OFF gateway.
    # Only bootstrap with no bindings is eligible for first OFF deployment.
    if state != "BOOTSTRAP_ALREADY_EMPTY":
        raise AuditError("worker_not_empty_bootstrap")
    result = make_candidate(template, identities, account)
    if result["name"] != WORKER or result["vars"] != {"INGEST_ENABLED": "false"}:
        raise AuditError("gateway_not_off_test")
    if result["d1_databases"][0]["database_id"] == identities[MAIN_DB]:
        raise AuditError("main_db_forbidden")
    return result


def create_ephemeral_bundle(config: dict, runner_temp: str,
                            source: Path = GATEWAY_SOURCE) -> Path:
    if verify_manifest(config) != "STRUCTURALLY_READY_OFFLINE_ONLY":
        raise AuditError("unresolved_or_unsafe_manifest")
    root = Path(runner_temp)
    if (not root.is_absolute() or not root.is_dir() or root.is_symlink()
            or "\n" in str(root) or "\r" in str(root)):
        raise AuditError("runner_temp_untrusted")
    if not source.is_file() or source.is_symlink():
        raise AuditError("gateway_source_missing")
    code = source.read_bytes()
    if not (0 < len(code) <= MAX_SOURCE_BYTES
            and b'if (!configured) return reply(503, "disabled")' in code
            and b'env?.INGEST_ENABLED === "true"' in code):
        raise AuditError("gateway_source_not_fail_closed")
    output = Path(tempfile.mkdtemp(prefix="remura-test-off-", dir=root))
    try:
        for name, data in (
            ("worker.mjs", code),
            ("wrangler.json", (json.dumps(config, separators=(",", ":")) + "\n").encode()),
        ):
            dest = output / name
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
        # No unexpected extra files, routes or Secrets. The example remains unchanged.
        if {item.name for item in output.iterdir()} != {"worker.mjs", "wrangler.json"}:
            raise AuditError("bundle_contents_changed")
        if json.loads((output / "wrangler.json").read_text()) != config:
            raise AuditError("bundle_roundtrip_mismatch")
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise
    return output


def main() -> int:
    folder = None
    try:
        account = os.getenv("REMURA_CF_ACCOUNT_ID", "")
        d1_token = os.getenv("REMURA_CF_D1_READ_TOKEN", "")
        editor = os.getenv("REMURA_CF_TEST_WORKER_EDITOR_TOKEN", "")
        env_file = os.getenv("GITHUB_ENV", "")
        runner = os.getenv("RUNNER_TEMP", "")
        if not env_file or not Path(env_file).is_file() or not runner:
            raise AuditError("github_runner_only")
        template = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        cfg = verified_off_candidate(account, d1_token, editor, template)
        folder = create_ephemeral_bundle(cfg, runner)
        # GitHub masking commands are registered before Wrangler can log binding info.
        print("::add-mask::" + cfg["d1_databases"][0]["database_id"])
        print("::add-mask::" + cfg["ratelimits"][0]["namespace_id"])
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write("REMURA_TEST_OFF_BUNDLE=" + str(folder) + "\n")
    except (AuditError, AuditFailure, RollbackUnsafe, ValueError,
            TypeError, OSError):
        if folder is not None:
            shutil.rmtree(folder, ignore_errors=True)
        print("REMURA_TEST_OFF_PREPARE=BLOCKED_FAIL_CLOSED")
        print("CLOUDFLARE_MUTATION=NONE; D1_SQL=NONE; WEBHOOK=OFF")
        return 2
    print("REMURA_TEST_OFF_PREPARE=EPHEMERAL_BUNDLE_READY")
    print("TARGET=remura-tv-webhook-test; DATABASE=EU_TEST_ONLY")
    print("INGEST=false; PREVIEW_URLS=false; SECRET=NONE; DEPLOY=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
