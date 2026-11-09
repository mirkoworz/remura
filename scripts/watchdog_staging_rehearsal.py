#!/usr/bin/env python3
"""OFFLINE-ONLY integration audit, bundle hashes and rollback rehearsal.

All inputs are caller-supplied. No remote state, LIVE hashes, signed authority,
deployment permission or actual compatibility is attested by these helpers.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import os
from pathlib import PurePosixPath, Path
import tempfile

from watchdog_release_gate import check_bundle, SERVER, WATCHDOG

MAX_SOURCE = 2_000_000


def sha256(blob):
    if type(blob) is not bytes:
        raise TypeError("expected bytes")
    return hashlib.sha256(blob).hexdigest()


def _source(source):
    if type(source) is not str or len(source) > MAX_SOURCE:
        raise ValueError("invalid offline source")
    ast.parse(source)
    return source.splitlines(keepends=True)


def _changed_ranges(base_lines, fork_lines):
    return tuple(
        (i1, i2) for tag, i1, i2, _, _ in
        difflib.SequenceMatcher(a=base_lines, b=fork_lines, autojunk=False).get_opcodes()
        if tag != "equal"
    )


def _ranges_overlap(left, right):
    # Insertions at the same position, or inside a modified span, overlap.
    for a, b in left:
        for c, d in right:
            if (a == b and c == d and a == c) or (
                a == b and c <= a <= d
            ) or (c == d and a <= c <= b) or max(a, c) < min(b, d):
                return True
    return False


def audit_shared_server(base_source, fork_sources):
    """Report code changes in several forks of private_server.py.

    Never labels an automatic merge safe; even nonoverlapping edits require
    explicit human reconciliation and independent runtime regressions.
    """
    if type(fork_sources) is not dict or not 1 <= len(fork_sources) <= 5:
        return {"state": "INVALID_INPUT"}
    try:
        base = _source(base_source)
        ranges = {}
        digests = {}
        for name, source in fork_sources.items():
            if type(name) is not str or not name or len(name) > 50:
                return {"state": "INVALID_INPUT"}
            lines = _source(source)
            ranges[name] = _changed_ranges(base, lines)
            digests[name] = hashlib.sha256(source.encode("utf-8")).hexdigest()
        collisions = tuple(sorted(
            (a, b) for a in ranges for b in ranges
            if a < b and _ranges_overlap(ranges[a], ranges[b])
        ))
        changed = tuple(sorted(k for k, v in ranges.items() if v))
        return {
            "state": "MANUAL_RECONCILIATION_REQUIRED" if changed else "NO_FORK_CHANGES_OBSERVED",
            "changed_forks": changed,
            "overlap_pairs": collisions,
            "source_sha256": dict(sorted(digests.items())),
            "release_authorized": False,
        }
    except (SyntaxError, ValueError, TypeError, RecursionError, UnicodeError):
        return {"state": "INVALID_INPUT"}


def _safe_path(path):
    if type(path) is not str or not path or len(path) > 255:
        return False
    p = PurePosixPath(path)
    return not p.is_absolute() and str(p) == path and all(
        segment not in ("", ".", "..") and not segment.startswith(".")
        for segment in p.parts
    )


def verify_staged_bundle(manifest, files, expected_sha256):
    """Pure in-memory hash and dependency preflight against caller-supplied pins.

    This does not authenticate those pins, inspect LIVE, or certify an installer.
    """
    if type(files) is not dict or type(expected_sha256) is not dict:
        return False, "INVALID_BUNDLE"
    if type(manifest) not in (list, tuple) or not 2 <= len(manifest) <= 100:
        return False, "INVALID_BUNDLE"
    if any(type(path) is not str for path in manifest):
        return False, "INVALID_BUNDLE"
    if len(set(manifest)) != len(manifest):
        return False, "INVALID_BUNDLE"
    if any(not _safe_path(path) for path in manifest):
        return False, "UNSAFE_PATH"
    if set(manifest) != set(files) or set(manifest) != set(expected_sha256):
        return False, "FILE_SET_MISMATCH"
    for path in manifest:
        value, pin = files[path], expected_sha256[path]
        if type(value) is not bytes or len(value) > MAX_SOURCE:
            return False, "INVALID_BUNDLE"
        if type(pin) is not str or len(pin) != 64 or any(c not in "0123456789abcdef" for c in pin):
            return False, "INVALID_DIGEST"
        if sha256(value) != pin:
            return False, "HASH_MISMATCH"
    try:
        server = files[SERVER].decode("utf-8")
        watchdog = files[WATCHDOG].decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return False, "DEPENDENCY_UNAVAILABLE"
    ok, reason = check_bundle(manifest, server, watchdog)
    if not ok:
        return False, reason
    return True, "OFFLINE_PINS_MATCH_NO_RELEASE_AUTHORITY"


def simulate_rollback(original, candidate, failure_at="after_replace"):
    """Copy ONLY artificial bytes into a newly created temporary sandbox.

    failure_at: before_replace, after_replace, or none.
    Never accepts a target path; never operates on the repository or VPS.
    """
    if (type(original) is not bytes or type(candidate) is not bytes or
            max(len(original), len(candidate)) > MAX_SOURCE or
            failure_at not in ("before_replace", "after_replace", "none")):
        return False, "INVALID_INPUT"
    with tempfile.TemporaryDirectory(prefix="remura-watchdog-synthetic-") as temporary:
        root = Path(temporary)
        target, backup, staged = root / "target", root / "backup", root / "staged"
        target.write_bytes(original)
        backup.write_bytes(original)
        staged.write_bytes(candidate)
        try:
            if failure_at == "before_replace":
                raise RuntimeError("synthetic_pre_swap_failure")
            os.replace(staged, target)
            if failure_at == "after_replace":
                raise RuntimeError("synthetic_post_swap_failure")
        except RuntimeError:
            os.replace(backup, target)
            if target.read_bytes() != original:
                return False, "SYNTHETIC_ROLLBACK_FAILED"
            return True, "SYNTHETIC_ROLLBACK_VERIFIED"
        if target.read_bytes() != candidate:
            return False, "SYNTHETIC_STAGING_FAILED"
        return True, "SYNTHETIC_STAGING_VERIFIED_NOT_DEPLOYED"
