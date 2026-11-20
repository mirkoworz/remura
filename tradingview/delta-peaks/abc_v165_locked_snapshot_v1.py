"""REMURA v0.8.158 LAB — 18/11/2026, 13:29 CET.
Descriptor-bound candidate snapshot under the historical maintenance lock.
No CLI, installation, writes, signature acceptance, or service actions.
Caller must independently establish executable/import and anchor trust.
"""
import fcntl
import hashlib
import os
import stat
from contextlib import contextmanager
from abc_v165_start_guard_v1 import open_chain, trusted_dir

BUNDLE_BYTES = 1771520
BUNDLE_SHA256 = "6804531c819ec16af972755b042394ac5c9acee23b7c03f70a09ab765369cfcc"
MARKER = "maintenance-v165.inhibit"
FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def require(ok):
    if not ok:
        raise ValueError("LOCKED_SNAPSHOT_GATE")


def identity(s):
    return s.st_dev, s.st_ino


def fingerprint(s):
    return identity(s), s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_uid, s.st_nlink


def private_file(s, uid):
    return (stat.S_ISREG(s.st_mode) and s.st_uid == uid
            and not s.st_mode & 0o077 and s.st_nlink == 1)


def check_entry(directory, name, fd, uid):
    s = os.fstat(fd)
    require(private_file(s, uid))
    require(fingerprint(s) == fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)))
    return s


def read_exact(directory, name, uid, length, digest):
    require(type(length) is int and 0 < length <= 8 * 1024 * 1024)
    require(name not in ("", ".", "..") and "/" not in name)
    fd = os.open(name, FLAGS, dir_fd=directory)
    try:
        s = check_entry(directory, name, fd, uid)
        require(s.st_size == length)
        with os.fdopen(os.dup(fd), "rb") as stream:
            data = stream.read(length + 1)
        require(len(data) == length)
        require(fingerprint(s) == fingerprint(check_entry(directory, name, fd, uid)))
        require(hashlib.sha256(data).hexdigest() == digest)
        return data
    finally:
        os.close(fd)


@contextmanager
def _locked_snapshot(anchor, work_parts, stage_parts, uid, length, digest):
    # Existing lock only: never recreate a missing lock or truncate it.
    work = open_chain(anchor, work_parts, uid)
    try:
        require(trusted_dir(work, uid, private=True))
        fd = os.open("lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=work)
        try:
            original = check_entry(work, "lock", fd, uid)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(identity(original) == identity(check_entry(work, "lock", fd, uid)))
            marker = os.stat(MARKER, dir_fd=work, follow_symlinks=False)
            require(private_file(marker, uid))
            stage = open_chain(anchor, stage_parts, uid)
            try:
                require(trusted_dir(stage, uid, private=True))
                require(identity(os.fstat(stage)) != identity(os.fstat(work)))
                data = read_exact(stage, "remura-v165-candidate.tar", uid, length, digest)
                # Recheck the named lock and durable inhibit before exposing bytes.
                require(identity(original) == identity(check_entry(work, "lock", fd, uid)))
                require(fingerprint(marker) == fingerprint(os.stat(MARKER, dir_fd=work, follow_symlinks=False)))
                yield data
            finally:
                os.close(stage)
        finally:
            os.close(fd)
    finally:
        os.close(work)


@contextmanager
def locked_candidate_bytes(anchor, work_parts, stage_parts, uid):
    """Yield only the pinned immutable bytes, with the cooperative lock held.
    Not authorization. No root bootstrap, coherent live snapshot, journal
    authentication, or signature verification is inferred from this operation.
    """
    with _locked_snapshot(anchor, work_parts, stage_parts, uid, BUNDLE_BYTES, BUNDLE_SHA256) as data:
        yield data
