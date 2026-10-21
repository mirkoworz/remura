"""Serialize cTrader access/refresh across REMURA collector and backfill.

The private VM is Linux; flock is advisory and scoped to REMURA processes.
Prevents concurrent broker sessions and simultaneous OAuth refresh token writes.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import time


@contextmanager
def collection_guard(db_path, timeout_seconds=180):
    if timeout_seconds <= 0:
        raise ValueError("Timeout non valido.")
    private = Path(db_path).expanduser().resolve().parent
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = private / "ctrader-collection.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("cTrader occupato: raccolta saltata senza modifiche.")
                time.sleep(0.5)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
