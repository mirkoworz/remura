"""REMURA v0.8.167 LAB — 18/11/2026, sessione successiva alle 16:21 CET.
Dual-inhibit descriptor-bound maintenance boundary, offline fixture only.
No CLI, service action, marker creation, installation or signature acceptance.
The caller must establish executable/import, anchor, mount and actual service trust.
"""
import fcntl
import os
from contextlib import contextmanager
from abc_v165_start_guard_v1 import open_chain, trusted_dir
from abc_v165_locked_snapshot_v1 import (
    BUNDLE_BYTES, BUNDLE_SHA256, check_entry, fingerprint, identity,
    private_file, read_exact, require,
)

MARKERS = ("maintenance-v165.inhibit", "collector-v165.inhibit")

def marker_fingerprints(work, uid):
    result = []
    for name in MARKERS:
        s = os.stat(name, dir_fd=work, follow_symlinks=False)
        require(private_file(s, uid))
        result.append(fingerprint(s))
    return tuple(result)

@contextmanager
def _boundary(anchor, work_parts, stage_parts, uid, length, digest):
    work = open_chain(anchor, work_parts, uid)
    try:
        require(trusted_dir(work, uid, private=True))
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        lock = os.open("lock", flags, dir_fd=work)
        try:
            original = check_entry(work, "lock", lock, uid)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            markers = marker_fingerprints(work, uid)
            def recheck():
                require(trusted_dir(work, uid, private=True))
                require(identity(original) == identity(check_entry(work, "lock", lock, uid)))
                require(markers == marker_fingerprints(work, uid))
                # Check the named directory still resolves to the held directory.
                named = open_chain(anchor, work_parts, uid)
                try:
                    require(identity(os.fstat(named)) == identity(os.fstat(work)))
                finally:
                    os.close(named)
            recheck()
            stage = open_chain(anchor, stage_parts, uid)
            try:
                require(trusted_dir(stage, uid, private=True))
                require(identity(os.fstat(stage)) != identity(os.fstat(work)))
                require(work_parts and stage_parts and
                        tuple(work_parts) != tuple(stage_parts[:len(work_parts)]) and
                        tuple(stage_parts) != tuple(work_parts[:len(stage_parts)]))
                data = read_exact(stage, "remura-v165-candidate.tar", uid, length, digest)
                recheck()
                try:
                    yield data
                finally:
                    recheck()
            finally:
                os.close(stage)
        finally:
            os.close(lock)
    finally:
        os.close(work)

@contextmanager
def locked_dual_inhibit_bytes(anchor, work_parts, stage_parts, uid):
    """Pinned TAR only. Cooperative lock; markers do not prove active systemd guards."""
    with _boundary(anchor, work_parts, stage_parts, uid, BUNDLE_BYTES, BUNDLE_SHA256) as data:
        yield data
