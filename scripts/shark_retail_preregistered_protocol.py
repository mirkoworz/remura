"""Track B: frozen RULES for a future prospective paired-retail study.

This freezes a deterministic calendar rule BEFORE future outcome analysis,
not an authorized study, actual enrollment, a fitted model, or a CVD change.
Only a synthetic METADATA eligibility rehearsal is allowed here: rows must
not contain prices, outcomes, Myfxbook metrics, account/broker details or PnL.
The upstream genuine receipt verification must precede any future adapter;
untrusted row fields are NOT authentication of a provider or local clock.

Never imported by LIVE, never trains/scores signals or accesses SQLite, file
data, Oracle, APIs, secrets, jobs or broker feeds. No background collection.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json

SCHEMA = "remura-retail-preregistered-paired-design-v1"
FROZEN_RULES = {
    "id": "remura-retail-paired-prospective-v1",
    "pilot": ["EURUSD", "XAUUSD"],
    "start_rule": "first_utc_monday_at_least_7_days_after_external_authorization",
    "fold_weeks": {"train": 12, "validation": 8, "test": 8},
    "embargo_hours": 24,
    "required_complete_decisions_per_fold": 30,
    "required_independent_cot_weeks_per_fold": 8,
    "inferential_cot_weeks_minimum_test": 20,
    "primary_metric": "untouched_test_paired_log_loss_improvement_A_minus_B",
    "baseline_features": [
        "cot_side", "cot_weekly", "price_side", "h4_side", "h1_side", "m15_side"
    ],
    "additional_retail_features": [
        "lPct", "sPct", "lLots", "sLots", "lPos", "sPos"
    ],
    "model": "separate_L2_logistic_fixed_C1_train_only_standardization",
    "target": "24h_direction_outcome_only_after_actual_evaluated_at",
    "costs": "observed_spread_slippage_fees_required_for_secondary_net_R_not_imputed",
    "out_of_sample": "test_once_after_train_validation_hyperparameters_and_features_frozen",
    "missing": "UNKNOWN_exclude_from_paired_aggregate_report_denominator_no_zero_fill",
    "clusters": "UTC_COT_publication_week_market_shared_and_current_release_sha_quarantine",
    "no_backfill": True,
    "not_original_signal_input": True,
    "no_live_activation": True,
    "cvd_protocol_unchanged": True,
}
# Independent frozen reference in tests; never silently replace when changing
# the rules. A protocol amendment MUST be a distinct, explicitly reviewed
# protocol version before any real independent outcomes are unblinded.
FROZEN_RULES_SHA256 = "6c4413a9851233e0785cb86eb30a03a22e8fa0a20efd4385c22638cba2ba4f6e"
FOLDS = ("train", "validation", "test")
UTC = timezone.utc
MAX_META_ROWS = 10000
REQUIRED_KEYS = frozenset((
    "event_id", "symbol", "observed_at", "evaluated_at",
    "source_recorded_at", "source_linked_at", "cot_week_monday",
    "cot_current_receipts", "retail_state",
))
RETAIL_STATES = frozenset((
    "COMPLETE_RETAIL_AT_FIRST_SEEN", "UNKNOWN_MISSING",
    "PARTIAL_OR_MISSING_AGGREGATES",
))


def fingerprint():
    payload = json.dumps(FROZEN_RULES, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _utc(value):
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError("explicit_timezone_aware_clock_required")
    offset = value.utcoffset()
    if offset is None:
        raise ValueError("explicit_timezone_aware_clock_required")
    return value.astimezone(UTC)


def _iso(value):
    return _utc(value).isoformat().replace("+00:00", "Z")


def frozen_calendar(authorized_at):
    """Only a hypothetical calendar on explicitly supplied authorization.

    Actual authorization, backups, provider consent and quota approval can
    NOT be conferred by calling this function.
    """
    if fingerprint() != FROZEN_RULES_SHA256:
        raise ValueError("retail_protocol_fingerprint_modified")
    if authorized_at is None:
        return {
            "status": "BLOCKED_NO_AUTHORIZED_RETAIL_START",
            "releaseAuthorized": False, "liveEnabled": False,
            "actualAuthorizationVerified": False,
            "protocolSha256": FROZEN_RULES_SHA256,
            "scoreOrOutcomeProduced": False,
        }
    allowed = _utc(authorized_at) + timedelta(days=7)
    # Next Monday 00:00 UTC strictly not earlier than the +7 day cutoff.
    monday = (allowed - timedelta(days=allowed.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    if monday < allowed:
        monday += timedelta(days=7)
    train_end = monday + timedelta(weeks=FROZEN_RULES["fold_weeks"]["train"])
    valid_end = train_end + timedelta(weeks=FROZEN_RULES["fold_weeks"]["validation"])
    test_end = valid_end + timedelta(weeks=FROZEN_RULES["fold_weeks"]["test"])
    return {
        "status": "HYPOTHETICAL_OFFLINE_CALENDAR_ONLY",
        "trainStartUtc": _iso(monday),
        "validationStartUtc": _iso(train_end),
        "testStartUtc": _iso(valid_end),
        "testEndUtc": _iso(test_end),
        "releaseAuthorized": False,
        "liveEnabled": False,
        "actualAuthorizationVerified": False,
        "testOutcomesUnblinded": False,
        "protocolSha256": FROZEN_RULES_SHA256,
        "scoreOrOutcomeProduced": False,
    }


def _fold(observed, bounds):
    start, train_end, valid_end, test_end = bounds
    if start <= observed < train_end:
        return "train"
    if train_end <= observed < valid_end:
        return "validation"
    if valid_end <= observed < test_end:
        return "test"
    return None


def audit_synthetic_metadata(rows, *, authorized_at=None, as_of):
    """A leakage-resistant fold/count rehearsal, NOT genuine enrollment.

    Rows are exact-schema synthetic metadata, not sourced from LIVE. The
    eligibility counts cannot establish independent outcomes, provider
    authenticity or statistical significance.
    """
    calendar = frozen_calendar(authorized_at)
    if calendar["status"] == "BLOCKED_NO_AUTHORIZED_RETAIL_START":
        return dict(calendar, status="BLOCKED_NO_AUTHORIZED_RETAIL_START",
                    metadataRowsProcessed=0)
    cutoff = _utc(as_of)
    if type(rows) not in (tuple, list) or len(rows) > MAX_META_ROWS:
        raise ValueError("bounded_synthetic_metadata_sequence_required")
    bounds = tuple(datetime.fromisoformat(calendar[key].replace("Z", "+00:00"))
                   for key in ("trainStartUtc", "validationStartUtc",
                               "testStartUtc", "testEndUtc"))
    embargo = timedelta(hours=FROZEN_RULES["embargo_hours"])
    counts = Counter()
    denominator = Counter()
    candidate = []
    ids = set()
    for row in rows:
        if type(row) is not dict or set(row) != REQUIRED_KEYS:
            raise ValueError("exact_non_sensitive_metadata_schema_required")
        ident = row["event_id"]
        if type(ident) is not int or ident <= 0 or ident in ids:
            counts["REJECTED_DUPLICATE_OR_INVALID_EVENT"] += 1
            continue
        ids.add(ident)
        if row["symbol"] not in FROZEN_RULES["pilot"]:
            counts["REJECTED_NONPILOT_MARKET"] += 1
            continue
        observed = _utc(row["observed_at"])
        if observed > cutoff:
            counts["UNKNOWN_FUTURE_OBSERVATION_ASOF"] += 1
            continue
        fold = _fold(observed, bounds)
        if fold is None:
            counts["OUTSIDE_LOCKED_CALENDAR"] += 1
            continue
        denominator[fold] += 1
        if row["retail_state"] != "COMPLETE_RETAIL_AT_FIRST_SEEN":
            if row["retail_state"] not in RETAIL_STATES:
                counts["REJECTED_UNKNOWN_RETAIL_STATUS"] += 1
            else:
                counts[row["retail_state"]] += 1
            continue
        recorded = _utc(row["source_recorded_at"])
        linked = _utc(row["source_linked_at"])
        week = _utc(row["cot_week_monday"])
        if (recorded > observed
                or not observed <= linked <= observed + timedelta(seconds=30)):
            counts["REJECTED_RETAIL_TIMING"] += 1
            continue
        if (week.weekday() != 0 or any((week.hour, week.minute, week.second,
                                        week.microsecond))
                or week > observed):
            counts["REJECTED_COT_WEEK_CLOCK"] += 1
            continue
        receipts = row["cot_current_receipts"]
        if (type(receipts) not in (tuple, list) or not (1 <= len(receipts) <= 4)
                or any(type(x) is not str or len(x) != 64 or
                       any(c not in "0123456789abcdef" for c in x)
                       for x in receipts)
                or len(set(receipts)) != len(receipts)):
            counts["REJECTED_COT_RECEIPTS"] += 1
            continue
        # Keep the COT release calendar week indivisible across all symbols.
        if _fold(week, bounds) != fold:
            counts["QUARANTINED_COT_WEEK_SPANS_FOLD"] += 1
            continue
        fold_end = bounds[FOLDS.index(fold) + 1]
        if fold != "train" and observed < bounds[FOLDS.index(fold)] + embargo:
            counts["EMBARGO_AFTER_BOUNDARY"] += 1
            continue
        evaluated_at = row["evaluated_at"]
        if evaluated_at is None:
            counts["UNKNOWN_EVALUATION_CLOCK"] += 1
            continue
        evaluated = _utc(evaluated_at)
        if evaluated < observed:
            counts["REJECTED_OUTCOME_PRECEDES_DECISION"] += 1
            continue
        if evaluated > cutoff:
            counts["UNKNOWN_OUTCOME_NOT_MATURE_ASOF"] += 1
            continue
        # Purge by the ACTUAL evaluation timestamp, not an assumed 24h.
        # The final fold also needs a fully matured horizon by study end.
        if evaluated > fold_end - embargo:
            counts["PURGED_OR_EMBARGOED_REAL_EVALUATION_TIME"] += 1
            continue
        candidate.append((fold, week, tuple(receipts)))
    # Shared current COT release SHA across folds is research contamination.
    # Quarantine both sides, not only the later observation.
    receipt_folds = defaultdict(set)
    for fold, _, receipts in candidate:
        for digest in receipts:
            receipt_folds[digest].add(fold)
    contaminated = {digest for digest, folds in receipt_folds.items()
                    if len(folds) > 1}
    accepted = Counter()
    weeks = defaultdict(set)
    for fold, week, receipts in candidate:
        if any(r in contaminated for r in receipts):
            counts["QUARANTINED_COT_RELEASE_CROSS_FOLD"] += 1
        else:
            accepted[fold] += 1
            weeks[fold].add(_iso(week))
    summary = {
        fold: {
            "denominatorOriginalDecisions": denominator[fold],
            "pairedCompleteMetadata": accepted[fold],
            "distinctCotPublicationWeeksUpperBound": len(weeks[fold]),
            "minimumDesignCountsSatisfied": (
                accepted[fold] >= FROZEN_RULES["required_complete_decisions_per_fold"]
                and len(weeks[fold]) >=
                FROZEN_RULES["required_independent_cot_weeks_per_fold"]
            ),
        } for fold in FOLDS
    }
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_PLANNING_ONLY_NO_PROSPECTIVE_ENROLLMENT",
        "protocolSha256": FROZEN_RULES_SHA256,
        "hypotheticalCalendarUtc": calendar,
        "folds": summary,
        "exclusions": dict(sorted(counts.items())),
        "metadataRowsProcessed": len(rows),
        "independentSamplesProven": 0,
        "actualProviderReceiptsVerified": False,
        "originalSqualincomeUsedRetail": False,
        "outcomeValuesRead": 0,
        "executionCostsRead": 0,
        "tradeReturnsCalculated": False,
        "trainedModels": 0,
        "outOfSampleUnblinded": False,
        "realEdgeEstablished": False,
        "releaseAuthorized": False,
        "liveEnabled": False,
        "newAPICalls": 0,
    }
