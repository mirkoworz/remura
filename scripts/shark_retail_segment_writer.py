"""Track B: explicitly isolated, OFFLINE 14-day Myfxbook first-seen writer.

Routes ORIGINAL already-in-memory EURUSD+XAUUSD pairs through the existing
capture_pair() transaction into separate SQLite segments. Every segment is
under /tmp/remura-retail-lab-*, protected 0700/0600, with an explicit
lab acknowledgement. This is NEVER imported/called by the LIVE collector
or Squalincome. No API calls, source rereads, archive deletion or cron.

Rollover is NOT a cross-database transaction, and cannot yet attach to an
original Squalincome decision. A failed insert or a crash cannot fabricate a
receipt; unused empty next segments remain visible, not counted as samples.
An unpublished .pending file blocks access until human review; this module
never silently cleans it up. Hashes are local integrity checks, not external
signatures or backup proof.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import fcntl
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from urllib.parse import quote

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_retail_segment_readiness as layout

SCHEMA="remura-track-b-isolated-retail-segment-writer-v1"
META="research_retail_segment_metadata"
ENV="REMURA_RETAIL_ISOLATED_LAB"
ACK="I_CONFIRM_NO_LIVE"
MAX_BYTES=12_000_000
NAME=re.compile(r"retail-(\d{6})\.sqlite3\Z")
LOCK=".retail-shards.lock"


def _folder(root):
    p=Path(root)
    temp=Path(tempfile.gettempdir()).resolve()
    if (os.environ.get(ENV)!=ACK or not p.is_absolute()
            or p.is_symlink() or not p.is_dir()
            or p.resolve().parent!=temp
            or not p.name.startswith("remura-retail-lab-")
            or stat.S_IMODE(p.stat().st_mode)&0o077):
        raise ValueError("explicit_private_tmp_retail_lab_required")
    return p


@contextmanager
def _exclusive(root):
    folder=_folder(root)
    fd=os.open(folder/LOCK,os.O_CREAT|os.O_RDWR
               |getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or (
                stat.S_IMODE(os.fstat(fd).st_mode)&0o077):
            raise ValueError("unsafe_isolated_retail_lab_lock")
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("retail_lab_concurrent_writer_busy") from exc
        yield folder
    finally:
        os.close(fd)


def _path(folder,index):
    return folder/f"retail-{index:06d}.sqlite3"


def _digest(path):
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size>MAX_BYTES
            or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise ValueError("retail_segment_file_unsafe_or_oversized")
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda:stream.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()


def _ro(path):
    uri="file:"+quote(str(path.resolve()),safe="/")+"?mode=ro"
    db=sqlite3.connect(uri,uri=True,timeout=2)
    db.execute("PRAGMA query_only=ON")
    return db


def _read_meta(db,index,slot,previous_sha,cycle):
    row=db.execute(
        f"SELECT schema,index_number,start_utc,end_exclusive_utc,"
        f"previous_sha256,protocol_sha256,cycle_minutes FROM {META}"
    ).fetchall()
    expected=(SCHEMA,index,slot["startUtc"],slot["endExclusiveUtc"],
              previous_sha,layout.protocol.FROZEN_RULES_SHA256,cycle)
    if row!=[expected]:
        raise ValueError("retail_segment_identity_or_hash_chain_invalid")
    triggers={r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
        (META,))}
    if triggers!={"retail_segment_meta_no_update","retail_segment_meta_no_delete"}:
        raise ValueError("retail_segment_meta_immutability_missing")


def _inspect(folder,plan,cycle):
    shards={}
    for p in folder.iterdir():
        if p.name==LOCK:
            continue
        if p.name.startswith(".remura-retail-init-") and p.name.endswith(".pending"):
            raise ValueError("unpublished_retail_segment_requires_review")
        m=NAME.fullmatch(p.name)
        if m is None:
            raise ValueError("unexpected_file_inside_isolated_retail_lab")
        k=int(m.group(1))
        if k<1 or k>layout.EXPECTED_SEGMENTS or k in shards:
            raise ValueError("retail_segment_number_invalid_or_duplicate")
        _digest(p)
        shards[k]=p
    indexes=sorted(shards)
    if indexes!=list(range(1,len(indexes)+1)):
        raise ValueError("missing_retail_segment_calendar_index")
    dbs=[]
    previous_sha=None
    try:
        for i,slot in enumerate(plan["segments"],1):
            if i in shards:
                path=shards[i]
                db=_ro(path)
                dbs.append(db)
                if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                    raise ValueError("retail_segment_sqlite_integrity_failed")
                retail.require_schema(db)
                numeric.require_schema(db)
                _read_meta(db,i,slot,previous_sha,cycle)
                if db.execute(f"SELECT count(*) FROM {retail.LINK}").fetchone()[0]:
                    raise ValueError("cross_db_decision_link_unsupported")
                previous_sha=_digest(path)
            else:
                # The existing read-only auditor deliberately accepts empty
                # slots only as UNKNOWN, never as collected observations.
                db=sqlite3.connect(":memory:")
                dbs.append(db)
                retail.ensure_schema(db)
                numeric.ensure_schema(db)
                db.execute("PRAGMA query_only=ON")
        audit=layout.audit_shards(
            plan_authorization_from_start(plan),dbs,
            scenario_cycle_minutes=cycle)
        latest={}
        for i in indexes:
            db=dbs[i-1]
            for symbol,updated in db.execute(
                f"SELECT symbol,max(source_updated_at) FROM {retail.TABLE}"
                " GROUP BY symbol"):
                last=latest.get(symbol)
                stamped=layout._time(updated)
                if last is not None and stamped<=last:
                    raise ValueError("retail_cross_segment_backfill")
                latest[symbol]=stamped
        return shards,latest,audit
    finally:
        for db in dbs:
            db.close()


def plan_authorization_from_start(plan):
    # Only reconstruct the hypothetical calendar anchor for the existing
    # read-only auditor. Use the original caller-supplied anchor elsewhere.
    return plan["_authorized_at"]


def _create(folder,index,slot,previous_sha,cycle):
    target=_path(folder,index)
    if target.exists() or target.is_symlink():
        raise FileExistsError("retail_segment_no_overwrite")
    fd,tempname=tempfile.mkstemp(
        prefix=".remura-retail-init-",suffix=".pending",dir=str(folder))
    os.fchmod(fd,0o600)
    os.close(fd)
    tmp=Path(tempname)
    ok=False
    try:
        db=sqlite3.connect(str(tmp),timeout=2)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            retail.ensure_schema(db)
            numeric.ensure_schema(db)
            with db:
                db.execute(f"""CREATE TABLE {META}(
                  schema TEXT NOT NULL,index_number INTEGER PRIMARY KEY,
                  start_utc TEXT NOT NULL,end_exclusive_utc TEXT NOT NULL,
                  previous_sha256 TEXT,protocol_sha256 TEXT NOT NULL,
                  cycle_minutes INTEGER NOT NULL
                )""")
                db.execute(
                    f"INSERT INTO {META} VALUES (?,?,?,?,?,?,?)",
                    (SCHEMA,index,slot["startUtc"],slot["endExclusiveUtc"],
                     previous_sha,layout.protocol.FROZEN_RULES_SHA256,cycle))
                for op,name in (
                    ("UPDATE","retail_segment_meta_no_update"),
                    ("DELETE","retail_segment_meta_no_delete")):
                    db.execute(f"""CREATE TRIGGER {name} BEFORE {op}
                        ON {META} BEGIN
                        SELECT RAISE(ABORT,'immutable_retail_segment'); END""")
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("retail_unpublished_segment_corrupt")
        finally:
            db.close()
        fd=os.open(tmp,os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        if tmp.stat().st_size>MAX_BYTES:
            raise ValueError("retail_unpublished_segment_oversized")
        os.link(tmp,target)
        ok=True
    finally:
        # Crash artifacts remain for explicit human inspection; do not
        # erase ambiguous initializations if publication did not succeed.
        if ok:
            tmp.unlink()
    return target


def record(root,*,authorized_at,original_snapshot,file_read_at,clock,
           scenario_cycle_minutes=20):
    """Explicit lab write: one genuine capture_pair() per allocated slot.

    No background loop, no provider fetch, no backfill, no Squalincome link.
    The argument authorized_at is only an offline calendar ANCHOR, not
    evidence of external approval or authorization to deploy.
    """
    p=layout.plan(authorized_at,scenario_cycle_minutes=scenario_cycle_minutes)
    if p["status"]!="OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO":
        raise ValueError("retail_lab_calendar_not_capacity_safe")
    recorded=retail._utc(clock)
    read=retail._utc(file_read_at)
    if not read<=recorded<=read+retail.WRITE_GRACE:
        raise ValueError("retail_lab_read_clock_out_of_range")
    identities={}
    for symbol in ("EURUSD","XAUUSD"):
        updated,_=retail._identity(original_snapshot,symbol)
        if not (updated<=read and read-updated<=retail.MAX_AGE
                and updated>=retail.clocking._parse(retail.study.START)):
            raise ValueError("retail_lab_source_unavailable_or_stale")
        identities[symbol]=updated
    slot=None
    for i,part in enumerate(p["segments"],1):
        if layout._time(part["startUtc"])<=recorded<layout._time(part["endExclusiveUtc"]):
            slot=i
            break
    if slot is None:
        raise ValueError("retail_lab_clock_outside_frozen_study")
    with _exclusive(root) as folder:
        # Read-only preflight of ALL existing protected segments.
        checked={**p,"_authorized_at":authorized_at}
        existing,last,audit=_inspect(folder,checked,scenario_cycle_minutes)
        if any(s in last and identities[s]<=last[s] for s in identities):
            raise ValueError("retail_lab_duplicate_or_backdated_across_shards")
        if not existing and slot!=1:
            raise ValueError("retail_lab_initial_segment_must_be_first")
        if existing and slot not in (len(existing),len(existing)+1):
            raise ValueError("retail_lab_skipped_or_old_segment")
        if slot not in existing:
            prev=_digest(existing[slot-1]) if existing else None
            _create(folder,slot,p["segments"][slot-1],prev,scenario_cycle_minutes)
        path=_path(folder,slot)
        db=sqlite3.connect(str(path),timeout=2)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            out=retail.capture_pair(
                db,original_snapshot=original_snapshot,file_read_at=read,
                clock=recorded,research_numeric_features=True)
        finally:
            db.close()
        if path.stat().st_size>MAX_BYTES:
            raise ValueError("retail_lab_written_segment_oversized")
        return {
            "schema":SCHEMA,
            "status":"ISOLATED_RETAIL_SEGMENT_PAIR_WRITTEN_NOT_LIVE_GO",
            "segmentNumber":slot,"pairReceiptsWritten":2,
            "firstSeenOriginal":out["status"],
            "sourceReadAgain":False,
            "crossDatabaseSignalLink":False,
            "liveAuthorized":False,
            "newApiCalls":0,"sourceDataDeleted":0,
        }


def verify(root,*,authorized_at,scenario_cycle_minutes=20):
    p=layout.plan(authorized_at,scenario_cycle_minutes=scenario_cycle_minutes)
    if p["status"]!="OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO":
        raise ValueError("retail_lab_calendar_invalid")
    with _exclusive(root) as folder:
        shards,_,aud=_inspect(
            folder,{**p,"_authorized_at":authorized_at},scenario_cycle_minutes)
        return {
            "schema":SCHEMA,
            "status":"ISOLATED_RETAIL_SEGMENTS_VERIFIED_NOT_LIVE_GO",
            "publishedSegments":len(shards),
            "sourcePairs":aud["locallyRevalidatedRetailReceipts"]//2,
            "numericRows":aud["locallyRevalidatedNumericRows"],
            "unknownCalendarSlotsRemainUnknown":True,
            "crossDatabaseSignalAtomicityProven":False,
            "offHostRestoreVerified":False,
            "liveAuthorized":False,
            "newApiCalls":0,
        }
