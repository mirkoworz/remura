#!/usr/bin/env python3
"""REMURA v1.65 preflight: independent, LOCAL, read-only v1.64 file identity.

PREPARED CODE ONLY; DO NOT RUN ON LIVE WITHOUT SEPARATE APPROVAL.
No autoupdater, state-file, SQLite, shell, GitHub/OCI/HTTP/Tailscale, credentials,
environment variables, service or private-data access. Reads precisely 15
allowlisted application files, max 3 MiB each, from a descriptor-pinned
/opt/remura tree, with no symlink following. No writes or automatic repair.
The OS may update access times when content is read (mount-dependent).

The pinned Git blob hashes were independently checked against the full tree
of the published v1.64 release commit. nav.js has ONE deliberate exception:
its real Italian install-time stamp is normalized back to the source
preparation stamp before hashing, rejecting all other differences.
A match does NOT attest the updater installedSha, service health, LIVE version,
Oracle eligibility, backup, release approval or any v1.65 installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat

SOURCE_COMMIT = "883336a4e956a9e50c94dcfebf8d7ba78910fb65"
SCHEMA = "remura-v165-independent-v164-code-identity-readonly-v1"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
MAX_FILE = 3_000_000
STAMP_PREPARED = b"05/11/2026 18:03 (Italia, preparazione)"
STAMP_LIVE = re.compile(
    rb"(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/20[0-9]{2} "
    rb"(?:[01][0-9]|2[0-3]):[0-5][0-9] \(Italia\)")
FILES = (
    "scripts/private_server.py",
    "nav.js",
    "sw.js",
    "index.html",
    "asset.html",
    "mercati.html",
    "forex.html",
    "catalogo.html",
    "statistica-squali.html",
    "stato-prezzi.html",
    "fonti.html",
    "impostazioni.html",
    "splash.js",
    "splash.css",
    "splash-mascot.webp",
)
GIT_BLOBS = {
    "scripts/private_server.py": "0853194762f3f0340451a69c9ed8b4e0261db42d",
    "nav.js": "d35c9d06f9c64a10938f30ec7e7ae7b2f2c5fbec",
    "sw.js": "6e447938533ff91183959d1902853634e6a83257",
    "index.html": "b41ebbf9f768bfa4a57d625620eb9b3f53b3e445",
    "asset.html": "2036c63dc8ff2930636f6dc9d4259fa2353c8b11",
    "mercati.html": "10d20744ed69531d4d51bdda194c01b5fcd116f3",
    "forex.html": "e4f7c9fea8924dd3a1fffed18363e30dd539f8ca",
    "catalogo.html": "2847a1ecb36ee92aa36e14444db5770f846f4978",
    "statistica-squali.html": "4cd8ca9420f95deaa916fa5853d9fae697f0ad0a",
    "stato-prezzi.html": "193211906f303db1b8ef9e6c1af4e30e01b6ce4c",
    "fonti.html": "17b6ebedf83531e070f150d29ad508c1812c0cee",
    "impostazioni.html": "d772e2e8313148384fc2495faf189f8b1fa9d800",
    "splash.js": "9484df12d5ff9e3b538f5fc513d013d7c641b470",
    "splash.css": "54a847194847c88c0eca12824f860574e4909aaa",
    "splash-mascot.webp": "60433776bf6a94d2b342023446dc62a409f58962",
}


class LocalReadOnlyStop(ValueError):
    """Sanitized stop; never includes file names, paths or file contents."""


def require(condition, reason):
    if not condition:
        raise LocalReadOnlyStop("STOP_" + reason)


def git_blob(payload):
    require(type(payload) is bytes and 0 < len(payload) <= MAX_FILE,
            "BOUNDED_BYTES_REQUIRED")
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    ).hexdigest()


def _directory_flags():
    require(all(hasattr(os, f) for f in ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")),
            "LINUX_NOFOLLOW_REQUIRED")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _file_flags():
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "LINUX_SAFE_OPEN_REQUIRED")
    return os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)


def _open_live_dir():
    """Only / -> opt -> remura, with pinned directory fds and NOFOLLOW."""
    flags = _directory_flags()
    fd = os.open("/", flags)
    try:
        for name in ("opt", "remura"):
            child = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _bounded_file(directory_fd, name):
    """One regular, non-hardlinked file via O_NOFOLLOW; fail on concurrent edits."""
    require(type(name) is str and name not in ("", ".", "..")
            and "/" not in name and "\\" not in name, "FILE_COMPONENT")
    fd = os.open(name, _file_flags(), dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= MAX_FILE,
                "FILE_NOT_REGULAR_SINGLE_LINK_OR_BOUNDED")
        parts = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_FILE + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            require(total <= MAX_FILE, "FILE_TOO_LARGE")
            parts.append(chunk)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size,
                    after.st_mtime_ns, after.st_ctime_ns)
                and total == before.st_size,
                "CHANGED_DURING_READ")
        return b"".join(parts)
    finally:
        os.close(fd)


def _normalized_blob(name, data):
    if name != "nav.js":
        return git_blob(data)
    require(STAMP_PREPARED not in data, "NAV_PREPARATION_STAMP_NOT_LIVE")
    stamps = STAMP_LIVE.findall(data)
    require(len(stamps) == 1, "NAV_STAMP_MISSING_OR_AMBIGUOUS")
    require(stamps[0] != STAMP_PREPARED, "NAV_PREPARATION_STAMP_NOT_LIVE")
    return git_blob(data.replace(stamps[0], STAMP_PREPARED))


def _verify_fd(root_fd, expected):
    """Fixture-friendly core, still an exact 15-file allowlist."""
    require(type(expected) is dict and tuple(expected) == FILES
            and all(type(x) is str and re.fullmatch("[0-9a-f]{40}", x)
                    for x in expected.values()), "MANIFEST_INVALID")
    scripts_fd = None
    try:
        for name in FILES:
            if name.startswith("scripts/"):
                if scripts_fd is None:
                    scripts_fd = os.open("scripts", _directory_flags(), dir_fd=root_fd)
                data = _bounded_file(scripts_fd, name[8:])
            else:
                data = _bounded_file(root_fd, name)
            require(_normalized_blob(name, data) == expected[name],
                    "PINNED_FILE_MISMATCH")
        return len(FILES)
    finally:
        if scripts_fd is not None:
            os.close(scripts_fd)


def _result(*, status, count):
    return {
        "schema": SCHEMA,
        "status": status,
        "fixedReleaseSourceCommit": SOURCE_COMMIT,
        "expectedPinnedFiles": len(FILES),
        "independentlyComparedFiles": count,
        "fullInstalledShaFromUpdaterVerified": False,
        "liveV165VersionAttested": False,
        "realSqliteBackupOrRestoreVerified": False,
        "oracleAlwaysFreeVerified": False,
        "privateAccessAclVerified": False,
        "authorizedRelease": False,
        "productionFilesModifiedByProgram": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }


def scan_local_readonly():
    """Future explicitly authorized local run only; no live paths configurable."""
    require(len(FILES) == 15 and set(FILES) == set(GIT_BLOBS),
            "PINNED_MANIFEST_DRIFT")
    root_fd = _open_live_dir()
    try:
        count = _verify_fd(root_fd, GIT_BLOBS)
    finally:
        os.close(root_fd)
    return _result(status="V164_PINNED_SOURCE_CONTENT_MATCH_ONLY",
                   count=count)


def main():
    parser = argparse.ArgumentParser(
        description="REMURA v1.64 immutable local-code check; NO update or deploy")
    parser.add_argument("--audit-live-readonly", action="store_true", required=True)
    parser.add_argument("--operator-approved", action="store_true", required=True)
    args = parser.parse_args()
    _ = args
    try:
        print(json.dumps(scan_local_readonly(), sort_keys=True))
        return 0
    except BaseException:
        # Never echo paths, file data, host-specific permission errors or hashes.
        print(json.dumps(_result(status="STOP_LOCAL_CODE_NOT_ATTESTED",
                                 count=0), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
