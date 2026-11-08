#!/usr/bin/env python3
"""Track C3c-c: LAB-ONLY separate-process worker chaos gate.

The caller is a RESEARCH ORCHESTRATOR, never a core collector. A process
boundary plus a separate temporary research WAL are rehearsed here; this is
NOT a production supervisor, real-time delivery guarantee, or measured
Oracle capacity. Core writers must never call this synchronous function.
No provider, network, broker, Oracle, notification, or live database access.
The only possible ACK is synthetic; crash/timeout/lock = UNKNOWN.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

# -I excludes both PYTHONPATH and the script directory. Restore ONLY the
# immutable sibling scripts directory for our audited, standard-library-only
# research WAL module; do not restore external module lookup paths.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import track_c_c3b_durable_shadow as shadow

MODE = "OFFLINE_SYNTHETIC_C3CC_ISOLATED_WORKER_ONLY"
UNKNOWN = shadow.UNKNOWN
BEHAVIORS = frozenset(("ack", "crash", "stall", "spin"))
MAX_TIMEOUT_SECONDS = 5.0


def run_lab_once(path, *, at, enabled=False, mode=None,
                 behavior="ack", timeout_seconds=2.0):
    """Run only a bounded synthetic worker in another Python interpreter.

    NEVER invoke from price/COT/retail collector code. A blocking wait here
    is permissible ONLY in this independent offline research harness.
    """
    if mode != MODE:
        raise ValueError("explicit_isolated_offline_lab_mode_required")
    p = shadow._path(path, shadow.MODE)
    if type(enabled) is not bool or not enabled:
        return UNKNOWN
    if (type(behavior) is not str or behavior not in BEHAVIORS or
            type(timeout_seconds) not in (float, int) or
            type(timeout_seconds) is bool or
            not 0.2 <= timeout_seconds <= MAX_TIMEOUT_SECONDS):
        raise ValueError("bounded_synthetic_behavior_and_timeout_required")
    try:
        shadow._utc(at)
        if not p.is_file():
            return UNKNOWN
        # No environment inherited: no tokens, credentials, paths, proxy
        # configuration or custom Python import path in the child.
        clean_env = {"PYTHONDONTWRITEBYTECODE": "1",
                     "PYTHONNOUSERSITE": "1"}
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()),
             "--child", str(p), at, behavior],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            cwd=str(p.parent), env=clean_env, shell=False,
            timeout=timeout_seconds, check=False)
        return (shadow.ACKED
                if result.returncode == 0 and
                result.stdout.strip() == "SYNTHETIC_ACK"
                else UNKNOWN)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # subprocess.run kills and waits for an over-time child.
        return UNKNOWN


def _child_limits():
    """Linux GitHub Actions laboratory caps; fail CLOSED if unavailable."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,
                                               256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,
                                                  1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
        return True
    except (ImportError, OSError, ValueError):
        return False


def _child(argv):
    if len(argv) != 4 or argv[0] != "--child":
        return 70
    _, filename, at, behavior = argv
    if behavior not in BEHAVIORS or not _child_limits():
        return 71
    # CPython may add LC_CTYPE when coercing the C locale (PEP 538).
    # It was NOT forwarded from the parent; never permit other variables.
    if set(os.environ) - {"PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE",
                           "LC_CTYPE"}:
        return 72
    try:
        p = shadow._path(filename, shadow.MODE)
        if not p.is_file():
            return 73
        job = shadow.claim(p, at=at, enabled=True, mode=shadow.MODE)
        if job is None:
            return 74
        if behavior == "crash":
            os._exit(77)  # abrupt process death AFTER durable lease
        if behavior == "stall":
            time.sleep(30)
            return 75
        if behavior == "spin":
            while True:
                pass
        receipt = shadow.finish(
            p, item_id=job["id"], lease_token=job["leaseToken"],
            at=at, synthetic_worker_ok=True, enabled=True, mode=shadow.MODE)
        if receipt != shadow.ACKED:
            return 76
        print("SYNTHETIC_ACK")
        return 0
    except (OSError, ValueError):
        return 78


if __name__ == "__main__":
    sys.exit(_child(sys.argv[1:]))
