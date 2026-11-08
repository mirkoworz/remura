#!/usr/bin/env python3
"""REMURA Track C4b(b): TEST-ONLY SQLite recovery and research kill gate.

Only a single fixed-name synthetic SQLite DB in a dedicated temporary folder
is readable. Backup/restore targets are synthetic siblings and are removed
after the test. NEVER opens or migrates an application/Oracle database, never
starts a service, polls providers, modifies a live collector or deploys.
Passing an offline restore is NOT proof that LIVE backups exist or are safe.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
from urllib.parse import quote

MODE = "OFFLINE_SYNTHETIC_C4BB_BACKUP_RESTORE_KILL_GATE_ONLY"
FILE = "track-c4bb-synthetic-core.sqlite3"
BACKUP = "track-c4bb-synthetic-backup.sqlite3"
RESTORED = "track-c4bb-synthetic-restored.sqlite3"
LAB_SCHEMA = "remura-c4bb-synthetic-restore-v1"
MAX_CORE_BYTES = 256 * 1024
MAX_WAL_BYTES = 256 * 1024
MAX_SHM_BYTES = 64 * 1024
MAX_RECEIPTS = 32
RESERVE_BYTES = 1024 * 1024
UNKNOWN = "UNKNOWN_NO_LIVE_BACKUP_RESTORE_PROOF"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def _path(value, *, mode):
    if mode != MODE:
        raise ValueError("explicit_offline_restore_mode_required")
    if not isinstance(value, (str, Path)):
        raise ValueError("synthetic_core_path_required")
    raw = Path(value).absolute()
    root = Path(tempfile.gettempdir()).resolve()
    if (raw.name != FILE or raw.is_symlink() or raw.parent.is_symlink()
            or not raw.parent.is_dir()
            or not raw.parent.name.startswith("remura-c4bb-")
            or raw.parent.resolve().parent != root
            or raw.resolve().parent != raw.parent.resolve()):
        raise ValueError("only_named_synthetic_temp_core_allowed")
    return raw


def _parts(core):
    paths = {"core": core, "wal": Path(str(core) + "-wal"),
             "shm": Path(str(core) + "-shm")}
    limits = {"core": MAX_CORE_BYTES, "wal": MAX_WAL_BYTES,
              "shm": MAX_SHM_BYTES}
    result = {}
    for name, path in paths.items():
        if path.is_symlink():
            raise ValueError("sqlite_symlink_sidecar_forbidden")
        if not path.exists():
            if name == "core":
                raise ValueError("synthetic_core_missing")
            result[name] = {"state": "NOT_PRESENT_NOT_ZERO_USAGE_PROOF",
                            "bytes": None}
            continue
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("sqlite_nonregular_or_hardlinked_file_forbidden")
        size = path.stat().st_size
        if size <= 0 and name == "core":
            raise ValueError("empty_core_not_valid")
        if size > limits[name]:
            raise ValueError("synthetic_file_limit_exceeded")
        result[name] = {"state": "PRESENT_SYNTHETIC", "bytes": size}
    return result


def inventory_lab(path, *, mode=None):
    """Counts synthetic files only; absent WAL/SHM NEVER becomes zero bytes."""
    core = _path(path, mode=mode)
    try:
        parts = _parts(core)
        return {"state": "SYNTHETIC_FILE_SIZES_ONLY",
                "main": parts["core"], "wal": parts["wal"],
                "shm": parts["shm"],
                "liveStorageVerified": False,
                "allLiveDatabaseFilesCovered": False}
    except (OSError, ValueError):
        return {"state": UNKNOWN, "liveStorageVerified": False,
                "allLiveDatabaseFilesCovered": False}


def _verify(db):
    """Strict dummy schema plus bounded deterministic receipts, no market data."""
    db.execute("PRAGMA query_only=ON")
    integrity = db.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        raise ValueError("sqlite_integrity_check_failed")
    names = {
        (name, kind) for name, kind in db.execute(
            "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
    if names != {("lab_schema", "table"), ("lab_receipts", "table")}:
        raise ValueError("strict_synthetic_tables_only")
    version = db.execute("SELECT version FROM lab_schema").fetchall()
    if version != [(LAB_SCHEMA,)]:
        raise ValueError("strict_synthetic_version_only")
    rows = db.execute("SELECT id,witness FROM lab_receipts ORDER BY id").fetchall()
    if not 1 <= len(rows) <= MAX_RECEIPTS:
        raise ValueError("bounded_lab_receipts_required")
    if any(type(i) is not int or i != n or type(w) is not str
           or not HEX.fullmatch(w) for n, (i, w) in enumerate(rows, 1)):
        raise ValueError("strict_synthetic_receipts_required")
    serialized = json.dumps(rows, separators=(",", ":"), ensure_ascii=True)
    return len(rows), hashlib.sha256(serialized.encode("ascii")).digest()


def _readonly(path):
    # The path is pre-validated and synthetic; mode=ro prevents core writes.
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=0.05)


def _targets(core):
    parent = core.parent
    return parent / BACKUP, parent / RESTORED


def _guard_targets(core):
    backup, restored = _targets(core)
    for path in (backup, restored):
        for suffix in ("", "-wal", "-shm"):
            target = Path(str(path) + suffix)
            if target.exists() or target.is_symlink():
                raise ValueError("never_replace_existing_backup_or_restore")
    return backup, restored


def _result(state, *, restored=False, rows=None, minimum=None):
    return {
        "state": state,
        "syntheticRestorePassed": restored,
        "syntheticRowsCompared": rows,
        "syntheticMinimumFreeBytes": minimum,
        "liveBackupVerified": False,
        "liveRestoreVerified": False,
        "crossHostRecoveryVerified": False,
        "oracleBillingVerified": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
        "newProviderCalls": 0,
    }


def rehearse_backup_restore(path, *, mode=None, enabled=False,
                            free_bytes_override=None, fault=None):
    """Attempt bounded SQLite online backup + restore ONLY in temporary LAB.

    No false durable backup claim: temporary backup/restore are cleaned.
    free_bytes_override is only a synthetic chaos input, NEVER VM evidence.
    """
    core = _path(path, mode=mode)
    if type(enabled) is not bool or not enabled:
        return _result("DISABLED_DEFAULT_OFF")
    if fault not in (None, "simulate_disk_full", "corrupt_backup"):
        raise ValueError("only_explicit_synthetic_faults_allowed")
    if (free_bytes_override is not None and
            (type(free_bytes_override) is not int
             or not 0 <= free_bytes_override <= 2**63 - 1)):
        raise ValueError("bounded_synthetic_free_space_required")
    created = []
    try:
        parts = _parts(core)
        backup, restored = _guard_targets(core)
        source_bytes = sum(v["bytes"] or 0 for v in parts.values())
        # Conservative sandbox-only reserve; NOT a proof that this formula
        # suffices for any live data, service, journal or cross-host backup.
        minimum = 4 * source_bytes + RESERVE_BYTES
        free = (shutil.disk_usage(str(core.parent)).free if
                free_bytes_override is None else free_bytes_override)
        if free < minimum or fault == "simulate_disk_full":
            return _result("UNKNOWN_INSUFFICIENT_SYNTHETIC_FREE_SPACE",
                           minimum=minimum)
        with _readonly(core) as original:
            rows, digest = _verify(original)
            target = sqlite3.connect(str(backup), timeout=0.05)
            created.append(backup)
            try:
                original.backup(target, pages=16, sleep=0.01)
            finally:
                target.close()
        if fault == "corrupt_backup":
            with backup.open("r+b") as handle:
                handle.seek(0)
                handle.write(b"NOTSQLITE")
        with _readonly(backup) as backed:
            if _verify(backed) != (rows, digest):
                raise ValueError("synthetic_backup_mismatch")
            restored_db = sqlite3.connect(str(restored), timeout=0.05)
            created.append(restored)
            try:
                backed.backup(restored_db, pages=16, sleep=0.01)
            finally:
                restored_db.close()
        with _readonly(restored) as reopened:
            if _verify(reopened) != (rows, digest):
                raise ValueError("synthetic_restored_data_mismatch")
        return _result("SYNTHETIC_BACKUP_AND_REOPENED_RESTORE_MATCH",
                       restored=True, rows=rows, minimum=minimum)
    except (OSError, ValueError, sqlite3.Error):
        return _result(UNKNOWN)
    finally:
        # Delete only paths created by this test, never any existing file,
        # source, live DB, real backup or user-supplied path outside the lab.
        for item in created:
            for suffix in ("-shm", "-wal", ""):
                path = Path(str(item) + suffix)
                try:
                    if path.exists() and not path.is_symlink():
                        path.unlink()
                except OSError:
                    pass


def preview_kill_gate(restore_result, *, mode=None, kill_switch_active=True,
                      request_lab_probe=False):
    """Pure policy preview, never dispatches a worker and NEVER enables LIVE."""
    if mode != MODE:
        raise ValueError("explicit_offline_restore_mode_required")
    if type(kill_switch_active) is not bool or type(request_lab_probe) is not bool:
        raise ValueError("explicit_boolean_kill_switch_required")
    passed = (type(restore_result) is dict and
              restore_result.get("state") ==
              "SYNTHETIC_BACKUP_AND_REOPENED_RESTORE_MATCH" and
              restore_result.get("syntheticRestorePassed") is True and
              restore_result.get("liveBackupVerified") is False)
    return {
        "state": ("KILL_SWITCH_ACTIVE" if kill_switch_active else
                  "LAB_PREVIEW_ONLY_NO_LIVE_DISPATCH"),
        "hypotheticalLabProbeEligible": bool(passed and not kill_switch_active
                                             and request_lab_probe),
        "workerActuallyStarted": False,
        "liveResearchEnabled": False,
        "independentExternalKillSwitchVerified": False,
        "operationalDecision": NO_GO,
        "newProviderCalls": 0,
    }
