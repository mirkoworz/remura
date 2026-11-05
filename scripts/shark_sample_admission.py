"""REMURA Track B: conservative research-sample admission gate (OFFLINE).

Reads only already-stored, immutable FULL_34 batches, the LOCAL first-periodic
invocation, and observed-only failures. Never reads mutable current COT/prices
to manufacture past evidence, never joins a future COT revision to an older
price, never imputes missing scan slots, never backfills CVD divergences.

A locally valid price-only observation is descriptive research material, NOT
an institutional cohort, net-PnL label, out-of-sample test, or trade signal.
For those stronger claims we still require a causally joined, locally
witnessed COT value at observation, actual CVD detectedAt where applicable,
an independently frozen outcome, and costs/spread/slippage. These are NOT
present in the compact price-only ledger, so all institutional and net
walk-forward admissions fail closed, irrespective of sample size.

This module has no server/collector/cron/HTTP entrypoint, DB writes, secrets,
raw OHLC output, account names or broker calls. Explicit READ-only snapshot.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact
from scripts import shark_prospective_coverage as coverage

SCHEMA = "remura-track-b-scientific-sample-admission-v1"
MAX_DAYS = 7
MAX_FULL_BATCHES = 7 * 96
BATCH_TRIGGERS = ("research_compact_no_update",
                  "research_compact_no_delete")
NO_EDGE_REASON = (
    "NO_CAUSAL_JOINED_COT_VERSION_CVD_EVENT_EXECUTION_COSTS_AND_OOS_OUTCOME"
)
CATEGORY = {
    "PRICE_UNIVERSE_NOT_RECORDED": "MARKET_OBSERVATION_UNKNOWN",
    "PRICE_QUALITY_BLOCKED": "PRICE_QUALITY_NOT_READY",
    "PRICE_NUMERIC_AMBIGUOUS": "PRICE_DIRECTION_NUMERIC_AMBIGUOUS",
    "PRICE_NO_TREND": "PRICE_CONTEXT_HAS_NO_TREND",
}


def _report(status, audit, **fields):
    return {
        "schema": SCHEMA,
        "status": status,
        "source": "validated_compact_full_34_local_observations",
        "admissionPolicy": "DESCRIPTIVE_PRICE_ONLY_NOT_TRADING",
        "firstInvocationLocallyWitnessed": bool(
            audit.get("firstEnabledScannerInvocationWitnessed", False)),
        "calculatedFromRetrospectiveOHLC": False,
        "unknownCalendarSlotsAssignedPositiveOrNegativeLabels": False,
        "calendarGapsEquatedToObservedErrors": False,
        "privateEventDetailsReturned": False,
        "localHashIsExternalMarketAttestation": False,
        "cvdAggressorDeltaMeasured": False,
        "cvdDivergenceDetectionTimeWitnessed": False,
        "priceCollectionTimeIndependentlyCertified": False,
        "institutionalCohortsAdmissible": 0,
        "netWalkForwardOutcomesAdmissible": 0,
        "cvdDivergenceEventsAdmissible": 0,
        "institutionalAdmissionBlocker": NO_EDGE_REASON,
        "spreadSlippageExecutionCostsObserved": False,
        "independentOutOfSampleValidated": False,
        "brokerCalls": 0,
        "ordersEnabled": False,
        "notificationsEnabled": False,
        "tradingEdgeEstablished": False,
        **fields,
    }


def audit(db, *, as_of, days=1):
    """Classify immutable FULL batches in a <=7-day UTC read snapshot.

    Never interpret a missing witness/table as zero candidate observations.
    The reference UTC clock must be explicit, not guessed from stored data.
    All evidence is checked *as known by* as_of, not reconstructed later.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1 <= days <= MAX_DAYS:
        raise ValueError("invalid_admission_window")
    at = witness._parse(as_of)
    began = not db.in_transaction
    if began:
        db.execute("BEGIN")
    try:
        slot_report = coverage.audit(db, as_of=witness._iso(at), days=days)
        observed_failure = slot_report["observedScanFailures"]
        common = {
            "finalizedThroughSlot": slot_report["finalizedThroughSlot"],
            "recordingOpportunities": slot_report["recordingOpportunities"],
            "verifiedFullScanSlots": slot_report["verifiedFullScanSlots"],
            "unrecordedCalendarSlots": slot_report["unrecordedCalendarSlots"],
            "observedFailures": observed_failure,
            "fullErrorTelemetryCertified": False,
        }
        if slot_report["status"] in (
                "NO_RESEARCH_TABLE", "NO_FINALIZED_FULL_BATCH",
                "NO_FINALIZED_EXPECTED_SLOTS_AFTER_START"):
            return _report("NO_FINALIZED_ADMISSIBLE_POPULATION",
                           slot_report,
                           fullBatchMarketCells=None,
                           priceContextDescriptiveCandidates=None,
                           priceContextWithCompleteTickVolume=None,
                           excludedMarketCells=None,
                           exclusionReasons=None, **common)

        # A first-invocation witness can survive an aborted first scan
        # without creating the compact table at all. Its calendar gaps are
        # observable, but there is NO stored population to admit.
        batch_table=db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (compact.TABLE,)).fetchone()
        if batch_table is None:
            return _report("NO_FINALIZED_PRICE_BATCH_WITH_WITNESSED_START",
                           slot_report,fullBatchMarketCells=None,
                           priceContextDescriptiveCandidates=None,
                           priceContextWithCompleteTickVolume=None,
                           excludedMarketCells=None,
                           exclusionReasons=None,**common)

        # Without a first-invocation witness the first stored batch is NOT
        # proof of when research was enabled. Old standalone/offline archives
        # can be inspected for integrity but never admitted to the sample.
        if not slot_report["firstEnabledScannerInvocationWitnessed"]:
            return _report("START_WITNESS_UNAVAILABLE",
                           slot_report, fullBatchMarketCells=(
                               34 * slot_report["verifiedFullScanSlots"]),
                           priceContextDescriptiveCandidates=None,
                           priceContextWithCompleteTickVolume=None,
                           excludedMarketCells=None,
                           exclusionReasons={"START_WITNESS_UNAVAILABLE": (
                               34 * slot_report["verifiedFullScanSlots"])},
                           **common)

        found = {name for (name,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' "
            "AND tbl_name=?", (compact.TABLE,))}
        if not set(BATCH_TRIGGERS).issubset(found):
            raise ValueError("compact_immutability_triggers_missing")

        start = slot_report["examinedFromSlot"]
        end = slot_report["finalizedThroughSlot"]
        data = db.execute(
            f"SELECT scan_slot, sealed_at, payload_sha256, payload_zlib "
            f"FROM {compact.TABLE} WHERE scope=? "
            "AND scan_slot BETWEEN ? AND ? ORDER BY scan_slot",
            (compact.FULL_SCOPE, start, end)).fetchall()
        if (len(data) > MAX_FULL_BATCHES
                or len(data) != slot_report["verifiedFullScanSlots"]):
            raise ValueError("unbounded_or_mismatched_batches")

        counts = Counter()
        descriptive = 0
        volume_complete = 0
        admission_time = witness._parse(
            slot_report["firstEnabledScannerInvocationAt"])

        # coverage.audit already calls compact.verify for EVERY FULL slot,
        # and its SHA/metadata/34-market verification happens in this very
        # same READ transaction. Decode a second time only for bounded,
        # row-level classification; raw data never leaves this function.
        for slot, sealed, sha, zipped in data:
            if (witness._parse(sealed) > at or
                    witness._parse(sealed) < witness._parse(slot)):
                raise ValueError("batch_time_invalid_for_historical_asof")
            if not isinstance(sha, str):
                raise ValueError("batch_sha_invalid")
            doc = compact._decode(zipped, sha)
            rows = doc.get("observations")
            if not isinstance(rows, list) or len(rows) != 34:
                raise ValueError("full_denominator_missing")
            for row in rows:
                checked = compact._validate_row(row, slot)
                state = checked[4]
                observed = witness._parse(checked[2])
                recorded = witness._parse(checked[3])
                if observed > at or recorded > at:
                    raise ValueError("future_observation_leaks_into_audit")
                if observed < admission_time:
                    counts["OBSERVED_BEFORE_FIRST_INVOCATION"] += 1
                elif state != "PRICE_CONTEXT_READY":
                    counts[CATEGORY.get(state, "UNCLASSIFIED_PRICE_STATE")] += 1
                elif (checked[5] != "verified" or checked[6] != "recent"
                      or checked[7] is None or checked[13] is None):
                    # Redundant defensive check; status alone is not proof.
                    counts["MISSING_FRESH_PRICE_SOURCE_PROOF"] += 1
                else:
                    descriptive += 1
                    if checked[14] == 1:
                        volume_complete += 1
                    else:
                        counts["PRICE_READY_BUT_TICK_VOLUME_INCOMPLETE"] += 1

        total = len(data)*34
        excluded = total-descriptive
        if (descriptive < 0 or volume_complete > descriptive
                or sum(v for k,v in counts.items()
                       if k != "PRICE_READY_BUT_TICK_VOLUME_INCOMPLETE"
                       ) != excluded):
            raise ValueError("nonconserving_admission_denominator")

        return _report(
            "PRICE_ONLY_DESCRIPTIVE_AUDITED_INSTITUTIONAL_GATE_CLOSED",
            slot_report,
            fullBatchMarketCells=total,
            priceContextDescriptiveCandidates=descriptive,
            priceContextWithCompleteTickVolume=volume_complete,
            priceContextWithoutCompleteTickVolume=(
                descriptive-volume_complete),
            excludedMarketCells=excluded,
            exclusionReasons=dict(sorted(counts.items())),
            fullBatchSHAAndMarketScopeVerified=True,
            firstCompletePostActivationSlot=(
                slot_report["examinedFromSlot"]),
            sameSourceValueVersionsForCOTWitnessedInTheseRows=False,
            marketOutcomesIndependentlyFrozen=False,
            **common,
        )
    finally:
        if began:
            db.rollback()
