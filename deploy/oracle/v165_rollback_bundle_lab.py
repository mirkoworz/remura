#!/usr/bin/env python3
"""REMURA v1.65: persisted rollback-bundle rehearsal on disposable fake files.

THIS IS NOT AN INSTALLER. The sole CLI runs inside a private TemporaryDirectory
created by this module, with 12 invented prior files and 14 invented candidate
files. The synthetic rollback bundle survives only while the rehearsal runs;
it is deleted at exit and is NOT off-host backup, an authenticated signature,
an installed-LIVE proof, or a production rollback.

No path argument, live mode, network, services, SQLite or updater state writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

import v165_release_protocol_draft as protocol

SCHEMA = "remura-v165-synthetic-persistent-rollback-v1"
MODE = "OFFLINE_FAKE_FILES_ONLY"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
MAX_BYTES = 100_000
FAULTS = frozenset((
    "after_seal", "mid_install", "after_install", "during_rollback",
    "corrupt_manifest", "corrupt_backup", "symlink_backup",
    "unexpected_backup", "tamper_installed", "symlink_installed",
))
BAD_BUNDLE_FAULTS = frozenset((
    "corrupt_manifest", "corrupt_backup", "symlink_backup", "unexpected_backup",
))
BAD_LIVE_FAULTS = frozenset(("tamper_installed", "symlink_installed"))


class LabStop(ValueError):
    """A failure in an entirely synthetic disposable filesystem."""


def require(ok, reason):
    if not ok:
        raise LabStop("STOP_" + reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _fixtures():
    protocol.validate_manifest(protocol.EXISTING_FILES, protocol.NEW_FILES)
    before = {name: ("FAKE_V164_PRIOR_" + name + "\n").encode("ascii")
              for name in protocol.EXISTING_FILES}
    after = {name: ("FAKE_V165_NEXT_" + name + "\n").encode("ascii")
             for name in protocol.FILE_SET}
    return before, after


def _regular_bytes(path):
    """O_NOFOLLOW + fstat and bounded read. Only used for fake test files."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        meta = os.fstat(fd)
        require(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= MAX_BYTES,
                "UNSAFE_OR_OVERSIZED_FILE")
        with os.fdopen(os.dup(fd), "rb") as file:
            data = file.read(MAX_BYTES + 1)
        require(len(data) == meta.st_size, "FILE_SIZE_CHANGED")
        return data
    finally:
        os.close(fd)


def _mkdir(parent, name):
    require(name in ("installed", "rollback", "old", "scripts"),
            "UNEXPECTED_DIRECTORY")
    directory = parent / name
    directory.mkdir(mode=0o700, exist_ok=False)
    require(stat.S_ISDIR(directory.lstat().st_mode), "UNSAFE_DIRECTORY")
    return directory


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_new(path, data):
    require(type(data) is bytes and 0 < len(data) <= MAX_BYTES,
            "INVALID_FAKE_BYTES")
    require(path.parent.is_dir() and not path.parent.is_symlink(),
            "UNSAFE_PARENT")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    _sync_directory(path.parent)


def _replace(path, data):
    require(path.is_file() and not path.is_symlink(), "UNSAFE_REPLACE")
    # All paths are already constrained to the private TemporaryDirectory.
    fd, tmp = tempfile.mkstemp(prefix=".synthetic-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        require(path.is_file() and not path.is_symlink(), "UNSAFE_REPLACE")
        os.replace(tmp, path)
        _sync_directory(path.parent)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def _path(root, name):
    require(name in protocol.FILE_SET, "PATH_NOT_ALLOWLISTED")
    if name.startswith("scripts/"):
        return root / "scripts" / name.split("/", 1)[1]
    return root / name


def _initial_install_dir(base, before):
    installed = _mkdir(base, "installed")
    _mkdir(installed, "scripts")
    for name, content in before.items():
        _write_new(_path(installed, name), content)
    return installed


def _bundle_inventory(bundle):
    """Reject any unexpected backup file/dir, including hidden or symlink."""
    require(bundle.is_dir() and not bundle.is_symlink(), "UNSAFE_BUNDLE_DIR")
    expected_files = {"manifest.json"} | {
        "old/" + name for name in protocol.EXISTING_FILES}
    expected_dirs = {"old", "old/scripts"}
    actual_files, actual_dirs = set(), set()
    for base, dirs, files in os.walk(bundle, followlinks=False):
        relative = Path(base).relative_to(bundle)
        for dirname in dirs:
            path = Path(base) / dirname
            sub = (relative / dirname).as_posix()
            require(path.is_dir() and not path.is_symlink(),
                    "UNSAFE_BUNDLE_DIR")
            actual_dirs.add(sub)
        for filename in files:
            path = Path(base) / filename
            sub = (relative / filename).as_posix()
            require(path.is_file() and not path.is_symlink(),
                    "UNSAFE_BUNDLE_FILE")
            actual_files.add(sub)
    require(actual_files == expected_files and actual_dirs == expected_dirs,
            "BUNDLE_EXTRA_OR_MISSING")
    return True


def _manifest(before, after):
    return {
        "schema": SCHEMA, "fixture": MODE,
        "liveAttested": False, "releaseAuthorized": False,
        "files": {
            name: {
                "kind": "new" if name in protocol.NEW_FILES else "existing",
                "oldSha256": sha(before[name]) if name in before else None,
                "proposedSha256": sha(after[name]),
            }
            for name in sorted(protocol.FILE_SET)
        },
    }


def _seal(base, before, after):
    """FSYNC bounded fake originals + manifest. Seal digest stays in memory."""
    bundle = _mkdir(base, "rollback")
    olddir = _mkdir(bundle, "old")
    _mkdir(olddir, "scripts")
    for name, data in before.items():
        _write_new(_path(olddir, name), data)
    content = json.dumps(_manifest(before, after),
                         separators=(",", ":"), sort_keys=True).encode("utf-8")
    _write_new(bundle / "manifest.json", content)
    _sync_directory(bundle)
    return bundle, sha(content)


def _verify_bundle(bundle, expected_seal, before, after):
    """Fail closed before restoring any byte from a changed backup."""
    require(type(expected_seal) is str and len(expected_seal) == 64,
            "MISSING_TRUSTED_SEAL")
    _bundle_inventory(bundle)
    raw = _regular_bytes(bundle / "manifest.json")
    require(sha(raw) == expected_seal, "MANIFEST_CHANGED")
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise LabStop("STOP_BAD_MANIFEST_JSON") from exc
    require(type(record) is dict and record == _manifest(before, after),
            "UNEXPECTED_MANIFEST")
    for name, expected in before.items():
        require(sha(_regular_bytes(_path(bundle / "old", name))) == sha(expected),
                "BACKUP_HASH_MISMATCH")
    return True


def _live_inventory(installed):
    require(installed.is_dir() and not installed.is_symlink(),
            "UNSAFE_INSTALLED_DIR")
    require((installed / "scripts").is_dir()
            and not (installed / "scripts").is_symlink(),
            "UNSAFE_INSTALLED_DIR")
    files = set()
    for base, dirs, names in os.walk(installed, followlinks=False):
        relative = Path(base).relative_to(installed)
        for d in dirs:
            require((Path(base) / d).is_dir()
                    and not (Path(base) / d).is_symlink()
                    and (relative / d).as_posix() == "scripts",
                    "LIVE_UNEXPECTED_DIRECTORY")
        for name in names:
            p = Path(base) / name
            require(p.is_file() and not p.is_symlink(), "LIVE_SYMLINK_OR_FILE")
            files.add((relative / name).as_posix())
    require(protocol.EXISTING_FILES and
            set(protocol.EXISTING_FILES) <= files <= protocol.FILE_SET,
            "LIVE_UNEXPECTED_FILE_SET")
    return files


def _validate_live_state(installed, before, after):
    names = _live_inventory(installed)
    for name in protocol.EXISTING_FILES:
        current = _regular_bytes(_path(installed, name))
        require(current in (before[name], after[name]),
                "LIVE_FILE_TAMPERED")
    for name in protocol.NEW_FILES:
        if name in names:
            require(_regular_bytes(_path(installed, name)) == after[name],
                    "LIVE_NEW_MODULE_TAMPERED")
    return True


def _install_fake(installed, before, after, *, fault=None):
    _validate_live_state(installed, before, after)
    for index, name in enumerate((*protocol.EXISTING_FILES, *protocol.NEW_FILES)):
        target = _path(installed, name)
        if name in before:
            _replace(target, after[name])
        else:
            _write_new(target, after[name])
        if fault == "mid_install" and index == 4:
            raise LabStop("STOP_INJECT_MID_INSTALL")
    if fault == "after_install":
        raise LabStop("STOP_INJECT_AFTER_INSTALL")
    return True


def _rollback_fake(installed, bundle, seal, before, after, *, fault=None):
    """Prevalidate every original/current before any restore, then replay."""
    _verify_bundle(bundle, seal, before, after)
    _validate_live_state(installed, before, after)
    for index, name in enumerate(protocol.EXISTING_FILES):
        _replace(_path(installed, name),
                 _regular_bytes(_path(bundle / "old", name)))
        if fault == "during_rollback" and index == 2:
            raise LabStop("STOP_INJECT_INTERRUPTED_ROLLBACK")
    for name in protocol.NEW_FILES:
        p = _path(installed, name)
        if p.exists() or p.is_symlink():
            require(p.is_file() and not p.is_symlink()
                    and _regular_bytes(p) == after[name],
                    "UNSAFE_NEW_MODULE_REMOVAL")
            p.unlink()
            _sync_directory(p.parent)
    return _originals_restored(installed, before)


def _originals_restored(installed, before):
    require(_live_inventory(installed) == set(protocol.EXISTING_FILES),
            "ORIGINAL_FILES_NOT_EXACT")
    require(all(_regular_bytes(_path(installed, n)) == old
                for n, old in before.items()), "ORIGINAL_HASHES_NOT_RESTORED")
    return True


def rehearse(*, mode=None, fault=None):
    """No caller-controlled paths. All writes strictly inside disposable tmp."""
    require(mode == MODE, "OFFLINE_MODE_REQUIRED")
    require(fault is None or fault in FAULTS, "UNKNOWN_FAULT")
    before, after = _fixtures()
    report = {
        "schema": SCHEMA, "state": "UNTESTED",
        "syntheticBundlePersistedAndSealed": False,
        "syntheticRollbackAttempted": False,
        "syntheticRollbackComplete": False,
        "syntheticFaultInjected": fault is not None,
        "syntheticTamperRejected": False,
        "syntheticInterruptedRollbackRetried": False,
        "temporaryFixtureErasedAtExit": True,
        "fakeNewModulesAbsentAfterRecovery": False,
        "trustedSealIndependentOfFixture": False,
        "liveInstalledVersionAttested": False,
        "realSqliteOpened": False, "offhostBackupVerified": False,
        "liveFilesModified": False, "realAutoupdaterReconciled": False,
        "realServerAccessed": False, "releaseAuthorized": False,
        "researchC5Enabled": False, "operationalDecision": NO_GO,
    }
    with tempfile.TemporaryDirectory(prefix="remura-v165-rollback-fixture-") as tmp:
        base = Path(tmp)
        installed = _initial_install_dir(base, before)
        bundle, seal = _seal(base, before, after)
        _verify_bundle(bundle, seal, before, after)
        report["syntheticBundlePersistedAndSealed"] = True
        try:
            if fault == "after_seal":
                raise LabStop("STOP_INJECT_AFTER_SEAL")
            try:
                _install_fake(installed, before, after, fault=fault)
            except LabStop:
                if fault not in ("mid_install", "after_install"):
                    raise
            if fault == "corrupt_manifest":
                _replace(bundle / "manifest.json", b'{"fake":true}')
            if fault == "corrupt_backup":
                _replace(_path(bundle / "old", protocol.EXISTING_FILES[0]),
                         b"FAKE_CORRUPTED")
            if fault == "symlink_backup":
                p = _path(bundle / "old", protocol.EXISTING_FILES[0])
                p.unlink()
                p.symlink_to(bundle / "manifest.json")
            if fault == "unexpected_backup":
                _write_new(bundle / "unreviewed.txt", b"FAKE_EXTRA")
            if fault == "tamper_installed":
                _replace(_path(installed, protocol.EXISTING_FILES[0]),
                         b"FAKE_UNEXPECTED_CODE")
            if fault == "symlink_installed":
                p = _path(installed, protocol.EXISTING_FILES[0])
                p.unlink()
                p.symlink_to(_path(installed, protocol.EXISTING_FILES[1]))
            report["syntheticRollbackAttempted"] = True
            try:
                _rollback_fake(installed, bundle, seal, before, after,
                               fault="during_rollback" if fault == "during_rollback" else None)
            except (LabStop, OSError):
                if fault == "during_rollback":
                    report["syntheticInterruptedRollbackRetried"] = True
                    _rollback_fake(installed, bundle, seal, before, after)
                elif fault in BAD_BUNDLE_FAULTS | BAD_LIVE_FAULTS:
                    report["syntheticTamperRejected"] = True
                    report["state"] = "SYNTHETIC_FAIL_CLOSED_NO_RECOVERY_CLAIM"
                    return report
                else:
                    raise
            report["syntheticRollbackComplete"] = _originals_restored(installed, before)
            report["fakeNewModulesAbsentAfterRecovery"] = all(
                not _path(installed, n).exists() for n in protocol.NEW_FILES)
            report["state"] = "SYNTHETIC_ROLLBACK_CHECKED"
        except LabStop:
            if fault != "after_seal":
                raise
            report["state"] = "SYNTHETIC_STOPPED_BEFORE_INSTALL"
            require(_originals_restored(installed, before), "UNEXPECTED_INSTALL")
    return report


def main():
    parser = argparse.ArgumentParser(
        description="v1.65 fake-file disk rollback test ONLY; no VPS installer")
    parser.add_argument("--rehearse-fixture-offline", action="store_true",
                        required=True)
    parser.parse_args()
    print(json.dumps(rehearse(mode=MODE), sort_keys=True))


if __name__ == "__main__":
    main()
