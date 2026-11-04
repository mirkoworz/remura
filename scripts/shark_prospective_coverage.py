"""REMURA Track B: bounded, prospective FULL_34 recording coverage audit.

OFFLINE / explicit read-only call only: not imported by the LIVE server, not
scheduled, and never a broker query. Starts at the FIRST *recorded* full batch,
NOT inferred activation. Never treats pre-first-record data as missing, never
uses targeted scans as a full-market denominator, and never backfills gaps.

A missing calendar recording slot is NOT evidence of a missed trading setup,
a broker outage, an actual scheduled invocation or a closed/open market. A
stored unknown-market cell differs from a missing whole scan.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact

SCHEMA = "remura-track-b-prospective-recording-coverage-v1"
MINUTES_PER_SLOT = 15
SEAL_GRACE = timedelta(minutes=3)
SLOT_SPAN = timedelta(minutes=15)
MAX_DAYS = 7
MAX_EXAMPLE_MISSING = 12


def _utc_slot(at):
    return datetime.fromtimestamp(
        int(at.timestamp()) // 900 * 900, tz=timezone.utc)


def _result(status, **details):
    return {
        "schema": SCHEMA,
        "status": status,
        "scope": compact.FULL_SCOPE,
        "evidenceType": "locally_recorded_full_scan_batches_only",
        "preFirstBatchCoverageKnown": False,
        "activationTimeCertified": False,
        "calendarCadenceIsBrokerCoverage": False,
        "calendarCadenceIsMarketOpportunityCoverage": False,
        "realIngestInterferenceProven": False,
        "syntheticBackfillPerformed": False,
        "brokerCalls": 0,
        "alertsEnabled": False,
        "edgeEstablished": False,
        **details,
    }


def audit(db, *, as_of, days=1):
    """Audit only finalizable UTC slots, within at most seven calendar days.

    as_of MUST be an explicit UTC observation clock. A slot is finalized for
    this audit only once the entire 15-minute interval plus up to 3 minutes
    for sealing has elapsed. Thus an in-flight archive is not falsely absent.

    The first actually archived FULL batch anchors the earliest lower bound.
    A missing first batch cannot be reconstructed, even if a config flag
    was enabled earlier. An eligible PRICE_CONTEXT_READY is not a trade.
    No SELECT touches the original prices or COT tables.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1 <= days <= MAX_DAYS:
        raise ValueError("invalid_coverage_days")
    instant = witness._parse(as_of)
    if instant.utcoffset() != timedelta(0):
        raise ValueError("UTC_clock_required")
    cutoff = _utc_slot(instant - SLOT_SPAN - SEAL_GRACE)
    until = witness._iso(cutoff)
    # Respect any caller's existing transaction. A single read snapshot
    # prevents partial interpretation if an independent writer commits.
    started = not db.in_transaction
    if started:
        db.execute("BEGIN")
    try:
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (compact.TABLE,)).fetchone()
        if exists is None:
            return _result("NO_RESEARCH_TABLE",
                           finalizedThroughSlot=until,
                           recordingOpportunities=None,
                           verifiedFullScanSlots=None,
                           unrecordedCalendarSlots=None)
        first_row = db.execute(
            f"SELECT min(scan_slot) FROM {compact.TABLE} "
            "WHERE scope=? AND scan_slot<=?",
            (compact.FULL_SCOPE, until)).fetchone()
        earliest = first_row[0] if first_row else None
        if earliest is None:
            return _result("NO_FINALIZED_FULL_BATCH",
                           finalizedThroughSlot=until,
                           recordingOpportunities=None,
                           verifiedFullScanSlots=None,
                           unrecordedCalendarSlots=None)
        # An archived batch from an invalid timestamp must fail rather
        # than silently shifting the start of an apparent clean sample.
        first = compact._slot(earliest)
        earliest_dt = witness._parse(first)
        start_dt = max(earliest_dt, cutoff - timedelta(days=days) + SLOT_SPAN)
        first_in_window = witness._iso(start_dt)
        coverage = compact.audit_slot_coverage(
            db, first_slot=first_in_window, last_slot=until)
        rows = db.execute(
            f"SELECT scan_slot,scope_count,eligible_count,uncertain_count "
            f"FROM {compact.TABLE} WHERE scope=? "
            "AND scan_slot BETWEEN ? AND ? ORDER BY scan_slot",
            (compact.FULL_SCOPE, first_in_window, until)).fetchall()
        # All archive bytes and metadata were already verified by the
        # bounded audit above; this second query is inside its snapshot.
        observed = {slot for slot,_,_,_ in rows}
        unknown = sum(n for _,_,_,n in rows)
        eligible = sum(n for _,_,n,_ in rows)
        expected = coverage["potential15MinRecordingSlots"]
        missing_total = coverage["missingFullScanSlots"]
        examples = []
        for index in range(expected):
            if len(examples) >= MAX_EXAMPLE_MISSING:
                break
            slot = witness._iso(start_dt + SLOT_SPAN * index)
            if slot not in observed:
                examples.append(slot)
        if (len(rows) != coverage["verifiedFullScanSlots"]
                or any(count != 34 for _,count,_,_ in rows)
                or missing_total != expected-len(observed)):
            raise ValueError("coverage_snapshot_mismatch")
        return _result(
            "RECORDED_CALENDAR_COVERAGE_AUDITED",
            finalizedThroughSlot=until,
            firstKnownFullBatchSlot=first,
            examinedFromSlot=first_in_window,
            auditWindowTruncated=(start_dt > earliest_dt),
            recordingOpportunities=expected,
            verifiedFullScanSlots=len(rows),
            unrecordedCalendarSlots=missing_total,
            firstMissingSlotExamples=examples,
            omittedMissingSlotExamples=max(0, missing_total-len(examples)),
            verifiedMarketCells=34*len(rows),
            unknownMarketCellsInsideRecordedBatches=unknown,
            priceContextReadyCells=eligible,
            fullBatchIntegrityChecked=True,
            fullBatchFraction=round(len(rows)/expected, 5),
            statisticalCompletenessCertified=False,
        )
    finally:
        if started:
            db.rollback()
