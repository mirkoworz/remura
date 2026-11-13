"""Track C3b-c(b) -- independent pre-registered schedule/gap ledger, LAB ONLY.

An isolated, explicit TEST planner registers EXPECTED future scan slots in
a third SQLite file before their nominal UTC due times. If a simulated
source process crashes BEFORE writing its core attempt, the absent attempt
is counted as a schedule GAP_UNKNOWN rather than silently disappearing.

This is neither a live scheduler nor proof every real scan was planned.
Times are UNTRUSTED caller-supplied lab clocks, not server-attested times.
An expected slot says 'work due', NEVER 'data received' or 'signal observed'.
No provider calls, automatic replay, backfill, trade, notification or LIVE
integration. All operational gates remain NO-GO.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sqlite3
import tempfile

try:
    from scripts import track_c_c3b_durable_shadow as shadow
    from scripts import track_c_c3bc_attempt_denominator as den
    from scripts import track_c_c3b_postcommit_handoff as post
except ImportError:
    import track_c_c3b_durable_shadow as shadow
    import track_c_c3bc_attempt_denominator as den
    import track_c_c3b_postcommit_handoff as post

MODE = "OFFLINE_SYNTHETIC_PRE_REGISTERED_SCAN_SCHEDULE_ONLY"
FILE = "track-c3bc-synthetic-schedule.sqlite3"
TABLE = "c3bc_synthetic_expected_slots"
MAX_SLOTS = 4500
MIN_LEAD = timedelta(seconds=1)
MAX_LEAD = timedelta(hours=48)
GRACE = timedelta(seconds=30)


def _paths(core, research, schedule, *, mode):
    if mode != MODE:
        raise ValueError("explicit_offline_schedule_mode_required")
    p, q = post._paths(core, research, mode=post.MODE)
    if not isinstance(schedule,(str, Path)):
        raise ValueError("explicit_synthetic_schedule_file_required")
    s = Path(schedule).absolute()
    if (s.name != FILE or s.is_symlink() or s.parent.is_symlink()
            or s.parent.resolve() != q.parent.resolve()
            or s.resolve().parent != q.parent.resolve()
            or s == p or s == q):
        raise ValueError("schedule_must_be_third_isolated_temp_sqlite")
    return p, q, s


def _open_ro(path):
    # URI mode=ro guarantees no silent creation, migration or source writes.
    from urllib.parse import quote
    db = sqlite3.connect("file:"+quote(str(path),safe="/")+"?mode=ro",
                         uri=True, timeout=.025)
    db.execute("PRAGMA query_only=ON")
    return db


def _schema(db):
    objects = dict(db.execute(
        "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?)",
        (TABLE,"c3bc_schedule_no_update","c3bc_schedule_no_delete")
    ).fetchall())
    if (objects.get(TABLE)!="table" or
            objects.get("c3bc_schedule_no_update")!="trigger" or
            objects.get("c3bc_schedule_no_delete")!="trigger"):
        raise ValueError("explicit_schedule_schema_not_prepared")


def prepare(core, research, schedule, *, mode=None):
    """EXPLICIT lab migration only, not called by any producer/collector."""
    p,q,s = _paths(core,research,schedule,mode=mode)
    if not p.is_file() or not q.is_file():
        raise ValueError("separate_preexisting_synthetic_sources_required")
    if s.exists():
        raise ValueError("refuse_overwrite_existing_schedule")
    db = sqlite3.connect(str(s),timeout=.025)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=25")
        with db:
            db.execute(f"""CREATE TABLE {TABLE}(
                slot_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
                source TEXT NOT NULL CHECK(source IN ('cot','ctrader','retail')),
                registered_at TEXT NOT NULL,
                due_at TEXT NOT NULL,
                UNIQUE(symbol,source,due_at)
            )""")
            db.execute(f"""CREATE TRIGGER c3bc_schedule_no_update
                BEFORE UPDATE ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_expected_slot'); END""")
            db.execute(f"""CREATE TRIGGER c3bc_schedule_no_delete
                BEFORE DELETE ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_expected_slot'); END""")
    finally:
        db.close()
    return "OFFLINE_SYNTHETIC_EXPECTED_SLOT_DB_ONLY"


def register(core, research, schedule, *, slot_id, symbol, source,
             registered_at, due_at, mode=None):
    """Pre-register a *future* expected slot, not a completed market event.

    Caller clock is not provider-signed: test proves timing constraints in
    code, NOT that caller sampled a genuine time in the deployed scheduler.
    No automatic retroactive registration is permitted in this contract.
    """
    _,_,s = _paths(core,research,schedule,mode=mode)
    den._ident(slot_id)
    start=shadow._utc(registered_at)
    due=shadow._utc(due_at)
    if not MIN_LEAD<=due-start<=MAX_LEAD:
        raise ValueError("must_register_slot_before_it_is_due")
    if (type(symbol) is not str or symbol not in ("EURUSD","XAUUSD")
            or type(source) is not str
            or source not in ("cot","ctrader","retail")):
        raise ValueError("only_pilot_market_source_slots_allowed")
    if not s.is_file():
        raise ValueError("explicit_schedule_migration_required")
    db=sqlite3.connect(str(s),timeout=.025)
    try:
        db.execute("BEGIN IMMEDIATE")
        _schema(db)
        if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_SLOTS:
            raise ValueError("bounded_synthetic_schedule_capacity_exceeded")
        db.execute(
            f"INSERT INTO {TABLE}(slot_id,symbol,source,registered_at,due_at)"
            " VALUES (?,?,?,?,?)",
            (slot_id,symbol,source,registered_at,due_at))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return "EXPECTED_SYNTHETIC_SLOT_REGISTERED_NOT_OBSERVED"


def audit(core, research, schedule, *, as_of, mode=None):
    """Cross-check known future plans against the existing core denominator.

    Pure read; never auto-backfills an absent attempt. Late/unknown scans
    never become successfully witnessed data. Both registered slots and
    actually committed attempts are reconciled by exact immutable IDs.
    """
    p,q,s = _paths(core,research,schedule,mode=mode)
    now=shadow._utc(as_of)
    if not all(x.is_file() for x in (p,q,s)):
        raise ValueError("explicit_three_synthetic_databases_required")
    plans=_open_ro(s)
    source=_open_ro(p)
    try:
        _schema(plans)
        rows=plans.execute(
            f"SELECT slot_id,symbol,source,registered_at,due_at "
            f"FROM {TABLE} ORDER BY slot_id").fetchall()
        attempts=source.execute(
            f"SELECT attempt_id,symbol,source,scan_at,outcome "
            f"FROM {den.CORE_TABLE}").fetchall()
        ids={r[0] for r in rows}
        if len(ids)!=len(rows):
            raise ValueError("schedule_duplicate_slot_id_detected")
        indexed={r[0]:r for r in attempts}
        if len(indexed)!=len(attempts):
            raise ValueError("source_duplicate_attempt_id_detected")
        # Reuse the existing read-only attempt receipt check; keep its
        # limitations (transport-only, no provider-authenticated FIRST-SEEN).
        context=den.audit(p,q,mode=den.MODE)
        future=within=due=gap=attempted=excluded=candidates=late=invalid=0
        for ident,symbol,kind,registered_at,due_at in rows:
            den._ident(ident)
            reg=shadow._utc(registered_at)
            scheduled=shadow._utc(due_at)
            if not MIN_LEAD<=scheduled-reg<=MAX_LEAD:
                invalid+=1
                continue
            if scheduled>now:
                future+=1
                # An attempt claiming to belong to an as-yet-future
                # expected slot is an integrity anomaly, not a success.
                if ident in indexed:
                    invalid+=1
                continue
            if now<scheduled+GRACE:
                within+=1
                # Grace window is not a missing count, but future-dated
                # or pre-schedule attempts must never be accepted silently.
                if ident in indexed:
                    actual=shadow._utc(indexed[ident][3])
                    if not scheduled<=actual<=now:
                        invalid+=1
                continue
            due+=1
            attempt=indexed.get(ident)
            if attempt is None:
                gap+=1
                continue
            _,got_symbol,got_kind,scan_at,outcome=attempt
            moment=shadow._utc(scan_at)
            if (got_symbol!=symbol or got_kind!=kind
                    or not scheduled<=moment<=scheduled+GRACE
                    or moment>now):
                invalid+=1
                late+=1
                continue
            attempted+=1
            if outcome=="CANDIDATE":
                candidates+=1
            else:
                excluded+=1
        orphans=len(set(indexed)-ids)
        return {
            "status":"OFFLINE_SYNTHETIC_PREPLANNED_GAP_AUDIT_NOT_LIVE",
            "registeredExpectedSlots":len(rows),
            "futureNotYetDue":future,
            "dueWithinGrace":within,
            "settledDueSlots":due,
            "missingBeforeCoreAttempt":gap,
            "startedInWindow":attempted,
            "startedCandidates":candidates,
            "startedExcluded":excluded,
            "lateOrMisassignedAttempts":late,
            "unplannedCoreAttempts":orphans,
            "integrityBlockers":invalid+orphans+context["integrityBlockerCount"],
            "postCommitCandidateMissingOrUnknown":
                context["missingOrUnknownCount"],
            "researchMetadataStagedNotEvidence":
                context["stagedResearchMetadataCount"],
            "retailParentReadVerified":False,
            "everyLiveScanPreplanned":False,
            "clockIsIndependentOrSigned":False,
            "realProspectiveObservations":False,
            "coreVsScheduleCrossDbAtomic":False,
            "completeRealDenominator":False,
            "tradingEdgeEstablished":False,
            "liveEnabled":False,
            "newProviderCalls":0,
            "notificationsEnabled":False,
        }
    finally:
        source.close()
        plans.close()
