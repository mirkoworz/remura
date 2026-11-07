"""Track C3b-c(c) -- independently reconstructible lab schedule plan, NOT LIVE.

One explicit frozen synthetic cadence plan is committed BEFORE future due
times in the third temporary SQLite file. The read-only auditor derives
the expected scan IDs directly from the immutable plan, even if a process
crashed before registering ANY individual slot.

These are SYNTHETIC POLLING CHECKS, not actual provider publication times,
trading sessions, official calendar or verified scheduler executions.
No live timers, cron, provider requests, backfill, credentials or trades.
The plan's own creation cannot be inferred if it never committed; genuine
completeness needs independent production schedule/timestamp verification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3

try:
    from scripts import track_c_c3bc_expected_slots as calendar
    from scripts import track_c_c3b_durable_shadow as shadow
    from scripts import track_c_c3bc_attempt_denominator as denominator
except ImportError:
    import track_c_c3bc_expected_slots as calendar
    import track_c_c3b_durable_shadow as shadow
    import track_c_c3bc_attempt_denominator as denominator

MODE = "OFFLINE_SYNTHETIC_FROZEN_SCAN_POLICY_PLAN_ONLY"
TABLE = "c3bcc_synthetic_frozen_plan"
FINGERPRINT = "afaf963f3b66d85ca91557f99a97ec8fce14a849b548e6c4db96fc3b3c6d4206"
PLAN_VERSION = "lab-only-v1"
MARKETS = ("EURUSD","XAUUSD")
# Explicitly SYNTHETIC poll cadences, never official publication promises.
SOURCES = (
    ("cot","weekly-monday-12utc-poll-not-publication",604800),
    ("ctrader","15m-synthetic-poll",900),
    ("retail","30m-synthetic-poll",1800),
)
EXPECTED_SAMPLE_WINDOW = timedelta(hours=1)
MAX_EXPECTED = 24


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def _frozen():
    policy={"policy":PLAN_VERSION,"sources":[list(x) for x in SOURCES],
            "markets":list(MARKETS)}
    if _hash(policy) != FINGERPRINT:
        raise ValueError("frozen_synthetic_policy_contract_changed")
    return policy


def _paths(core,research,schedule,mode):
    if mode!=MODE:
        raise ValueError("explicit_synthetic_frozen_policy_mode_required")
    _frozen()
    return calendar._paths(core,research,schedule,mode=calendar.MODE)


def _plan_id(created,start,end):
    return _hash({"schema":"track-c-frozen-plan-v1","created":created,
                  "windowStart":start,"windowEnd":end,
                  "protocolSha256":FINGERPRINT})


def _expand(plan_id,start,end):
    """One hour synthetic Monday: 2 COT checks + 8 price + 4 retail."""
    base=shadow._utc(start)
    finish=shadow._utc(end)
    if (base.weekday()!=0 or base.hour!=12 or base.minute or base.second
            or finish-base!=EXPECTED_SAMPLE_WINDOW
            or base<datetime(2026,11,9,tzinfo=timezone.utc)):
        raise ValueError("fixed_monday_utc_synthetic_window_only")
    out=[]
    for source, rule, seconds in SOURCES:
        # COT here is an *attempt to check availability*, not a CFTC
        # publication event; no business/holiday calendar implied.
        for market in MARKETS:
            t=base
            while t<finish:
                due=shadow._iso(t)
                ident=_hash({"plan":plan_id,"symbol":market,
                             "source":source,"dueAt":due})
                out.append((ident,market,source,due))
                t+=timedelta(seconds=seconds)
    if not 1<=len(out)<=MAX_EXPECTED:
        raise ValueError("synthetic_plan_capacity_exceeded")
    return tuple(sorted(out))


def prepare(core,research,schedule,*,mode=None):
    """Separate explicit schema migration; does NOT create a plan."""
    _,_,s=_paths(core,research,schedule,mode)
    if not s.is_file():
        raise ValueError("preregistered_schedule_schema_required")
    db=sqlite3.connect(str(s),timeout=.025)
    try:
        db.execute("BEGIN IMMEDIATE")
        calendar._schema(db)
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            plan_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            window_start TEXT NOT NULL,
            window_end TEXT NOT NULL,
            frozen_policy_sha256 TEXT NOT NULL,
            expected_slots INTEGER NOT NULL,
            CHECK(expected_slots BETWEEN 1 AND 24)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bcc_plan_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_frozen_plan'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS c3bcc_plan_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_frozen_plan'); END""")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return "SYNTHETIC_POLICY_SCHEMA_ONLY_NO_PLAN_YET"


def commit_plan(core,research,schedule,*,created_at,start_at,end_at,mode=None):
    """Plan must be durably committed before its first hypothetical scan."""
    _,_,s=_paths(core,research,schedule,mode)
    created=shadow._utc(created_at)
    start=shadow._utc(start_at)
    shadow._utc(end_at)
    if not calendar.MIN_LEAD<=start-created<=calendar.MAX_LEAD:
        raise ValueError("plan_would_be_created_too_late_or_too_early")
    plan_id=_plan_id(created_at,start_at,end_at)
    slots=_expand(plan_id,start_at,end_at)
    db=sqlite3.connect(str(s),timeout=.025)
    try:
        db.execute("BEGIN IMMEDIATE")
        _schema(db)
        if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]:
            raise ValueError("only_one_explicit_plan_per_test_db")
        db.execute(
            f"INSERT INTO {TABLE}(plan_id,created_at,window_start,"
            "window_end,frozen_policy_sha256,expected_slots) "
            "VALUES (?,?,?,?,?,?)",
            (plan_id,created_at,start_at,end_at,FINGERPRINT,len(slots)))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return plan_id


def _schema(db):
    names=dict(db.execute(
        "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?)",
        (TABLE,"c3bcc_plan_no_update","c3bcc_plan_no_delete")
    ).fetchall())
    if (names.get(TABLE)!="table"
            or names.get("c3bcc_plan_no_update")!="trigger"
            or names.get("c3bcc_plan_no_delete")!="trigger"):
        raise ValueError("explicit_frozen_policy_schema_required")


def _read_plan(db):
    _schema(db)
    rows=db.execute(
        f"SELECT plan_id,created_at,window_start,window_end,"
        f"frozen_policy_sha256,expected_slots FROM {TABLE}"
    ).fetchall()
    if len(rows)!=1:
        raise ValueError("exact_one_committed_plan_required")
    ident,created,start,end,digest,count=rows[0]
    if (digest!=FINGERPRINT or
            ident!=_plan_id(created,start,end) or
            not calendar.MIN_LEAD<=shadow._utc(start)-shadow._utc(created)
                   <=calendar.MAX_LEAD):
        raise ValueError("plan_identity_or_policy_mismatch")
    expanded=_expand(ident,start,end)
    if len(expanded)!=count:
        raise ValueError("planned_expected_count_mismatch")
    return ident,expanded


def register_planned(core,research,schedule,*,slot_id,registered_at,mode=None):
    """Explicit lab scan-slot registration; never a background scheduler.

    If omitted or crashed BEFORE registration, audit STILL reconstructs
    the expectation from the independently stored root plan.
    """
    p,q,s=_paths(core,research,schedule,mode)
    denominator._ident(slot_id)
    db=calendar._open_ro(s)
    try:
        _,expected=_read_plan(db)
    finally:
        db.close()
    matched=[x for x in expected if x[0]==slot_id]
    if len(matched)!=1:
        raise ValueError("slot_not_derived_from_frozen_plan")
    ident,sym,src,due=matched[0]
    return calendar.register(p,q,s,slot_id=ident,symbol=sym,source=src,
                             registered_at=registered_at,due_at=due,
                             mode=calendar.MODE)


def expected_ids(core,research,schedule,*,mode=None):
    """Deterministic fixture helper, no clock or side effects."""
    _,_,s=_paths(core,research,schedule,mode)
    ro=calendar._open_ro(s)
    try:
        _,items=_read_plan(ro)
        return items
    finally:
        ro.close()


def audit(core,research,schedule,*,as_of,mode=None):
    """Independent reconstruction, all missing registrations are gaps.

    Do not replace UNKNOWN with 'no signal'. Does not repair missing
    slots and does not imply any source reported market data.
    """
    p,q,s=_paths(core,research,schedule,mode)
    now=shadow._utc(as_of)
    if not all(x.is_file() for x in (p,q,s)):
        raise ValueError("explicit_three_lab_databases_required")
    schedule_ro=calendar._open_ro(s)
    try:
        _,items=_read_plan(schedule_ro)
        registered=schedule_ro.execute(
            f"SELECT slot_id,symbol,source,due_at FROM {calendar.TABLE}"
        ).fetchall()
    finally:
        schedule_ro.close()
    lookup={x[0]:(x[1],x[2],x[3]) for x in registered}
    if len(lookup)!=len(registered):
        raise ValueError("duplicate_registered_identity")
    found={x[0] for x in items}
    unexpected=len(set(lookup)-found)
    due_missing=notyet=grace=due_total=0
    wrong=0
    for ident,sym,src,due in items:
        if ident in lookup and lookup[ident]!=(sym,src,due):
            wrong+=1
        planned=shadow._utc(due)
        if planned>now:
            notyet+=1
        elif now<planned+calendar.GRACE:
            grace+=1
        else:
            due_total+=1
            if ident not in lookup:
                due_missing+=1
    # Existing audit checks any registered slot against committed source
    # attempts and stage receipts; it has no authority to infer unregistered
    # scheduled slots on its own.
    old=calendar.audit(p,q,s,as_of=as_of,mode=calendar.MODE)
    if old["registeredExpectedSlots"]!=len(registered):
        raise ValueError("inconsistent_schedule_snapshot")
    gaps=due_missing+old["missingBeforeCoreAttempt"]
    return {
        "status":"OFFLINE_SYNTHETIC_RECONSTRUCTED_SCHEDULE_NOT_LIVE",
        "protocolSha256":FINGERPRINT,
        "planExpectedSlots":len(items),
        "registeredSlots":len(registered),
        "planFutureNotDue":notyet,
        "planWithinGrace":grace,
        "planSettledDue":due_total,
        "missingSlotRegistrations":due_missing,
        "registeredButNoCoreAttempt":old["missingBeforeCoreAttempt"],
        "totalKnownPreAttemptGaps":gaps,
        "postCommitResearchUnknown":old["postCommitCandidateMissingOrUnknown"],
        "unplannedAttempts":old["unplannedCoreAttempts"],
        "unexpectedRegisteredSlots":unexpected,
        "integrityBlockers":wrong+unexpected+old["integrityBlockers"],
        "planCommittedBeforeDue":True,
        "planClockIndependentlyAuthenticated":False,
        "realMarketSessionScheduleVerified":False,
        "officialProviderPublicationVerified":False,
        "liveSchedulerEmissionVerified":False,
        "realRetailFirstSeenVerified":False,
        "completeLiveDenominatorProven":False,
        "realTradingEdgeEstablished":False,
        "actualProspectiveData":False,
        "liveEnabled":False,
        "newProviderApiCalls":0,
    }
