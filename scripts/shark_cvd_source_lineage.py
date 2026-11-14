"""REMURA Track B: private, future-only CVD proxy source-document binding.

A CVD divergence detected on cTrader M15 is never admitted via mere market
name/time coincidence. The recorder must rerun the ORIGINAL detector on the
very same in-memory document and match the COMPLETE original event before a
HMAC of the canonical full document SHA can be bound to the event atomically.

The SHA is the identical canonical full OHLC document hash used in
shark_price_asof_evidence. The stored HMAC does not disclose broker mapping
or raw document hash. Any later cross-ledger join can check SAME snapshot
without trusting a mutable current price table.

The document cannot establish independent collection-time, execution volume,
H1/H4 historical freshness, CFTC first-seen, orders, profits or edge.
Only synthetic tests; not imported or enabled in LIVE. No retroactive binding.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import hmac
import json
import re
import sqlite3

from scripts import cvd_divergence as detector
from scripts import shark_price_asof_evidence as price
from scripts import shark_cot_asof_witness as witness

TABLE = "research_cvd_price_bindings"
SCHEMA = "remura-cvd-price-document-hmac-v1"
ALG = "rerun-original-detector-and-bind-source-document-v1"
TRIGGERS = ("research_cvd_price_bindings_no_update",
            "research_cvd_price_bindings_no_delete")
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_M15 = 4320
DOMAIN = b"remura-cvd-source-document-v1|"


def _schema(db):
    db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
        event_key TEXT PRIMARY KEY,
        document_hmac TEXT NOT NULL,
        bound_at TEXT NOT NULL,
        algorithm TEXT NOT NULL CHECK(algorithm='{ALG}'),
        FOREIGN KEY(event_key) REFERENCES research_cvd_observations(key)
    )""")
    for op,trigger in (("UPDATE",TRIGGERS[0]),("DELETE",TRIGGERS[1])):
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {trigger}
            BEFORE {op} ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_cvd_source_binding'); END""")


def ensure_schema(db):
    """For synthetic/private future migration, never called in LIVE."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        _schema(db)


def _has_protected_schema(db):
    tables={r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,))}
    if TABLE not in tables:
        return False
    present={r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
        (TABLE,))}
    if not set(TRIGGERS).issubset(present):
        raise ValueError("cvd_source_binding_triggers_missing")
    return True


def _document_sha(doc):
    canonical=json.dumps(doc,sort_keys=True,separators=(",",":"),
                         ensure_ascii=True)
    if len(canonical)>4_000_000:
        raise ValueError("source_document_unbounded")
    return hashlib.sha256(canonical.encode()).hexdigest()


def _mac(secret,sha):
    # domain-separated keyed proof, not a raw public hash or broker symbol
    if not isinstance(secret,bytes) or len(secret)<16:
        raise ValueError("stable_private_hmac_secret_required")
    if not isinstance(sha,str) or not HEX.fullmatch(sha):
        raise ValueError("canonical_sha256_required")
    return hmac.new(secret,DOMAIN+sha.encode(),hashlib.sha256).hexdigest()


def prepare(event, doc, *, detected_at, secret):
    """Rerun live detector and require the exact event from original source.

    A source SHA supplied by the caller without its original OHLC document
    is NEVER acceptable: caller cannot bless a fabricated matching digest.
    """
    if not isinstance(event,dict) or not isinstance(doc,dict):
        raise ValueError("source_event_and_document_required")
    detected=witness._clock(detected_at)
    if (doc.get("symbol")!=event.get("symbol")
            or doc.get("provider")!="ctrader"
            or doc.get("providerSymbol")!=event.get("providerSymbol")
            or doc.get("timezone")!="UTC"
            or doc.get("sourceTimeframe")!="M15"):
        raise ValueError("original_source_mapping_mismatch")
    frames=doc.get("timeframes")
    if (not isinstance(frames,dict)
            or any(not isinstance(frames.get(f),list)
                   for f in ("M15","H1","H4"))):
        raise ValueError("original_full_document_required")
    bars=price._bars(frames["M15"],900,MAX_M15)
    if (witness._parse(doc.get("lastComplete"))!=bars[-1][0]
            or detected<bars[-1][0]+timedelta(minutes=15)
            or detected-bars[-1][0]>timedelta(minutes=105)):
        raise ValueError("source_last_closed_at_detection_invalid")
    # Only the M15 input is consumed by the original CLV*tick detector.
    # H1/H4 in the original document are bound by the same digest, but
    # are NOT declared independently verified by this private module.
    market={
        "symbol":doc["symbol"],"provider":"ctrader",
        "providerSymbol":doc["providerSymbol"],
        "frames":{"M15":[
            {**row,"t":int(start.timestamp()*1000)}
            for start,row in bars
        ]},
    }
    result=detector.analyze(market,now=int(detected.timestamp()*1000))
    if (result.get("status")!="ok" or
            not any(existing==event for existing in result.get("events",[]))):
        raise ValueError("cvd_event_not_reproduced_from_source_document")
    sha=_document_sha(doc)
    return _mac(secret,sha)


def insert(db, *, event_key, doc_hmac, recorded_at):
    """Requires existing caller transaction, directly after NEW event insert."""
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("new_event_transaction_required")
    if (not isinstance(event_key,str) or not HEX.fullmatch(event_key)
            or not isinstance(doc_hmac,str) or not HEX.fullmatch(doc_hmac)):
        raise ValueError("invalid_private_binding_identity")
    _schema(db)
    if not _has_protected_schema(db):
        raise ValueError("cvd_binding_schema_unavailable")
    exists=db.execute(
        f"SELECT 1 FROM {TABLE} WHERE event_key=?",(event_key,)
    ).fetchone()
    if exists:
        raise ValueError("cvd_binding_not_new")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(event_key,document_hmac,bound_at,algorithm) VALUES (?,?,?,?)",
        (event_key,doc_hmac,witness._iso(recorded_at),ALG))


def match(db, *, event_key, original_price_sha, observed_at,
          as_of, secret):
    """Check a single already-written CVD event against a price proof SHA.

    This is only an EXACT-SOURCE and chronology primitive for a future
    joint auditor. It does not check COT; calling it on a source SHA inferred
    after the event would violate its intended evidence contract.
    Returns no event data or broker identifiers.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    observed=witness._parse(observed_at)
    now=witness._parse(as_of)
    expected=_mac(secret,original_price_sha)
    if not _has_protected_schema(db):
        return {"state":"NO_SOURCE_BINDINGS","sourceMatch":False,
                "causal":False,"tradingEdgeEstablished":False,
                "brokerCalls":0}
    rows=db.execute(
        f"SELECT e.confirmed_at,e.collected_at,e.detected_at,"
        f"b.bound_at,b.document_hmac,b.algorithm "
        "FROM research_cvd_observations e "
        f"JOIN {TABLE} b ON b.event_key=e.key WHERE e.key=?",
        (event_key,)).fetchall()
    if len(rows)>1:
        raise ValueError("duplicate_cvd_binding")
    if not rows:
        return {"state":"CVD_SOURCE_UNVERIFIABLE","sourceMatch":False,
                "causal":False,"tradingEdgeEstablished":False,
                "brokerCalls":0}
    confirmed,collected,detected,bound,stored,alg=rows[0]
    if (alg!=ALG or not isinstance(stored,str) or not HEX.fullmatch(stored)
            or witness._parse(bound)!=witness._parse(detected)):
        raise ValueError("cvd_binding_integrity_invalid")
    confirm=witness._parse(confirmed)
    received=witness._parse(collected)
    discovered=witness._parse(detected)
    if not confirm<=received<=discovered:
        raise ValueError("cvd_source_clock_noncausal")
    causal=(discovered<=observed<=now
            and observed-discovered<=timedelta(minutes=90))
    equal=hmac.compare_digest(stored,expected)
    return {
        "state":("EXACT_LOCAL_SOURCE_AND_CHRONOLOGY" if causal and equal
                 else "NOT_SAME_SOURCE_OR_NOT_CAUSAL"),
        "sourceMatch":bool(equal),
        "causal":bool(causal),
        "eventWasReproducedOnOriginalDocument":bool(causal and equal),
        "independentBrokerCollectionTimeKnown":False,
        "cvdAggressorFlowMeasured":False,
        "tradingEdgeEstablished":False,
        "brokerCalls":0,
    }
