"""Track B, OFFLINE: local first-seen of ORIGINAL Myfxbook latest.json data.

The existing Myfxbook collector writes latest.json AFTER its API request.
Its updatedAt is NOT a Myfxbook-signed publication timestamp. A FUTURE
authorized caller must pass the actual original in-memory document and a
local UTC clock sampled immediately after that file was read. No data may
be backfilled by examining a later latest.json. Neither retail capture nor
optional original-decision attachment is enabled by LIVE production.

Store hashes and local clock metadata ONLY; never positions, percentages,
accounts, broker symbols, tokens, source JSON or OHLC. This does not prove
that Squalincome used retail: its original signal side uses COT+price.
CVD continues separately on the PRIVATE pilot ledger; absence is UNKNOWN.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import math
import sqlite3

from scripts import shark_cot_asof_witness as clocking
from scripts import shark_cvd_incremental_protocol as study
from scripts import shark_signal_ingest_decision_link as signal

SCHEMA="remura-retail-local-first-seen-context-v1"
TABLE="research_retail_original_first_seen"
LINK="research_retail_signal_context"
SOURCE="Myfxbook Community Outlook"
PILOT=frozenset(("EURUSD","XAUUSD"))
FIELDS=frozenset(("t","lPct","sPct","lLots","sLots","lPos","sPos","avgL","avgS"))
MAX_AGE=timedelta(minutes=35)
WRITE_GRACE=timedelta(seconds=30)
DECISION_GRACE=timedelta(seconds=30)
MAX_ROWS=15000
ALG="myfxbook-original-numeric-sha256-v1"


def ensure_schema(db):
    """Standalone explicit research migration, never called by LIVE."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("clean_explicit_research_migration_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            source_updated_at TEXT NOT NULL,
            original_read_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            numeric_sha256 TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            UNIQUE(symbol,source_updated_at)
        )""")
        db.execute(f"""CREATE TABLE IF NOT EXISTS {LINK}(
            history_id INTEGER PRIMARY KEY,
            retail_witness_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            linked_at TEXT NOT NULL,
            original_numeric_sha256 TEXT NOT NULL
        )""")
        for table,op,name in (
            (TABLE,"UPDATE","research_retail_first_update"),
            (TABLE,"DELETE","research_retail_first_delete"),
            (LINK,"UPDATE","research_retail_context_update"),
            (LINK,"DELETE","research_retail_context_delete")):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
               BEFORE {op} ON {table}
               BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def _utc(value):
    if type(value) is not datetime:
        raise ValueError("explicit_real_utc_runtime_clock_required")
    return clocking._clock(value)


def _identity(snapshot,symbol):
    if (symbol not in PILOT or type(snapshot) is not dict
            or set(snapshot)!={"status","source","updatedAt","symbols"}
            or snapshot["status"]!="ok" or snapshot["source"]!=SOURCE
            or type(snapshot["symbols"]) is not dict):
        raise ValueError("original_myfxbook_latest_source_required")
    updated=clocking._parse(snapshot["updatedAt"])
    data=snapshot["symbols"].get(symbol)
    if type(data) is not dict or set(data)!=FIELDS:
        raise ValueError("original_myfxbook_pilot_numeric_row_missing")
    if clocking._parse(data["t"])!=updated:
        raise ValueError("myfxbook_row_updated_at_mismatch")
    for key in FIELDS-{"t"}:
        val=data[key]
        if val is None and key not in ("lPct","sPct"):
            continue
        if (type(val) not in (int,float) or not math.isfinite(val)
                or val<0 or key in ("lPct","sPct") and val>100
                or key in ("lPos","sPos") and (type(val) is not int or val>10**12)):
            raise ValueError("invalid_retail_numeric_value")
    if abs(data["lPct"]+data["sPct"]-100)>1.5:
        raise ValueError("invalid_retail_percentages")
    canon=json.dumps({"source":SOURCE,"symbol":symbol,
                      "updatedAt":snapshot["updatedAt"],"entry":data},
                     ensure_ascii=True,sort_keys=True,separators=(",",":"),
                     allow_nan=False)
    if len(canon)>200000:
        raise ValueError("retail_original_unbounded")
    return updated,hashlib.sha256(canon.encode()).hexdigest()


def capture(db, *, symbol, original_snapshot, file_read_at, clock):
    """Append only on FIRST actual local read, not a later historical replay."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("fresh_retail_first_seen_transaction_required")
    now=_utc(clock)
    receipt=_utc(file_read_at)
    updated,sha=_identity(original_snapshot,symbol)
    if study.protocol_sha256()!=study.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_protocol_mismatch")
    if (not clocking._parse(study.START)<=updated<=receipt<=now
            or now-receipt>WRITE_GRACE or receipt-updated>MAX_AGE):
        raise ValueError("retail_local_first_seen_not_causal_or_fresh")
    db.execute("BEGIN IMMEDIATE")
    try:
        last=db.execute(
            f"SELECT source_updated_at FROM {TABLE} WHERE symbol=? "
            "ORDER BY id DESC LIMIT 1",(symbol,)).fetchone()
        if last and clocking._parse(last[0])>=updated:
            raise ValueError("duplicate_or_backfilled_retail_snapshot")
        if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_ROWS:
            raise ValueError("retail_research_capacity_reached")
        db.execute(
            f"INSERT INTO {TABLE} (symbol,source_updated_at,"
            "original_read_at,recorded_at,numeric_sha256,algorithm) "
            "VALUES(?,?,?,?,?,?)",
            (symbol,clocking._iso(updated),clocking._iso(receipt),
             clocking._iso(now),sha,ALG))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"schema":SCHEMA,"state":"LOCAL_NUMERIC_RETAIL_RECEIPT",
            "myfxbookPublicationIndependentlyVerified":False,
            "usedInOriginalSignal":False,
            "brokerCalls":0,"statisticalEdgeEstablished":False}


def attach_new(db, *, history_id, original_snapshot, clock):
    """Optional context ONLY in the original new-history transaction.

    Requires original COT+price link already recorded in this same
    transaction by the strict offline coordinator. This function cannot
    independently authenticate a caller's history INSERT.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("original_history_transaction_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("new_history_id_required")
    now=_utc(clock)
    row=db.execute("SELECT symbol,observed_at FROM squalincome_history "
                   "WHERE id=?",(history_id,)).fetchone()
    if row is None:
        raise ValueError("new_history_absent")
    symbol,stamp=row
    observed=clocking._parse(stamp)
    if (observed<clocking._parse(study.START)
            or not observed<=now<=observed+DECISION_GRACE):
        raise ValueError("retail_not_recorded_at_original_decision")
    proof=db.execute(
        f"SELECT observed_at_utc,linked_at_utc FROM {signal.TABLE} "
        "WHERE history_id=?",(history_id,)).fetchone()
    if (proof is None or clocking._parse(proof[0])!=observed
            or not observed<=clocking._parse(proof[1])<=now):
        raise ValueError("original_cot_price_signal_proof_missing")
    updated,digest=_identity(original_snapshot,symbol)
    last=db.execute(
        f"SELECT id,source_updated_at,original_read_at,recorded_at,"
        f"numeric_sha256,algorithm FROM {TABLE} WHERE symbol=? "
        "ORDER BY id DESC LIMIT 1",(symbol,)).fetchone()
    if last is None:
        raise ValueError("original_retail_local_receipt_missing")
    ident,stamp_updated,stamp_read,stamp_recorded,sha,algorithm=last
    if (algorithm!=ALG or updated!=clocking._parse(stamp_updated)
            or sha!=digest or
            not updated<=clocking._parse(stamp_read)<=
                clocking._parse(stamp_recorded)<=observed
            or observed-updated>MAX_AGE):
        raise ValueError("retail_source_not_known_at_original_signal")
    if db.execute(f"SELECT 1 FROM {LINK} WHERE history_id=?",
                  (history_id,)).fetchone():
        raise ValueError("retail_context_cannot_be_rebound")
    db.execute(
        f"INSERT INTO {LINK}(history_id,retail_witness_id,symbol,"
        "observed_at,linked_at,original_numeric_sha256) "
        "VALUES(?,?,?,?,?,?)",
        (history_id,ident,symbol,stamp,clocking._iso(now),digest))
    return {"status":"LOCAL_RETAIL_CONTEXT_BEFORE_DECISION",
            "retailUsedByOriginalSqualincomeSignal":False,
            "cvdEvaluation":"UNKNOWN",
            "independentRetailProviderReceipt":False,
            "ordersEnabled":False,"statisticalEdgeEstablished":False}


def aggregate(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    a=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    b=db.execute(f"SELECT count(*) FROM {LINK}").fetchone()[0]
    return {"schema":SCHEMA,"localFirstSeenSnapshots":a,
            "localOriginalSignalContextLinks":b,
            "retailInputToActualSignalAlgorithm":False,
            "cvdScansAdmitted":False,"outcomesMeasured":False,
            "realTradingEdgeEstablished":False,"brokerCalls":0}
