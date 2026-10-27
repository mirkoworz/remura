#!/usr/bin/env python3
"""REMURA v1.40 candidate: conservative, private, forward-only signal validation.

No order execution, external calls, synthetic fills or retroactive COT availability.
Cohorts originate from real Squalincome observations; entry is the next M15 OPEN
at/after observation (not the historical Tuesday COT report date).
Outcomes use contiguous, broker-consistent, fully closed M15 bars only.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sqlite3
from collections import defaultdict

from price_feed import parse_time, utcnow
from price_store import connect, latest
from signals_monitor import monitored_symbols

UTC = dt.timezone.utc
HORIZONS = (1, 4, 24)
MIN_SAMPLES = 30
MIN_REPORT_WEEKS = 8
MAX_ENTRY_DELAY = dt.timedelta(minutes=45)


def ensure_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_validation_cohorts(
        symbol TEXT NOT NULL,
        report_date TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        price_time TEXT NOT NULL,
        cot_side INTEGER NOT NULL CHECK(cot_side IN (-1,1)),
        relationship TEXT NOT NULL CHECK(relationship IN ('aligned','divergent')),
        stage TEXT NOT NULL CHECK(stage IN ('observation','technical_confirmation','qualified_event')),
        broker_symbol TEXT NOT NULL,
        entry_at TEXT NOT NULL,
        entry_open REAL NOT NULL CHECK(entry_open > 0),
        PRIMARY KEY(symbol,report_date,stage))""")
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_validation_outcomes(
        symbol TEXT NOT NULL,
        report_date TEXT NOT NULL,
        stage TEXT NOT NULL CHECK(stage IN ('observation','technical_confirmation','qualified_event')),
        horizon_hours INTEGER NOT NULL CHECK(horizon_hours IN (1,4,24)),
        evaluated_at TEXT NOT NULL,
        directional_bps REAL NOT NULL,
        long_benchmark_bps REAL NOT NULL,
        favorable_bps REAL NOT NULL,
        adverse_bps REAL NOT NULL,
        PRIMARY KEY(symbol,report_date,stage,horizon_hours),
        FOREIGN KEY(symbol,report_date,stage)
          REFERENCES squalincome_validation_cohorts(symbol,report_date,stage))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_squal_validation_horizon"
               " ON squalincome_validation_outcomes(horizon_hours)")
    db.commit()


def _bars(doc):
    if not isinstance(doc, dict) or doc.get("provider") != "ctrader":
        return None
    rows = doc.get("timeframes", {}).get("M15")
    if not isinstance(rows, list):
        return None
    output = {}
    previous = None
    try:
        for row in rows:
            stamp = parse_time(row["t"])
            prices = tuple(float(row[k]) for k in ("o", "h", "l", "c"))
            op, high, low, close = prices
            if (stamp.tzinfo is None or int(stamp.timestamp()) % 900
                    or (previous is not None and stamp <= previous)
                    or not all(math.isfinite(v) and v > 0 for v in prices)
                    or high < max(op, low, close) or low > min(op, high, close)):
                return None
            output[stamp] = prices
            previous = stamp
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return None
    return output or None


def _entry(bars, observed, price_time, now):
    """Require the price candle used for the actual observation to be present."""
    if (observed > now or price_time > observed or
            observed - price_time > dt.timedelta(hours=3)):
        return None
    if price_time - dt.timedelta(minutes=15) not in bars:
        return None
    start = next((t for t in bars if t >= observed), None)
    if start is None or start - observed > MAX_ENTRY_DELAY:
        return None
    if start + dt.timedelta(minutes=15) > now:
        return None
    return start, bars[start][0]


def _outcome(bars, entry_at, entry_open, side, hours, now):
    end = entry_at + dt.timedelta(hours=hours)
    if end > now:
        return None
    # An exact M15 time grid also excludes weekend/session gaps and holidays.
    rows = []
    for i in range(hours * 4):
        candle = bars.get(entry_at + dt.timedelta(minutes=15 * i))
        if candle is None:
            return None
        rows.append(candle)
    exit_close = rows[-1][3]
    upper = max(row[1] for row in rows)
    lower = min(row[2] for row in rows)
    factor = 10000 / entry_open
    directional = side * (exit_close - entry_open) * factor
    favorable = ((upper-entry_open) if side == 1 else (entry_open-lower)) * factor
    adverse = ((lower-entry_open) if side == 1 else (entry_open-upper)) * factor
    return (round(directional, 6), round((exit_close-entry_open)*factor, 6),
            round(max(0, favorable), 6), round(min(0, adverse), 6))


def update_validation(db_path, now=None):
    """Idempotent; called after each monitor scan. Adds only authentic matured data."""
    now = now or utcnow()
    db = connect(db_path)
    try:
        ensure_tables(db)
        # Existing history is never rewritten or reinterpreted as prior COT access.
        try:
            history = db.execute(
                "SELECT symbol,report_date,observed_at,price_time,cot_side,"
                "state,price_state,event_type FROM squalincome_history"
                " ORDER BY observed_at,id").fetchall()
        except sqlite3.OperationalError:
            history = []
        allowed = set(monitored_symbols())
        cached = {}
        seen = set()
        added = completed = 0
        for symbol, report_date, observed, price_time, side, relation, price_state, event in history:
            stages = ["observation"]
            if price_state == "confirmed":
                stages.append("technical_confirmation")
            if event:
                stages.append("qualified_event")
            for stage in stages:
                key = (symbol, report_date, stage)
                if key in seen:
                    continue
                seen.add(key)  # earliest authentic occurrence in this experiment arm
                if (symbol not in allowed or side not in (-1, 1)
                        or relation not in ("aligned", "divergent")):
                    continue
                if db.execute("SELECT 1 FROM squalincome_validation_cohorts"
                              " WHERE symbol=? AND report_date=? AND stage=?", key).fetchone():
                    continue
                try:
                    observed_dt = parse_time(observed)
                    price_dt = parse_time(price_time)
                    report_dt = dt.date.fromisoformat(report_date)
                    if report_dt > observed_dt.date():
                        continue
                    if symbol not in cached:
                        doc = latest(db, symbol)
                        cached[symbol] = (doc, _bars(doc))
                    doc, bars = cached[symbol]
                    if bars is None:
                        continue
                    entry = _entry(bars, observed_dt, price_dt, now)
                    if entry is None:
                        continue
                    entry_at, entry_open = entry
                    with db:
                        cur = db.execute(
                            "INSERT OR IGNORE INTO squalincome_validation_cohorts"
                            "(symbol,report_date,observed_at,price_time,cot_side,"
                            "relationship,stage,broker_symbol,entry_at,entry_open)"
                            " VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (symbol,report_date,observed,price_time,side,relation,
                             stage,doc["providerSymbol"],entry_at.isoformat(),entry_open))
                        added += int(cur.rowcount > 0)
                except (ValueError, TypeError, KeyError, OverflowError):
                    continue
        cohorts = db.execute(
            "SELECT symbol,report_date,stage,cot_side,broker_symbol,entry_at,entry_open"
            " FROM squalincome_validation_cohorts").fetchall()
        for symbol, report_date, stage, side, broker, when, op in cohorts:
            try:
                if symbol not in cached:
                    doc = latest(db, symbol)
                    cached[symbol] = (doc, _bars(doc))
                doc, bars = cached[symbol]
                if bars is None or doc.get("providerSymbol") != broker:
                    continue  # never join prices from different brokers
                start = parse_time(when)
                # Verify the original entry candle is still available and unchanged.
                if start not in bars or not math.isclose(bars[start][0], op, rel_tol=1e-9):
                    continue
                for hours in HORIZONS:
                    if db.execute("SELECT 1 FROM squalincome_validation_outcomes"
                                  " WHERE symbol=? AND report_date=? AND stage=? AND horizon_hours=?",
                                  (symbol,report_date,stage,hours)).fetchone():
                        continue
                    values = _outcome(bars,start,op,side,hours,now)
                    if values is None:
                        continue
                    with db:
                        cur = db.execute(
                            "INSERT OR IGNORE INTO squalincome_validation_outcomes"
                            "(symbol,report_date,stage,horizon_hours,evaluated_at,directional_bps,"
                            "long_benchmark_bps,favorable_bps,adverse_bps)"
                            " VALUES(?,?,?,?,?,?,?,?,?)",
                            (symbol,report_date,stage,hours,now.isoformat(),*values))
                        completed += int(cur.rowcount > 0)
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        return {"cohortsAdded": added, "outcomesAdded": completed}
    finally:
        db.close()


def _wilson(success, count):
    if not count:
        return None
    z = 1.95996398454
    p = success / count
    denom = 1 + z*z/count
    center = (p + z*z/(2*count))/denom
    distance = z*math.sqrt(p*(1-p)/count + z*z/(4*count*count))/denom
    return [round(100*(center-distance),1), round(100*(center+distance),1)]


def _statistics(rows):
    n = len(rows)
    weeks = len({row[1] for row in rows})
    if not n:
        return {"samples":0, "reportWeeks":0, "verdict":"Campione insufficiente"}
    successes = sum(row[2] > 0 for row in rows)
    avg = lambda ix: round(sum(row[ix] for row in rows)/n,2)
    return {"samples":n,"reportWeeks":weeks,
            "verdict":"Descrittivo, non prova predittiva" if
                      n >= MIN_SAMPLES and weeks >= MIN_REPORT_WEEKS else
                      "Campione insufficiente",
            "directionHitPct":round(100*successes/n,1),
            "wilson95Pct":_wilson(successes,n),
            "meanDirectionalBps":avg(2),"meanLongBenchmarkBps":avg(3),
            "meanFavorableBps":avg(4),"meanAdverseBps":avg(5)}


def validation_status(db_path, now=None):
    """Aggregate only: no private price, broker, token, or single-trade exposure."""
    db = connect(db_path)
    try:
        ensure_tables(db)
        rows = db.execute(
            "SELECT c.report_date,c.relationship,c.stage,o.horizon_hours,"
            "o.directional_bps,o.long_benchmark_bps,o.favorable_bps,o.adverse_bps"
            " FROM squalincome_validation_outcomes o JOIN squalincome_validation_cohorts c"
            " ON o.symbol=c.symbol AND o.report_date=c.report_date AND o.stage=c.stage").fetchall()
        cohorts = db.execute("SELECT count(*) FROM squalincome_validation_cohorts").fetchone()[0]
        groups = defaultdict(list)
        for week, relation, stage, horizon, direction, benchmark, favorable, adverse in rows:
            record = (relation,week,direction,benchmark,favorable,adverse)
            if stage == "observation":
                groups[(horizon,"all")].append(record)
                groups[(horizon,relation)].append(record)
            groups[(horizon,stage)].append(record)
        summary = []
        for horizon in HORIZONS:
            for segment in ("all","aligned","divergent","observation",
                            "technical_confirmation","qualified_event"):
                summary.append({"horizonHours":horizon,"segment":segment,
                                **_statistics(groups[(horizon,segment)])})
        return {"schema":"remura-forward-validation-v1","mode":"research_only",
                "method":"earliest_authentic_event_per_symbol_COT_week_and_study_arm",
                "entry":"first_next_M15_open_after_observed_at",
                "costsIncluded":False, "sampleIndependence":"one per symbol/week in each arm; arms overlap, assets correlated",
                "cohorts":cohorts,"outcomes":len(rows),
                "warning":"Solo prezzi lordi; spread, slippage e commissioni non inclusi. "
                          "COT e sentiment non provano causalità.",
                "segments":summary}
    finally:
        db.close()
