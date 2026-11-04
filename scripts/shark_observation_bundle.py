"""REMURA Track B: offline-only coordinator for prospectively observed evidence.

Use only AFTER a genuine Squalincome history INSERT with cursor.rowcount == 1,
in the SAME SQLite transaction, with the in-memory OHLC document used to
calculate the original Squalincome classification. Does not patch or import
the LIVE monitor. Does NOT create tables or backfill history itself.

Two independent attestations: COT as-of value digest AND exact M15/H1/H4
price document freshness/rollups. If one cannot be demonstrated the other
may still be recorded, but the combined state is PARTIAL/N/D, not a signal
to trade or an institutional order-flow measurement.

Unexpected sqlite3 errors must bubble to the caller and abort its transaction.
Only a FUTURE, coordinated release may wire this to a backend feature flag.
"""
from __future__ import annotations

import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_signal_evidence as cot
from scripts import shark_price_asof_evidence as price

SCHEMA = "remura-research-observation-bundle-v1"


def record(db, *, history_id, observed_document, clock=None):
    """Record two distinct proofs with one real clock and transaction.

    The caller must check the squalincome_history INSERT rowcount==1.
    Provide its SAME original in-memory price document before the transaction.
    Never call on stored historical observations or reconstructed OHLC data.
    """
    if not isinstance(db, sqlite3.Connection) or not db.in_transaction:
        raise ValueError("original_observation_transaction_required")
    if type(history_id) is not int or history_id <= 0:
        raise ValueError("original_new_history_id_required")
    if db.execute("SELECT last_insert_rowid()").fetchone()[0] != history_id:
        raise ValueError("history_must_be_last_insert_before_recording")
    now = witness._clock(clock)
    cot_result = cot.capture_optional(db, history_id=history_id, clock=now)
    price_result = price.capture_optional(
        db, history_id=history_id,
        observed_document=observed_document, clock=now)
    available_cot = cot_result["status"] == "FUTURE_OBSERVATION_CERTIFIED_LOCALLY"
    available_price = price_result["status"] == "PRICE_ASOF_SOURCE_VERIFIED"
    if available_cot and available_price:
        state = "BOTH_LOCAL_PROOFS_PRESENT"
    elif available_cot or available_price:
        state = "PARTIAL_LOCAL_PROOFS"
    else:
        state = "NO_VERIFIABLE_LOCAL_PROOF"
    return {
        "schema": SCHEMA,
        "state": state,
        "cotValueVersionMatched": available_cot,
        "priceM15H1H4SourceVerified": available_price,
        "priceSourceCollectionTimeIndependentlyKnown": False,
        "h1AndH4FreshAtObservation": bool(
            available_price and price_result["m15H1H4FreshAtOriginalObservation"]),
        "last16TickVolumeComplete": bool(
            available_price and price_result["last16TickVolumeComplete"]),
        "cvdAggressorFlowMeasured": False,
        "pricedExecutionCostsKnown": False,
        "historicEventBackfillPerformed": False,
        "sourceComparisons": "live_COT_source_and_original_in_memory_OHLC_only",
        "edge": "NOT_ESTABLISHED",
        "notificationsEnabled": False,
        "ordersEnabled": False,
        "brokerCalls": 0,
    }


def summary(db):
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    ct = cot.summarize(db)
    px = price.aggregate(db)
    # Tables are append-only future-only, one logical unique key per event,
    # but counts of rows in each table must not be assumed to overlap!
    paired = db.execute(
        f"SELECT count(*) FROM {cot.TABLE} c "
        f"INNER JOIN {price.TABLE} p "
        "ON p.symbol=c.symbol AND p.report_date=c.cot_week "
        "AND p.price_time=c.price_closed_at").fetchone()[0]
    return {
        "schema": SCHEMA,
        "cotEvidenceRows": ct["total"],
        "priceEvidenceRows": px["recordedEvidence"],
        "pairedEvidenceRows": paired,
        "sourceCollectionTimeIndependentlyKnown": False,
        "tradingEdgeVerified": False,
        "brokerCalls": 0,
    }
