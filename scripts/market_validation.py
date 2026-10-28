#!/usr/bin/env python3
"""REMURA v1.46 — read-only paired per-market audit of 24h research.

One observation per market and COT report week, no stages mixed, and no
comparison between different subsets of observations. Only a pair of fully
evaluated, already persisted calendar24/trading96 outcomes from the SAME
cohort contributes to any number. This is descriptive, not a trading signal.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from collections import defaultdict
from pathlib import Path

from price_feed import parse_time, utcnow
from statistical_validation import _statistics

UTC = dt.timezone.utc
MIN_MATURITY = dt.timedelta(hours=24, minutes=15)
EXIT_CLOSE = dt.timedelta(minutes=15)
RELATIONSHIPS = ("aligned", "divergent")


def _snapshot(db, now):
    # Read-only; do NOT call ensure_tables or run a collector through GET.
    cohorts = db.execute(
        "SELECT symbol,report_date,relationship,entry_at "
        "FROM squalincome_validation_cohorts WHERE stage='observation'"
    ).fetchall()
    outcomes = db.execute(
        "SELECT o.symbol,o.report_date,o.metric,o.entry_at,o.exit_at,o.evaluated_at,"
        "o.directional_bps,o.long_benchmark_bps,o.favorable_bps,o.adverse_bps "
        "FROM squalincome_dual24_outcomes o "
        "JOIN squalincome_validation_cohorts c "
        "ON o.symbol=c.symbol AND o.report_date=c.report_date AND o.stage=c.stage "
        "WHERE o.stage='observation' AND o.metric IN ('calendar24','trading96')"
    ).fetchall()

    eligible = {}
    for symbol, week, relation, entry in cohorts:
        if relation not in RELATIONSHIPS:
            continue
        try:
            when = parse_time(entry)
            if when + MIN_MATURITY > now:
                continue
            if dt.date.fromisoformat(week) > when.date():
                continue
        except (ValueError, TypeError, OverflowError, AttributeError):
            continue
        eligible[(symbol,week)] = (relation,when)

    paired = defaultdict(dict)
    for symbol, week, metric, entry, exit_at, evaluated_at, direction, long, fav, adv in outcomes:
        key = (symbol,week)
        if key not in eligible:
            continue
        try:
            beginning = parse_time(entry)
            ending = parse_time(exit_at)
            evaluated = parse_time(evaluated_at)
        except (TypeError, ValueError, OverflowError, AttributeError):
            continue
        if (beginning != eligible[key][1] or ending <= beginning or
                ending + EXIT_CLOSE > now or evaluated > now or
                evaluated < ending + EXIT_CLOSE):
            continue
        paired[key][metric] = (direction,long,fav,adv)

    complete = {}
    for key, vals in paired.items():
        if len(vals) == 2 and all(m in vals for m in ("calendar24","trading96")):
            complete[key] = vals

    def segment(keys):
        records = {"calendar24": [], "trading96": []}
        for key in keys:
            if key not in complete:
                continue
            sym,week = key
            relation = eligible[key][0]
            for metric in records:
                records[metric].append((relation,week,*complete[key][metric]))
        a = _statistics(records["calendar24"])
        b = _statistics(records["trading96"])
        return {
            "cohortsMatured":len(keys),
            "pairedSamples":len(records["calendar24"]),
            "unpairedMatured":len(keys)-len(records["calendar24"]),
            "reportWeeksPaired":a["reportWeeks"],
            "calendar24":a, "trading96":b,
            "deltaTradingMinusCalendarBps":round(
                b["meanDirectionalBps"]-a["meanDirectionalBps"],2)
                if a["samples"] else None,
        }

    by_symbol = defaultdict(list)
    by_relation = defaultdict(list)
    for key in eligible:
        symbol, _ = key
        by_symbol[symbol].append(key)
        by_relation[eligible[key][0]].append(key)

    markets = [
        {"symbol":symbol, **segment(by_symbol[symbol])}
        for symbol in sorted(by_symbol)
    ]
    relations = [
        {"relationship":rel, **segment(by_relation[rel])}
        for rel in RELATIONSHIPS
    ]
    overall = segment(list(eligible))
    return {
        "schema":"remura-market-audit-v1",
        "mode":"research_only",
        "method":"paired_observation_only_same_symbol_COT_week",
        "costsIncluded":False,
        "noSyntheticCandles":True,
        "sampleIndependence":"at most one observation per symbol/week; markets and COT weeks correlated",
        "warning":"Statistiche descrittive su coorti abbinate. La differenza non misura "
                  "un vantaggio operativo né un test fuori campione; intervallo "
                  "Wilson non corregge la correlazione. Costi e spread esclusi.",
        "total":overall,
        "relationships":relations,
        "markets":markets,
    }


def market_audit_status(db_path, now=None):
    """Aggregate market-by-market metadata, never reveal prices, accounts, timestamps."""
    now = (now or utcnow()).astimezone(UTC)
    path = Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Private validation store not available")
    db = sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        return _snapshot(db,now)
    finally:
        db.close()
