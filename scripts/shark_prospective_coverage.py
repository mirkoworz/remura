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
from scripts import shark_first_invocation as first_gate

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
    """Audit finalized UTC slots, with an immutable first-invocation witness.

    With no witness, retains the conservative FIRST STORED full-batch anchor:
    any period before that batch stays N/D. With a valid first-invocation
    witness, expect calendar recording slots ONLY FROM the first 15-minute
    boundary ON/AFTER that observed invocation. An initial partial slot is
    excluded rather than retroactively treated as a scheduled requirement.

    Witness is local host-clock evidence, NOT an independently notarized
    timestamp of a configuration change. Gaps do not prove a skipped job,
    broker/ingest outage, open market or lost trading opportunity. All
    queries run in the same bounded read-only snapshot, no backfill.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1<=days<=MAX_DAYS:
        raise ValueError("invalid_coverage_days")
    instant=witness._parse(as_of)
    cutoff=_utc_slot(instant-SLOT_SPAN-SEAL_GRACE)
    until=witness._iso(cutoff)
    started=not db.in_transaction
    if started:
        db.execute("BEGIN")
    try:
        activation=first_gate.read(db,at=instant)
        activation_time=witness._parse(activation) if activation else None
        activation_details={
            "firstEnabledScannerInvocationWitnessed":activation is not None,
            "firstEnabledScannerInvocationAt":activation,
            "configurationSwitchTimeKnown":False,
            "continuousEnablementEstablished":False,
            "externallyNotarizedActivation":False,
            "asOfClockExternallyVerified":False,
        }
        table=db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (compact.TABLE,)).fetchone()
        if not table and activation is None:
            return _result("NO_RESEARCH_TABLE",
                           finalizedThroughSlot=until,
                           recordingOpportunities=None,
                           verifiedFullScanSlots=None,
                           unrecordedCalendarSlots=None,
                           **activation_details)
        first=None
        if table:
            first_row=db.execute(
                f"SELECT min(scan_slot) FROM {compact.TABLE} "
                "WHERE scope=? AND scan_slot<=?",
                (compact.FULL_SCOPE,until)).fetchone()
            if first_row and first_row[0] is not None:
                first=compact._slot(first_row[0])
        if activation is None and first is None:
            return _result("NO_FINALIZED_FULL_BATCH",
                           finalizedThroughSlot=until,
                           recordingOpportunities=None,
                           verifiedFullScanSlots=None,
                           unrecordedCalendarSlots=None,
                           **activation_details)
        if activation_time is not None:
            # Never include an incomplete first slot merely because the
            # feature flag was observed AFTER that slot started.
            first_slot=_utc_slot(activation_time)
            if first_slot<activation_time:
                first_slot+=SLOT_SPAN
        else:
            # Legacy standalone/offline research archives have no reliable
            # activation event, so pre-first-batch intervals are unknown.
            first_slot=witness._parse(first)
        start_dt=max(first_slot,cutoff-timedelta(days=days)+SLOT_SPAN)
        if start_dt>cutoff:
            return _result(
                "NO_FINALIZED_EXPECTED_SLOTS_AFTER_START"
                if activation else "NO_FINALIZED_FULL_BATCH",
                finalizedThroughSlot=until,
                recordingOpportunities=None,
                verifiedFullScanSlots=None,
                unrecordedCalendarSlots=None,
                firstKnownFullBatchSlot=first,
                **activation_details)
        first_in_window=witness._iso(start_dt)
        if table:
            coverage=compact.audit_slot_coverage(
                db,first_slot=first_in_window,last_slot=until)
            rows=db.execute(
                f"SELECT scan_slot,scope_count,eligible_count,uncertain_count "
                f"FROM {compact.TABLE} WHERE scope=? "
                "AND scan_slot BETWEEN ? AND ? ORDER BY scan_slot",
                (compact.FULL_SCOPE,first_in_window,until)).fetchall()
            expected=coverage["potential15MinRecordingSlots"]
            missing_total=coverage["missingFullScanSlots"]
            if len(rows)!=coverage["verifiedFullScanSlots"]:
                raise ValueError("coverage_snapshot_mismatch")
        else:
            rows=[]
            expected=int((cutoff-start_dt).total_seconds()//900)+1
            missing_total=expected
        observed={slot for slot,_,_,_ in rows}
        if (len(observed)!=len(rows)
                or any(count!=34 for _,count,_,_ in rows)
                or missing_total!=expected-len(observed)):
            raise ValueError("coverage_snapshot_mismatch")
        examples=[]
        for index in range(expected):
            if len(examples)>=MAX_EXAMPLE_MISSING:
                break
            slot=witness._iso(start_dt+SLOT_SPAN*index)
            if slot not in observed:
                examples.append(slot)
        return _result(
            "WITNESSED_CALENDAR_COVERAGE_AUDITED" if activation
            else "RECORDED_CALENDAR_COVERAGE_AUDITED",
            finalizedThroughSlot=until,
            firstKnownFullBatchSlot=first,
            examinedFromSlot=first_in_window,
            auditWindowTruncated=(start_dt>first_slot),
            recordingOpportunities=expected,
            verifiedFullScanSlots=len(rows),
            unrecordedCalendarSlots=missing_total,
            firstMissingSlotExamples=examples,
            omittedMissingSlotExamples=max(0,missing_total-len(examples)),
            verifiedMarketCells=34*len(rows),
            unknownMarketCellsInsideRecordedBatches=sum(x[3] for x in rows),
            priceContextReadyCells=sum(x[2] for x in rows),
            fullBatchIntegrityChecked=True,
            fullBatchFraction=round(len(rows)/expected,5),
            statisticalCompletenessCertified=False,
            **activation_details,
        )
    finally:
        if started:
            db.rollback()
