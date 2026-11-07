"""REMURA Track B: bounded, append-only evidence of OBSERVED failed scans.

Only called by the FUTURE double-opt-in single-pass periodic route, *after*
an actual exception. Does not infer causes from absent calendar slots, detect
SIGKILL, claim broker downtime, or capture free-form exception messages,
credentials, symbol names, quotes or data. A failed logging attempt remains
UNKNOWN; never silently turn it into a recorded failure.

Local SQLite short transaction on the SAME already-existing database;
no network calls or independent scheduler. No writes in the legacy path.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sqlite3

from scripts import shark_cot_asof_witness as witness

TABLE = "research_scan_failures"
SCHEMA = "remura-research-scan-failures-v1"
MAX_ROWS = 10000
MAX_DAYS = 7
STAGES = ("ACTIVATION", "COMPACT_SCAN")
CODES = ("SOURCE_CHANGED", "SQLITE_BUSY", "SQLITE_OTHER",
         "WITNESS_INVALID", "SCAN_INVALID", "OTHER_ERROR")
TRIGGERS = ("research_scan_failures_no_update",
            "research_scan_failures_no_delete")


def reason(exc, *, stage):
    """Allowlist classifier: never persist str(exc) or exception repr."""
    if stage not in STAGES:
        raise ValueError("invalid_failure_stage")
    if (stage == "COMPACT_SCAN"
            and isinstance(exc, sqlite3.OperationalError)
            and str(exc) == "research_source_changed_before_atomic_commit"):
        return "SOURCE_CHANGED"
    if isinstance(exc, sqlite3.OperationalError):
        # Only literal, engine-recognized lock/busy errors. Do not treat
        # unknown operational errors as a writer collision.
        if str(exc).lower() in ("database is locked", "database is busy",
                                "database table is locked"):
            return "SQLITE_BUSY"
        return "SQLITE_OTHER"
    if isinstance(exc, sqlite3.Error):
        return "SQLITE_OTHER"
    if isinstance(exc, (ValueError, TypeError, KeyError, OverflowError)):
        return "WITNESS_INVALID" if stage == "ACTIVATION" else "SCAN_INVALID"
    return "OTHER_ERROR"


def _schema(db):
    db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        logged_at TEXT NOT NULL,
        stage TEXT NOT NULL CHECK(stage IN {STAGES}),
        reason_code TEXT NOT NULL CHECK(reason_code IN {CODES}),
        schema_version TEXT NOT NULL CHECK(schema_version='{SCHEMA}')
    )""")
    for action,name in (("UPDATE",TRIGGERS[0]),("DELETE",TRIGGERS[1])):
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
            BEFORE {action} ON {TABLE}
            BEGIN SELECT RAISE(ABORT, 'immutable_research_failure'); END""")


def _verify_schema(db):
    table=db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone()
    if not table:
        return False
    found={x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND tbl_name=?", (TABLE,))}
    if not set(TRIGGERS).issubset(found):
        raise ValueError("failure_ledger_triggers_missing")
    return True


def record(db_path, *, stage, exc, started_at, logged_at=None):
    """Record ONE observed failure; raises if it cannot be recorded.

    Caller MUST preserve original scanner exception even if this write fails.
    A collision with cTrader may make this write impossible: that is an
    unobserved (N/D) failure, never an alleged success or logged event.
    """
    code=reason(exc,stage=stage)
    start=witness._clock(started_at)
    end=witness._clock(logged_at)
    if end < start or end-start > timedelta(hours=1):
        raise ValueError("untrustworthy_failure_clock")
    uri=Path(db_path).expanduser().resolve().as_uri()+"?mode=rw"
    db=sqlite3.connect(uri,uri=True,timeout=0.2)
    try:
        db.execute("BEGIN IMMEDIATE")
        if _verify_schema(db):
            count=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
            if count>=MAX_ROWS:
                raise ValueError("failure_ledger_capacity_reached")
        else:
            _schema(db)
        inserted=db.execute(
            f"INSERT INTO {TABLE} "
            "(started_at,logged_at,stage,reason_code,schema_version) "
            "VALUES (?,?,?,?,?)",
            (witness._iso(start),witness._iso(end),stage,code,SCHEMA))
        db.commit()
        return {"status":"OBSERVED_FAILURE_RECORDED",
                "eventId":inserted.lastrowid,"reasonCode":code}
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def summary(db, *, as_of, days=1):
    """Explicit read-only, UTC-bounded aggregate, no inferred missing causes."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1<=days<=MAX_DAYS:
        raise ValueError("invalid_failure_window")
    now=witness._parse(as_of)
    start=now-timedelta(days=days)
    if not _verify_schema(db):
        return {
            "schema":SCHEMA,"status":"NO_FAILURE_LEDGER",
            "observedFailureCount":None,"observedReasons":None,
            "fullFailureTelemetryCertified":False,
            "unobservedAttemptCausesKnown":False,
            "calendarMissingSlotsAttributedToErrors":False,
            "brokerCalls":0,
        }
    rows=db.execute(
        f"SELECT started_at,logged_at,stage,reason_code,schema_version "
        f"FROM {TABLE} WHERE started_at>? AND started_at<=? "
        "ORDER BY started_at,id",
        (witness._iso(start),witness._iso(now))).fetchall()
    counts={}
    for begun,logged,stage,code,version in rows:
        if (stage not in STAGES or code not in CODES or version!=SCHEMA
                or witness._parse(logged)<witness._parse(begun)
                or witness._parse(logged)>now+timedelta(seconds=1)):
            raise ValueError("failure_ledger_integrity_invalid")
        counts[code]=counts.get(code,0)+1
    return {
        "schema":SCHEMA,"status":"OBSERVED_FAILURES_AUDITED",
        "observedFailureCount":len(rows),
        "observedReasons":dict(sorted(counts.items())),
        "fullFailureTelemetryCertified":False,
        "unobservedAttemptCausesKnown":False,
        "calendarMissingSlotsAttributedToErrors":False,
        "brokerCalls":0,
    }
