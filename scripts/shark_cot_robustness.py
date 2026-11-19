"""REMURA Track B: chronological cost-stress checks on authentic COT cohorts.

Research only. Not independent walk-forward proof: the original trading idea
was not frozen before these observations and historic COT/quote revisions are
not immutable. All comparisons use EXACTLY the same eligible cohort, entry
and outcome horizon. No new market data, orders, or external I/O.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
import sqlite3

from scripts import shark_cot_paired_baseline as base

SCHEMA = "remura-cot-robustness-v1"
MIN_WEEKS = 8
MIN_COHORTS = 30
MULTIPLIERS = (1, 2, 3)
ARMS = ("cot", "long", "invertedCot")


def _window(case, train, validation, today, embargo):
    """Purge on actual OUTCOME EVALUATION time, not just theoretical close."""
    observed, evaluated = case["observed"], case["evaluated"]
    if observed < train:
        return "train" if evaluated <= train - embargo else "purged"
    if observed < validation:
        return ("validation" if observed >= train + embargo
                and evaluated <= validation - embargo else "purged")
    return ("test" if observed >= validation + embargo
            and evaluated <= today else "purged")


def _stats(cases, costs, multiple):
    weeks = {case["week"] for case in cases}
    n = len(cases)
    scenarios = {arm: [] for arm in ARMS}
    for c in cases:
        cost = costs[c["symbol"]] * multiple
        scenarios["cot"].append(c["cotGrossBps"]-cost)
        scenarios["long"].append(c["longGrossBps"]-cost)
        # Deliberately wrong-sign COT as a negative directional control.
        scenarios["invertedCot"].append(-c["cotGrossBps"]-cost)
    summaries = {}
    reliable = n >= MIN_COHORTS and len(weeks) >= MIN_WEEKS
    for name, values in scenarios.items():
        mean = sum(values)/n if n else None
        good = sum(x > 0 for x in values)
        summaries[name] = {
            "meanNetBps": round(mean, 4) if mean is not None else None,
            "positiveCount": good,
            "positivePct": round(100*good/n, 2) if reliable else None,
        }
    return {
        "samples": n,
        "distinctCotWeeks": len(weeks),
        "sampleGate": ("DESCRIPTIVE_ONLY" if reliable
                       else "INSUFFICIENT"),
        "arms": summaries,
        "cotMinusLongMeanBps": (
            round(sum(c["cotGrossBps"]-c["longGrossBps"]
                      for c in cases)/n, 4) if n else None),
        # Equal round-trip costs cancel in the difference between arms,
        # but NOT when evaluating net profitability or trade-vs-no-trade.
        "costGapCaveat": "paired_difference_cancels_equal_costs",
    }


def _cot_week_cluster_audit(cases):
    """Sensitivity to correlated observations sharing a COT report week.

    The unit is a COT publication week, shared across all markets. Reusing
    the same COT release, even on different instruments, is not independent
    evidence. Aggregate each week's SAME-cohort COT-minus-long paired gaps
    first; then remove ONE entire week at a time. Never cherry-pick a week
    or recompute the trading rule. This is a descriptive influence screen,
    NOT a significance test, confidence interval, causal effect or real PnL.
    """
    by_week = defaultdict(list)
    for case in cases:
        # Equal explicit round-trip costs on the paired arms cancel. These
        # are gross directional bps differences, NOT net profits or fills.
        by_week[case["week"]].append(
            case["cotGrossBps"] - case["longGrossBps"]
        )
    n = len(cases)
    k = len(by_week)
    sorted_week_means = [
        sum(gaps) / len(gaps)
        for _, gaps in sorted(by_week.items())
    ]
    # The cohorts are provenance-verified by _verified_cases upstream, but
    # the historic source revisions and actual fills remain unverified.
    admitted = n >= MIN_COHORTS and k >= MIN_WEEKS
    pooled = (
        sum(sum(gaps) for gaps in by_week.values()) / n if n else None
    )
    balanced = (
        sum(sorted_week_means) / k if k else None
    )
    if admitted and k > 1:
        loo = [
            (sum(sorted_week_means) - x) / (k - 1)
            for x in sorted_week_means
        ]
        sensitivity = {
            "minPairedBps": round(min(loo), 4),
            "maxPairedBps": round(max(loo), 4),
        }
    else:
        sensitivity = None
    return {
        "clusterUnit": "shared_cot_report_week_across_all_markets",
        "samples": n,
        "distinctCotWeeks": k,
        "maxSamplesOneWeek": (
            max(map(len, by_week.values())) if k else 0
        ),
        "maxShareOneWeekPct": (
            round(100 * max(map(len, by_week.values())) / n, 2)
            if n else None
        ),
        "pooledPairedCotMinusLongBps": (
            round(pooled, 4) if pooled is not None else None
        ),
        "equalCotWeekWeightPairedBps": (
            round(balanced, 4) if balanced is not None else None
        ),
        "leaveOneWholeCotWeekOutPairedBpsRange": sensitivity,
        "sensitivityGate": (
            "DESCRIPTIVE_ONLY_NOT_INDEPENDENT" if admitted
            else "INSUFFICIENT_WEEKS_OR_COHORTS"
        ),
        "costsCancelOnlyInPairedDifference": True,
        "weekClusterIsIndependentOosProof": False,
        "noPValuesOrConfidenceIntervals": True,
        "noTradingEdgeEstablished": True,
    }


def evaluate(db, *, as_of, train_end, validation_end, costs,
             embargo_hours=24):
    """Use existing persisted cohorts, with windows fixed BEFORE results read.

    Users must pre-register split boundaries and cost assumptions externally.
    This function does not choose good boundaries or optimize parameters.
    Output is aggregate-only. No historical broker symbols or event timestamps.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    today = base._utc(as_of)
    train, validation = base._utc(train_end), base._utc(validation_end)
    if not train < validation < today:
        raise ValueError("non_chronological_research_windows")
    if (type(embargo_hours) is not int or embargo_hours < 0
            or embargo_hours > 168):
        raise ValueError("invalid_embargo")
    embargo = timedelta(hours=embargo_hours)
    if not isinstance(costs, dict) or set(costs) != set(base.PILOT):
        raise ValueError("exact_market_costs_required")
    cost_bps = {symbol: base._cost(costs[symbol]) for symbol in base.PILOT}
    cases, rejected, received, missing = base._verified_cases(db, today)
    if missing:
        return {
            "schema": SCHEMA, "status": "UNAVAILABLE",
            "missingTables": missing, "edge": "NOT_ESTABLISHED",
            "brokerCalls": 0,
        }
    proposed = [(c, _window(c, train, validation, today, embargo))
                for c in cases]
    # One COT report date is a shared information release across assets,
    # so it may not contribute to multiple folds.
    by_week = defaultdict(set)
    for case, fold in proposed:
        if fold != "purged":
            by_week[case["week"]].add(fold)
    contaminated_weeks = {week for week, folds in by_week.items()
                          if len(folds) > 1}
    excluded = Counter(rejected)
    originally_eligible = excluded.pop("paired_valid", 0)
    buckets = {f: defaultdict(list)
               for f in ("train", "validation", "test")}
    for c, fold in proposed:
        if c["week"] in contaminated_weeks:
            excluded["cot_week_crosses_folds"] += 1
        elif fold == "purged":
            excluded["embargo_or_unobserved_outcome"] += 1
        else:
            buckets[fold][c["horizon"]].append(c)
    folds = {}
    for fold in ("train", "validation", "test"):
        folds[fold] = []
        for horizon in base.HORIZONS:
            studies = buckets[fold][horizon]
            folds[fold].append({
                "horizonHours": horizon,
                "cotWeekClusterAudit": _cot_week_cluster_audit(studies),
                "costScenarios": [
                    {"costMultiple": multiple,
                     **_stats(studies, cost_bps, multiple)}
                    for multiple in MULTIPLIERS
                ],
            })
    return {
        "schema": SCHEMA, "status": "RESEARCH_ONLY",
        "received": received,
        "eligibleProvenance": originally_eligible,
        "excluded": dict(sorted(excluded.items())),
        "folds": folds,
        "design": "fixed_chronological_windows_outcome_purged",
        "perWeekDisjoint": True,
        "embargoHours": embargo_hours,
        "comparison": "same_paired_observation_cot_vs_long_vs_inverted",
        "costScenarios": "one_two_three_times_explicit_per_market_bps",
        "noTradeBenchmarkNetBps": 0,
        "measuredBrokerCosts": False,
        "preRegisteredBeforeSeeingData": False,
        "independentOutOfSample": False,
        "independentTradingSamples": False,
        "historicCotRevisionsVerified": False,
        "actualTradeFills": False,
        "edge": "NOT_ESTABLISHED",
        "probability": None,
        "ordersEnabled": False,
        "alertsEnabled": False,
        "brokerCalls": 0,
    }
