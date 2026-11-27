#!/usr/bin/env python3
"""Read-only in-process collector liveness indicator for private REMURA.

No broker/Oracle/GitHub calls, file writes, restart, logging or timers.
This does NOT independently verify every market candle or broker connection.
"""
from __future__ import annotations

import datetime as dt
import math
import threading
import time

SCHEMA = "remura-collector-watchdog-v1"
RECENT_MINUTES = 45  # informational, not a market-hours model or alert gate
CYCLE_GAP_MINUTES = 60  # conservative advisory window, NOT an SLA or auto-restart


class CycleProgress:
    """Volatile in-process witness of completed collector loop iterations.

    Only the collector marks a completion; HTTP requests only read the clock.
    No worker, timer, broker request, database write or persistence is added.
    """

    def __init__(self, clock=None):
        self._clock = time.monotonic if clock is None else clock
        self._lock = threading.Lock()
        self._started_at = self._clock()
        self._last_completed_at = None

    def mark_completed(self):
        """Best-effort telemetry must not interrupt a valid collector batch."""
        try:
            stamp = self._clock()
            if type(stamp) not in (int, float) or not math.isfinite(stamp):
                return
            with self._lock:
                self._last_completed_at = stamp
        except Exception:
            return

    def age_minutes(self):
        """Return (integer minutes since last completion or start, completed)."""
        try:
            now = self._clock()
            with self._lock:
                completed = self._last_completed_at is not None
                stamp = self._last_completed_at if completed else self._started_at
            if (type(now) not in (int, float) or type(stamp) not in (int, float)
                    or not math.isfinite(now) or not math.isfinite(stamp)):
                return None
            elapsed = now - stamp
            if not math.isfinite(elapsed) or elapsed < 0:
                return None
            return int(elapsed // 60), completed
        except Exception:
            return None



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


def snapshot(*, enabled, thread, last_success, now=None, progress=None):
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
        "progressState": "unknown",
        "progressAgeMinutes": None,
        "autoRestart": False,
        "action": "observe_only",
    }
    if enabled is not True:
        result["threadState"] = "disabled"
        result["progressState"] = "disabled"
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
    if not alive:
        result["progressState"] = "stopped"
    elif isinstance(progress, CycleProgress):
        observed = progress.age_minutes()
        if observed is not None:
            progress_age, completed = observed
            result["progressAgeMinutes"] = progress_age
            if completed:
                result["progressState"] = ("recent_cycle" if progress_age <= CYCLE_GAP_MINUTES
                                           else "no_recent_cycle")
            else:
                result["progressState"] = ("awaiting_first_cycle" if progress_age <= CYCLE_GAP_MINUTES
                                           else "first_cycle_overdue")
    age = _batch_age(last_success, now)
    if age is not None:
        result["batchAgeMinutes"] = age
        result["latestBatch"] = "recent" if age <= RECENT_MINUTES else "old_or_market_closed"
    return result
