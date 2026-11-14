"""Track B OFFLINE: bounded prospective numeric Myfxbook research feature vault.

SOURCE: the SAME original in-memory private latest.json received by the
research-only Myfxbook parent process. Six anonymous aggregate numeric
metrics for EURUSD/XAUUSD, and the first-seen receipt SHA, are stored in the
SAME SQLite transaction that creates the two original local receipts.
No extra API calls, source fetch, historical backfill, account/position IDs,
source JSON or average entry prices; NOT connected to live production.

Not encrypted at rest: intended for an existing private permission-restricted
SQLite research DB only, with explicit authorized schema migration. A fixed
capacity fails closed; retention or deletion requires separate governance
since these are append-only witness values. Readout is only for a receipt
ALREADY pinned to an original Squalincome decision. Results are research
features, not signals; source times are local, NOT Myfxbook signatures.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import sqlite3

from scripts import shark_cot_asof_witness as clocks
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_retail_first_seen as original

TABLE="research_retail_numeric_features"
ALG="remura-retail-six-aggregate-features-v1"
FIELDS=("lPct","sPct","lLots","sLots","lPos","sPos")
COLUMNS=("long_pct","short_pct","long_lots","short_lots",
         "long_positions","short_positions")
MAX_FEATURE_ROWS=4500


def ensure_schema(db):
    """Explicit migration only; no caller auto-creates this table."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("explicit_clean_numeric_feature_migration_required")
    original.require_schema(db)
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            receipt_id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            original_sha256 TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            long_pct REAL NOT NULL CHECK(long_pct BETWEEN 0 AND 100),
            short_pct REAL NOT NULL CHECK(short_pct BETWEEN 0 AND 100),
            long_lots REAL CHECK(long_lots >= 0),
            short_lots REAL CHECK(short_lots >= 0),
            long_positions INTEGER CHECK(long_positions >= 0),
            short_positions INTEGER CHECK(short_positions >= 0),
            features_sha256 TEXT NOT NULL,
            algorithm TEXT NOT NULL
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_retail_features_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_retail_features_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def require_schema(db):
    """Read-only preflight to perform BEFORE a future Myfxbook subprocess."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("numeric_features_preflight_requires_clean_connection")
    original.require_schema(db)
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? AND type='table'",
        (TABLE,)).fetchone() is None:
        raise ValueError("numeric_features_explicit_migration_required")
    for name in ("research_retail_features_no_update",
                 "research_retail_features_no_delete"):
        if db.execute(
            "SELECT 1 FROM sqlite_master WHERE name=? AND type='trigger'",
            (name,)).fetchone() is None:
            raise ValueError("numeric_features_append_only_trigger_missing")
    expected={"receipt_id","symbol","original_sha256","recorded_at",
              *COLUMNS,"features_sha256","algorithm"}
    cols={row[1] for row in db.execute(f"PRAGMA table_info({TABLE})")}
    if not expected.issubset(cols):
        raise ValueError("numeric_features_schema_incomplete")
    return True


def _six(entry):
    """Validate 6 anonymous metrics; keep optional missing as SQL NULL."""
    if type(entry) is not dict or not set(FIELDS).issubset(entry):
        raise ValueError("original_six_retail_metrics_missing")
    ret={}
    for key in FIELDS:
        val=entry[key]
        if val is None and key in ("lLots","sLots","lPos","sPos"):
            ret[key]=None
            continue
        if (type(val) not in (int,float) or not math.isfinite(val)
                or val<0 or key in ("lPct","sPct") and val>100):
            raise ValueError("invalid_original_retail_metric")
        if key in ("lPos","sPos"):
            if type(val) is not int or val>10**12:
                raise ValueError("invalid_retail_aggregate_positions")
            ret[key]=val
        else:
            ret[key]=float(val)
    if abs(ret["lPct"]+ret["sPct"]-100)>1.5:
        raise ValueError("inconsistent_retail_long_short_percentages")
    return ret


def _hash(symbol,original_sha,six):
    blob=json.dumps(
        {"algorithm":ALG,"symbol":symbol,
         "sourceSha":original_sha,"values":six},
        sort_keys=True,separators=(",",":"),allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def append_inside_original_pair(db, *, receipt_id, symbol, entry,
                                original_sha, recorded_clock):
    """Invoked AFTER receipt INSERT, before COMMIT, on SAME connection."""
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("same_original_first_seen_receipt_transaction_required")
    if (type(receipt_id) is not int or receipt_id<=0
            or symbol not in original.PILOT
            or type(original_sha) is not str or len(original_sha)!=64
            or any(c not in "0123456789abcdef" for c in original_sha)):
        raise ValueError("invalid_numeric_source_identity")
    if type(recorded_clock) is not datetime:
        raise ValueError("explicit_utc_retail_feature_clock_required")
    recorded=clocks._clock(recorded_clock)
    source=db.execute(
        f"SELECT symbol,numeric_sha256,recorded_at FROM {original.TABLE} "
        "WHERE id=?",(receipt_id,)
    ).fetchone()
    if (source is None or source[0]!=symbol or source[1]!=original_sha
            or clocks._parse(source[2])!=recorded):
        raise ValueError("numeric_values_not_bound_to_original_receipt")
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_FEATURE_ROWS:
        raise ValueError("numeric_features_capacity_reached")
    six=_six(entry)
    db.execute(
        f"INSERT INTO {TABLE} (receipt_id,symbol,original_sha256,recorded_at,"
        "long_pct,short_pct,long_lots,short_lots,long_positions,"
        "short_positions,features_sha256,algorithm)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (receipt_id,symbol,original_sha,clocks._iso(recorded),
         *(six[key] for key in FIELDS),_hash(symbol,original_sha,six),ALG)
    )
    return True


def read_linked(db, *, history_id):
    """Research-only readout after original event linked FIRST-SEEN receipt.

    Never infer a value by joining today/latest.json or older market history.
    No retail data is returned if the original decision lacks a feature row.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("private_sqlite_connection_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("original_history_id_required")
    if protocol.protocol_sha256()!=protocol.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_protocol_mismatch")
    item=db.execute(
        f"SELECT h.symbol,h.observed_at,c.retail_witness_id,"
        "c.original_numeric_sha256,c.symbol,c.observed_at,c.linked_at "
        "FROM squalincome_history h "
        f"JOIN {original.LINK} c ON h.id=c.history_id WHERE h.id=?",
        (history_id,)
    ).fetchone()
    if item is None:
        return {"status":"UNKNOWN_NO_ORIGINAL_RETAIL_LINK",
                "retailInputToOriginalSignal":False,
                "cvdCoverage":"UNKNOWN","realEdgeEstablished":False}
    symbol,observed_string,rid,link_sha,link_symbol,link_observed,link_at=item
    receipt=db.execute(
        f"SELECT symbol,source_updated_at,original_read_at,recorded_at,"
        f"numeric_sha256 FROM {original.TABLE} WHERE id=?",(rid,)
    ).fetchone()
    if receipt is None:
        raise ValueError("original_retail_receipt_missing_at_feature_read")
    source_sym,source_time,read_time,record_time,original_sha=receipt
    observed=clocks._parse(observed_string)
    if (symbol!=source_sym or original_sha!=link_sha
            or link_symbol!=symbol
            or clocks._parse(link_observed)!=observed
            or not observed<=clocks._parse(link_at)<=observed+original.DECISION_GRACE
            or not clocks._parse(protocol.START)<=clocks._parse(source_time)
               <=clocks._parse(read_time)<=clocks._parse(record_time)<=observed
            or observed-clocks._parse(source_time)>original.MAX_AGE):
        raise ValueError("retail_link_not_valid_for_original_decision")
    # A later locally witnessed receipt cannot be swapped with an older
    # numeric value that was never pinned as latest at original decision.
    latest=db.execute(
        f"SELECT id FROM {original.TABLE} WHERE symbol=? AND recorded_at<=? "
        "ORDER BY id DESC LIMIT 1",
        (symbol,clocks._iso(observed))
    ).fetchone()
    if latest is None or latest[0]!=rid:
        raise ValueError("retail_receipt_superseded_before_original_decision")
    from scripts import shark_signal_ingest_decision_link as signal
    proof=db.execute(
        f"SELECT observed_at_utc,linked_at_utc FROM {signal.TABLE} "
        "WHERE history_id=?",(history_id,)
    ).fetchone()
    if (proof is None or clocks._parse(proof[0])!=observed
            or not observed<=clocks._parse(proof[1])<=clocks._parse(link_at)):
        raise ValueError("retail_original_decision_source_proof_missing")
    vals=db.execute(
        f"SELECT symbol,original_sha256,recorded_at,"
        "long_pct,short_pct,long_lots,short_lots,long_positions,"
        "short_positions,features_sha256,algorithm "
        f"FROM {TABLE} WHERE receipt_id=?",(rid,)
    ).fetchone()
    if vals is None:
        return {"status":"UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN",
                "retailInputToOriginalSignal":False,
                "cvdCoverage":"UNKNOWN","realEdgeEstablished":False}
    feat_symbol,feat_sha,feat_stamp,*remainder=vals
    feat_digest,algo=remainder[-2:]
    six=dict(zip(FIELDS,remainder[:6]))
    if (feat_symbol!=symbol or feat_sha!=original_sha
            or clocks._parse(feat_stamp)!=clocks._parse(record_time)
            or algo!=ALG or _six(six)!=six
            or _hash(symbol,original_sha,six)!=feat_digest):
        raise ValueError("numeric_features_tampered_or_not_same_original_receipt")
    return {
        "status":"LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH",
        "features":dict(six),
        "retailInputToOriginalSignal":False,
        "myfxbookTimestampIndependentlyAuthenticated":False,
        "cvdCoverage":"UNKNOWN",
        "actualOutcomesOrCostsMeasured":False,
        "realEdgeEstablished":False,
        "brokerCalls":0,
    }


def aggregate(db):
    """Safe summary only: no raw metrics, dates, symbols or receipt IDs."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    count=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    return {"schema":ALG,"prospectiveNumericRows":count,
            "hardRowLimit":MAX_FEATURE_ROWS,
            "marketsMax":2,"liveEnabled":False,
            "noAutomaticDeletionOrExpansion":True,
            "cvdCoverage":"UNKNOWN",
            "realEdgeEstablished":False,"newAPICalls":0}
