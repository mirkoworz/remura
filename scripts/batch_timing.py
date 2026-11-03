"""Bounded private batch-lifecycle telemetry. Optional, no network/API calls.

Collect end is the RETURN from collect_once AFTER SQLite ingest; it is an
UPPER BOUND on persistence time, not the exact per-symbol commit timestamp.
Never record symbols, candles, tokens, provider details or request payloads.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import sqlite3
from statistics import median

SCHEMA = "remura-collector-batch-timing-v1"
MAX_ROWS = 256
MAX_SECONDS = 2 * 60 * 60
MAX_MARKETS = 8


def _utc(value):
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValueError("timezone_required")
    return value.astimezone(dt.timezone.utc)


def _stamp(value):
    return _utc(value).isoformat()


def record(db_path, *, started, ingest_returned, finished,
           scheduled_markets, saved_markets, slot,
           post_scan_state="not_run", post_scan_finished=None):
    """One bounded row per actual batch. No symbols and no extra broker call.

    Valid post_scan_state values: not_run, ok, failed. The post-ingest scan,
    when present, is already separately recorded in squalincome_scan_timing.
    """
    started, ingest_returned, finished = map(_utc, (started, ingest_returned, finished))
    if (not started <= ingest_returned <= finished or
            (finished - started).total_seconds() > MAX_SECONDS):
        raise ValueError("invalid_batch_clock")
    if (type(slot) is not int or not 1 <= slot <= 8 or
            type(scheduled_markets) is not int or not 1 <= scheduled_markets <= MAX_MARKETS or
            type(saved_markets) is not int or not 0 <= saved_markets <= scheduled_markets):
        raise ValueError("invalid_batch_counts")
    if post_scan_state not in ("not_run", "ok", "failed"):
        raise ValueError("invalid_scan_status")
    if post_scan_state == "not_run":
        if post_scan_finished is not None:
            raise ValueError("scan_timestamp_without_scan")
        post_scan_lag_ms = None
    else:
        end = _utc(post_scan_finished)
        if not ingest_returned <= end <= finished:
            raise ValueError("scan_timestamp_outside_batch")
        post_scan_lag_ms = round((end - ingest_returned).total_seconds() * 1000)
    path = Path(db_path)
    if not path.is_file():
        raise ValueError("database_missing")
    with sqlite3.connect(str(path), timeout=5) as db:
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS remura_batch_timing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_utc TEXT NOT NULL,
            ingest_returned_utc TEXT NOT NULL,
            finished_utc TEXT NOT NULL,
            slot INTEGER NOT NULL,
            scheduled_markets INTEGER NOT NULL,
            saved_markets INTEGER NOT NULL,
            batch_elapsed_ms INTEGER NOT NULL,
            post_scan_state TEXT NOT NULL,
            post_scan_lag_ms INTEGER)""")
        db.execute("""INSERT INTO remura_batch_timing (
            started_utc, ingest_returned_utc, finished_utc,
            slot, scheduled_markets, saved_markets,
            batch_elapsed_ms, post_scan_state, post_scan_lag_ms)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
                _stamp(started), _stamp(ingest_returned), _stamp(finished),
                slot, scheduled_markets, saved_markets,
                round((ingest_returned - started).total_seconds() * 1000),
                post_scan_state, post_scan_lag_ms))
        db.execute("""DELETE FROM remura_batch_timing WHERE id NOT IN (
            SELECT id FROM remura_batch_timing ORDER BY id DESC LIMIT ?)""",
            (MAX_ROWS,))


def _empty(state):
    return {"schema": SCHEMA, "state": state, "windowMax": MAX_ROWS,
            "samples": None, "lastIngestReturnedUtc": None,
            "scheduledMarkets": None, "savedMarkets": None,
            "zeroSavedBatches": None, "medianCollectorToIngestReturnMs": None,
            "maxCollectorToIngestReturnMs": None,
            "postScanSuccesses": None, "postScanFailures": None,
            "postScanNotRun": None, "medianIngestReturnToPostScanMs": None,
            "meaning": "sqlite_ingest_return_is_upper_bound_not_per_symbol_commit"}


def summary(db_path):
    """Aggregates from SQLite via read-only connection, no raw data exported."""
    path = Path(db_path)
    if not path.is_file():
        return _empty("not_collected")
    try:
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as db:
            rows = db.execute("""SELECT ingest_returned_utc, scheduled_markets,
                saved_markets, batch_elapsed_ms, post_scan_state,
                post_scan_lag_ms FROM remura_batch_timing
                ORDER BY id DESC LIMIT ?""", (MAX_ROWS,)).fetchall()
    except (sqlite3.Error, OSError, ValueError):
        return _empty("not_collected")
    if not rows:
        return _empty("not_collected")
    if any((type(x[1]) is not int or not 1 <= x[1] <= MAX_MARKETS or
            type(x[2]) is not int or not 0 <= x[2] <= x[1] or
            type(x[3]) is not int or not 0 <= x[3] <= MAX_SECONDS * 1000 or
            x[4] not in ("ok", "failed", "not_run") or
            (x[5] is not None and
             (type(x[5]) is not int or not 0 <= x[5] <= MAX_SECONDS * 1000)) or
            (x[4] == "not_run") != (x[5] is None))
           for x in rows):
        return _empty("invalid_data")
    try:
        latest = dt.datetime.fromisoformat(rows[0][0])
        if latest.tzinfo is None:
            return _empty("invalid_data")
        latest_stamp = latest.astimezone(dt.timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return _empty("invalid_data")
    durations = [x[3] for x in rows]
    lags = [x[5] for x in rows if x[4] == "ok"]
    return {"schema": SCHEMA, "state": "ready", "windowMax": MAX_ROWS,
            "samples": len(rows), "lastIngestReturnedUtc": latest_stamp,
            "scheduledMarkets": sum(x[1] for x in rows),
            "savedMarkets": sum(x[2] for x in rows),
            "zeroSavedBatches": sum(x[2] == 0 for x in rows),
            "medianCollectorToIngestReturnMs": int(median(durations)),
            "maxCollectorToIngestReturnMs": max(durations),
            "postScanSuccesses": sum(x[4] == "ok" for x in rows),
            "postScanFailures": sum(x[4] == "failed" for x in rows),
            "postScanNotRun": sum(x[4] == "not_run" for x in rows),
            "medianIngestReturnToPostScanMs": int(median(lags)) if lags else None,
            "meaning": "sqlite_ingest_return_is_upper_bound_not_per_symbol_commit"}
