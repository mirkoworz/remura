"""Track B: OFFLINE-only atomic original COT+price+ingest decision rehearsal.

Only a *future* authorized research caller may provide the callback that
inserts a NEW Squalincome observation from a genuine current scan and the
SAME in-memory OHLC document evaluated by that scan. This coordinator
owns BEGIN IMMEDIATE through COMMIT or complete ROLLBACK:
  1. exactly one new history INSERT, with original cursor and rowid
  2. original COT/price evidence bundle while still in the transaction
  3. strict append-only source link to already-attested original ingest

Partial or missing local COT/price/ingest proof is a failure (NOT a trade
signal); no history record is committed in this RESEARCH rehearsal.
Do not wire this to production signals_monitor: production currently keeps
some observations even if research proofs are missing. This is an isolated
strict pilot, not a proposal to drop genuine LIVE observations.

SQLite locks and the operator-supplied clock do NOT prove a real scan
occurred. Existing COT witness is local, not CFTC-signed; cTrader parent-read
is local, not a Spotware reply; retail and CVD remain UNKNOWN. NO orders,
broker calls, network, API, notifications, outcome/edge claims, file access,
scheduler, auto migration or historic backfill.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_observation_bundle as bundle
from scripts import shark_signal_ingest_decision_link as link

SCHEMA = "remura-track-b-future-original-decision-atomicity-v1"


def record_new(db, *, insert_history, original_document, clock,
               original_retail_snapshot=None, retail_receipt_id=None,
               research_retail_inbox=False):
    """Guarantee all-or-none for a NEW pilot event on one SQLite connection.

    insert_history(db) must return the cursor for exactly ONE new
    squalincome_history INSERT. It must not commit, insert other records or
    set clocks itself. Reject INSERT OR IGNORE, a stale cursor, a borrowed
    connection, a preexisting transaction and extra callback writes.

    This protects against ACCIDENTAL backfill/reuse. Like every SQLite-only
    test, a malicious caller with direct DB access can forge its inputs;
    independent provider timestamp/authentication is still absent.
    """
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("fresh_owned_original_observation_transaction_required")
    if not callable(insert_history) or type(original_document) is not dict:
        raise ValueError("fresh_original_insert_and_ohlc_required")
    if type(clock) is not datetime:
        raise ValueError("explicit_genuine_utc_observation_clock_required")
    if type(research_retail_inbox) is not bool:
        raise ValueError("retail_inbox_opt_in_requires_boolean")
    if sum((original_retail_snapshot is not None,
            retail_receipt_id is not None,
            research_retail_inbox))>1:
        raise ValueError("retail_sources_are_mutually_exclusive")
    if retail_receipt_id is not None and (
            type(retail_receipt_id) is not int or retail_receipt_id<=0):
        raise ValueError("exact_positive_retail_receipt_id_required")
    now=witness._clock(clock)
    if (protocol.protocol_sha256()!=protocol.FROZEN_PROTOCOL_SHA256
            or now < witness._parse(protocol.START)):
        raise ValueError("frozen_prospective_study_start_or_digest_invalid")

    db.execute("BEGIN IMMEDIATE")
    try:
        baseline=db.total_changes
        cur=insert_history(db)
        if (not isinstance(cur,sqlite3.Cursor)
                or cur.connection is not db or not db.in_transaction
                or cur.rowcount != 1
                or type(cur.lastrowid) is not int or cur.lastrowid <= 0
                or db.total_changes != baseline + 1):
            raise ValueError("exactly_one_new_history_insert_required")
        hid=cur.lastrowid
        if db.execute("SELECT last_insert_rowid()").fetchone()[0]!=hid:
            raise ValueError("original_history_must_be_final_callback_insert")

        evidence=bundle.record(
            db,history_id=hid,observed_document=original_document,
            clock=now,capture_cvd_prefix=False)
        if (evidence.get("state")!="BOTH_LOCAL_PROOFS_PRESENT"
                or evidence.get("cotValueVersionMatched") is not True
                or evidence.get("priceM15H1H4SourceVerified") is not True):
            raise ValueError("strict_pilot_requires_both_original_cot_price_proofs")

        paired=link.capture(
            db,history_id=hid,original_document=original_document,
            clock=now)
        if paired.get("status")!="ORIGINAL_LOCAL_COT_PRICE_INGEST_LINKED":
            raise ValueError("original_ingest_decision_link_not_verified")
        retail_attached=False
        retail_by_receipt=False
        if original_retail_snapshot is not None:
            from scripts import shark_retail_first_seen as retail
            context=retail.attach_new(
                db,history_id=hid,original_snapshot=original_retail_snapshot,
                clock=now)
            if context["status"]!="LOCAL_RETAIL_CONTEXT_BEFORE_DECISION":
                raise ValueError("invalid_original_retail_context")
            retail_attached=True
        if retail_receipt_id is not None:
            from scripts import shark_retail_first_seen as retail
            context=retail.attach_receipt_new(
                db,history_id=hid,retail_receipt_id=retail_receipt_id,
                clock=now)
            if context["status"]!="PINNED_LOCAL_RETAIL_RECEIPT_AVAILABLE_NOT_SIGNAL_INPUT":
                raise ValueError("pinned_retail_not_available_at_original_decision")
            retail_by_receipt=True
        if research_retail_inbox:
            from scripts import shark_retail_scan_inbox as inbox
            context=inbox.attach_from_inbox(
                db,history_id=hid,clock=now)
            if context["status"]!="LOCAL_RETAIL_INBOX_PINNED_ASOF_NOT_SIGNAL_INPUT":
                raise ValueError("local_retail_inbox_source_unverifiable")
            retail_by_receipt=True
        db.commit()
        return {
            "schema":SCHEMA,
            "status":"LOCAL_NEW_OBSERVATION_AND_THREE_PROOFS_ATOMIC",
            "freshInsertCursorVerified":True,
            "originalLocalCOTPriceIngestMatched":True,
            "wholeTransactionCommittedTogether":True,
            "noRetrospectiveAttach":True,
            "retailFirstSeen":(
                "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT" if retail_by_receipt
                else "LOCAL_PRIOR_CONTEXT_NOT_SIGNAL_INPUT" if retail_attached
                else "UNKNOWN"),
            "retailReceiptBoundWithoutSourceRefetch":retail_by_receipt,
            "retailSelectedInsideOriginalDecision":research_retail_inbox,
            "retailValuesRehydrated":False,
            "retailUsedByOriginalSqualincomeSignal":False,
            "cvdCoverage":"UNKNOWN",
            "brokerReceiptExternallyAuthenticated":False,
            "cotFirstSeenIndependentlyAuthenticated":False,
            "actualProspectiveOutcomesMeasured":False,
            "statisticalEdgeEstablished":False,
            "productionObserverWired":False,
            "ordersEnabled":False,
            "notificationsEnabled":False,
            "brokerCalls":0,
        }
    except BaseException:
        db.rollback()
        raise
