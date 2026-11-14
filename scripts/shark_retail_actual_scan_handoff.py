"""Track B OFFLINE hook for a fresh INSERT by the ACTUAL scanner.

No standalone history INSERT, no after-commit linkage, no latest.json read,
no extra provider calls. Only a future *explicit* pilot-mode scanner may call
this function. The normal LIVE scan_once entrypoint never imports it.

A complete local COT/price/ingest source chain and a previously recorded
Myfxbook first-seen receipt must exist. All four links are written inside
the SAME SQLite write transaction as the new original history row.
Fail closed on missing proof; do not invoke on the production observer.
Local clock and digest are not provider-signed evidence. No CVD or PnL.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3

from scripts import shark_observation_bundle as evidence
from scripts import shark_signal_ingest_decision_link as source
from scripts import shark_retail_scan_inbox as inbox

SCHEMA="remura-track-b-actual-original-scan-retail-handoff-v1"


def attach_new(db, *, history_id, observed_document, clock):
    if (not isinstance(db,sqlite3.Connection) or not db.in_transaction
            or type(history_id) is not int or history_id<=0
            or type(clock) is not datetime
            or type(observed_document) is not dict):
        raise ValueError("owned_new_original_observation_required")
    if db.execute("SELECT last_insert_rowid()").fetchone()[0]!=history_id:
        raise ValueError("history_must_be_last_original_insert")
    present=db.execute(
        "SELECT symbol,observed_at FROM squalincome_history WHERE id=?",
        (history_id,)).fetchone()
    if present is None:
        raise ValueError("fresh_original_history_absent")
    from scripts import shark_cot_asof_witness as clocks
    if clocks._parse(present[1])!=clocks._clock(clock):
        raise ValueError("original_history_clock_mismatch")
    cot_price=evidence.record(
        db,history_id=history_id,observed_document=observed_document,
        clock=clock,capture_cvd_prefix=False)
    if (cot_price.get("state")!="BOTH_LOCAL_PROOFS_PRESENT"
            or cot_price.get("cotValueVersionMatched") is not True
            or cot_price.get("priceM15H1H4SourceVerified") is not True):
        raise ValueError("original_cot_price_proof_incomplete")
    linked=source.capture(
        db,history_id=history_id,original_document=observed_document,
        clock=clock)
    if linked.get("status")!="ORIGINAL_LOCAL_COT_PRICE_INGEST_LINKED":
        raise ValueError("original_ingest_evidence_incomplete")
    retail=inbox.attach_from_inbox(db,history_id=history_id,clock=clock)
    if retail.get("status")!="LOCAL_RETAIL_INBOX_PINNED_ASOF_NOT_SIGNAL_INPUT":
        raise ValueError("original_retail_receipt_incomplete")
    return {
        "schema":SCHEMA,
        "status":"ORIGINAL_SCANNER_RETAIL_INBOX_LINKED",
        "sameOriginalTransaction":True,
        "sourceRefetched":False,
        "originalSignalUsesRetail":False,
        "providerClocksIndependentlyAuthenticated":False,
        "cvdEvidence":"UNKNOWN",
        "tradingEdgeEstablished":False,
        "notificationsEnabled":False,
        "ordersEnabled":False,
        "apiCallsAdded":0,
    }
