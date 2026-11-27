#!/usr/bin/env python3
"""REMURA v1.65 release PROTOCOL DRAFT. No real deployment code.

A deterministic, offline-only release contract: the intended steps and their
order are checked against a strict 12-existing/2-new file manifest. It may
be reused by a future separately approved installer after independent LIVE
verification, but this module CANNOT apply updates, open SQLite, run
systemctl, reach GitHub/Tailscale, or change autoupdater state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re

SCHEMA = "remura-v165-release-protocol-offline-v1"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
BASE_MAIN_SHA = "5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74"
VERSION_BEFORE = "v1.64"
VERSION_AFTER = "v1.65"
EXISTING_FILES = (
    "scripts/private_server.py", "nav.js", "sw.js",
    "index.html", "asset.html", "mercati.html", "forex.html",
    "catalogo.html", "statistica-squali.html", "stato-prezzi.html",
    "fonti.html", "impostazioni.html",
)
NEW_FILES = (
    "scripts/storage_inventory_v165.py",
    "scripts/storage_cache_v165.py",
)
FILE_SET = frozenset((*EXISTING_FILES, *NEW_FILES))
RELEASE_SEQUENCE = (
    "baseline_v164_attested",
    "separate_authorization_and_billing_attested",
    "private_access_and_autoupdater_lock_verified",
    "v165_tree_sha_and_push_main_ci_verified",
    "preflight_live_sqlite_and_disk_verified",
    "consistent_sqlite_backup_and_isolated_restore_verified",
    "v164_rollback_bundle_sealed",
    "collector_stopped_under_lock",
    "existing_files_replaced_and_new_modules_created",
    "post_install_hashes_and_private_health_verified",
    "all_nine_version_banners_and_pwa_cache_verified",
    "autoupdater_reconciled_in_separate_pinned_step",
    "collector_continuity_and_costs_rechecked",
)
UNVERIFIED_LIVE_GATES = (
    "live_v164_installed_sha",
    "exact_live_file_hashes_and_banner_timestamp",
    "main_target_sha_and_two_push_ci_results",
    "separate_operator_authorization",
    "private_tailscale_acl_and_proxy_policy",
    "always_free_eligibility_and_billing",
    "filesystem_permissions_and_linux_fd_support",
    "consistent_live_sqlite_backup",
    "live_isolated_restore_and_integrity",
    "predeploy_code_rollback_verified",
    "real_service_health_and_collector_continuity",
    "autoupdater_state_sha_and_lock",
)
STATES = ("NOT_STARTED", *RELEASE_SEQUENCE, "ROLLED_BACK_SYNTHETIC", "FAILED_CLOSED_SYNTHETIC")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class ReleaseGuardError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ReleaseGuardError("STOP_" + reason)


def validate_manifest(existing, new):
    """Reject arbitrary paths, omissions, duplicates, private data and old modules."""
    require(type(existing) in (tuple, list) and type(new) in (tuple, list),
            "MANIFEST_TYPE")
    require(tuple(existing) == EXISTING_FILES and tuple(new) == NEW_FILES,
            "EXACT_FILE_MANIFEST")
    require(len(FILE_SET) == 14 and len(EXISTING_FILES) == 12 and len(NEW_FILES) == 2,
            "MANIFEST_COUNT")
    require(all(not name.startswith((".", "/", "private/", "local/"))
                and ".." not in name.split("/") and "\\" not in name
                for name in FILE_SET), "MANIFEST_SAFETY")
    return True


def sanitized_snapshot():
    """Never claim that a CI fixture attests LIVE, even when tests are green."""
    validate_manifest(EXISTING_FILES, NEW_FILES)
    return {
        "schema": SCHEMA,
        "targetVersion": VERSION_AFTER,
        "sourceVersion": VERSION_BEFORE,
        "baseMainShaOnlyNotLiveSha": BASE_MAIN_SHA,
        "existingFiles": len(EXISTING_FILES),
        "newModules": len(NEW_FILES),
        "ninePageBannerPlanned": True,
        "requiresRealItalianTimestampAtInstall": True,
        "storageMetadataOptInDefaultOff": True,
        "preflightEvidenceRequired": list(UNVERIFIED_LIVE_GATES),
        "releaseOrder": list(RELEASE_SEQUENCE),
        "installerAvailable": False,
        "applyAvailable": False,
        "realLiveEvidenceVerified": False,
        "realBackupOrRestoreVerified": False,
        "realRollbackVerified": False,
        "realCostsVerified": False,
        "productionAuthorizationVerified": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }


def estimate_workspace_bytes(db_bytes=None, wal_bytes=None, shm_bytes=None,
                             candidate_bytes=None):
    """Conservative OFFLINE reserve proposal, not actual VPS capacity check.

    The proposed reserve accounts for multiple snapshot/restore generations,
    rollback, plus 512 MiB buffer. If any number is unknown -> UNKNOWN.
    A positive number never authorizes release.
    """
    values = (db_bytes, wal_bytes, shm_bytes, candidate_bytes)
    if any(v is None for v in values):
        return {"state": "UNKNOWN_REAL_FILE_BYTES_NOT_MEASURED",
                "minimumFreeBytesProposed": None, "operationalDecision": NO_GO}
    require(all(type(v) is int and 0 <= v <= 8 * 1024**3 for v in values),
            "INVALID_SIZE_INPUT")
    require(db_bytes > 0 and candidate_bytes > 0, "REQUIRED_SOURCE_ZERO")
    proposed = 4 * (db_bytes + wal_bytes + shm_bytes) + 3 * candidate_bytes + 512 * 1024**2
    return {"state": "OFFLINE_ONLY_ESTIMATE_NOT_FREE_CAPACITY_ATTESTATION",
            "minimumFreeBytesProposed": proposed, "operationalDecision": NO_GO}


def advance_synthetic(state, event, *, evidence=None):
    """Finite-state design. 'evidence' is a TEST marker, NEVER a signed proof."""
    require(type(state) is str and state in STATES, "INVALID_STATE")
    require(type(event) is str and event in RELEASE_SEQUENCE, "INVALID_EVENT")
    require(state not in ("ROLLED_BACK_SYNTHETIC", "FAILED_CLOSED_SYNTHETIC"),
            "TERMINAL_STATE")
    index = 0 if state == "NOT_STARTED" else RELEASE_SEQUENCE.index(state) + 1
    require(index < len(RELEASE_SEQUENCE), "SEQUENCE_COMPLETE")
    require(event == RELEASE_SEQUENCE[index], "OUT_OF_ORDER")
    require(type(evidence) is dict and set(evidence) == {"synthetic", "step"},
            "SYNTHETIC_EVIDENCE_REQUIRED")
    require(evidence["synthetic"] is True and evidence["step"] == event,
            "ONLY_SYNTHETIC_EVIDENCE_ACCEPTED")
    return event


def rollback_synthetic(state):
    require(type(state) is str and state in STATES, "INVALID_STATE")
    require(state not in ("ROLLED_BACK_SYNTHETIC", "FAILED_CLOSED_SYNTHETIC"),
            "TERMINAL_STATE")
    return "ROLLED_BACK_SYNTHETIC"


def replay_offline(*, fail_after=None):
    """A model sequence; never performs any named step's real-world effect."""
    require(fail_after is None or fail_after in RELEASE_SEQUENCE, "UNKNOWN_FAIL_POINT")
    state = "NOT_STARTED"
    visited = []
    for event in RELEASE_SEQUENCE:
        state = advance_synthetic(state, event,
                                  evidence={"synthetic": True, "step": event})
        visited.append(event)
        if event == fail_after:
            state = rollback_synthetic(state)
            break
    return {
        "schema": SCHEMA,
        "state": "OFFLINE_PROTOCOL_REHEARSAL_ONLY",
        "lastSyntheticState": state,
        "syntheticStepsVisited": len(visited),
        "syntheticRollbackTriggered": fail_after is not None,
        "productionInstallerExecuted": False,
        "realVpsChanged": False,
        "sqliteLiveTouched": False,
        "realRollbackPerformed": False,
        "operatorAuthorizationObtained": False,
        "operationalDecision": NO_GO,
    }


def main():
    parser = argparse.ArgumentParser(description="Draft v1.65 OFFLINE plan, never installer")
    parser.add_argument("--plan-offline", action="store_true", required=True)
    args = parser.parse_args()
    _ = args
    print(json.dumps(sanitized_snapshot(), sort_keys=True))


if __name__ == "__main__":
    main()
