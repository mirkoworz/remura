#!/usr/bin/env python3
"""REMURA v1.48 — read-only COT capture provenance & weekly independence audit.

Do not infer CFTC publication time from the Tuesday report date. For new rows
the collector stores the FIRST time REMURA observed that official row; for old
rows first-seen is UNKNOWN and never reconstructed. The COT direction depends
on two reports (current + predecessor) and for FX crosses on both currencies.
This audit is retrospective metadata; it never rewrites or filters old outcomes.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from price_feed import parse_time, utcnow
from case_audit import _snapshot as case_snapshot
from signals_monitor import FX_CODES, OTHER

UTC=dt.timezone.utc
STATUSES=("recorded_before_observation","unknown_legacy",
          "captured_after_observation","missing_cot_reference")
MIN_INDEPENDENT_WEEKS=8
MAX_WEEKS=12


def _contracts(symbol):
    if symbol in OTHER:
        return (OTHER[symbol],)
    if len(symbol)!=6:
        return ()
    base,quote=symbol[:3],symbol[3:]
    if base not in FX_CODES and base!="USD":
        return ()
    if quote not in FX_CODES and quote!="USD":
        return ()
    return tuple(("tff",FX_CODES[x]) for x in (base,quote) if x!="USD")


def _exposures(symbol):
    # Overlap warnings only; no false correlation coefficients or clustering.
    if symbol in ("XAUUSD","XAGUSD"):
        return ("USD","precious_metals")
    if symbol in ("US500","NAS100","US30"):
        return ("us_equity_indices",)
    if symbol=="USOIL":
        return ("energy",)
    if len(symbol)==6 and symbol[:3] in FX_CODES|{"USD":None} and symbol[3:] in FX_CODES|{"USD":None}:
        return tuple(sorted({symbol[:3],symbol[3:]}))
    return ()


def _case_status(db, symbol, week, observed, has_first_seen):
    contracts=_contracts(symbol)
    if not contracts:
        return "missing_cot_reference"
    # For a cross, BOTH currencies must share this week's report AND the
    # preceding common week. Compare against the same pair used by cot_series.
    common=None
    for dataset,code in contracts:
        dates={row[0] for row in db.execute(
            "SELECT report_date FROM cot_reports "
            "WHERE dataset=? AND code=? AND report_date<=?",
            (dataset,code,week)).fetchall()}
        common=dates if common is None else common & dates
    if not common or week not in common:
        return "missing_cot_reference"
    predecessor=max((d for d in common if d<week),default=None)
    if predecessor is None:
        return "missing_cot_reference"
    if not has_first_seen:
        return "unknown_legacy"
    has_unknown=False
    has_future=False
    for dataset,code in contracts:
        for date in (week,predecessor):
            row=db.execute(
                "SELECT first_seen_at FROM cot_first_seen "
                "WHERE dataset=? AND code=? AND report_date=?",
                (dataset,code,date)).fetchone()
            if row is None:
                has_unknown=True
                continue
            try:
                recorded=parse_time(row[0])
            except (ValueError,TypeError,OverflowError,AttributeError):
                has_unknown=True
                continue
            if recorded>observed:
                has_future=True
    if has_future:
        return "captured_after_observation"
    if has_unknown:
        return "unknown_legacy"
    return "recorded_before_observation"


def _snapshot(db,now):
    audit=case_snapshot(db,now)
    cohorts=db.execute(
        "SELECT symbol,report_date,observed_at "
        "FROM squalincome_validation_cohorts WHERE stage='observation'").fetchall()
    observed={}
    for sym,week,value in cohorts:
        try:
            timestamp=parse_time(value)
            if timestamp<=now:
                observed[(sym,week)]=timestamp
        except (ValueError,TypeError,OverflowError,AttributeError):
            continue

    existing_tables={r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('cot_reports','cot_first_seen')").fetchall()}
    have_cot="cot_reports" in existing_tables
    have_seen="cot_first_seen" in existing_tables
    cases=[]
    for case in audit["cases"]:
        sym,week=case["symbol"],case["cotWeek"]
        first=observed.get((sym,week))
        status=(_case_status(db,sym,week,first,have_seen)
                if have_cot and first else "missing_cot_reference")
        cases.append({
            "symbol":sym,"cotWeek":week,
            "captureStatus":status,
            # Non-execution metadata: original sign and relation remain unchanged.
            "cotSide":case["cotSide"],
            "initialRelationship":case["initialRelationship"],
        })
    by_week=defaultdict(list)
    for case in cases:
        by_week[case["cotWeek"]].append(case)

    weekly=[]
    for week in audit["weekly"]:
        rows=by_week[week["cotWeek"]]
        exposure=defaultdict(set)
        for case in rows:
            for factor in _exposures(case["symbol"]):
                exposure[factor].add(case["symbol"])
        # Cross-market "shared factors" is qualitative, not independence-adjusted N.
        overlap=[{"factor":factor,"markets":len(symbols)}
                 for factor,symbols in sorted(exposure.items())
                 if len(symbols)>1]
        aligned=week["aligned"]
        divergent=week["divergent"]
        comparison=(round(100*(
            divergent["positiveCalendar"]/divergent["samples"]-
            aligned["positiveCalendar"]/aligned["samples"]),1)
            if divergent["samples"] and aligned["samples"] else None)
        counts=Counter(x["captureStatus"] for x in rows)
        weekly.append({
            "cotWeek":week["cotWeek"],
            "pairedSamples":len(rows),
            "alignedSamples":aligned["samples"],
            "divergentSamples":divergent["samples"],
            "alignedHits":aligned["positiveCalendar"],
            "divergentHits":divergent["positiveCalendar"],
            "divergentMinusAlignedHitPp":comparison,
            "captureCounts":{key:counts[key] for key in STATUSES},
            "sharedFactorWarnings":overlap,
        })

    with_both=[w for w in weekly
               if w["alignedSamples"] and w["divergentSamples"]]
    n_weeks=sum(w["pairedSamples"]>0 for w in weekly)
    better=sum(w["divergentMinusAlignedHitPp"]>0 for w in with_both)
    worse=sum(w["divergentMinusAlignedHitPp"]<0 for w in with_both)
    tied=len(with_both)-better-worse
    statuses=Counter(x["captureStatus"] for x in cases)
    return {
        "schema":"remura-weekly-quality-v1",
        "mode":"research_only",
        "firstSeenMeaning":"REMURA first CFTC row capture (NOT official publication)",
        "legacyProvenance":"unknown_not_backfilled",
        "noSyntheticCandles":True,
        "independentCotWeeksObserved":n_weeks,
        "weeksWithBothRelationships":len(with_both),
        "weeksDivergenceBetter":better,
        "weeksConcordanceBetter":worse,
        "weeksEqual":tied,
        "minCotWeeksForDescriptiveReview":MIN_INDEPENDENT_WEEKS,
        "quality":"Campione insufficiente" if n_weeks<MIN_INDEPENDENT_WEEKS
                  else "Descrittivo: correlazioni e verifica fuori campione non risolte",
        "casesAudited":len(cases),
        "captureCounts":{key:statuses[key] for key in STATUSES},
        "weekly":weekly,
        "warning":"La data di riferimento COT non è la pubblicazione. "
                  "Per gli archivi precedenti alla v1.48 la prima acquisizione "
                  "è sconosciuta. Nessuna prova causale, coefficiente di "
                  "correlazione, rendimento netto o segnale operativo.",
    }


def weekly_quality_status(db_path,now=None):
    now=(now or utcnow()).astimezone(UTC)
    path=Path(db_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Archivio REMURA non trovato")
    db=sqlite3.connect("file:"+str(path)+"?mode=ro",uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        return _snapshot(db,now)
    finally:
        db.close()
