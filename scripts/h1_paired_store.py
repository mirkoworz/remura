"""Private, bounded H1 before/after-ingest observations. No network or broker calls.

Only aggregate counters and UTC timestamps are stored. No symbols, OHLC,
provider identifiers, tokens, trading events or notifications leave this module.
This telemetry is strictly opt-in and never changes trading eligibility.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sqlite3

SCHEMA = "remura-h1-paired-observation-v1"
MAX_ROWS = 256
MAX_SNAPSHOT_BYTES = 65536
STATES = frozenset((
    "COMPARABLE", "MISSING_OR_UNBOUNDED", "INVALID_TARGETS",
    "INVALID_CLOCKS", "NON_COMPARABLE_CLOCKS", "INVALID_FULL_SCAN",
    "INCOMPLETE_FULL_SCAN", "INCOMPLETE_H1", "REGRESSED_H1",
))
COUNTS = (
    "compared", "fullScanH1ReadyAtSameUtc", "postIngestH1ReadyAtSameUtc",
    "staleToReady", "freshestH1Advanced", "unchangedH1",
    "fullScanAgeSeconds",
)


def _utc(value):
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise ValueError("timezone_required")
    return value.astimezone(dt.timezone.utc)


def _readonly(db_path):
    return sqlite3.connect(
        Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=3
    )


def load_full_scan(db_path):
    """Read the last 34-market scan, never perform another scan or fetch."""
    path = Path(db_path)
    if not path.is_file():
        return None
    try:
        with _readonly(path) as db:
            row = db.execute(
                "SELECT summary FROM squalincome_last_scan WHERE id=1"
            ).fetchone()
        if not row or type(row[0]) is not str:
            return None
        if len(row[0].encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            return None
        candidate = json.loads(row[0])
        return candidate if isinstance(candidate, dict) else None
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
        return None


def _verified_counts(comparison):
    if not isinstance(comparison, dict) or comparison.get("state") not in STATES:
        raise ValueError("invalid_comparison")
    if comparison.get("schema") != "remura-h1-paired-readiness-research-v1":
        raise ValueError("invalid_comparison_schema")
    state = comparison["state"]
    values = tuple(comparison.get(key) for key in COUNTS)
    if state != "COMPARABLE":
        if any(value is not None for value in values):
            raise ValueError("noncomparable_counts_must_be_null")
        return state, values
    if any(type(value) is not int for value in values):
        raise ValueError("missing_comparable_counts")
    n, old, new, recovered, advanced, unchanged, age = values
    if not (1 <= n <= 5 and 0 <= old <= new <= n and
            0 <= recovered <= new - old and
            advanced + unchanged == n and
            recovered <= advanced and 0 <= age <= 1800):
        raise ValueError("inconsistent_comparable_counts")
    return state, values


def record(db_path, comparison, *, post_scan_utc, ingest_returned_utc):
    """Store only allowlisted counters. Bounded to 256 rows, no raw snapshots."""
    post = _utc(post_scan_utc)
    ingest = _utc(ingest_returned_utc)
    if not ingest <= post or (post - ingest).total_seconds() > 3600:
        raise ValueError("invalid_pair_clock")
    state, counts = _verified_counts(comparison)
    path = Path(db_path)
    if not path.is_file():
        raise ValueError("database_missing")
    with sqlite3.connect(str(path), timeout=5) as db:
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS remura_h1_paired (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_utc TEXT NOT NULL,
            ingest_returned_utc TEXT NOT NULL,
            state TEXT NOT NULL,
            compared INTEGER,
            full_ready INTEGER,
            post_ready INTEGER,
            stale_to_ready INTEGER,
            advanced INTEGER,
            unchanged INTEGER,
            full_scan_age_seconds INTEGER)""")
        db.execute("""INSERT INTO remura_h1_paired (
            post_utc, ingest_returned_utc, state, compared,
            full_ready, post_ready, stale_to_ready, advanced,
            unchanged, full_scan_age_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
                post.isoformat(), ingest.isoformat(), state, *counts))
        db.execute("""DELETE FROM remura_h1_paired WHERE id NOT IN (
            SELECT id FROM remura_h1_paired ORDER BY id DESC LIMIT ?)""",
            (MAX_ROWS,))


def _empty(state):
    return {
        "schema": SCHEMA, "state": state, "windowMax": MAX_ROWS,
        "samples": None, "comparableSamples": None, "unverifiableSamples": None,
        "lastPostScanUtc": None, "lastState": None,
        "marketsCompared": None, "readyBefore": None, "readyAfter": None,
        "staleToReady": None, "h1Advanced": None, "h1Unchanged": None,
        "meaning": "paired_availability_not_ingest_causality_or_trading_edge",
    }


def summary(db_path):
    """Read only 256 aggregate rows, fail closed on missing/corrupt SQLite."""
    path = Path(db_path)
    if not path.is_file():
        return _empty("not_collected")
    try:
        with _readonly(path) as db:
            rows = db.execute("""SELECT post_utc, state, compared,
                full_ready, post_ready, stale_to_ready, advanced,
                unchanged, full_scan_age_seconds
                FROM remura_h1_paired ORDER BY id DESC LIMIT ?""",
                (MAX_ROWS,)).fetchall()
    except (sqlite3.Error, OSError, ValueError, OverflowError):
        return _empty("not_collected")
    if not rows:
        return _empty("not_collected")
    comparable = []
    try:
        for row in rows:
            stamp = dt.datetime.fromisoformat(row[0])
            if stamp.tzinfo is None:
                return _empty("invalid_data")
            metrics = dict(zip(COUNTS, row[2:]))
            _verified_counts({
                "schema": "remura-h1-paired-readiness-research-v1",
                "state": row[1], **metrics,
            })
            if row[1] == "COMPARABLE":
                comparable.append(row)
    except (TypeError, ValueError, OverflowError):
        return _empty("invalid_data")
    result = _empty("ready")
    result.update({
        "samples": len(rows),
        "comparableSamples": len(comparable),
        "unverifiableSamples": len(rows) - len(comparable),
        "lastPostScanUtc": dt.datetime.fromisoformat(rows[0][0])
            .astimezone(dt.timezone.utc).isoformat(),
        "lastState": rows[0][1],
    })
    if comparable:
        result.update({
            "marketsCompared": sum(r[2] for r in comparable),
            "readyBefore": sum(r[3] for r in comparable),
            "readyAfter": sum(r[4] for r in comparable),
            "staleToReady": sum(r[5] for r in comparable),
            "h1Advanced": sum(r[6] for r in comparable),
            "h1Unchanged": sum(r[7] for r in comparable),
        })
    return result
