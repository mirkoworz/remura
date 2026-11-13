#!/usr/bin/env python3
"""PR #99 research-only static compatibility contract for a FUTURE merged server.

No branch fetching, imports of app modules, execution of candidate code, IO,
secret access, deployment or merge. The caller provides candidate source and pin.
A green static check is NEVER release authorization.
"""
from __future__ import annotations

import ast
import hashlib

MAX_SOURCE_CHARS = 2_000_000


def _node(tree, name):
    return next((n for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == name), None)


def _call(node, name):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == name for n in ast.walk(node))


def _attribute_call(node, obj, meth):
    return any(isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute)
               and isinstance(n.func.value, ast.Name)
               and n.func.value.id == obj
               and n.func.attr == meth for n in ast.walk(node))


def _constant(node, value):
    return any(isinstance(n, ast.Constant) and n.value == value
               for n in ast.walk(node))


def _optional_off(function, argument):
    """An explicit kw-only opt-in, default literal False, never implicit True."""
    if function is None:
        return False
    for arg, default in zip(function.args.kwonlyargs, function.args.kw_defaults):
        if arg.arg == argument:
            return isinstance(default, ast.Constant) and default.value is False
    return False


def _keyword_call(node, callee, keyword):
    for c in ast.walk(node):
        if not isinstance(c, ast.Call):
            continue
        if isinstance(c.func, ast.Name):
            found = c.func.id == callee
        elif isinstance(c.func, ast.Attribute):
            found = c.func.attr == callee
        else:
            found = False
        if found and any(k.arg == keyword for k in c.keywords):
            return True
    return False


def _named_import(tree, module, original, alias=None):
    return any(isinstance(n, ast.ImportFrom) and n.level == 0
               and n.module == module
               and any(a.name == original and a.asname == alias
                       for a in n.names) for n in tree.body)


def inspect_candidate(server_source, expected_sha256):
    """Return explicit missing contracts; no automatic merge or production GO.

    expected_sha256 is caller-supplied and NOT independently authenticated.
    Source structural matches do NOT establish runtime behavior or security.
    """
    if (type(server_source) is not str or
            len(server_source) > MAX_SOURCE_CHARS or
            type(expected_sha256) is not str or len(expected_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in expected_sha256)):
        return {"state": "INVALID_INPUT", "release_authorized": False}
    actual = hashlib.sha256(server_source.encode("utf-8")).hexdigest()
    if actual != expected_sha256:
        return {"state": "UNPINNED_CANDIDATE", "release_authorized": False}
    try:
        tree = ast.parse(server_source, filename="scripts/private_server.py")
    except (SyntaxError, RecursionError, ValueError, MemoryError):
        return {"state": "INVALID_SYNTAX", "release_authorized": False}

    collect = _node(tree, "collect_once")
    collector_loop = _node(tree, "collector_loop")
    retail = _node(tree, "retail_once")
    periodic = _node(tree, "observe_periodic_squalincome")
    squal_loop = _node(tree, "squalincome_loop")
    handler = _node(tree, "http_handler")
    main = _node(tree, "main")
    missing = []

    # PR #89: only optional research paths, still disabled by default.
    if not (collect and _optional_off(collect, "research_ingest_first_seen")
            and _keyword_call(collect, "ingest", "research_parent_read_at")):
        missing.append("B_INGEST_OPTIN")
    if not (retail and _optional_off(retail, "research_retail_first_seen")
            and _optional_off(retail, "research_retail_numeric_features")
            and _attribute_call(retail, "retail_research", "capture_pair")):
        missing.append("B_RETAIL_OPTIN")
    if not (periodic and squal_loop
            and _call(squal_loop, "observe_periodic_squalincome")
            and _constant(periodic, "REMURA_SHARK_COMPACT_RESEARCH_ENABLED")
            and _constant(periodic, "REMURA_SHARK_COMPACT_RESEARCH_ACK")):
        missing.append("B_PERIODIC_RESEARCH_GUARD")

    # PR #98: metadata cache on the existing resources route, explicitly gated.
    if not (_named_import(tree, "storage_cache_v165", "StorageMetadataCache")
            and handler and _constant(handler, "storageInventory")
            and _constant(handler, "REMURA_STORAGE_DIAG_ENABLED")
            and _attribute_call(handler, "_STORAGE_CACHE", "peek")):
        missing.append("V165_RESOURCES_CACHE")
    if not (main and _constant(main, "REMURA_STORAGE_DIAG_ENABLED")
            and _attribute_call(main, "_STORAGE_CACHE", "start")):
        missing.append("V165_STORAGE_START")

    # PR #99: health observation and explicit collector thread binding.
    if not _named_import(tree, "collector_watchdog", "snapshot", "collector_watchdog_snapshot"):
        missing.append("WATCHDOG_IMPORT")
    if not (handler and _constant(handler, "collectorWatchdog")
            and _call(handler, "collector_watchdog_snapshot")
            and _keyword_call(handler, "collector_watchdog_snapshot", "thread")):
        missing.append("WATCHDOG_HEALTH_FIELD")
    if not (handler and main and
            any(arg.arg == "collector_thread" for arg in handler.args.args)
            and _keyword_call(main, "http_handler", "collector_thread")):
        missing.append("WATCHDOG_THREAD_WIRING")
    if not (_named_import(tree, "collector_watchdog", "CycleProgress")
            and collector_loop and handler and main
            and any(arg.arg == "progress" for arg in collector_loop.args.kwonlyargs)
            and _attribute_call(collector_loop, "progress", "mark_completed")
            and any(arg.arg == "collector_progress" for arg in handler.args.args)
            and _keyword_call(handler, "collector_watchdog_snapshot", "progress")
            and _call(main, "CycleProgress")
            and (_constant(main, "progress") or
                 _keyword_call(main, "collector_loop", "progress"))
            and _keyword_call(main, "http_handler", "collector_progress")):
        missing.append("WATCHDOG_CYCLE_PROGRESS")

    return {
        "state": "STRUCTURAL_REVIEW_REQUIRED" if not missing else "BLOCKED_MISSING_CONTRACTS",
        "missing": tuple(sorted(missing)),
        "candidate_sha256": actual,
        "release_authorized": False,
    }
