#!/usr/bin/env python3
"""Track C3b: persistent isolated SQLite SHADOW rehearsal, NEVER LIVE.

No provider imports, account data, prices, positions, credentials, raw retail,
notifications, orders, schedules or network. Every function requires a test
file in a dedicated temporary folder and explicit OFFLINE mode.
The simulated coreCommittedAtUtc is caller-asserted, NOT proof of a real
core commit or a provider-signed timestamp. This is not yet a production
delivery protocol or proof of cross-database atomicity.

Lease expiry -> UNKNOWN without automatic retry/backdating. "Completed"
means synthetic worker ACK, never scientific or financial validation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile

MODE = "OFFLINE_SYNTHETIC_C3B_PERSISTENT_SHADOW_ONLY"
FILE = "track-c3b-synthetic-shadow.sqlite3"
SCHEMA = "remura-track-c3b-synthetic-wal-v1"
TABLE = "c3b_synthetic_shadow_items"
MAX_PENDING = 16
MAX_TOTAL = 4500
MAX_AGE = timedelta(minutes=3)
LEASE = timedelta(seconds=20)
MAX_MAIN_BYTES = 1048576
MAX_WAL_BYTES = 262144
HEX = re.compile(r"[0-9a-f]{64}\Z")
UNKNOWN = "UNKNOWN_NO_ORIGINAL_PROSPECTIVE_PROOF"
STAGED = "SYNTHETIC_METADATA_DURABLY_STAGED"
ACKED = "SYNTHETIC_WORKER_ACK_ONLY"


def _utc(s):
    if type(s) is not str or len(s) != 20 or not s.endswith("Z"):
        raise ValueError("strict_utc_second_required")
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(value, mode):
    if mode != MODE:
        raise ValueError("explicit_offline_synthetic_mode_required")
    if not isinstance(value, (str, Path)):
        raise ValueError("explicit_synthetic_path_required")
    p = Path(value).absolute()
    root = Path(tempfile.gettempdir()).resolve()
    if p.is_symlink() or p.parent.is_symlink():
        raise ValueError("symlink_forbidden")
    parent = p.parent.resolve()
    if (p.name != FILE or parent.parent != root
            or not parent.name.startswith("remura-c3b-")
            or not parent.is_dir() or p.resolve().parent != parent):
        raise ValueError("only_dedicated_temp_lab_db_allowed")
    return p


def _budget(p):
    for file,limit in ((p,MAX_MAIN_BYTES),
                       (Path(str(p)+"-wal"),MAX_WAL_BYTES)):
        if file.exists() and file.stat().st_size > limit:
            raise ValueError("synthetic_disk_guard_exceeded")


def _connect(p):
    db=sqlite3.connect(str(p),timeout=0.025)
    db.execute("PRAGMA busy_timeout=25")
    db.execute("PRAGMA synchronous=FULL")
    return db


def _schema(db):
    objects=dict(db.execute(
        "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?,?)",
        (TABLE,"c3b_identity_no_update","c3b_no_delete",
         "c3b_schema_guard")).fetchall())
    if (objects.get(TABLE)!="table" or
        objects.get("c3b_identity_no_update")!="trigger" or
        objects.get("c3b_no_delete")!="trigger" or
        objects.get("c3b_schema_guard")!="table"):
        raise ValueError("explicit_research_migration_required")
    if db.execute("SELECT version FROM c3b_schema_guard").fetchall()!=[(SCHEMA,)]:
        raise ValueError("wrong_research_schema_version")


def prepare(path, *, mode=None):
    """Manual test migration only; NEVER called from main/server."""
    p=_path(path,mode)
    if p.exists():
        raise ValueError("will_not_overwrite_or_migrate_existing_sqlite")
    db=_connect(p)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA wal_autocheckpoint=8")
        db.execute("PRAGMA journal_size_limit=131072")
        db.execute("PRAGMA max_page_count=256")
        with db:
            db.execute("CREATE TABLE c3b_schema_guard(version TEXT PRIMARY KEY)")
            db.execute("INSERT INTO c3b_schema_guard VALUES (?)",(SCHEMA,))
            db.execute(f"""CREATE TABLE {TABLE}(
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
                source TEXT NOT NULL CHECK(source IN ('cot','ctrader','retail')),
                source_seen TEXT NOT NULL,
                core_committed TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                staged_at TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN
                    ('pending','leased','unknown','synthetic_ack')),
                lease_token TEXT,
                lease_deadline TEXT,
                resolved_at TEXT,
                UNIQUE(symbol,source,source_seen,sha256))""")
            db.execute(f"""CREATE TRIGGER c3b_identity_no_update
                BEFORE UPDATE OF symbol,source,source_seen,core_committed,
                                 sha256,staged_at ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_research_identity'); END""")
            db.execute(f"""CREATE TRIGGER c3b_no_delete
                BEFORE DELETE ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'append_only_no_delete'); END""")
            db.execute(f"CREATE INDEX c3b_state_idx ON {TABLE}(state,id)")
        _budget(p)
    finally:
        db.close()
    return SCHEMA


def _metadata(m,now):
    if type(m) is not dict or set(m)!={
            "symbol","source","seenAtUtc","coreCommittedAtUtc",
            "originalSha256"}:
        return None
    symbol,source,sha=m["symbol"],m["source"],m["originalSha256"]
    if (type(symbol) is not str or symbol not in ("EURUSD","XAUUSD")
        or type(source) is not str or source not in ("cot","ctrader","retail")
        or type(sha) is not str or not HEX.fullmatch(sha)):
        return None
    try:
        seen=_utc(m["seenAtUtc"])
        committed=_utc(m["coreCommittedAtUtc"])
    except (TypeError,ValueError):
        return None
    if not (timedelta(0)<=committed-seen<=timedelta(seconds=30)
            and timedelta(0)<=now-committed<=MAX_AGE
            and timedelta(0)<=now-seen<=MAX_AGE):
        return None
    return symbol,source,_iso(seen),_iso(committed),sha


def stage(path, metadata, *, at, enabled=False, mode=None):
    """Best effort research-side stage. Caller runs AFTER its core commit.

    Any SQLite lock/missing migration/full queue returns UNKNOWN. Do not
    call from the actual core collector; no delivery guarantee is implied.
    """
    p=_path(path,mode)
    if type(enabled) is not bool or not enabled:
        return UNKNOWN
    try:
        now=_utc(at)
        values=_metadata(metadata,now)
        if values is None or not p.is_file():
            return UNKNOWN
        _budget(p)
        db=_connect(p)
        try:
            db.execute("BEGIN IMMEDIATE")
            _schema(db)
            total,pending=db.execute(
                f"SELECT count(*),sum(state IN ('pending','leased')) "
                f"FROM {TABLE}").fetchone()
            if total>=MAX_TOTAL or (pending or 0)>=MAX_PENDING:
                db.rollback()
                return UNKNOWN
            db.execute(
                f"INSERT INTO {TABLE}(symbol,source,source_seen,core_committed,"
                "sha256,staged_at,state) VALUES (?,?,?,?,?,?,'pending')",
                (*values,at))
            db.commit()
            return STAGED
        except (sqlite3.Error,ValueError):
            db.rollback()
            return UNKNOWN
        finally:
            db.close()
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return UNKNOWN


def claim(path, *, at, enabled=False, mode=None):
    """Explicit, separate research worker step; no callback inside core."""
    p=_path(path,mode)
    if type(enabled) is not bool or not enabled:
        return None
    try:
        now=_utc(at)
        _budget(p)
        if not p.is_file():
            return None
        db=_connect(p)
        try:
            db.execute("BEGIN IMMEDIATE")
            _schema(db)
            db.execute(
                f"UPDATE {TABLE} SET state='unknown',resolved_at=?,"
                "lease_token=NULL,lease_deadline=NULL "
                "WHERE (state='leased' AND lease_deadline<=?) "
                "OR (state='pending' AND source_seen<?)",
                (at,at,_iso(now-MAX_AGE)))
            row=db.execute(
                f"SELECT id,symbol,source,source_seen,sha256 FROM {TABLE} "
                "WHERE state='pending' AND source_seen<=? ORDER BY id LIMIT 1",
                (at,)).fetchone()
            if row is None:
                db.commit()
                return None
            token=secrets.token_hex(16)
            db.execute(
                f"UPDATE {TABLE} SET state='leased',lease_token=?,"
                "lease_deadline=? WHERE id=? AND state='pending'",
                (token,_iso(now+LEASE),row[0]))
            db.commit()
            return {"id":row[0],"symbol":row[1],"source":row[2],
                    "seenAtUtc":row[3],"originalSha256":row[4],
                    "leaseToken":token}
        except (sqlite3.Error,ValueError):
            db.rollback()
            return None
        finally:
            db.close()
    except (sqlite3.Error,OSError,ValueError):
        return None


def finish(path, *, item_id, lease_token, at, synthetic_worker_ok,
           enabled=False, mode=None):
    """Synthetic ACK only: never actual scientific source verification."""
    p=_path(path,mode)
    if type(enabled) is not bool or not enabled:
        return UNKNOWN
    if (type(item_id) is not int or item_id<=0
            or type(lease_token) is not str or len(lease_token)!=32
            or any(c not in "0123456789abcdef" for c in lease_token)
            or type(synthetic_worker_ok) is not bool):
        return UNKNOWN
    try:
        now=_utc(at)
        _budget(p)
        if not p.is_file():
            return UNKNOWN
        db=_connect(p)
        try:
            db.execute("BEGIN IMMEDIATE")
            _schema(db)
            row=db.execute(
                f"SELECT state,source_seen,lease_deadline,lease_token "
                f"FROM {TABLE} WHERE id=?", (item_id,)).fetchone()
            if row is None or row[0]!="leased" or row[3]!=lease_token:
                db.rollback()
                return UNKNOWN
            if (not _utc(row[1])<=now<=_utc(row[2])
                    or now-_utc(row[1])>MAX_AGE):
                state="unknown"
            else:
                state="synthetic_ack" if synthetic_worker_ok else "unknown"
            db.execute(
                f"UPDATE {TABLE} SET state=?,resolved_at=?,"
                "lease_token=NULL,lease_deadline=NULL WHERE id=?",
                (state,at,item_id))
            db.commit()
            return ACKED if state=="synthetic_ack" else UNKNOWN
        except (sqlite3.Error,ValueError):
            db.rollback()
            return UNKNOWN
        finally:
            db.close()
    except (sqlite3.Error,OSError,ValueError):
        return UNKNOWN


def inspect_lab(path, *, mode=None):
    """Sanitized summary, no payload, symbols, timestamps, SHA or lease token."""
    p=_path(path,mode)
    try:
        _budget(p)
        if not p.is_file():
            return {"state":UNKNOWN}
        db=_connect(p)
        try:
            _schema(db)
            totals=dict(db.execute(
                f"SELECT state,count(*) FROM {TABLE} GROUP BY state").fetchall())
            wal=Path(str(p)+"-wal")
            return {
                "schema":SCHEMA,
                "state":"OFFLINE_SYNTHETIC_WAL_ONLY_NOT_LIVE",
                "pending":totals.get("pending",0),
                "leased":totals.get("leased",0),
                "unknown":totals.get("unknown",0),
                "syntheticAck":totals.get("synthetic_ack",0),
                "total":sum(totals.values()),
                "mainBytes":p.stat().st_size,
                "walBytes":wal.stat().st_size if wal.exists() else 0,
                "diskLimitIsHard":False,
                "providerTimestampSigned":False,
                "realCrossDbAtomicity":False,
                "realCollectorIsolationProven":False,
                "actualOOSOutcomes":False,
                "actualEdgeEstablished":False,
                "liveEnabled":False,
                "newProviderCalls":0,
                "cvd":"UNKNOWN",
            }
        finally:
            db.close()
    except (sqlite3.Error,OSError,ValueError):
        return {"state":UNKNOWN}
