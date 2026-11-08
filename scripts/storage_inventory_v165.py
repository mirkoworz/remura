#!/usr/bin/env python3
"""REMURA draft v1.65: bounded SQLite/WAL/SHM + local backup metadata.

Prepared for an explicitly approved separate diagnostic; not installed or
called by the LIVE app. The default MODE is a synthetic temporary LAB folder.
LIVE path needs an explicit flag and is only /opt/remura/private. A call only
filesystem metadata operations (lstat/stat/scandir/statvfs, directory fds): no SQLite connection, PRAGMA, file reads/writes,
checkpoint, network, shell, environment secrets, process or deployment.
Metadata is non-atomic. Backups are NEVER authenticated or restored here.
"""
from __future__ import annotations

import os
from contextlib import ExitStack
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
MAX_ROLLBACK_NODES = 128
MAX_ROLLBACK_DEPTH = 4
ARCHIVE_NAME = re.compile(r"backup-v\d{2,4}-[A-Za-z0-9-]{8,96}\Z")
ROLLBACK_NAME = re.compile(r"rollback-v\d{2,4}-[A-Za-z0-9-]{4,96}\Z")
BACKUP_FILES = frozenset((DB_NAME, "manifest.txt"))


def _root(value, mode, approved):
    if not isinstance(value, (str, Path)):
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


def _rollback_metadata(path):
    """Bounded nested source-file metadata of release_v164 rollback bundles.

    This is NOT an integrity check and must not read manifest contents.
    """
    nodes = 0
    apparent = 0
    manifest_seen = False
    pending = [(path, 0)]
    while pending:
        directory, depth = pending.pop()
        if depth > MAX_ROLLBACK_DEPTH:
            raise ValueError("rollback_too_deep")
        if not stat.S_ISDIR(directory.lstat().st_mode):
            raise ValueError("rollback_directory_not_plain")
        with os.scandir(directory) as iterator:
            for entry in iterator:
                nodes += 1
                if nodes > MAX_ROLLBACK_NODES:
                    raise ValueError("rollback_files_over_cap")
                child = directory / entry.name
                info = child.lstat()
                if stat.S_ISDIR(info.st_mode):
                    if depth >= MAX_ROLLBACK_DEPTH:
                        raise ValueError("rollback_depth_cap")
                    pending.append((child, depth + 1))
                elif (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                      and 0 <= info.st_size <= MAX_DB):
                    apparent += info.st_size
                    if depth == 0 and entry.name == "manifest.json":
                        manifest_seen = True
                else:
                    raise ValueError("rollback_symlink_hardlink_or_special_file")
    if not manifest_seen:
        raise ValueError("rollback_manifest_missing")
    return apparent


def _backup_tree(root):
    """Count v156 DB snapshots AND v164 code rollbacks as distinct local kinds."""
    directory = root / BACKUP_DIR
    unknown = {"state": "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS",
               "archives": None, "apparentBytes": None,
               "rollbacks": None, "rollbackApparentBytes": None}
    try:
        s = directory.lstat()
    except FileNotFoundError:
        return {**unknown, "state": "UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY"}
    if not stat.S_ISDIR(s.st_mode):
        return {**unknown, "state": "UNKNOWN_BACKUP_DIRECTORY_TYPE"}
    snapshot_bytes = snapshot_count = rollback_bytes = rollback_count = 0
    try:
        with os.scandir(directory) as iterator:
            for index, entry in enumerate(iterator):
                if index >= MAX_BACKUP_DIRS:
                    raise ValueError("bounded_backup_directory_entries")
                current = directory / entry.name
                if not stat.S_ISDIR(current.lstat().st_mode):
                    raise ValueError("backup_entry_not_plain_directory")
                if ARCHIVE_NAME.fullmatch(entry.name):
                    contents = set()
                    with os.scandir(current) as files:
                        for number, file in enumerate(files):
                            if number >= MAX_BACKUP_FILES or file.name not in BACKUP_FILES:
                                raise ValueError("unrecognized_backup_file_or_limit")
                            contents.add(file.name)
                            info = _item(current / file.name)
                            snapshot_bytes += info["apparentBytes"]
                    if contents != BACKUP_FILES:
                        raise ValueError("incomplete_backup_archive")
                    snapshot_count += 1
                elif ROLLBACK_NAME.fullmatch(entry.name):
                    rollback_bytes += _rollback_metadata(current)
                    rollback_count += 1
                else:
                    # Includes interrupted candidate-v156 and unexpected files:
                    # refuse complete-enumeration claims rather than omitting.
                    raise ValueError("unrecognized_or_incomplete_backup_entry")
    except (OSError, ValueError, OverflowError):
        return unknown
    if snapshot_count:
        state = "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE"
    elif rollback_count:
        state = "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF"
    else:
        state = "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE"
    return {"state": state,
            "archives": snapshot_count,
            "apparentBytes": snapshot_bytes if snapshot_count else None,
            "rollbacks": rollback_count,
            "rollbackApparentBytes": rollback_bytes if rollback_count else None}



# LIVE-only directory-descriptor walker. Path lstat checks alone are subject
# to rename/symlink TOCTOU races; pinned directory FDs + O_NOFOLLOW prevent a
# replaced child directory from redirecting metadata reads elsewhere.
# We open *directories only*, NEVER the database, WAL, SHM or backup files.
def _dir_flags():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("linux_nofollow_directory_support_required")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _open_live_root():
    flags = _dir_flags()
    fd = os.open("/", flags)
    try:
        for component in ("opt", "remura", "private"):
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _fd_item(directory_fd, name, *, optional=False):
    """Never open files; fstatat with AT_SYMLINK_NOFOLLOW on a pinned parent."""
    try:
        s = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
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


def _fd_rollback(directory_fd):
    nodes = 0
    apparent = 0
    manifest_seen = False
    with ExitStack() as cleanup:
        pending = [(directory_fd, 0)]
        while pending:
            current_fd, depth = pending.pop()
            if depth > MAX_ROLLBACK_DEPTH:
                raise ValueError("rollback_too_deep")
            with os.scandir(current_fd) as entries:
                for entry in entries:
                    nodes += 1
                    if nodes > MAX_ROLLBACK_NODES:
                        raise ValueError("rollback_files_over_cap")
                    name = entry.name
                    s = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
                    if stat.S_ISDIR(s.st_mode):
                        if depth >= MAX_ROLLBACK_DEPTH:
                            raise ValueError("rollback_depth_cap")
                        child_fd = os.open(name, _dir_flags(), dir_fd=current_fd)
                        cleanup.callback(os.close, child_fd)
                        pending.append((child_fd, depth + 1))
                    elif (stat.S_ISREG(s.st_mode) and s.st_nlink == 1
                          and 0 <= s.st_size <= MAX_DB):
                        apparent += s.st_size
                        if depth == 0 and name == "manifest.json":
                            manifest_seen = True
                    else:
                        raise ValueError("rollback_symlink_hardlink_or_special_file")
    if not manifest_seen:
        raise ValueError("rollback_manifest_missing")
    return apparent


def _fd_backup_tree(root_fd):
    unknown = {"state": "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS",
               "archives": None, "apparentBytes": None,
               "rollbacks": None, "rollbackApparentBytes": None}
    try:
        s = os.stat(BACKUP_DIR, dir_fd=root_fd, follow_symlinks=False)
    except FileNotFoundError:
        return {**unknown, "state": "UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY"}
    except OSError:
        return unknown
    if not stat.S_ISDIR(s.st_mode):
        return {**unknown, "state": "UNKNOWN_BACKUP_DIRECTORY_TYPE"}
    snapshot_bytes = snapshot_count = rollback_bytes = rollback_count = 0
    try:
        with ExitStack() as cleanup:
            backups_fd = os.open(BACKUP_DIR, _dir_flags(), dir_fd=root_fd)
            cleanup.callback(os.close, backups_fd)
            with os.scandir(backups_fd) as iterator:
                for index, entry in enumerate(iterator):
                    if index >= MAX_BACKUP_DIRS:
                        raise ValueError("bounded_backup_directory_entries")
                    name = entry.name
                    current = os.stat(name, dir_fd=backups_fd, follow_symlinks=False)
                    if not stat.S_ISDIR(current.st_mode):
                        raise ValueError("backup_entry_not_plain_directory")
                    current_fd = os.open(name, _dir_flags(), dir_fd=backups_fd)
                    cleanup.callback(os.close, current_fd)
                    if ARCHIVE_NAME.fullmatch(name):
                        contents = set()
                        with os.scandir(current_fd) as files:
                            for number, file in enumerate(files):
                                if number >= MAX_BACKUP_FILES or file.name not in BACKUP_FILES:
                                    raise ValueError("unrecognized_backup_file_or_limit")
                                contents.add(file.name)
                                info = _fd_item(current_fd, file.name)
                                snapshot_bytes += info["apparentBytes"]
                        if contents != BACKUP_FILES:
                            raise ValueError("incomplete_backup_archive")
                        snapshot_count += 1
                    elif ROLLBACK_NAME.fullmatch(name):
                        rollback_bytes += _fd_rollback(current_fd)
                        rollback_count += 1
                    else:
                        raise ValueError("unrecognized_or_incomplete_backup_entry")
    except (OSError, ValueError, OverflowError):
        return unknown
    if snapshot_count:
        state = "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE"
    elif rollback_count:
        state = "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF"
    else:
        state = "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE"
    return {"state": state,
            "archives": snapshot_count,
            "apparentBytes": snapshot_bytes if snapshot_count else None,
            "rollbacks": rollback_count,
            "rollbackApparentBytes": rollback_bytes if rollback_count else None}


def _fd_space(root_fd):
    v = os.fstatvfs(root_fd)
    block = v.f_frsize or v.f_bsize
    if block <= 0 or min(v.f_blocks, v.f_bavail, v.f_favail) < 0:
        raise ValueError("unavailable_filesystem_counters")
    return {"availableBytes": v.f_bavail * block,
            "availableInodes": v.f_favail}


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
        if mode == LIVE_MODE:
            root_fd = _open_live_root()
            try:
                main = _fd_item(root_fd, DB_NAME)
                wal = _fd_item(root_fd, DB_NAME+"-wal", optional=True)
                shm = _fd_item(root_fd, DB_NAME+"-shm", optional=True)
                backup = _fd_backup_tree(root_fd)
                space = _fd_space(root_fd)
            finally:
                os.close(root_fd)
        else:
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
