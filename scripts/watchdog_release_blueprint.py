#!/usr/bin/env python3
"""Watchdog future-release blueprint and full-bundle rollback rehearsal.

OFFLINE AND NON-DEPLOYABLE. This module does not contain a CLI, service
control, network calls or any path to a live installation. It operates only
on supplied repository bytes and ephemeral synthetic predecessor files.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import tempfile

from watchdog_staging_rehearsal import verify_staged_bundle

LEGACY_PATH = "deploy/oracle/release_v164.py"
SERVER = "scripts/private_server.py"
WATCHDOG = "scripts/collector_watchdog.py"
PAGES = (
    "index.html", "asset.html", "mercati.html", "forex.html",
    "catalogo.html", "statistica-squali.html", "stato-prezzi.html",
    "fonti.html", "impostazioni.html",
)
MAX_LEGACY_SOURCE = 100_000
MAX_TOTAL_BYTES = 30_000_000


def _legacy_files(release_source):
    """Read the old v1.64 manifest as data, NEVER import/execute its installer."""
    if type(release_source) is not str or len(release_source) > MAX_LEGACY_SOURCE:
        return None
    try:
        tree = ast.parse(release_source, filename=LEGACY_PATH)
        assignments = {}
        for n in tree.body:
            if not isinstance(n, ast.Assign):
                continue
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id in ("FILES", "NEW_FILES"):
                    assignments[target.id] = ast.literal_eval(n.value)
        files = assignments.get("FILES")
        new = assignments.get("NEW_FILES")
        if (type(files) is not tuple or len(files) != 15 or
                len(set(files)) != 15 or any(type(x) is not str for x in files) or
                new != () or SERVER not in files or WATCHDOG in files or
                set(PAGES) != {x for x in files if x.endswith(".html")}):
            return None
        return files
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
        return None


def preview_bundle(legacy_source, candidate_files):
    """Verify actual candidate bytes and list future release blockers.

    Candidate bytes are NOT authenticated as a GitHub commit or actual LIVE
    files. Passing here cannot authorize a deployment or merge.
    """
    old = _legacy_files(legacy_source)
    if old is None:
        return {"state": "INVALID_LEGACY_INSTALLER", "release_authorized": False}
    manifest = (*old, WATCHDOG)
    if type(candidate_files) is not dict or set(candidate_files) != set(manifest):
        return {"state": "MANIFEST_MISMATCH", "release_authorized": False}
    if (any(type(v) is not bytes for v in candidate_files.values()) or
            sum(len(v) for v in candidate_files.values()) > MAX_TOTAL_BYTES):
        return {"state": "INVALID_CANDIDATE", "release_authorized": False}
    pins = {p: hashlib.sha256(candidate_files[p]).hexdigest() for p in manifest}
    passed, reason = verify_staged_bundle(manifest, candidate_files, pins)
    if not passed:
        return {"state": "DEPENDENCY_OR_DIGEST_INVALID", "detail": reason,
                "release_authorized": False}

    # The branch still carries the v1.64 banner/cache. An actual update MUST
    # increment the version and stamp the Italian time during installation.
    current_legacy_ui = (
        b"Aggiornamento v1.64" in candidate_files["nav.js"] and
        all(b"nav.js?v=164" in candidate_files[p] for p in PAGES) and
        b"v1.64" in candidate_files["sw.js"]
    )
    return {
        "state": "OFFLINE_BLUEPRINT_ONLY_NO_DEPLOY",
        "files": manifest,
        "sha256": pins,
        "file_count": len(manifest),
        "html_pages": len(PAGES),
        "ui_version_gate": "V164_REFERENCE_NOT_A_NEW_RELEASE" if current_legacy_ui
                           else "UNVERIFIED_REQUIRES_REVIEW",
        "required_real_gates": (
            "separate_merger_review_B89_C98_A99",
            "approved_version_and_actual_Europe_Rome_time_on_9_pages",
            "complete_real_installer_and_autoupdater_reconciliation",
            "independent_live_file_hashes_and_resources",
            "consistent_SQLite_backup_restore_offhost_and_live_rollback",
            "Oracle_costs_and_quota_after_trial",
            "explicit_operator_release_authorization",
        ),
        "release_authorized": False,
    }


def rehearse_bundle_transaction(legacy_source, candidate_files, *, fail_after=None):
    """Swap all 16 candidate files inside a PRIVATE new temp sandbox.

    The 15 predecessors are synthetic sentinel bytes. The Watchdog module
    starts ABSENT. fail_after is a 0-based installed-file index, or None.
    This is NOT a DB backup, service restart, crash-durability or VPS test.
    """
    report = preview_bundle(legacy_source, candidate_files)
    if report.get("state") != "OFFLINE_BLUEPRINT_ONLY_NO_DEPLOY":
        return {"state": "BLOCKED_PREVIEW", "release_authorized": False}
    manifest = report["files"]
    if fail_after is not None and (type(fail_after) is not int or
                                   not 0 <= fail_after < len(manifest)):
        return {"state": "INVALID_INJECTION", "release_authorized": False}

    with tempfile.TemporaryDirectory(prefix="remura-watchdog-16file-lab-") as temp:
        root = Path(temp)
        install, backup, stage = (root / "install", root / "backup", root / "stage")
        install.mkdir()
        backup.mkdir()
        stage.mkdir()
        original = {}
        for path in manifest:
            target = install / path
            target.parent.mkdir(parents=True, exist_ok=True)
            source = stage / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(candidate_files[path])
            if path != WATCHDOG:
                original[path] = b"synthetic_v164_predecessor::" + path.encode("ascii")
                target.write_bytes(original[path])
                saved = backup / path
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(original[path])

        failed = False
        for index, path in enumerate(manifest):
            target, source = install / path, stage / path
            os.replace(source, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != report["sha256"][path]:
                return {"state": "STAGED_HASH_FAILED", "release_authorized": False}
            if index == fail_after:
                failed = True
                break
        if failed:
            # Explicitly restore EVERY original, including those not yet
            # replaced; the new module is removed if it was installed.
            for path in manifest:
                target = install / path
                if path == WATCHDOG:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup / path, target)
            verified = (not (install / WATCHDOG).exists() and
                        all((install / p).read_bytes() == original[p] for p in original))
            return {
                "state": "SYNTHETIC_ALL_FILES_ROLLBACK_VERIFIED" if verified
                         else "SYNTHETIC_ROLLBACK_FAILED",
                "files_restored": len(original) if verified else 0,
                "new_module_removed": not (install / WATCHDOG).exists(),
                "release_authorized": False,
            }
        verified = all((install / p).read_bytes() == candidate_files[p] for p in manifest)
        return {
            "state": "SYNTHETIC_ALL_FILES_STAGED_NO_LIVE" if verified
                     else "SYNTHETIC_STAGING_FAILED",
            "files_staged": len(manifest) if verified else 0,
            "release_authorized": False,
        }
