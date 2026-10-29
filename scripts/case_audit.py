#!/usr/bin/env python3
"""REMURA v1.47 — read-only register of the facts behind each 24h statistic.

These are hypothetical price changes, NOT trades, orders or a predictive score.
COT report week means report's reference date, not publication/entry time.
Same shared v1.46 validated pairs, strictly as-of; original outcomes untouched.
"""
from __future__ import annotations

import datetime as dt
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

from price_feed import utcnow
from market_validation import paired_cases

UTC = dt.timezone.utc
MAX_WEEKS = 12
METRICS = ("calendar24", "trading96")


def _metric(values):
    directional, long, favorable, adverse = values
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
        return None
    return {
        "directionalBps":round(directional,2),
        "benchmarkLongBps":round(long,2),
        "favorableBps":round(favorable,2),
        "adverseBps":round(adverse,2),
        "directionHit":directional > 0,
    }


def _snapshot(db, now):
    eligible, paired = paired_cases(db,now)
    # Select recent week cohort IDs, not individual best-performing events.
    weeks = sorted({week for _,week in eligible}, reverse=True)
    recent_weeks = set(weeks[:MAX_WEEKS])
    records=[]
    for (symbol, week), measures in sorted(
            paired.items(), key=lambda item:(item[0][1],item[0][0]),reverse=True):
        if week not in recent_weeks:
            continue
        rel, _entry, side = eligible[(symbol,week)]
        if side not in (-1,1):
            continue
        calendar = _metric(measures["calendar24"])
        traded = _metric(measures["trading96"])
        if calendar is None or traded is None:
            continue
        # A negative delta is NOT a loss: only difference between two
        # factual hypothetical windows on exactly the same observation.
        records.append({
            "symbol":symbol,
            "cotWeek":week,
            "cotSide":"long" if side==1 else "short",
            "initialRelationship":rel,
            "calendar24":calendar,
            "trading96":traded,
            "deltaTradingMinusCalendarBps":round(
                traded["directionalBps"]-calendar["directionalBps"],2),
        })

    totals=defaultdict(list)
    by_week=defaultdict(list)
    for record in records:
        totals[record["initialRelationship"]].append(record)
        by_week[record["cotWeek"]].append(record)

    def group(rows):
        n=len(rows)
        # Signed bps are NOT monetary P&L; all case observations receive
        # equal weight, including correlated USD/commodity exposures.
        return {
            "samples":n,
            "weeks":len({r["cotWeek"] for r in rows}),
            "positiveCalendar":sum(r["calendar24"]["directionHit"] for r in rows),
            "negativeOrFlatCalendar":sum(not r["calendar24"]["directionHit"] for r in rows),
            "positiveTraded":sum(r["trading96"]["directionHit"] for r in rows),
            "meanCalendarBps":round(
                sum(r["calendar24"]["directionalBps"] for r in rows)/n,2) if n else None,
            "meanTradedBps":round(
                sum(r["trading96"]["directionalBps"] for r in rows)/n,2) if n else None,
        }

    week_summary=[]
    for week in weeks[:MAX_WEEKS]:
        rows=by_week[week]
        aligned=[r for r in rows if r["initialRelationship"]=="aligned"]
        divergent=[r for r in rows if r["initialRelationship"]=="divergent"]
        week_summary.append({
            "cotWeek":week,
            "maturedCohorts":sum(k[1]==week for k in eligible),
            "pairedSamples":len(rows),
            "aligned":group(aligned),
            "divergent":group(divergent),
        })

    return {
        "schema":"remura-case-audit-v1",
        "mode":"research_only",
        "scope":"last_12_COT_reference_weeks",
        "noSyntheticCandles":True,
        "executionCostsIncluded":False,
        "independence":"market/week observations may share macro drivers; no correlation coefficients without independent repeated weeks",
        "source":"persisted_paired_observation_outcomes",
        "totalEligibleWeeks":len(weeks),
        "weeksShown":len(week_summary),
        "pairedCasesShown":len(records),
        "caseCountByRelationship":{
            "aligned":len(totals["aligned"]),
            "divergent":len(totals["divergent"])
        },
        "weekly":week_summary,
        "cases":records,
        "note":"COT settimanale e pubblicato in ritardo: la direzione è quella "
               "registrata all'osservazione reale. Settimana COT = riferimento, "
               "NON data d'ingresso. 14 mercati nella stessa settimana non sono "
               "14 prove indipendenti. Punti base lordi, non ordini.",
    }


def case_audit_status(db_path, now=None):
    now=(now or utcnow()).astimezone(UTC)
    path=Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Archivio privato non disponibile")
    db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        return _snapshot(db,now)
    finally:
        db.close()
