"""Track B OFFLINE ONLY: one-transaction original price/regime proof rehearsal.

Future original collector must hand over the SAME in-memory OHLC document,
a source receipt timestamp measured at the actual fetch and a new-history
INSERT function. This coordinator owns an entire SQLite transaction:
new observation INSERT -> original price as-of witness -> first-seen regime.
Every failure rolls the whole transaction back. Never patch LIVE ingestion,
read a broker cache again, or infer receipt time from candle-open fields.

The insert callback and clocks remain operator-controlled: this is a local
atomicity/provenance gate, NOT independently attested source timestamps,
broker signatures, trusted time, executed trades or predictive outcomes.
No network, cloud, broker GET, persistent files, orders or notifications.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_asof_evidence as price
from scripts import shark_regime_first_seen as regime
from scripts import shark_cvd_incremental_protocol as protocol

SCHEMA = "remura-track-b-price-regime-owned-transaction-rehearsal-v1"


def capture_new(db, *, insert_history, original_document,
                source_received_at, clock):
    """Own BEGIN/COMMIT/ROLLBACK; NEVER reuse a committed history row.

    Future caller must obtain source_received_at from real ingestion runtime
    when original_document arrives, and invoke this routine at the genuine
    new Squalincome decision. This offline prototype does NOT add such
    instrumentation; the historical price.updated_at is candle OPEN.
    All future table migrations must be authorized separately, before this
    function runs. This function does not create any schema or rows itself
    except through the provided new-history callback and the two witnesses.
    """
    if not isinstance(db, sqlite3.Connection) or db.in_transaction:
        raise ValueError("fresh_owned_sqlite_transaction_required")
    if not callable(insert_history):
        raise ValueError("new_history_insert_callback_required")
    if type(original_document) is not dict:
        raise ValueError("original_in_memory_document_required")
    if type(source_received_at) is not datetime or type(clock) is not datetime:
        raise ValueError("actual_utc_receipt_and_record_clocks_required")
    received = witness._clock(source_received_at)
    now = witness._clock(clock)
    if (now < witness._parse(protocol.START)
            or protocol.protocol_sha256() != protocol.FROZEN_PROTOCOL_SHA256):
        raise ValueError("frozen_prospective_protocol_gate")
    if received > now or received < witness._parse(protocol.START):
        raise ValueError("impossible_original_source_receipt_order")

    db.execute("BEGIN IMMEDIATE")
    try:
        changes_before = db.total_changes
        cursor = insert_history(db)
        # A SELECT, INSERT OR IGNORE, a cursor from another connection or
        # an already committed row must never be accepted as a fresh insert.
        if (not isinstance(cursor, sqlite3.Cursor)
                or cursor.connection is not db
                or cursor.rowcount != 1
                or type(cursor.lastrowid) is not int
                or cursor.lastrowid <= 0
                or db.total_changes <= changes_before):
            raise ValueError("one_new_original_history_insert_required")
        history_id = cursor.lastrowid
        if db.execute("SELECT last_insert_rowid()").fetchone()[0] != history_id:
            raise ValueError("original_history_insert_not_last")
        # Existing price proof validates original source vs locally stored
        # price document, including M15/H1/H4 rollups and observed time.
        price_result = price.capture(
            db, history_id=history_id,
            observed_document=original_document, clock=now)
        if price_result["status"] != "PRICE_ASOF_SOURCE_VERIFIED":
            raise ValueError("original_price_provenance_unverified")
        regime_result = regime.capture(
            db, history_id=history_id,
            observed_document=original_document,
            source_received_at=witness._iso(received), clock=now)
        if regime_result["status"] != "LOCALLY_WITNESSED_REGIME_RESEARCH_ONLY":
            raise ValueError("regime_source_provenance_unverified")
        db.commit()
        return {
            "schema": SCHEMA,
            "status": "LOCAL_ATOMIC_PAIR_RECORDED_RESEARCH_ONLY",
            "historyAndBothLocalProofsCommittedTogether": True,
            "sourceReceiptClockIndependentlyAttested": False,
            "originalCTraderFetchInstrumentedInLive": False,
            "originalSourceNotRefetched": True,
            "cotAndRetailProvenanceIncluded": False,
            "noHistoricalBackfill": True,
            "independentOutOfSample": False,
            "costsOrRealFillsMeasured": False,
            "tradingEdgeEstablished": False,
            "ordersEnabled": False,
            "notificationsEnabled": False,
            "brokerCalls": 0,
        }
    except BaseException:
        db.rollback()
        raise
