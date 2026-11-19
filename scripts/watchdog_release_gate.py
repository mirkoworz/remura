#!/usr/bin/env python3
"""Offline-only safety check for a FUTURE Watchdog release bundle.

Pure static validation: no filesystem, OCI, GitHub, broker calls, subprocess,
writes, timer, deployment or dynamic execution. Does not approve deployment.
"""
from __future__ import annotations

import ast


SERVER = "scripts/private_server.py"
WATCHDOG = "scripts/collector_watchdog.py"


def check_bundle(manifest, server_source, watchdog_source):
    """Validate staged file list AND syntax/import contract, fail closed.

    Inputs come from a future release planner. This does not inspect the
    installed VPS, hash files, verify rollback, or replace a release gate.
    """
    try:
        if type(manifest) not in (tuple, list):
            return False, "MANIFEST_INVALID"
        if (len(manifest) > 100 or
                any(type(x) is not str or not x or len(x) > 255 for x in manifest) or
                len(set(manifest)) != len(manifest)):
            return False, "MANIFEST_INVALID"
        if SERVER not in manifest or WATCHDOG not in manifest:
            return False, "DEPENDENCY_NOT_STAGED"
        if type(server_source) is not str or type(watchdog_source) is not str:
            return False, "SOURCE_INVALID"
        if len(server_source) > 2_000_000 or len(watchdog_source) > 50_000:
            return False, "SOURCE_INVALID"

        server_tree = ast.parse(server_source, filename=SERVER)
        watchdog_tree = ast.parse(watchdog_source, filename=WATCHDOG)
        imported = any(
            isinstance(item, ast.ImportFrom) and
            item.module == "collector_watchdog" and item.level == 0 and
            any(alias.name == "snapshot" and
                alias.asname == "collector_watchdog_snapshot" for alias in item.names)
            for item in server_tree.body
        )
        exposed = any(
            isinstance(node, ast.Constant) and node.value == "collectorWatchdog"
            for node in ast.walk(server_tree)
        )
        defined = any(
            isinstance(item, ast.FunctionDef) and item.name == "snapshot"
            for item in watchdog_tree.body
        )
        if not (imported and exposed and defined):
            return False, "WATCHDOG_CONTRACT_MISSING"
        compile(server_tree, SERVER, "exec")
        compile(watchdog_tree, WATCHDOG, "exec")
    except (SyntaxError, TypeError, ValueError, RecursionError, OverflowError):
        return False, "SOURCE_INVALID"
    return True, "BUNDLE_CONTRACT_READY_OFFLINE_ONLY"
