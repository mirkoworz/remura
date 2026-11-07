"""Track C3b-c -- LAB-ONLY denominator of all explicitly instrumented scan attempts.

A mock source-owner may append a scan attempt in its SAME core SQLite
transaction as a synthetic source update. This does NOT hook production
collectors or establish a complete real scan denominator. A separate
research process may stage a SHA witness after commit and then link it
conservatively to the attempt. Failure between those operations counts
as UNKNOWN, NOT a backfilled prospectively witnessed event.

No Myfxbook receipt or true provider FIRST-SEEN is collected. Retail may
only be EXCLUDED_UNKNOWN. No network, orders, notifications or PnL.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sqlite3

try:
    from scripts import track_c_c3b_durable_shadow as shadow
    from scripts import track_c_c3b_postcommit_handoff as post
except ImportError:
    import track_c_c3b_durable_shadow as shadow
    import track_c_c3b_postcommit_handoff as post

MODE = "OFFLINE_SYNTHETIC_C3BC_ATTEMPT_DENOMINATOR_ONLY"
CORE_TABLE = "c3bc_synthetic_core_attempts"
RESEARCH_TABLE = "c3bc_synthetic_research_links"
OUTCOMES = {"CANDIDATE", "EXCLUDED_SOURCE_MISSING",
            "EXCLUDED_STALE", "EXCLUDED_NOT_DUE", "EXCLUDED_UNKNOWN"}
MAX_ATTEMPTS = 4500
UNKNOWN = "UNKNOWN_NO_PROSPECTIVE_LINK"


def _files(core, research, mode):
    if mode != MODE:
        raise ValueError("explicit_offline_denominator_mode_required")
    return post._paths(core, research, mode=post.MODE)


def _core_db(db, core_path):
    if type(db) is not sqlite3.Connection or not db.in_transaction:
        raise ValueError("core_same_transaction_required")
    places = db.execute("PRAGMA database_list").fetchall()
    if (len(places) != 1 or places[0][1] != "main"
            or Path(places[0][2]).resolve() != core_path.resolve()):
        raise ValueError("core_transaction_must_use_synthetic_file")


def _ident(value):
    if type(value) is not str or len(value) != 64 or any(
            c not in "0123456789abcdef" for c in value):
        raise ValueError("synthetic_scan_id_sha256_required")


def prepare_core(core, research, *, mode=None):
    """Explicit OFFLINE schema migration, never run by deployed collector."""
    p,_ = _files(core,research,mode)
    if not p.is_file():
        raise ValueError("existing_synthetic_core_required")
    db = sqlite3.connect(str(p), timeout=0.025)
    try:
        with db:
            db.execute(f"""CREATE TABLE IF NOT EXISTS {CORE_TABLE}(
                attempt_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
                source TEXT NOT NULL CHECK(source IN ('cot','ctrader','retail')),
                scan_at TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN
                    ('CANDIDATE','EXCLUDED_SOURCE_MISSING','EXCLUDED_STALE',
                     'EXCLUDED_NOT_DUE','EXCLUDED_UNKNOWN'))
            )""")
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bc_core_no_update
                BEFORE UPDATE ON {CORE_TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_scan_denominator'); END""")
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bc_core_no_delete
                BEFORE DELETE ON {CORE_TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_scan_denominator'); END""")
    finally:
        db.close()


def prepare_research(core, research, *, mode=None):
    """Separate optional migration; never access or mutate source core."""
    _,p = _files(core,research,mode)
    db = sqlite3.connect(str(p),timeout=0.025)
    try:
        db.execute("BEGIN IMMEDIATE")
        shadow._schema(db)
        db.execute(f"""CREATE TABLE IF NOT EXISTS {RESEARCH_TABLE}(
            attempt_id TEXT PRIMARY KEY,
            shadow_item_id INTEGER NOT NULL UNIQUE,
            linked_at TEXT NOT NULL,
            source_sha256 TEXT NOT NULL
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bc_link_no_update
            BEFORE UPDATE ON {RESEARCH_TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_attempt_link'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bc_link_no_delete
            BEFORE DELETE ON {RESEARCH_TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_attempt_link'); END""")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def record_core_attempt(db, core, research, *, attempt_id, symbol, source,
                        scan_at, outcome, mode=None):
    """Caller MUST be inside an already-open simulated source transaction.

    This does not commit. The containing transaction either saves the source
    and the attempt together or rolls back both. No automatic migrations.
    """
    p,_ = _files(core,research,mode)
    _core_db(db,p)
    _ident(attempt_id)
    clock=shadow._utc(scan_at)
    if (type(symbol) is not str or symbol not in ("EURUSD","XAUUSD")
            or type(source) is not str
            or source not in ("cot","ctrader","retail")
            or type(outcome) is not str or outcome not in OUTCOMES
            or source == "retail" and outcome == "CANDIDATE"):
        raise ValueError("source_attempt_not_eligible_or_not_supported")
    # These are candidate classifications from an explicitly instrumented
    # synthetic scan, not provider/decision validation.
    n=db.execute(f"SELECT count(*) FROM {CORE_TABLE}").fetchone()[0]
    if n >= MAX_ATTEMPTS:
        raise ValueError("bounded_scan_denominator_capacity_reached")
    db.execute(
        f"INSERT INTO {CORE_TABLE}(attempt_id,symbol,source,scan_at,outcome) "
        "VALUES (?,?,?,?,?)",
        (attempt_id,symbol,source,scan_at,outcome))
    return "SYNTHETIC_CORE_ATTEMPT_SAME_TRANSACTION"


def link_after_stage(core, research, *, attempt_id, symbol, source,
                     read_at, mode=None):
    """Explicit research-side attempt link; no retroactive missing replay.

    The EXISTING postcommit dispatcher stages a SHA digest. Link insertion
    is in a second research transaction. A crash between stage and link is
    conservatively UNKNOWN in audit, not counted as a delivered observation.
    """
    p,q=_files(core,research,mode)
    _ident(attempt_id)
    if type(source) is not str or source not in ("cot","ctrader"):
        return UNKNOWN
    try:
        # Require preexisting committed CORE attempt; no historical scanning
        # of uninstrumented observations and no guessing omitted scan IDs.
        ro=sqlite3.connect("file:"+str(p)+"?mode=ro",uri=True,timeout=0.025)
        try:
            ro.execute("PRAGMA query_only=ON")
            attempt=ro.execute(
                f"SELECT symbol,source,scan_at,outcome FROM {CORE_TABLE} "
                "WHERE attempt_id=?", (attempt_id,)).fetchone()
        finally:
            ro.close()
        if (attempt is None or attempt[0]!=symbol or attempt[1]!=source
                or attempt[3]!="CANDIDATE"):
            return UNKNOWN
        scan=shadow._utc(attempt[2])
        now=shadow._utc(read_at)
        if not timedelta(0)<=now-scan<=timedelta(minutes=1):
            return UNKNOWN
        if post.dispatch(p,q,symbol=symbol,source=source,
                         read_at=read_at,enabled=True,
                         mode=post.MODE)!=post.STAGED:
            return UNKNOWN
        # A separate shadow-side link requires an exact unique synthetic
        # source digest; do not declare success based on mere row count.
        db=sqlite3.connect(str(q),timeout=0.025)
        try:
            db.execute("BEGIN IMMEDIATE")
            shadow._schema(db)
            row=db.execute(
                f"SELECT id,sha256 FROM {shadow.TABLE} WHERE symbol=? "
                "AND source=? AND source_seen=? AND state='pending'",
                (symbol,source,read_at)).fetchall()
            if len(row)!=1:
                db.rollback()
                return UNKNOWN
            db.execute(
                f"INSERT INTO {RESEARCH_TABLE}(attempt_id,shadow_item_id,"
                "linked_at,source_sha256) VALUES (?,?,?,?)",
                (attempt_id,row[0][0],read_at,row[0][1]))
            db.commit()
            return "SYNTHETIC_ATTEMPT_STAGED_AND_LINKED_NOT_VERIFIED"
        except (sqlite3.Error,ValueError):
            db.rollback()
            return UNKNOWN
        finally:
            db.close()
    except (sqlite3.Error,ValueError,TypeError,OSError):
        return UNKNOWN


def audit(core, research, *, mode=None):
    """Read-only denominator; every unlinked CANDIDATE remains missing.

    Counts only explicitly instrumented LAB scans, not all scans of LIVE.
    A linked staged row is NOT a verified scientific receipt, profit, or
    provider-authenticated source. No mutations/replay/backfill.
    """
    p,q=_files(core,research,mode)
    if not p.is_file() or not q.is_file():
        raise ValueError("explicit_two_synthetic_databases_required")
    source=sqlite3.connect("file:"+str(p)+"?mode=ro",uri=True,timeout=0.025)
    queue=sqlite3.connect("file:"+str(q)+"?mode=ro",uri=True,timeout=0.025)
    try:
        for db in (source,queue):
            db.execute("PRAGMA query_only=ON")
        shadow._schema(queue)
        attempts=source.execute(
            f"SELECT attempt_id,symbol,source,scan_at,outcome FROM "
            f"{CORE_TABLE} ORDER BY attempt_id").fetchall()
        links=queue.execute(
            f"SELECT attempt_id,shadow_item_id,linked_at,source_sha256 "
            f"FROM {RESEARCH_TABLE}").fetchall()
        linked={x[0]:x for x in links}
        if len(linked)!=len(links):
            raise ValueError("duplicate_research_link_identity")
        candidate=exclusion=staged=missing=invalid=0
        seen=set()
        for ident,sym,src,clock,outcome in attempts:
            _ident(ident)
            seen.add(ident)
            shadow._utc(clock)
            if outcome!="CANDIDATE":
                exclusion+=1
                if ident in linked:
                    invalid+=1
                continue
            candidate+=1
            entry=linked.get(ident)
            if entry is None:
                missing+=1
                continue
            row=queue.execute(
                f"SELECT symbol,source,source_seen,sha256,state "
                f"FROM {shadow.TABLE} WHERE id=?", (entry[1],)
            ).fetchone()
            if (row is None or row[0]!=sym or row[1]!=src
                    or row[3]!=entry[3] or row[2]!=entry[2]
                    or shadow._utc(row[2])-shadow._utc(clock)
                       not in (timedelta(seconds=i) for i in range(61))):
                missing+=1
                invalid+=1
            elif row[4] in ("pending","leased","synthetic_ack"):
                staged+=1
            else:
                missing+=1
        unknown_links=len(set(linked)-seen)
        invalid+=unknown_links
        # Zero success/profit claims: staged is transport-only metadata.
        return {
            "status":"OFFLINE_SYNTHETIC_DENOMINATOR_NOT_LIVE",
            "instrumentedAttemptCount":len(attempts),
            "candidateCount":candidate,
            "excludedCount":exclusion,
            "stagedResearchMetadataCount":staged,
            "missingOrUnknownCount":missing,
            "integrityBlockerCount":invalid,
            "orphanResearchLinks":unknown_links,
            "denominatorIsCompleteForLiveScans":False,
            "realMarketReceiptVerified":False,
            "retailOriginalParentReadLinked":False,
            "actualOutOfSampleObservations":False,
            "researchSuccessesProven":0,
            "realEdgeEstablished":False,
            "crossDatabaseCommitAtomicity":False,
            "liveEnabled":False,
            "newApiCalls":0,
            "notificationsEnabled":False,
        }
    finally:
        source.close()
        queue.close()
