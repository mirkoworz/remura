"""Track C3b-b: OFFLINE post-commit READ witness -> separate SQLite WAL queue.

Designed to rehearse a standalone research process reading a COMPLETED
synthetic core SQLite transaction via an SQLite read-only connection, then
staging metadata in the already isolated C3b WAL shadow. NEVER calls a
collector, provider or the production server and NEVER modifies the core.

A read after commit proves only that bytes existed at the LOCAL READ. It
does not reconstruct original HTTP receipt time, cTrader parent-read or an
actual core COMMIT clock, and does not guarantee receipt if the dispatcher
crashes between core commit and its own stage(). No cross-DB atomicity.
The queue field coreCommittedAtUtc is a synthetic caller time set equal to
read-time, NOT an authenticated core commit time. NO production enablement.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

try:
    from scripts import track_c_c3b_durable_shadow as shadow
except ImportError:
    import track_c_c3b_durable_shadow as shadow

MODE = "OFFLINE_SYNTHETIC_READ_AFTER_CORE_COMMIT_ONLY"
CORE_FILE = "track-c3b-synthetic-core.sqlite3"
DATASETS = {"EURUSD": ("tff","099741"), "XAUUSD": ("disagg","088691")}
STAGED = "SYNTHETIC_POSTCOMMIT_READ_STAGED_NOT_FIRST_SEEN"
UNKNOWN = shadow.UNKNOWN


def _paths(core, research, *, mode):
    if mode != MODE:
        raise ValueError("explicit_offline_postcommit_mode_required")
    # Shadow validates the fixed temp directory/name and rejects symlinks.
    research_path = shadow._path(research, shadow.MODE)
    if not isinstance(core, (str,Path)):
        raise ValueError("synthetic_core_path_required")
    core_path = Path(core).absolute()
    if (core_path.is_symlink() or core_path.name != CORE_FILE
            or core_path.parent.resolve() != research_path.parent.resolve()
            or core_path.resolve().parent != research_path.parent
            or core_path == research_path):
        raise ValueError("must_use_separate_temp_synthetic_core")
    return core_path,research_path


def _source(core, symbol, source, observed_at):
    if type(symbol) is not str or symbol not in DATASETS:
        raise ValueError("only_eurusd_xauusd_pilot_supported")
    if type(source) is not str or source not in ("cot","ctrader"):
        raise ValueError("offline_cot_or_ctrader_only_retail_still_unsupported")
    if not core.is_file():
        raise ValueError("original_synthetic_core_missing")
    # URI read-only: never create/initialize/migrate source DB, journal
    # or connect to a production pathname.
    db = sqlite3.connect("file:"+quote(str(core),safe="/")+"?mode=ro",
                         uri=True,timeout=0.025)
    try:
        db.execute("PRAGMA query_only=ON")
        if len(db.execute("PRAGMA database_list").fetchall()) != 1:
            raise ValueError("attached_source_database_forbidden")
        if source == "cot":
            dataset,code = DATASETS[symbol]
            rows=db.execute(
                "SELECT dataset,code,report_date,oi,first_long,first_short,"
                "second_long,second_short FROM cot_reports "
                "WHERE dataset=? AND code=? ORDER BY report_date",
                (dataset,code)).fetchall()
            if len(rows)!=2:
                raise ValueError("exact_two_pilot_cot_weeks_missing")
            dates=[datetime.strptime(r[2],"%Y-%m-%d").date() for r in rows]
            if ((dates[1]-dates[0]).days!=7
                    or dates[-1]>observed_at.date()
                    or (observed_at.date()-dates[1]).days>22):
                raise ValueError("invalid_cot_asof_weeks")
            if any(type(v) not in (float,int) for r in rows for v in r[3:]):
                raise ValueError("invalid_cot_source_numeric")
            # Sha binds both weeks, official contract code and values at
            # post-commit read. May change after revision (then recheck fails).
            payload=["cot",symbol,rows]
        else:
            row=db.execute(
                "SELECT source,updated_at,payload FROM prices WHERE symbol=?",
                (symbol,)).fetchone()
            if row is None or row[0]!="ctrader" or not row[2]:
                raise ValueError("actual_synthetic_price_missing")
            obj=json.loads(row[2])
            if (type(obj) is not dict or obj.get("symbol")!=symbol
                    or obj.get("provider")!="ctrader"
                    or obj.get("lastComplete")!=row[1]):
                raise ValueError("original_ctrader_stored_document_invalid")
            # Synthetic fixture must have all three derived timeframes:
            frames=obj.get("timeframes")
            if (type(frames) is not dict or
                    any(type(frames.get(k)) is not list or
                        not frames.get(k) for k in ("M15","H1","H4"))):
                raise ValueError("original_ctrader_frames_missing")
            from price_feed import parse_time
            last=parse_time(row[1])
            closed_at=last+timedelta(minutes=15)
            # A later post-commit reader must never turn an old last
            # close into a fresh FIRST-SEEN price observation.
            if (not timedelta(0)<=observed_at-closed_at
                    <=timedelta(minutes=3)
                    or frames["M15"][-1].get("t")!=row[1]):
                raise ValueError("stale_or_future_original_price_snapshot")
            payload=["ctrader",symbol,row[0],row[1],obj]
        canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True,allow_nan=False)
        return hashlib.sha256(canonical.encode("ascii")).hexdigest()
    finally:
        db.close()


def dispatch(core, research, *, symbol, source, read_at, enabled=False,
             mode=None):
    """Research process only. Caller guarantees core transaction has ended.

    A rejected/locked/missing research DB may drop science, NEVER corrupt
    core. The source SHA is computed from a committed read-only snapshot
    rather than blindly accepting a caller-supplied digest.
    """
    core_path,research_path=_paths(core,research,mode=mode)
    if type(enabled) is not bool or not enabled:
        return UNKNOWN
    try:
        timestamp=shadow._utc(read_at)
        digest=_source(core_path,symbol,source,timestamp)
        payload={"symbol":symbol,"source":source,"seenAtUtc":read_at,
                 "coreCommittedAtUtc":read_at,"originalSha256":digest}
        result=shadow.stage(research_path,payload,at=read_at,enabled=True,
                            mode=shadow.MODE)
        return STAGED if result==shadow.STAGED else UNKNOWN
    except (sqlite3.Error,ValueError,TypeError,OSError,OverflowError,
            json.JSONDecodeError):
        return UNKNOWN


def check_lease_source(core,research, *, job, checked_at, enabled=False,
                       mode=None):
    """Separate worker verifies claimed SHA STILL matches source bytes.

    Return a boolean for shadow.finish synthetic ACK; never infer profit,
    actual FIRST-SEEN or delivery completeness from this read.
    """
    core_path,_=_paths(core,research,mode=mode)
    if type(enabled) is not bool or not enabled:
        return False
    if (type(job) is not dict or
            set(job)!={"id","symbol","source","seenAtUtc",
                       "originalSha256","leaseToken"}):
        return False
    try:
        stamp=shadow._utc(checked_at)
        witnessed=shadow._utc(job["seenAtUtc"])
        if (stamp<witnessed or stamp-witnessed>shadow.MAX_AGE
                or type(job["originalSha256"]) is not str):
            return False
        current=_source(core_path,job["symbol"],job["source"],stamp)
        return current==job["originalSha256"]
    except (sqlite3.Error,ValueError,TypeError,OSError,OverflowError,
            json.JSONDecodeError):
        return False
