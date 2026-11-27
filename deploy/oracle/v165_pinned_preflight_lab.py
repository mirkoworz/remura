#!/usr/bin/env python3
"""REMURA v1.65 pinned preflight laboratory: fixtures ONLY, never LIVE evidence.

Verifies exact frozen Git blobs and a STRICT mock two-workflow push/main CI
attestation before computing a 14-file preview digest. This does NOT query
GitHub, inspect the live machine, touch SQLite, install files or grant GO.
Even a fully successful mock attestation remains NO_GO.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import v165_release_offline_preview as preview
import v165_release_protocol_draft as protocol

SCHEMA = "remura-v165-pinned-preflight-fixture-v1"
MODE = "OFFLINE_SYNTHETIC_METADATA_ONLY"
SOURCE_COMMIT = "3819fe1450980c046533e400d283b25f37a67bd3"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
WORKFLOWS = frozenset(("price-checks.yml", "insights-checks.yml"))
SHA = re.compile(r"[0-9a-f]{40}\Z")
CI_KEYS = frozenset(("workflow", "head_sha", "head_branch", "event",
                     "status", "conclusion"))
META_KEYS = frozenset(("mode", "sourceCommit", "sourceTree",
                       "baseMainSha", "futureMainSha", "mainAtCheckSha",
                       "ciRuns"))


class FixtureRejected(ValueError):
    """Fail closed without treating synthetic CI as provider evidence."""


def require(ok, reason):
    if not ok:
        raise FixtureRejected("STOP_" + reason)


def _sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def synthetic_metadata():
    """One explicitly fictional CI fixture, never remote GitHub metadata."""
    fictional = "1" * 40
    return {
        "mode": MODE, "sourceCommit": SOURCE_COMMIT,
        "sourceTree": dict(preview.SOURCE_BLOBS),
        "baseMainSha": preview.BASE_MAIN_SHA,
        "futureMainSha": fictional, "mainAtCheckSha": fictional,
        "ciRuns": [
            {"workflow": name, "head_sha": fictional, "head_branch": "main",
             "event": "push", "status": "completed", "conclusion": "success"}
            for name in sorted(WORKFLOWS)
        ],
    }


def verify_synthetic_pins(metadata):
    """Validate a shaped fixture; intentionally NOT a live GitHub API client.

    In a future, separately reviewed installer the actual tree and CI must
    be independently fetched and authenticated, with a second main HEAD
    check under the deploy lock. This module never substitutes for that.
    """
    require(type(metadata) is dict and set(metadata) == META_KEYS,
            "STRICT_FIXTURE_FIELDS")
    require(metadata["mode"] == MODE, "SYNTHETIC_MODE_REQUIRED")
    require(metadata["sourceCommit"] == SOURCE_COMMIT, "SOURCE_COMMIT_CHANGED")
    require(metadata["baseMainSha"] == preview.BASE_MAIN_SHA, "BASE_MAIN_CHANGED")
    target = metadata["futureMainSha"]
    observed = metadata["mainAtCheckSha"]
    require(type(target) is str and SHA.fullmatch(target) is not None
            and target not in (SOURCE_COMMIT, preview.BASE_MAIN_SHA),
            "FICTIONAL_TARGET_INVALID")
    require(type(observed) is str and observed == target, "MAIN_MOVED")
    blobs = metadata["sourceTree"]
    require(type(blobs) is dict and blobs == preview.SOURCE_BLOBS
            and all(type(k) is str and type(v) is str for k, v in blobs.items()),
            "SOURCE_TREE_UNPINNED")
    runs = metadata["ciRuns"]
    require(type(runs) is list and len(runs) == len(WORKFLOWS),
            "CI_RUN_COUNT")
    seen = set()
    for run in runs:
        require(type(run) is dict and set(run) == CI_KEYS, "CI_RUN_FIELDS")
        name = run["workflow"]
        require(type(name) is str and name in WORKFLOWS and name not in seen,
                "CI_WORKFLOW_MISSING_OR_DUPLICATE")
        seen.add(name)
        require(run["head_sha"] == target and run["head_branch"] == "main"
                and run["event"] == "push" and run["status"] == "completed"
                and run["conclusion"] == "success", "CI_NOT_GREEN_PUSH_MAIN")
    require(seen == WORKFLOWS, "CI_WORKFLOW_MISSING")
    return True


def preview_manifest(sources, simulated_install_time):
    """Compute per-file digest only from the pinned prepared candidate bytes.

    Source tree is *preparatory branch*, not an installed v1.64 or main v1.65
    snapshot. No LIVE old hashes are known and no rollback proof is claimed.
    """
    require(isinstance(simulated_install_time, datetime)
            and simulated_install_time.tzinfo is not None
            and simulated_install_time.utcoffset() is not None,
            "AWARE_SIMULATED_TIME_REQUIRED")
    protocol.validate_manifest(protocol.EXISTING_FILES, protocol.NEW_FILES)
    require(set(preview.SOURCE_BLOBS) == protocol.FILE_SET, "MISMATCHED_ALLOWLIST")
    staged = preview.preview(sources, simulated_install_time=simulated_install_time)
    require(type(staged) is dict and set(staged) == protocol.FILE_SET,
            "STAGED_FILE_SET")
    planned = {}
    for name in sorted(protocol.FILE_SET):
        body = staged[name]
        require(type(body) is bytes and 0 < len(body) <= preview.MAX_READ_BYTES,
                "STAGED_BYTES_INVALID")
        planned[name] = {
            "sourceGitBlob": preview.SOURCE_BLOBS[name],
            "previewSha256": _sha256(body), "previewBytes": len(body),
            "kind": "new" if name in protocol.NEW_FILES else "existing",
        }
    for name in protocol.NEW_FILES:
        require(staged[name] == sources[name], "NEW_MODULE_MUTATED")
    require(all(staged[p].count(preview.TARGET_NAV_TAG) == 1
                for p in preview.PAGE_NAMES), "NINE_PAGE_NAV_WRONG")
    stamp = simulated_install_time.astimezone(
        __import__("zoneinfo").ZoneInfo("Europe/Rome")
    ).strftime("%d/%m/%Y %H:%M (Italia)")
    banner = (preview.TARGET_BANNER_PREFIX + stamp).encode()
    require(staged["nav.js"].count(banner) == 1
            and b"DATA_ORA_REALE_SOLO_AL_RILASCIO" not in staged["nav.js"],
            "SYNTHETIC_BANNER_WRONG")
    require(staged["sw.js"].count(preview.TARGET_SW) == 1,
            "CACHE_VERSION_WRONG")
    manifest_material = b"".join(
        name.encode("utf-8") + b"\0" + staged[name] + b"\0"
        for name in sorted(staged)
    )
    return {"files": planned,
            "previewBundleSha256": _sha256(manifest_material),
            "simulatedTimeOnly": stamp,
            "realLiveRollbackHashesKnown": False}


def evaluate(metadata, sources, *, simulated_install_time):
    verify_synthetic_pins(metadata)
    manifest = preview_manifest(sources, simulated_install_time)
    return {
        "schema": SCHEMA, "state": "PINNED_FIXTURE_PREFLIGHT_ONLY",
        "sourceGitCommitFrozen": SOURCE_COMMIT,
        "sourceFilesPinnedAndPreviewed": len(manifest["files"]),
        "existingFiles": len(protocol.EXISTING_FILES),
        "newFiles": len(protocol.NEW_FILES),
        "ninePagesPreparedInMemory": len(preview.PAGE_NAMES),
        "syntheticFixtureCiMatches": True,
        "previewBundleSha256": manifest["previewBundleSha256"],
        "actualPushMainCiVerified": False,
        "installedLiveV164Attested": False,
        "realSqliteBackupAndRestoreVerified": False,
        "realRollbackVerified": False,
        "realReleaseAuthorized": False,
        "actualDateStampedOnLivePages": False,
        "newModulesInstalled": False,
        "autoUpdaterReconciled": False,
        "realVpsContacted": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }


def main():
    parser = argparse.ArgumentParser(description="v1.65 OFFLINE fixture preflight, NO LIVE")
    parser.add_argument("--check-fixture-offline", required=True, action="store_true")
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sources = preview.read_sources(root)
    report = evaluate(synthetic_metadata(), sources,
                      simulated_install_time=datetime(2026, 11, 8, 12, 0,
                                                      tzinfo=timezone.utc))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
