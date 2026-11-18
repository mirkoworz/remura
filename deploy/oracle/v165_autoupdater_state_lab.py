#!/usr/bin/env python3
"""REMURA v1.65: simulated installed-version and updater-state reconciliation.

STRICTLY OFFLINE. All writable paths are created inside a disposable temporary
directory from this module; inputs are invented bytes and MOCK CI attestations.
The real updater, VPS, DB, network, credentials, services, and GitHub are NEVER
contacted. A successful fixture is not authorization to release or reconcile.

This tests the essential design separation:
  1. An installed code transition does NOT change the updater state.
  2. Reconciliation requires an exact candidate, verified synthetic rollback,
     local fixture lock, a second matching mocked main HEAD, two push/main CI
     mock results, idle updater and synthetic health.
  3. Rollback AFTER reconciliation creates an explicit mismatch: do NOT silently
     rewrite updater state. A future independently reviewed inverse reconcile
     will be necessary, under authorization and exclusive lock.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile

import v165_release_protocol_draft as protocol
import v165_pinned_preflight_lab as pinned
import v165_rollback_bundle_lab as rollback

MODE = "OFFLINE_SYNTHETIC_STATE_ONLY"
SCHEMA = "remura-v165-synthetic-updater-reconcile-v1"
NO_GO = protocol.NO_GO
OLD_FAKE_SHA = "a" * 40
TARGET_FAKE_SHA = "1" * 40
FAULTS = frozenset((
    "stop_before_reconcile", "rollback_before_reconcile",
    "rollback_after_reconcile", "main_moved", "bad_ci_event",
    "updater_busy", "no_lock", "health_failed",
    "backup_unverified", "state_tampered", "candidate_tampered",
))
STATE_KEYS = frozenset((
    "enabled", "installedSha", "targetSha", "state",
    "manualSha", "skippedSha", "failedSha", "message",
))


class StateLabStop(ValueError):
    """Failure of invented fixture only; no production impact."""


def require(condition, reason):
    if not condition:
        raise StateLabStop("STOP_" + reason)


def _prior_state():
    return {
        "enabled": True, "installedSha": OLD_FAKE_SHA,
        "targetSha": OLD_FAKE_SHA, "state": "up_to_date",
        "manualSha": "", "skippedSha": "", "failedSha": "",
        "message": "FAKE_OLD_V164_ONLY",
    }


def _encode_state(record):
    require(type(record) is dict and set(record) == STATE_KEYS,
            "STATE_FIELDS")
    require(type(record["enabled"]) is bool
            and all(type(record[k]) is str for k in STATE_KEYS - {"enabled"}),
            "STATE_TYPES")
    return (json.dumps(record, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _read_state(path):
    try:
        raw = rollback._regular_bytes(path)
        record = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise StateLabStop("STOP_INVALID_FAKE_STATE_FILE") from exc
    require(type(record) is dict and set(record) == STATE_KEYS,
            "STATE_FIELDS")
    require(record["enabled"] is True
            and all(type(record[k]) is str for k in STATE_KEYS - {"enabled"}),
            "STATE_TYPES")
    return record, raw


def _write_state_atomic(path, data):
    """Only called with the fixed state path under our own TemporaryDirectory."""
    require(path.name == "mock-updater-state.json"
            and path.parent.name == "fixture-private"
            and path.is_file() and not path.is_symlink(),
            "UNSAFE_FAKE_STATE_PATH")
    require(type(data) is bytes and len(data) < 4096,
            "UNSAFE_FAKE_STATE_BYTES")
    fd, tmp = tempfile.mkstemp(prefix=".fake-state-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        require(path.is_file() and not path.is_symlink(),
                "FAKE_STATE_REPLACED")
        os.replace(tmp, path)
        rollback._sync_directory(path.parent)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def _exact_code_state(installed, before, after):
    """Reject partial installs, unknown files, symlinks or tampering."""
    filenames = rollback._live_inventory(installed)
    if filenames == set(protocol.EXISTING_FILES) and all(
            rollback._regular_bytes(rollback._path(installed, name)) == before[name]
            for name in protocol.EXISTING_FILES):
        return "FAKE_V164"
    if filenames == protocol.FILE_SET and all(
            rollback._regular_bytes(rollback._path(installed, name)) == after[name]
            for name in protocol.FILE_SET):
        return "FAKE_V165"
    raise StateLabStop("STOP_INCONSISTENT_FAKE_CODE")


def _audit(installed, statefile, before, after):
    """Reports a divergence. Never repairs or trusts state to identify files."""
    code = _exact_code_state(installed, before, after)
    state, _ = _read_state(statefile)
    sha = state["installedSha"]
    if code == "FAKE_V164" and sha == OLD_FAKE_SHA:
        return "FAKE_V164_MATCH"
    if code == "FAKE_V165" and sha == OLD_FAKE_SHA:
        return "FAKE_V165_RECONCILE_PENDING"
    if code == "FAKE_V165" and sha == TARGET_FAKE_SHA:
        return "FAKE_V165_MATCH"
    if code == "FAKE_V164" and sha == TARGET_FAKE_SHA:
        return "FAKE_ROLLBACK_REQUIRES_SEPARATE_INVERSE_RECONCILE"
    return "FAKE_STATE_CODE_MISMATCH_FAIL_CLOSED"


def _mock_target_evidence():
    """Strict synthetic HEAD/tree/two-CI fixture from the pinned lab."""
    return pinned.synthetic_metadata()


def _reconcile_only(installed, statefile, before, after, bundle, seal,
                    *, fake_evidence, local_lock_held, mock_health_ok,
                    mock_updater_idle, mock_backup_verified):
    """A deliberately separate fixture-only state change. Not a LIVE tool."""
    require(local_lock_held is True, "FAKE_EXCLUSIVE_LOCK_MISSING")
    require(mock_updater_idle is True, "FAKE_UPDATER_BUSY")
    require(mock_health_ok is True, "FAKE_HEALTH_FAILED")
    require(mock_backup_verified is True, "FAKE_BACKUP_GATE_MISSING")
    require(_exact_code_state(installed, before, after) == "FAKE_V165",
            "FAKE_CANDIDATE_NOT_INSTALLED")
    rollback._verify_bundle(bundle, seal, before, after)
    state, original_bytes = _read_state(statefile)
    require(state == _prior_state(), "FAKE_UPDATER_BASELINE_CHANGED")
    try:
        pinned.verify_synthetic_pins(fake_evidence)
    except (pinned.FixtureRejected, TypeError) as exc:
        raise StateLabStop("STOP_BAD_FAKE_GITHUB_PROOF") from exc
    require(fake_evidence["futureMainSha"] == TARGET_FAKE_SHA,
            "FAKE_TARGET_SHA_MISMATCH")
    # A separate state backup, not a full off-host or immutable backup.
    snapshot = statefile.parent / "fake-updater-state-before.json"
    require(not snapshot.exists() and not snapshot.is_symlink(),
            "FAKE_STATE_SNAPSHOT_EXISTS")
    rollback._write_new(snapshot, original_bytes)
    updated = dict(state)
    updated.update(installedSha=TARGET_FAKE_SHA, targetSha=TARGET_FAKE_SHA,
                   state="up_to_date", message="FAKE_V165_RECONCILED_ONLY")
    _write_state_atomic(statefile, _encode_state(updated))
    actual, _ = _read_state(statefile)
    require(actual == updated, "FAKE_STATE_COMMIT_INVALID")
    require(_audit(installed, statefile, before, after) == "FAKE_V165_MATCH",
            "FAKE_RECONCILE_INCONSISTENT")
    return True


def rehearse(*, mode=None, fault=None):
    require(mode == MODE, "OFFLINE_MODE_REQUIRED")
    require(fault is None or fault in FAULTS, "UNKNOWN_FAULT")
    report = {
        "schema": SCHEMA,
        "state": "UNTESTED",
        "faultInjected": fault is not None,
        "fakeUpdaterStateChangedByCodeInstall": False,
        "fakeUpdaterStateReconciledSeparately": False,
        "fakeRollbackVerified": False,
        "mockedGithubCiNotRealEvidence": True,
        "fakeFilesystemOnly": True,
        "realVpsAccess": False,
        "actualLiveVersionAttested": False,
        "realGitHubPushMainCiVerified": False,
        "realAutoupdaterChanged": False,
        "realSqliteBackupRestored": False,
        "offhostRollbackVerified": False,
        "productionAuthorization": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }
    before, after = rollback._fixtures()
    with tempfile.TemporaryDirectory(prefix="remura-v165-updater-fixture-") as tmp:
        base = Path(tmp)
        installed = rollback._initial_install_dir(base, before)
        private = base / "fixture-private"
        private.mkdir(mode=0o700)
        statefile = private / "mock-updater-state.json"
        rollback._write_new(statefile, _encode_state(_prior_state()))
        require(_audit(installed, statefile, before, after) == "FAKE_V164_MATCH",
                "FAKE_BASELINE_DIVERGED")
        original_state_bytes = rollback._regular_bytes(statefile)
        bundle, seal = rollback._seal(base, before, after)
        rollback._verify_bundle(bundle, seal, before, after)
        rollback._install_fake(installed, before, after)
        report["fakeUpdaterStateChangedByCodeInstall"] = (
            rollback._regular_bytes(statefile) != original_state_bytes)
        require(not report["fakeUpdaterStateChangedByCodeInstall"],
                "INSTALL_CHANGED_FAKE_UPDATER")
        require(_audit(installed, statefile, before, after)
                == "FAKE_V165_RECONCILE_PENDING", "FAKE_RECONCILE_NOT_PENDING")

        if fault == "stop_before_reconcile":
            report["state"] = "FAKE_PENDING_NOT_RECONCILED"
            return report
        if fault == "rollback_before_reconcile":
            report["fakeRollbackVerified"] = rollback._rollback_fake(
                installed, bundle, seal, before, after)
            require(_audit(installed, statefile, before, after)
                    == "FAKE_V164_MATCH", "FAKE_ROLLBACK_STATE_DIVERGED")
            require(rollback._regular_bytes(statefile) == original_state_bytes,
                    "FAKE_UPDATER_CHANGED_BY_ROLLBACK")
            report["state"] = "FAKE_ROLLBACK_BEFORE_RECONCILE_STATE_INTACT"
            return report

        evidence = _mock_target_evidence()
        if fault == "main_moved":
            evidence["mainAtCheckSha"] = "2" * 40
        if fault == "bad_ci_event":
            evidence["ciRuns"][0]["event"] = "pull_request"
        if fault == "state_tampered":
            bad = dict(_prior_state())
            bad["failedSha"] = "f" * 40
            _write_state_atomic(statefile, _encode_state(bad))
        if fault == "candidate_tampered":
            name = protocol.EXISTING_FILES[0]
            rollback._replace(rollback._path(installed, name), b"FAKE_TAMPERED")

        # This lock belongs solely to the disposable fixture. It does not prove
        # that the autoupdater lock on the real server has been obtained.
        fake_lock_path = private / "mock-lock"
        rollback._write_new(fake_lock_path, b"FAKE_LOCK\n")
        with fake_lock_path.open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                try:
                    _reconcile_only(
                        installed, statefile, before, after, bundle, seal,
                        fake_evidence=evidence,
                        local_lock_held=(fault != "no_lock"),
                        mock_health_ok=(fault != "health_failed"),
                        mock_updater_idle=(fault != "updater_busy"),
                        mock_backup_verified=(fault != "backup_unverified"))
                except (StateLabStop, rollback.LabStop):
                    if fault not in (
                        "main_moved", "bad_ci_event", "state_tampered",
                        "candidate_tampered", "no_lock", "health_failed",
                        "updater_busy", "backup_unverified",
                    ):
                        raise
                    report["state"] = "FAKE_RECONCILE_REJECTED"
                    report["fakeUpdaterStateReconciledSeparately"] = False
                    return report
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        report["fakeUpdaterStateReconciledSeparately"] = True
        require(_audit(installed, statefile, before, after) == "FAKE_V165_MATCH",
                "FAKE_STATE_COMMIT_FAILED")
        if fault == "rollback_after_reconcile":
            report["fakeRollbackVerified"] = rollback._rollback_fake(
                installed, bundle, seal, before, after)
            require(_audit(installed, statefile, before, after)
                    == "FAKE_ROLLBACK_REQUIRES_SEPARATE_INVERSE_RECONCILE",
                    "FAKE_INVERSE_RECONCILE_BYPASSED")
            report["state"] = "FAKE_INVERSE_RECONCILE_REQUIRED_NO_AUTO_FIX"
            return report
        report["state"] = "FAKE_STATE_ONLY_RECONCILED_NOT_LIVE"
    return report


def main():
    parser = argparse.ArgumentParser(
        description="REMURA v1.65 updater-state fixture only, NO LIVE")
    parser.add_argument("--rehearse-state-offline", action="store_true",
                        required=True)
    parser.parse_args()
    print(json.dumps(rehearse(mode=MODE), sort_keys=True))


if __name__ == "__main__":
    main()
