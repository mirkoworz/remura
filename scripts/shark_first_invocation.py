"""Track B: witness the FIRST actual entry to the opt-in periodic scanner.

Not the time somebody changed a feature flag: configuration changes outside
this process are NOT observable. The first periodic invocation is witnessed
on the VPS host clock and committed BEFORE the full scan attempts any OHLC
or COT read. A failed scan retains this earlier, immutable evidence.

Does not schedule scans, use a broker, backfill, export secrets, or run on the
legacy v1.62 default path. This is a local append-only SQLite witness, NOT a
trusted external timestamp / proof that the clock was synchronized.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact

TABLE = "research_first_periodic_invocation"
SCHEMA = "remura-research-first-periodic-invocation-v1"
KIND = "first_enabled_full_periodic_entry"
TRIGGER_UPDATE = "research_first_periodic_no_update"
TRIGGER_DELETE = "research_first_periodic_no_delete"


def read(db, *, at=None):
    """Read witness within caller's snapshot, or None if never initialized.

    A present table with missing/altered witness fails closed rather than
    treating the current scan as the original start of research.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    exists = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone()
    if not exists:
        return None
    triggers = {x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND tbl_name=?", (TABLE,))}
    if not {TRIGGER_UPDATE,TRIGGER_DELETE}.issubset(triggers):
        raise ValueError("activation_witness_triggers_missing")
    rows=db.execute(
        f"SELECT id,kind,observed_at,schema_version FROM {TABLE}").fetchall()
    if len(rows)!=1:
        raise ValueError("activation_witness_record_missing_or_duplicated")
    id_,kind,recorded,version=rows[0]
    if id_!=1 or kind!=KIND or version!=SCHEMA:
        raise ValueError("activation_witness_identity_invalid")
    captured=witness._parse(recorded)
    if witness._iso(captured)!=recorded:
        raise ValueError("activation_witness_clock_not_canonical")
    if at is not None and captured>witness._clock(at)+timedelta(seconds=1):
        raise ValueError("activation_witness_in_future")
    return recorded


def first_invocation(db_path, *, clock=None):
    """Record first opt-in scanner entry in its OWN bounded atomic transaction.

    Uses mode=rw so a typo cannot create an unrelated database, and a short
    SQLite busy timeout to avoid holding the live collector hostage. If the
    record cannot be committed/verified, the caller MUST NOT start research.
    The first observed time is never overwritten after restarts.
    """
    now=witness._clock(clock)
    # Exact future caller is the periodic server flag gate, not an HTTP
    # endpoint or a CLI. Test clock overrides are synthetic-only.
    uri=Path(db_path).expanduser().resolve().as_uri()+"?mode=rw"
    db=sqlite3.connect(uri, uri=True, timeout=0.5)
    try:
        old=read(db,at=now)
        if old is not None:
            return {"status":"EXISTING_FIRST_INVOCATION","observedAt":old}
        db.execute("BEGIN IMMEDIATE")
        # Never mislabel the date if a legacy tool inserted research batches
        # without this witness before the server was first enabled.
        exists=db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (compact.TABLE,)).fetchone()
        if exists and db.execute(
            f"SELECT 1 FROM {compact.TABLE} LIMIT 1").fetchone():
            raise ValueError("research_batches_precede_activation_witness")
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY CHECK(id=1),
            kind TEXT NOT NULL CHECK(kind='{KIND}'),
            observed_at TEXT NOT NULL,
            schema_version TEXT NOT NULL CHECK(schema_version='{SCHEMA}')
        )""")
        for action,name in (("UPDATE",TRIGGER_UPDATE),
                            ("DELETE",TRIGGER_DELETE)):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
                BEFORE {action} ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_research_activation'); END""")
        db.execute(
            f"INSERT OR IGNORE INTO {TABLE} "
            "(id,kind,observed_at,schema_version) VALUES (1,?,?,?)",
            (KIND,witness._iso(now),SCHEMA))
        recorded=read(db,at=now)
        db.commit()
        return {"status":"FIRST_INVOCATION_WITNESSED","observedAt":recorded}
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
