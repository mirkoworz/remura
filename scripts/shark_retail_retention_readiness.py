"""Track B OFFLINE read-only guard: retained original decisions vs retail evidence.

The research source tables are append-only, but Squalincome's original
history is bounded by time and per-market row count. An orphaned FIRST-SEEN
link cannot be treated as a verified original decision by read_linked().

ONLY SQLite SELECT / sqlite_master queries; no provider calls, no service,
no migration, no file writes, no prospective-study authorization or signal.
The row-count projections are capacity SCENARIOS, not observed market rates.
"""
from __future__ import annotations

import math
import sqlite3

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_signal_ingest_decision_link as ingest
from scripts import shark_retail_preregistered_protocol as protocol

SCHEMA="remura-track-b-original-history-retention-readiness-v1"
HISTORY="squalincome_history"
EXPECTED_PILOTS=2
CANDLE_MINUTES=15


def _present(db,name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def _orphan_count(db, link_table):
    return db.execute(
        f"SELECT count(*) FROM {link_table} l "
        f"WHERE NOT EXISTS (SELECT 1 FROM {HISTORY} h "
        "WHERE h.id=l.history_id)"
    ).fetchone()[0]


def audit(db, *, history_keep_days, history_max_per_symbol,
          retail_cycle_minutes=20):
    """Describe whether ORIGINAL proof retention can support frozen retail folds.

    No source payloads or symbols are exported. A hypothetical policy pass
    NEVER authorizes a LIVE release, deployment or profitability claim.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if any(type(x) is not int or x<=0 for x in
           (history_keep_days,history_max_per_symbol,retail_cycle_minutes)):
        raise ValueError("positive_integer_retention_policy_required")
    if protocol.fingerprint()!=protocol.FROZEN_RULES_SHA256:
        raise ValueError("frozen_retail_protocol_mismatch")
    weeks=protocol.FROZEN_RULES["fold_weeks"]
    required_days=7*sum(weeks[k] for k in ("train","validation","test"))
    original_present=_present(db,HISTORY)
    retail_link_present=_present(db,retail.LINK)
    original_ingest_link_present=_present(db,ingest.TABLE)
    retail_receipt_present=_present(db,retail.TABLE)
    numeric_present=_present(db,numeric.TABLE)
    missing=[name for name,exists in (
        (HISTORY,original_present),
        (retail.LINK,retail_link_present),
        (ingest.TABLE,original_ingest_link_present),
        (retail.TABLE,retail_receipt_present),
        (numeric.TABLE,numeric_present)) if not exists]
    orphan_retail=(_orphan_count(db,retail.LINK)
                   if original_present and retail_link_present else None)
    orphan_ingest=(_orphan_count(db,ingest.TABLE)
                   if original_present and original_ingest_link_present else None)
    # Both market receipts are generated once per successful local cycle,
    # independent of whether Squalincome produces a new decision.
    projected_receipts=(EXPECTED_PILOTS*math.ceil(
        required_days*24*60/retail_cycle_minutes))
    # Upper bound SCENARIO if a symbol gets one original update per M15.
    max_decision_rows_scenario=math.ceil(
        required_days*24*60/CANDLE_MINUTES)
    retention_short=history_keep_days<required_days
    history_cap_short=history_max_per_symbol<max_decision_rows_scenario
    receipt_cap_short=retail.MAX_ROWS<projected_receipts
    numeric_cap_short=numeric.MAX_FEATURE_ROWS<projected_receipts
    orphan_found=(orphan_retail is not None and orphan_retail>0) or (
        orphan_ingest is not None and orphan_ingest>0)
    no_go=bool(missing or retention_short or history_cap_short
               or receipt_cap_short or numeric_cap_short or orphan_found)
    return {
        "schema":SCHEMA,
        "status":("NO_GO_ORIGINAL_PROOF_RETENTION_OR_CAPACITY"
                  if no_go else "POLICY_SCENARIO_ONLY_NOT_LIVE_AUTHORIZATION"),
        "frozenRetailProtocolIntact":True,
        "frozenRetailStudyWeeks":required_days//7,
        "studyDaysRequired":required_days,
        "configuredOriginalHistoryDays":history_keep_days,
        "originalHistoryMaxRowsPerMarket":history_max_per_symbol,
        "hypotheticalOriginalDecisionIntervalMinutes":CANDLE_MINUTES,
        "scenarioOriginalDecisionRowsPerMarket":max_decision_rows_scenario,
        "scenarioRetailCollectorCycleMinutes":retail_cycle_minutes,
        "scenarioTwoMarketReceiptRows":projected_receipts,
        "maxResearchFirstSeenReceiptRows":retail.MAX_ROWS,
        "maxResearchNumericRows":numeric.MAX_FEATURE_ROWS,
        "originalHistoryDaysShorterThanStudy":retention_short,
        "originalHistoryRowCapBelowQuarterHourScenario":history_cap_short,
        "retailReceiptCapBelowCollectorScenario":receipt_cap_short,
        "retailNumericCapBelowCollectorScenario":numeric_cap_short,
        "missingResearchTables":tuple(sorted(missing)),
        "orphanedRetailHistoryLinks":orphan_retail,
        "orphanedIngestHistoryLinks":orphan_ingest,
        "sourceRowCountsNotProjectionOfOriginalDecisions":True,
        "historyLinkIsNotRecoveredFromLaterJSON":True,
        "liveCapacityOrCostVerified":False,
        "offHostRecoverabilityVerified":False,
        "retailFirstSeenLiveAuthorized":False,
        "realOutcomesOrCostsRead":0,
        "edgeEstablished":False,
        "newAPICalls":0,
        "sqliteWrites":0,
    }
