#!/usr/bin/env python3
"""REMURA C4b(f): metadata-only SQLite/WAL/SHM + local backup inventory.

Prepared for an explicitly approved separate diagnostic; not installed or
called by the LIVE app. The default MODE is a synthetic temporary LAB folder.
LIVE path needs an explicit flag and is only /opt/remura/private. A call only
lstats/scandirs/statvfs: no SQLite connection, PRAGMA, file reads/writes,
checkpoint, network, shell, environment secrets, process or deployment.
Metadata is non-atomic. Backups are NEVER authenticated or restored here.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import tempfile

LAB_MODE = "OFFLINE_C4BF_TEMP_METADATA_ONLY"
LIVE_MODE = "EXPLICIT_FUTURE_AUTHORIZED_READONLY_VPS_METADATA_ONLY"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
DB_NAME = "remura-prices.sqlite3"
BACKUP_DIR = "predeploy-backups"
MIN_FREE = 512 * 1024**2
MAX_DB = 8 * 1024**3
MAX_BACKUP_DIRS = 64
MAX_BACKUP_FILES = 8
ARCHIVE_NAME = re.compile(r"backup-v\d{2,4}-[A-Za-z0-9-]{8,96}\Z")
TRANSIENT_NAME = re.compile(r"(?:candidate|restore-test)-v\d{2,4}-[A-Za-z0-9-]{4,96}\Z")
BACKUP_FILES = frozenset((DB_NAME, "manifest.txt"))


def _root(value, mode, approved):
    if type(value) not in (str, Path):
        raise ValueError("explicit_root_required")
    root = Path(value)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("absolute_root_without_traversal_required")
    if mode == LAB_MODE:
        temp = Path(tempfile.gettempdir()).resolve()
        if (root.parent.resolve() != temp or
                not root.name.startswith("remura-c4bf-") or approved):
            raise ValueError("strict_lab_directory_only")
    elif mode == LIVE_MODE:
        if approved is not True or root != Path("/opt/remura/private"):
            raise ValueError("explicit_live_path_authorization_required")
        # Reject symlinks in every known parent component.
        for parent in (Path("/opt"), Path("/opt/remura"), root):
            s = parent.lstat()
            if not stat.S_ISDIR(s.st_mode):
                raise ValueError("live_root_not_plain_directory")
    else:
        raise ValueError("explicit_metadata_audit_mode_required")
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("root_must_be_real_directory")
    return root


def _item(path, *, optional=False):
    """No file open; report absent sidecars as ABSENT, not measured zero."""
    try:
        s = path.lstat()
    except FileNotFoundError:
        if optional:
            return {"state": "NOT_PRESENT_AT_METADATA_INSTANT",
                    "apparentBytes": None, "allocatedBytes": None}
        raise ValueError("required_file_not_found") from None
    if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
        raise ValueError("nonregular_symlink_or_hardlink_forbidden")
    if s.st_size > MAX_DB or (s.st_size == 0 and not optional):
        raise ValueError("file_size_not_plausible")
    return {"state": "FILE_SIZE_METADATA_ONLY",
            "apparentBytes": s.st_size,
            "allocatedBytes": s.st_blocks * 512}


def _backup_tree(root):
    """Count only known v156-style archive directories; NEVER read contents."""
    directory = root / BACKUP_DIR
    try:
        s = directory.lstat()
    except FileNotFoundError:
        return {"state": "UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY",
                "archives": None, "apparentBytes": None}
    if not stat.S_ISDIR(s.st_mode):
        return {"state": "UNKNOWN_BACKUP_DIRECTORY_TYPE",
                "archives": None, "apparentBytes": None}
    total = count = 0
    try:
        with os.scandir(directory) as iterator:
            for index, entry in enumerate(iterator):
                if index >= MAX_BACKUP_DIRS:
                    raise ValueError("bounded_backup_directory_entries")
                if not ARCHIVE_NAME.fullmatch(entry.name):
                    raise ValueError("unrecognized_or_incomplete_backup_entry")
                current = directory / entry.name
                if not stat.S_ISDIR(current.lstat().st_mode):
                    raise ValueError("backup_archive_not_real_directory")
                entries = set()
                with os.scandir(current) as files:
                    for number, file in enumerate(files):
                        if number >= MAX_BACKUP_FILES or file.name not in BACKUP_FILES:
                            raise ValueError("unrecognized_backup_file_or_limit")
                        entries.add(file.name)
                        info = _item(current / file.name)
                        total += info["apparentBytes"]
                if entries != BACKUP_FILES:
                    raise ValueError("incomplete_backup_archive")
                count += 1
    except (OSError, ValueError):
        return {"state": "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS",
                "archives": None, "apparentBytes": None}
    return {
        "state": ("LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE" if count else
                  "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE"),
        "archives": count,
        "apparentBytes": total if count else None
    }


def _space(root):
    v = os.statvfs(root)
    block = v.f_frsize or v.f_bsize
    if block <= 0 or min(v.f_blocks, v.f_bavail, v.f_favail) < 0:
        raise ValueError("unavailable_filesystem_counters")
    return {"availableBytes": v.f_bavail * block,
            "availableInodes": v.f_favail}


def _empty(state):
    return {
        "schema": "remura-c4bf-readonly-metadata-v1",
        "state": state,
        "main": None, "wal": None, "shm": None,
        "localBackups": {"state": "UNKNOWN_NO_SCANNED_BACKUP"},
        "filesystem": None, "pressure": "UNKNOWN",
        "scope": "ONE_KNOWN_PRICE_DATABASE_AND_LOCAL_PREDEPLOY_DIRECTORY_ONLY",
        "noDatabaseFileContentRead": True, "noSqliteConnectionOpened": True,
        "sourceUnmodifiedProven": False,
        "offhostBackupExistsVerified": False,
        "backupRestoreIntegrityVerified": False,
        "allOtherPrivateStorageCovered": False,
        "oracleAlwaysFreeBillingVerified": False,
        "operationalDecision": NO_GO,
        "newNetworkCalls": 0,
    }


def inventory(root, *, mode=None, live_approved=False, lab_free_override=None):
    """Metadata snapshot only. Produces no paths or tokens in output.

    The live_approved flag is a code precondition, NOT evidence that the user
    granted permission; never invoke in LIVE without separate authorization.
    """
    base = _root(root, mode, live_approved)
    if (lab_free_override is not None and
            (mode != LAB_MODE or type(lab_free_override) is not int or
             not 0 <= lab_free_override <= 2**63-1)):
        raise ValueError("only_bounded_lab_free_space_override")
    try:
        main = _item(base / DB_NAME)
        wal = _item(base / (DB_NAME+"-wal"), optional=True)
        shm = _item(base / (DB_NAME+"-shm"), optional=True)
        backup = _backup_tree(base)
        space = _space(base)
        if lab_free_override is not None:
            space["availableBytes"] = lab_free_override
        total = sum(part["apparentBytes"] or 0 for part in (main, wal, shm))
        # Test-only planning bound, NOT a general live backup/restore estimate.
        floor = 4 * total + MIN_FREE
        pressure = ("RESEARCH_PRESSURE_CAUTION" if
                    space["availableBytes"] < floor or
                    space["availableInodes"] < 512 else
                    "METADATA_HEADROOM_NOT_OPERATIONAL_GO")
        out = _empty("METADATA_ONLY_NOT_INDEPENDENTLY_ATTESTED")
        out.update(main=main, wal=wal, shm=shm, localBackups=backup,
                   filesystem=space, pressure=pressure,
                   suggestedLabReserveBytes=floor)
        return out
    except (OSError, ValueError, OverflowError):
        return _empty("UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")
