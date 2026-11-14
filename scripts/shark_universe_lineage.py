"""REMURA Track B: COT point-in-time provenance census across ALL monitored markets.

Read-only offline research. The two-market pilot rejected 73 of 77 stored
outcome rows as out of scope. These rows are NOT necessarily bad. Check real
availability of *each* market's CFTC instrument(s) independently, without
inventing historical first_seen times or retroactive order fills.

The static mappings are copied from live signals_monitor.py (v1.62); MUST be
reverified before deployment if the production catalog changes. No signals,
PnL, market raw data or broker identifiers are exported. Single FX legs use
one report, crosses need both currency legs for BOTH COT weeks.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import closing
from datetime import date, timedelta
import math
from pathlib import Path
import sqlite3
from urllib.parse import quote

from scripts import shark_cot_paired_baseline as base

SCHEMA = "remura-shark-universe-lineage-v1"
MAX_ROWS = 50_000
FX_CODES = {
    "EUR":"099741", "GBP":"096742", "JPY":"097741",
    "AUD":"232741", "CAD":"090741", "CHF":"092741",
    "NZD":"112741",
}
DIRECT = {
    "XAUUSD":("disagg","088691"), "XAGUSD":("disagg","084691"),
    "USOIL":("disagg","067651"),
    "US500":("tff","13874A"), "NAS100":("tff","209742"),
    "US30":("tff","124603"),
}
HORIZONS = (1,4,24)
CATEGORY = ("fx_one_leg","fx_cross_two_legs","direct_futures")
REQUIRED = {"cot_first_seen","squalincome_validation_cohorts",
            "squalincome_validation_outcomes"}


def contracts(symbol):
    """Return mapped CFTC legs and family; None means NOT proven/mapped."""
    if symbol in DIRECT:
        return "direct_futures", (DIRECT[symbol],)
    if (not isinstance(symbol,str) or len(symbol)!=6 or
            symbol[:3] == symbol[3:]):
        return None
    left,right=symbol[:3],symbol[3:]
    if (left not in FX_CODES and left!="USD") or (
            right not in FX_CODES and right!="USD"):
        return None
    if left=="USD" and right=="USD":
        return None
    pairs=tuple(("tff",FX_CODES[x]) for x in (left,right) if x!="USD")
    return ("fx_one_leg" if len(pairs)==1 else "fx_cross_two_legs",pairs)


def _seen(db):
    known={}
    for dataset,code,report_date,first_seen in db.execute(
            "SELECT dataset,code,report_date,first_seen_at FROM cot_first_seen"):
        try:
            if dataset not in ("tff","disagg"):
                continue
            ts=base._utc(first_seen)
            key=(dataset,code,report_date)
            known[key]=max(known.get(key,ts),ts)  # conservative duplicates
        except (ValueError,TypeError,OverflowError):
            continue
    return known


def _availability(seen,legs,week,obs):
    """Fail shut if ANY required report was not known at the original time."""
    target=date.fromisoformat(week)
    previous_candidates=tuple((target-timedelta(days=d)).isoformat()
                              for d in range(6,11))
    # A two-legged FX cross requires all four report records.
    for dataset,code in legs:
        instant=seen.get((dataset,code,week))
        if instant is None:
            return "current_report_not_recorded"
        if instant>obs:
            return "current_report_first_seen_late"
        prev=[seen.get((dataset,code,d)) for d in previous_candidates]
        if not any(x is not None and x<=obs for x in prev):
            if any(x is not None for x in prev):
                return "previous_report_first_seen_late"
            return "previous_report_not_recorded"
    return None


def audit_connection(db, *, as_of):
    """Only whitelisted instrument names and integer counters leave the DB."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now=base._utc(as_of)
    absent=sorted(REQUIRED-base._table_names(db))
    if absent:
        return {"schema":SCHEMA,"status":"UNAVAILABLE",
                "missingTables":absent,"edge":"NOT_ESTABLISHED",
                "brokerCalls":0}
    # SQLite aggregate count is cheap; hard bound before materializing outcomes.
    count=db.execute(
        "SELECT count(*) FROM squalincome_validation_outcomes").fetchone()[0]
    if type(count) is not int or count>MAX_ROWS:
        raise ValueError("archive_exceeds_research_bound")
    seen=_seen(db)
    rows=db.execute(
        "SELECT c.symbol,c.report_date,c.observed_at,c.price_time,"
        "c.cot_side,c.relationship,c.broker_symbol,c.entry_at,c.entry_open,"
        "o.horizon_hours,o.evaluated_at,o.directional_bps,o.long_benchmark_bps "
        "FROM squalincome_validation_cohorts c JOIN "
        "squalincome_validation_outcomes o "
        "ON c.symbol=o.symbol AND c.report_date=o.report_date "
        "AND c.stage=o.stage WHERE c.stage='observation' "
        "ORDER BY c.symbol,c.report_date,o.horizon_hours").fetchall()
    reasons=Counter()
    groups=defaultdict(list)
    seen_cohorts=set()
    for (symbol,week,observed,price_closed,side,relation,broker,
         entry_at,entry_price,hours,evaluated,directional,long_return) in rows:
        spec=contracts(symbol)
        if spec is None:
            reasons["not_in_live_cot_contract_catalog"]+=1
            continue
        family,legs=spec
        if hours not in HORIZONS or type(hours) is not int:
            reasons["unsupported_horizon"]+=1
            continue
        key=(symbol,week,hours)
        if key in seen_cohorts:
            reasons["duplicate_cohort_horizon"]+=1
            continue
        seen_cohorts.add(key)
        try:
            obs=base._utc(observed)
            closed=base._utc(price_closed)
            entry=base._utc(entry_at)
            mature=base._utc(evaluated)
            repdate=date.fromisoformat(week)
            if (repdate.isoformat()!=week or repdate>obs.date()
                    or obs.date()-repdate>timedelta(days=14)
                    or not closed<=obs<=entry<mature<=now
                    or obs-closed>timedelta(hours=3)
                    or entry-obs>base.MAX_DELAY
                    or entry.minute%15 or entry.second or entry.microsecond
                    or mature<entry+timedelta(hours=hours)
                    or type(side) is not int or side not in (-1,1)
                    or relation not in ("aligned","divergent")
                    or not isinstance(broker,str) or not broker.strip()
                    or not base._finite(entry_price) or entry_price<=0
                    or not base._finite(directional)
                    or not base._finite(long_return)
                    or not math.isclose(directional,side*long_return,
                                        rel_tol=1e-5,abs_tol=0.0001)):
                reasons["invalid_cohort_or_outcome"]+=1
                continue
            reason=_availability(seen,legs,week,obs)
            if reason:
                reasons[reason]+=1
                continue
            reasons["eligible_time_provenance_only"]+=1
            groups[symbol].append((week,hours))
        except (ValueError,TypeError,OverflowError):
            reasons["invalid_cohort_or_outcome"]+=1
    # Everything returned is aggregate, no single timestamp or individual
    # return value. Known ticker symbols are a published static catalog.
    markets={}
    for symbol in sorted(groups):
        rows_by_market=groups[symbol]
        markets[symbol]={
            "family":contracts(symbol)[0],
            "byHorizon":[{
                "hours":h,
                "eligibleOutcomes":sum(hour==h for _,hour in rows_by_market),
                "cotWeeks":len({week for week,hour in rows_by_market if hour==h}),
                "sampleGate": (
                    "DESCRIPTIVE_ONLY"
                    if sum(hour==h for _,hour in rows_by_market)>=30 and
                       len({week for week,hour in rows_by_market if hour==h})>=8
                    else "INSUFFICIENT")
            } for h in HORIZONS]
        }
    family_counts={k:sum(1 for m in markets.values() if m["family"]==k)
                   for k in CATEGORY}
    return {
        "schema":SCHEMA,
        "status":"POINT_IN_TIME_PROVENANCE_SCREEN_ONLY",
        "pilotScopeOnly":False,
        "observationStageOutcomeRowsExamined":len(rows),
        "allStageOutcomeRows":count,
        "reasons":dict(sorted(reasons.items())),
        "eligibleMarketsByFamily":family_counts,
        "eligibleMarkets":markets,
        "historicCotValuesVersioned":False,
        "historicalBrokerQuotesVerified":False,
        "historicalH1IndependentSnapshots":False,
        "returnsNetOfActualTradingCosts":False,
        "outOfSampleVerified":False,
        "edge":"NOT_ESTABLISHED","brokerCalls":0,"alertsEnabled":False,
    }


def audit_path(db_path, *, as_of):
    if not isinstance(db_path,(str,Path)):
        raise ValueError("invalid_private_path")
    target=Path(db_path).expanduser().resolve(strict=True)
    if not target.is_file():
        raise ValueError("not_a_database")
    uri="file:"+quote(str(target),safe="/")+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True,timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        return audit_connection(db,as_of=as_of)
