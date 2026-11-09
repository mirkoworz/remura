#!/usr/bin/env python3
"""Read-only in-process collector liveness indicator for private REMURA.

No broker/Oracle/GitHub calls, file writes, restart, logging or timers.
This does NOT independently verify every market candle or broker connection.
"""
from __future__ import annotations

import datetime as dt

SCHEMA = "remura-collector-watchdog-v1"
RECENT_MINUTES = 45  # informational, not a market-hours model or alert gate


def _batch_age(last_success, now):
    """Age of last successful batch, with strict UTC-aware timestamps."""
    if not isinstance(last_success, str) or len(last_success) > 64:
        return None
    try:
        parsed = dt.datetime.fromisoformat(last_success.replace("Z", "+00:00"))
    except (OverflowError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    seconds = (now - parsed.astimezone(dt.timezone.utc)).total_seconds()
    if not 0 <= seconds <= 366 * 24 * 3600:
        return None
    return int(seconds // 60)


def snapshot(*, enabled, thread, last_success, now=None):
    """Return sanitized, advisory status; never change collection behavior.

    A responsive HTTP server can have a dead collector thread. The thread
    state is independent from age of the last successful batch, which can
    grow while markets are closed or when a broker refuses new data.
    """
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    elif not isinstance(now, dt.datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)
    result = {
        "schema": SCHEMA,
        "threadState": "unknown",
        "latestBatch": "unknown",
        "batchAgeMinutes": None,
        "autoRestart": False,
        "action": "observe_only",
    }
    if enabled is not True:
        result["threadState"] = "disabled"
        return result
    if thread is None:
        return result
    try:
        alive = thread.is_alive()
    except Exception:  # advisory-only: never fail an existing health request
        return result
    if type(alive) is not bool:
        return result
    result["threadState"] = "running" if alive else "stopped"
    age = _batch_age(last_success, now)
    if age is not None:
        result["batchAgeMinutes"] = age
        result["latestBatch"] = "recent" if age <= RECENT_MINUTES else "old_or_market_closed"
    return result
