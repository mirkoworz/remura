"""Bounded private Squalincome scan timing, no price/credential data or API calls.

Metrics do NOT prove signal lead: a post-ingest batch-complete timestamp
may be later than individual price writes, and there is no matched
counterfactual periodic signal.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import sqlite3

KINDS = frozenset(("post_ingest", "periodic"))
MAX_ROWS = 256
MAX_MS = 12 * 60 * 60 * 1000
SCHEMA = "remura-squalincome-timing-v1"


def _utc(value):
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValueError("timestamp_timezone_required")
    return value.astimezone(dt.timezone.utc)


def record(db_path, *, kind, started, completed, duration_ms,
           saved_count=0, examined=0, new_events=0, ok=True, batch_completed=None):
    """One write after a finished scan; never call the broker."""
    if kind not in KINDS:
        raise ValueError("invalid_scan_kind")
    started, completed = _utc(started), _utc(completed)
    if completed < started or (completed-started).total_seconds() > MAX_MS/1000:
        raise ValueError("invalid_scan_clock")
    values = (duration_ms, saved_count, examined, new_events)
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError("invalid_scan_counts")
    if duration_ms > MAX_MS or saved_count > 5 or examined > 34 or new_events > 34:
        raise ValueError("invalid_scan_bounds")
    if type(ok) is not bool:
        raise ValueError("invalid_scan_result")
    if kind == "periodic":
        if batch_completed is not None or saved_count != 0:
            raise ValueError("periodic_has_batch")
        lag_ms = None
    else:
        batch_completed = _utc(batch_completed)
        lag_ms = round((completed-batch_completed).total_seconds()*1000)
        if not 0 <= lag_ms <= MAX_MS or examined > saved_count:
            raise ValueError("invalid_batch_lag")
    location = Path(db_path)
    if not location.is_file():
        raise ValueError("database_missing")
    with sqlite3.connect(str(location), timeout=5) as db:
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS squalincome_scan_timing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            started_utc TEXT NOT NULL,
            completed_utc TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            batch_to_scan_ms INTEGER,
            saved_count INTEGER NOT NULL,
            examined INTEGER NOT NULL,
            new_events INTEGER NOT NULL,
            ok INTEGER NOT NULL)""")
        db.execute("""INSERT INTO squalincome_scan_timing (
            kind, started_utc, completed_utc, duration_ms,
            batch_to_scan_ms, saved_count, examined, new_events, ok)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (kind, started.isoformat(), completed.isoformat(), duration_ms,
             lag_ms, saved_count, examined, new_events, int(ok)))
        db.execute("""DELETE FROM squalincome_scan_timing WHERE id NOT IN (
            SELECT id FROM squalincome_scan_timing ORDER BY id DESC LIMIT ?)""",
            (MAX_ROWS,))


def _stats(rows):
    if not rows:
        return {"samples": 0, "successes": 0, "failures": 0,
                "lastCompletedUtc": None, "medianDurationMs": None,
                "medianBatchToScanMs": None, "newEvents": 0}
    from statistics import median
    elapsed = sorted(int(x[2]) for x in rows if x[5])
    lag = sorted(int(x[3]) for x in rows if x[3] is not None and x[5])
    return {
        "samples": len(rows),
        "successes": sum(bool(x[5]) for x in rows),
        "failures": sum(not bool(x[5]) for x in rows),
        "lastCompletedUtc": rows[-1][1],
        "medianDurationMs": int(median(elapsed)) if elapsed else None,
        "medianBatchToScanMs": int(median(lag)) if lag else None,
        "newEvents": sum(int(x[4]) for x in rows if x[5]),
    }


def summary(db_path):
    """Safe metadata only; read-only and fail-closed on a pre-telemetry VPS."""
    empty = {"schema": SCHEMA, "state": "not_collected",
             "windowMax": MAX_ROWS, "periodic": _stats([]),
             "postIngest": _stats([]),
             "meaning": "batch_end_to_analysis_not_candle_or_signal_lead"}
    location = Path(db_path)
    if not location.is_file():
        return empty
    try:
        with sqlite3.connect(location.resolve().as_uri()+"?mode=ro",
                             uri=True, timeout=3) as db:
            rows = db.execute("""SELECT kind,completed_utc,duration_ms,
                batch_to_scan_ms,new_events,ok
                FROM squalincome_scan_timing ORDER BY id ASC LIMIT ?""",
                (MAX_ROWS,)).fetchall()
    except (sqlite3.Error, OSError):
        return empty
    if not rows or any(x[0] not in KINDS for x in rows):
        return empty
    return {"schema": SCHEMA, "state": "ready", "windowMax": MAX_ROWS,
            "periodic": _stats([x for x in rows if x[0]=="periodic"]),
            "postIngest": _stats([x for x in rows if x[0]=="post_ingest"]),
            "meaning": "batch_end_to_analysis_not_candle_or_signal_lead"}
