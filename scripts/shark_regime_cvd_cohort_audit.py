"""Offline Track B: SAME-decision regime x CVD candidate coverage matrix.

Reuses the frozen prospective COT+retail+price admission (without changing it)
and the existing original-document M15 regime classifier. Does not re-fetch
OHLC or derive historical regime labels from current caches. CVD label absence
is UNKNOWN rather than a negative. A COT report shared across assets cannot
occur in multiple chronological folds. Purging uses the largest frozen 24h
outcome horizon + 8 M15 embargo slots, without pretending an outcome was
actually recorded.

This is ONLY a metadata/coverage rehearsal; inputs are operator supplied.
No authenticated CFTC source, real executed fill, PnL, edge or actual future
outcome is inferred. No files, broker, SQLite, network, orders, notifications.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
import json

from scripts import shark_cvd_incremental_protocol as core
from scripts import shark_market_regime_context as regime

SCHEMA = "remura-track-b-regime-cvd-paired-coverage-v1"
LABELS = ("ALIGNED_CANDIDATE", "NEGATIVE_CANDIDATE",
          "INVERTED_PLACEBO_CANDIDATE", "UNKNOWN")
REGIMES = (*regime.STATES, "UNKNOWN")
FOLDS = ("train", "validation", "test")
EMBARGO = core.PROTOCOL["purgeEmbargoM15"] * core.STEP
HORIZON = timedelta(hours=max(core.PROTOCOL["outcomeHorizonsHours"]))
MAX_ROWS = 10000


def _fold(observed, train, validation, now):
    """Fixed split and 24h horizon; no cross-boundary outcome leakage."""
    if observed < train:
        return "train" if observed + HORIZON <= train - EMBARGO else "purged"
    if observed < validation:
        return ("validation" if observed >= train + EMBARGO and
                observed + HORIZON <= validation - EMBARGO else "purged")
    return ("test" if observed >= validation + EMBARGO and
            observed + HORIZON <= now else "purged")


def _regime_label(core_row, regime_row, *, as_of):
    """Require exactly the same original decision/source for a regime label."""
    if type(regime_row) is not dict:
        return "UNKNOWN", "missing_original_regime_witness"
    for key in ("symbol", "observedAtUtc", "firstRecordedAtUtc"):
        if (regime_row.get(key) != core_row.get(key)
                or type(core_row.get(key)) is not str):
            return "UNKNOWN", "different_original_decision"
    original = core_row.get("priceOriginalSha256")
    if (type(original) is not str
            or original != regime_row.get("originalDocumentSha256")):
        return "UNKNOWN", "different_original_price_sha"
    # The core timestamp is a locally witnessed price receipt; it cannot
    # be replaced by a later scan of the current broker price cache.
    if regime_row.get("sourceReceivedAtUtc") != core_row.get("priceWitnessAtUtc"):
        return "UNKNOWN", "different_original_price_receipt"
    try:
        doc = regime_row["document"]
        m15 = doc["timeframes"]["M15"][-1]
        close = core._time(m15["t"]) + core.STEP
        if close != core._time(core_row.get("m15ClosedAtUtc")):
            return "UNKNOWN", "different_original_m15_close"
        label = regime.classify(regime_row, as_of=as_of)["state"]
        return label, None
    except (ValueError, TypeError, KeyError, IndexError,
            AttributeError, OverflowError):
        return "UNKNOWN", "unverified_original_price_history"


def _cvd_label(core_row, observed):
    label = core._cvd_label(core_row, observed)
    if label == "UNKNOWN":
        return label, None
    # Same price document for CVD and the parallel regime: otherwise the
    # negative control or confirmation could be manufactured by a later
    # broker snapshot. This is local evidence, not independent attestation.
    price_sha = core_row.get("priceOriginalSha256")
    if (type(price_sha) is not str or
            not core._hex(price_sha) or
            core_row.get("cvdSourceWitnessSha256") != price_sha):
        return "UNKNOWN", "different_cvd_original_price_sha"
    return label, None


def audit(records, *, as_of, train_end, validation_end,
          expected_protocol_sha256):
    if type(records) is not list or len(records) > MAX_ROWS:
        raise ValueError("invalid_paired_coverage_records")
    now = core._time(as_of)
    train = core._time(train_end)
    validation = core._time(validation_end)
    if not core._time(core.START) < train < validation < now:
        raise ValueError("invalid_chronological_split_boundaries")
    if (core.protocol_sha256() != core.FROZEN_PROTOCOL_SHA256
            or expected_protocol_sha256 != core.FROZEN_PROTOCOL_SHA256):
        raise ValueError("frozen_protocol_mismatch")

    # The frozen admission owns all core exclusion rules, COT 2-leg witness,
    # date/release provenance and duplicate quarantine. Never modify it.
    core_rows = [x.get("core") if type(x) is dict and
                 type(x.get("core")) is dict else {} for x in records]
    original = core.assess(core_rows, as_of=as_of,
                           expected_protocol_sha256=expected_protocol_sha256)
    keys = Counter()
    accepted = []
    start = core._time(core.START)
    for item, c in zip(records, core_rows):
        verified, reason = core._raw_core(c, start, now)
        if reason is None:
            observed, week = verified
            key = (c["symbol"], observed)
            keys[key] += 1
            accepted.append((item, c, observed, week, key))
    valid = [x for x in accepted if keys[x[4]] == 1]
    if len(valid) != original["rowsCoreAdmitted"]:
        raise ValueError("inconsistent_frozen_admission")

    # Keep the denominator, even when a regime or CVD source cannot be
    # independently reconciled to the original price observation.
    proposed = [(item, c, obs, week, _fold(obs, train, validation, now))
                for item,c,obs,week,key in valid]
    by_week = defaultdict(set)
    for item,c,obs,week,fold in proposed:
        if fold in FOLDS:
            by_week[week].add(fold)
    contaminated = {week for week, folds in by_week.items()
                    if len(folds) > 1}

    matrices = {fold: {state: Counter() for state in REGIMES}
                for fold in FOLDS}
    weekly = {fold: {state: set() for state in REGIMES}
              for fold in FOLDS}
    reasons = Counter()
    kept = Counter()
    for item, c, obs, week, fold in proposed:
        if week in contaminated:
            reasons["cot_week_crosses_folds"] += 1
            continue
        if fold == "purged":
            reasons["embargo_or_nominal_24h_not_elapsed"] += 1
            continue
        wrapped_regime = item.get("regime") if type(item) is dict else None
        state, why_regime = _regime_label(c, wrapped_regime,as_of=as_of)
        label, why_cvd = _cvd_label(c, obs)
        if why_regime:
            reasons[why_regime] += 1
        if why_cvd:
            reasons[why_cvd] += 1
        matrices[fold][state][label] += 1
        weekly[fold][state].add(week)
        kept[fold] += 1

    folds = {}
    for fold in FOLDS:
        states = {}
        for state in REGIMES:
            labels = matrices[fold][state]
            n = sum(labels.values())
            week_count = len(weekly[fold][state])
            states[state] = {
                "candidates": n,
                "distinctCotReportWeeks": week_count,
                "descriptiveGate": ("DESCRIPTIVE_ONLY_NOT_INDEPENDENT"
                    if n >= core.PROTOCOL["minimumDescriptiveEpisodes"] and
                    week_count >= core.PROTOCOL["minimumDistinctCotWeeks"]
                    else "INSUFFICIENT_COHORTS_OR_WEEKS"),
                "cvd": {name: labels[name] for name in LABELS},
            }
        folds[fold] = {"candidates": kept[fold], "regimes": states}
    if sum(kept.values()) + reasons["cot_week_crosses_folds"] + reasons[
            "embargo_or_nominal_24h_not_elapsed"] != original["rowsCoreAdmitted"]:
        raise ValueError("cohort_conservation_failed")
    return {
        "schema": SCHEMA,
        "status": "PROSPECTIVE_CANDIDATE_COVERAGE_ONLY_NO_OUTCOMES",
        "protocolSha256": core.protocol_sha256(),
        "asOfUtc": as_of,
        "received": len(records),
        "coreAdmitted": original["rowsCoreAdmitted"],
        "coreExcluded": original["rowsExcluded"],
        "coreExclusions": original["exclusionReasons"],
        "foldExclusionsAndMissingProvenance": dict(sorted(reasons.items())),
        "folds": folds,
        "fixedLargestOutcomeHorizonHours": 24,
        "fixedEmbargoM15": core.PROTOCOL["purgeEmbargoM15"],
        "crossFoldCotWeeksQuarantined": True,
        "notRealized24hOutcomes": True,
        "splitsExternallyPreRegistered": False,
        "operatorSuppliedEvidenceNotIndependent": True,
        "cotFirstSeenIndependentlyVerified": False,
        "regimesIndependentOfOutcomes": True,
        "cvdUnknownNotNegative": True,
        "missingAtRandomNotAssumed": True,
        "costsSpreadSlippageNotEstimated": True,
        "riskAdjustedPnLCalculated": False,
        "independentOutOfSampleValidated": False,
        "statisticalEdgeEstablished": False,
        "tradingOrNotificationsAuthorized": False,
        "brokerCalls": 0,
        "writes": 0,
    }
