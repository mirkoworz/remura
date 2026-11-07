"""Track B OFFLINE: local FIRST-SEEN retail inbox to original Squalincome scan.

The genuine private Myfxbook collector and the real Squalincome observer
run in different processes. On a FUTURE authorized research rollout the
shared private SQLite first-seen table (already written by retail_once)
could be their inbox. Resolve a previously recorded receipt ID INSIDE the
same BEGIN IMMEDIATE that inserts the NEW Squalincome decision.

No latest.json read, HTTP/API, source mutation, new runner, SELECT after
commit, retrospective backfill or inference from updatedAt. Explicit
research-only, NOT imported into production signals_monitor. This proves
local temporal availability of SHA metadata, NOT access to original retail
percentages, Myfxbook provider-signed timestamps, actual signal usage,
CVD status, institutional orders, or PnL.

The synthetic caller can supply an arbitrary clock: SQLite alone cannot
certify a genuine live decision. The real observer does not yet call this.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3

from scripts import shark_cot_asof_witness as clocks
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_retail_first_seen as retail

SCHEMA="remura-track-b-retail-shared-sqlite-atomic-original-inbox-v1"


def attach_from_inbox(db, *, history_id, clock):
    """Select and pin latest as-of local receipt in the NEW event transaction.

    The parent coordinator must already own a fresh BEGIN IMMEDIATE and
    have just inserted exactly one history row + COT/price/ingest proof.
    BEGIN IMMEDIATE prevents a concurrent Myfxbook writer interleaving
    between the source selection and the original decision's COMMIT.
    Missing retail is a FAIL of the strict RESEARCH opt-in, never a
    reason for production to discard legitimate core observations.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("original_signal_immediate_transaction_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("new_history_row_id_required")
    if type(clock) is not datetime:
        raise ValueError("explicit_original_utc_scan_clock_required")
    scan=clocks._clock(clock)
    if protocol.protocol_sha256()!=protocol.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_cvd_protocol_mismatch")
    row=db.execute(
        "SELECT symbol,observed_at FROM squalincome_history WHERE id=?",
        (history_id,)
    ).fetchone()
    if row is None:
        raise ValueError("original_signal_row_missing")
    symbol,observed_string=row
    observed=clocks._parse(observed_string)
    if (symbol not in retail.PILOT
            or not clocks._parse(protocol.START)<=observed<=scan
            or scan-observed>retail.DECISION_GRACE):
        raise ValueError("not_a_new_pilot_observation")
    original=db.execute(
        "SELECT 1 FROM research_signal_ingest_source_links "
        "WHERE history_id=?",(history_id,)
    ).fetchone()
    if original is None:
        raise ValueError("original_cot_price_ingest_proof_missing")
    # Canonical UTC times in first-seen table use six fractional digits,
    # but some fixture signal clocks are Z without fractions. The safer
    # approach is NOT a textual timestamp range, but explicit UTC parse
    # of each bounded local pilot receipt. Max 15k research rows globally.
    choices=db.execute(
        f"SELECT id,recorded_at FROM {retail.TABLE} "
        "WHERE symbol=? ORDER BY id DESC",(symbol,)
    ).fetchall()
    selected=None
    for rid,recorded in choices:
        if clocks._parse(recorded)<=observed:
            selected=rid
            break
    if selected is None:
        raise ValueError("retail_prior_receipt_inbox_empty")
    # The actual strict attached-source routine validates digest, symbol,
    # source/read/record clock ordering, stale horizon, superseding rows,
    # original COT+price link and duplicate attachment. No privileged bypass.
    result=retail.attach_receipt_new(
        db,history_id=history_id,retail_receipt_id=selected,
        clock=scan)
    if result["status"]!="PINNED_LOCAL_RETAIL_RECEIPT_AVAILABLE_NOT_SIGNAL_INPUT":
        raise ValueError("retail_provenance_handoff_unverifiable")
    return {
        "schema":SCHEMA,
        "status":"LOCAL_RETAIL_INBOX_PINNED_ASOF_NOT_SIGNAL_INPUT",
        "selectedInsideOriginalDecisionTransaction":True,
        "sameSQLiteWriteTransaction":True,
        "originalRetailValuesAvailable":False,
        "providerTimestampIndependentlyTrusted":False,
        "originalSignalUsedRetail":False,
        "futureReceiptPreventedFromLeakingBackward":True,
        "sourceFileOrBrokerRefetched":False,
        "cvdCoverage":"UNKNOWN",
        "realOOSOrCostsKnown":False,
        "statisticalEdgeEstablished":False,
        "liveObserverWired":False,
        "additionalAPICalls":0,
        "ordersEnabled":False,
        "notificationsEnabled":False,
    }
