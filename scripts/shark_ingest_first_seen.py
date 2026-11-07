"""Track B RESEARCH opt-in: locally atomic merged-price FIRST-SEEN fingerprint.

This module may only be called from price_store.ingest() immediately AFTER
the original prices UPSERT, inside its SAME SQLite transaction. The opt-in
caller must provide the actual parent process JSON read timestamp; neither
ctrader_feed.generatedAt (COLLECTION START) nor prices.updated_at (M15 OPEN)
is a receipt time. Clocks are local caller claims, NOT exchange/broker-signed.

Append-only fingerprints of the *merged* document and original child market
allow a later observer to reject a reloaded or revised price store. We store
NO raw OHLC, broker symbol, token, account ID or original payload in this
extra evidence table. No retroactive backfill or independent attestation.
Only a FUTURE coordinated release could authorize the integration and schema;
the default ingest path does not import or invoke this module.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import re
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as study
from scripts import shark_ctrader_ingest_handoff as handoff
from scripts import shark_market_regime_context as regime

SCHEMA="remura-track-b-local-merged-price-ingest-first-seen-v1"
TABLE="research_price_ingest_first_seen"
PILOT=frozenset(("EURUSD","XAUUSD"))
MAX_ROWS=15000
ALGORITHM="ctrader-child-merged-canonical-sha256-v1"


def ensure_schema(db):
    """Explicit research migration BEFORE ingest; never called automatically."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("fresh_explicit_research_migration_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            last_complete_open_utc TEXT NOT NULL,
            closed_at_utc TEXT NOT NULL,
            collection_started_utc TEXT NOT NULL,
            parent_read_at_utc TEXT NOT NULL,
            recorded_at_utc TEXT NOT NULL,
            child_document_sha256 TEXT NOT NULL,
            merged_document_sha256 TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            UNIQUE(symbol,parent_read_at_utc,child_document_sha256)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_ingest_first_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_ingest_first_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def _utc_clock(value):
    if type(value) is not datetime:
        raise ValueError("explicit_utc_instant_required")
    return witness._clock(value)


def preflight(export, *, parent_read_at, ingest_at):
    """Whole import must explicitly target only two authorized pilot markets."""
    received=_utc_clock(parent_read_at)
    now=_utc_clock(ingest_at)
    if study.protocol_sha256()!=study.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_science_protocol_mismatch")
    if (type(export) is not dict or export.get("schema")!="remura-price-v1"
            or type(export.get("markets")) is not dict
            or not export["markets"]
            or any(type(k) is not str or k not in PILOT
                   for k in export["markets"])):
        raise ValueError("explicit_two_market_research_pilot_only")
    started=witness._parse(study.START)
    origin=witness._parse(export.get("generatedAt"))
    if (not started<=origin<=received<=now
            or received-origin>handoff.MAX_CHILD_DURATION
            or now-received>handoff.MAX_INGEST_DURATION):
        raise ValueError("unverifiable_original_json_read_clock")
    return received,now


def record(db, *, symbol, child_export, merged_document,
           parent_read_at, ingest_at):
    """Persist fingerprint alongside actual prices UPSERT, or roll back both.

    Must not be invoked from a post-ingest observer; it requires an active
    transaction and the already-written, exact SQLite prices.payload.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("same_original_price_upsert_transaction_required")
    receipt,recorded=preflight(
        child_export,parent_read_at=parent_read_at,ingest_at=ingest_at)
    if symbol not in PILOT or symbol not in child_export["markets"]:
        raise ValueError("pilot_symbol_missing_from_original_child")
    if type(merged_document) is not dict:
        raise ValueError("original_merged_document_required")
    original=child_export["markets"][symbol]
    child=handoff._identity(original,symbol=symbol)
    merged=handoff._identity(merged_document,symbol=symbol)
    if original["providerSymbol"]!=merged_document["providerSymbol"]:
        raise ValueError("original_broker_mapping_changed")
    if child!=merged:
        raise ValueError("last33_child_bars_not_equal_to_merged")
    close=merged[-1][0]+handoff.STEP
    if (not close<=receipt<=recorded
            or recorded-close>handoff.MAX_SCAN_AGE
            or witness._parse(child_export["generatedAt"])<close):
        raise ValueError("unclosed_stale_or_future_original_price")
    original_sha=regime._digest(original)
    merged_sha=regime._digest(merged_document)
    # Re-read the row INSIDE the SAME transaction to demonstrate that this
    # proof binds the bytes just UPSERTed, not a parallel caller's guess.
    row=db.execute("SELECT payload FROM prices WHERE symbol=?",(symbol,)).fetchone()
    if row is None:
        raise ValueError("missing_same_transaction_price_upsert")
    try:
        stored=json.loads(row[0])
    except (TypeError,ValueError) as exc:
        raise ValueError("saved_original_price_invalid_json") from exc
    if regime._digest(stored)!=merged_sha:
        raise ValueError("stored_merged_price_sha_different_from_upsert")
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_ROWS:
        raise ValueError("local_ingest_first_seen_capacity_reached")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(symbol,last_complete_open_utc,closed_at_utc,"
        "collection_started_utc,parent_read_at_utc,recorded_at_utc,"
        "child_document_sha256,merged_document_sha256,algorithm)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (symbol,witness._iso(merged[-1][0]),witness._iso(close),
         witness._iso(witness._parse(child_export["generatedAt"])),
         witness._iso(receipt),witness._iso(recorded),
         original_sha,merged_sha,ALGORITHM)
    )
    return {"schema":SCHEMA,"state":"LOCAL_APPEND_ONLY_INGEST_PROOF",
            "capturedWithinOriginalPriceUpsert":True,
            "brokerReceiptIndependentlyAuthenticated":False,
            "sourceCollectionTimeIndependentlyAuthenticated":False,
            "remoteBrokerRequestsAdded":0,
            "liveCaptureEnabled":False,"tradingEdgeEstablished":False}


def verify_scan(db, *, symbol, current_document, scan_at):
    """Read-only later scan rejects changed SQLite source or stale receipt.

    This does NOT claim to have an authentic source process clock, nor prove
    any actual time-disjoint market outcome. No broker data or secrets out.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    scan=_utc_clock(scan_at)
    if symbol not in PILOT or type(current_document) is not dict:
        raise ValueError("invalid_pilot_scan_source")
    row=db.execute(
        f"SELECT closed_at_utc,parent_read_at_utc,recorded_at_utc,"
        f"merged_document_sha256,algorithm FROM {TABLE} "
        "WHERE symbol=? ORDER BY id DESC LIMIT 1",(symbol,)
    ).fetchone()
    if row is None:
        raise ValueError("original_ingest_first_seen_proof_absent")
    close,receipt,recorded,digest,algo=row
    first=witness._parse(receipt)
    finished=witness._parse(recorded)
    close=witness._parse(close)
    if (algo!=ALGORITHM
            or not close<=first<=finished<=scan
            or scan-close>handoff.MAX_SCAN_AGE):
        raise ValueError("source_receipt_not_available_at_scan")
    if type(digest) is not str or re.fullmatch("[0-9a-f]{64}",digest) is None:
        raise ValueError("invalid_persistent_digest")
    if regime._digest(current_document)!=digest:
        raise ValueError("source_document_mutated_since_original_ingest")
    stored=db.execute("SELECT payload FROM prices WHERE symbol=?",(symbol,)).fetchone()
    if stored is None:
        raise ValueError("price_store_missing_at_scan")
    try:
        current_saved=json.loads(stored[0])
    except (ValueError,TypeError) as exc:
        raise ValueError("unreadable_price_source_at_scan") from exc
    if regime._digest(current_saved)!=digest:
        raise ValueError("current_price_store_not_original_document")
    return {"schema":SCHEMA,
            "status":"LOCAL_SAME_MERGED_DOCUMENT_MATCHED",
            "locallyPersistedAsPartOfPriceUpsert":True,
            "parentJsonReadTimeIsNotBrokerResponseTime":True,
            "brokerSignedOrExternallyTimestamped":False,
            "realProspectiveOutcomeOrCostsKnown":False,
            "independentOOSValidated":False,
            "statisticalEdgeEstablished":False,
            "ordersEnabled":False,"notificationsEnabled":False,
            "additionalBrokerCalls":0,"writes":0}


def aggregate(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    n=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    return {"schema":SCHEMA,"locallyRecorded":n,"maxRows":MAX_ROWS,
            "pilotMarketCount":len(PILOT),
            "proofsNotIndependentlyTimestamped":True,
            "liveEnabled":False,"realPnL":False,"statisticalEdgeEstablished":False,
            "brokerCalls":0}
