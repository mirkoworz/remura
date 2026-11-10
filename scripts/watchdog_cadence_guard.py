#!/usr/bin/env python3
"""Static read-only broker-cadence guard for the PR #99 passive Watchdog.

Protects a SMALL set of recognizable scheduling invariants, not the full
semantics or actual broker API quota. Never imports/executes app code.
"""
from __future__ import annotations

import ast


def _function(tree, name):
    return next((node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == name), None)


def _calls(tree, name):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == name]


def _attr_calls(tree, receiver, method):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == receiver and n.func.attr == method]


def inspect_cadence(server_source):
    """Return fail-closed result. Passing requires human review, never deploy.

    Constraints reflect the existing collector plan (two syntactic sites:
    primary + permitted restricted backup) and exact normal quarter wait.
    """
    if type(server_source) is not str or not 0 < len(server_source) <= 2_000_000:
        return {"state": "INVALID_INPUT", "release_authorized": False}
    try:
        tree = ast.parse(server_source)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return {"state": "INVALID_SYNTAX", "release_authorized": False}
    collector = _function(tree, "collector_loop")
    handler = _function(tree, "http_handler")
    main = _function(tree, "main")
    if not all((collector, handler, main)):
        return {"state": "MISSING_SERVER_FUNCTIONS", "release_authorized": False}
    violations = []

    calls = _calls(collector, "collect_once")
    primary = [c for c in calls if not any(kw.arg == "source" for kw in c.keywords)]
    backup = [c for c in calls if any(kw.arg == "source"
              and isinstance(kw.value, ast.Constant) and kw.value.value == "backup"
              for kw in c.keywords)]
    if len(calls) != 2 or len(primary) != 1 or len(backup) != 1:
        violations.append("BROKER_CALL_SITE_DRIFT")

    loops = [n for n in ast.walk(collector) if isinstance(n, (ast.While, ast.For, ast.AsyncFor))]
    whiles = [n for n in loops if isinstance(n, ast.While)]
    if len(whiles) != 1 or len(loops) != 3:
        # Existing collector has 1 outer while, 2 nested for loops.
        violations.append("LOOP_STRUCTURE_DRIFT")
    else:
        outer = whiles[0]
        if (not isinstance(outer.test, ast.UnaryOp) or
                not isinstance(outer.test.op, ast.Not) or
                not _attr_calls(outer.test, "stop", "is_set")):
            violations.append("STOP_GUARD_DRIFT")
        waits = _attr_calls(collector, "stop", "wait")
        if len(waits) != 1 or len(waits[0].args) != 1 or not (
                isinstance(waits[0].args[0], ast.Call) and
                isinstance(waits[0].args[0].func, ast.Name) and
                waits[0].args[0].func.id == "seconds_to_next_quarter"):
            violations.append("QUARTER_WAIT_DRIFT")
        marks = _attr_calls(collector, "progress", "mark_completed")
        if len(marks) != 1:
            violations.append("PROGRESS_WITNESS_DRIFT")
        # The progress marker must be in the same outer loop and precede wait.
        if not marks or not waits or marks[0].lineno >= waits[0].lineno:
            violations.append("PROGRESS_ORDER_DRIFT")

    symbols_constants = [n.value for n in ast.walk(collector) if isinstance(n, ast.Constant)]
    if "REMURA_PRIORITY_COLLECTOR_ENABLED" not in symbols_constants or not (
            _calls(collector, "collector_batches") and
            _calls(collector, "collector_priority_batches")):
        violations.append("PRIORITY_OPTIN_OR_BATCH_PLAN_DRIFT")

    if (_calls(handler, "collect_once") or _calls(handler, "collector_loop") or
            _calls(handler, "CycleProgress")):
        violations.append("BROKER_OR_WORKER_IN_HTTP")

    if _attr_calls(collector, "time", "sleep") or _attr_calls(collector, "threading", "Timer"):
        violations.append("EXTRA_TIMER_IN_COLLECTOR")

    starter = [c for c in _attr_calls(main, "threading", "Thread")
               if any(kw.arg == "target" and isinstance(kw.value, ast.Name)
                      and kw.value.id == "collector_loop" for kw in c.keywords)]
    if len(starter) != 1 or len(_calls(main, "CycleProgress")) != 1:
        violations.append("COLLECTOR_THREAD_OR_PROGRESS_START_DRIFT")

    return {
        "state": "STATIC_REVIEW_REQUIRED" if not violations else "BLOCKED_CADENCE_DRIFT",
        "violations": tuple(sorted(set(violations))),
        "release_authorized": False,
    }
