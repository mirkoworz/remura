#!/usr/bin/env python3
"""REMURA v1.45 — two DISTINCT forward 24h experiments, research-only.

calendar24: exit at OPEN of the M15 starting exactly entry+24 calendar hours.
           If that instant lies in the verified XAU/XAG daily pause, use the
           first M15 OPEN after it (maximum 60 minutes), with delay reported.
trading96: exit at OPEN of the 97th authentic M15 after 96 CLOSED M15 bars.
           Real sessions may push elapsed wall-clock time over 24 hours.

Both require every observed M15 to be fully closed, strictly ordered, with
no synthetic candles. The only accepted intraweek gap is the directly verified
FP Markets XAUUSD/XAGUSD 21:00–22:00 UTC daily pause. No weekend interpolation
or generic broker-session assumptions; unsupported windows remain unevaluated.

Existing v1.40 outcomes are NEVER modified. Signal knowledge starts with the
original stored cohort entry_at, NOT the Tuesday date of the COT report.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from price_feed import parse_time, utcnow
from price_store import connect, latest
from statistical_validation import _bars, _statistics

UTC = dt.timezone.utc
STEP = dt.timedelta(minutes=15)
H24 = dt.timedelta(hours=24)
METRICS = ("calendar24", "trading96")
SEGMENTS = ("all", "aligned", "divergent",
            "observation", "technical_confirmation", "qualified_event")
# Evidence from user's cTrader FP Markets trading hours and actual M15
# gaps on Oct 21, 22, 26 and 27 2026. Do not claim global market schedules.
METAL_PAUSE_VERIFIED_FROM = dt.date(2026, 10, 21)


def _approved_gap(symbol, before, after):
    """Only the observed, verified one-hour daily metal break; never holidays."""
    return (
        symbol in ("XAUUSD", "XAGUSD")
        and before.date() >= METAL_PAUSE_VERIFIED_FROM
        and before.hour == 20 and before.minute == 45
        and after == before + dt.timedelta(minutes=75)
        and after.hour == 22 and after.minute == 0
    )


def _measurement(doc, symbol, start, entry_open, side, metric, now):
    """Return immutable factual outcome or None. No data from unclosed M15."""
    if metric not in METRICS or side not in (-1, 1):
        return None
    bars = _bars(doc)
    if not bars:
        return None
    start = start.astimezone(UTC)
    now = now.astimezone(UTC)
    if start not in bars or not math.isclose(bars[start][0], entry_open,
                                            rel_tol=1e-9, abs_tol=1e-9):
        return None
    timestamps = [t for t in bars if t >= start and t + STEP <= now]
    if not timestamps or timestamps[0] != start:
        return None

    target = start + H24
    if metric == "calendar24":
        if target + STEP > now:
            return None
        exit_idx = next((i for i, t in enumerate(timestamps) if t >= target), None)
        if exit_idx is None:
            return None
        exit_at = timestamps[exit_idx]
        # No "next Monday" exit; only genuine 1h daily metal session breaks.
        if exit_at > target and (
                symbol not in ("XAUUSD", "XAGUSD")
                or exit_at - target > dt.timedelta(minutes=60)):
            return None
    else:
        if len(timestamps) < 97:
            return None
        exit_idx = 96
        exit_at = timestamps[exit_idx]
    if exit_idx <= 0 or exit_at <= start:
        return None

    gap_count = 0
    for left, right in zip(timestamps[:exit_idx], timestamps[1:exit_idx+1]):
        if right - left == STEP:
            continue
        if not _approved_gap(symbol, left, right):
            return None
        gap_count += 1

    # A gap at the 24h calendar target must also be an explicitly permitted pause.
    if metric == "calendar24" and exit_at > target:
        if not _approved_gap(symbol, timestamps[exit_idx-1], exit_at):
            return None

    window = [bars[t] for t in timestamps[:exit_idx]]
    if metric == "trading96" and len(window) != 96:
        return None
    if any(t + STEP > now for t in timestamps[:exit_idx+1]):
        return None
    close_open = bars[exit_at][0]  # actual quote, not invented weekend price
    factor = 10000.0 / entry_open
    high = max(row[1] for row in window)
    low = min(row[2] for row in window)
    raw = (close_open - entry_open) * factor
    favorable = (high - entry_open) * factor if side == 1 else (entry_open - low) * factor
    adverse = (low - entry_open) * factor if side == 1 else (entry_open - high) * factor
    return {
        "exit_at": exit_at.isoformat(),
        "exit_open": close_open,
        "calendar_minutes": round((exit_at - start).total_seconds() / 60),
        "closed_m15": len(window),
        "verified_pauses": gap_count,
        "exit_delay_minutes": round((exit_at - target).total_seconds() / 60)
                              if metric == "calendar24" else 0,
        "directional_bps": round(side * raw, 6),
        "long_benchmark_bps": round(raw, 6),
        "favorable_bps": round(max(0, favorable), 6),
        "adverse_bps": round(min(0, adverse), 6),
    }


def ensure_tables(db):
    # Separate table: never change or rewrite legacy 1h/4h/24h measurements.
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_dual24_outcomes(
        symbol TEXT NOT NULL, report_date TEXT NOT NULL, stage TEXT NOT NULL,
        metric TEXT NOT NULL CHECK(metric IN ('calendar24','trading96')),
        entry_at TEXT NOT NULL, exit_at TEXT NOT NULL,
        evaluated_at TEXT NOT NULL,
        entry_open REAL NOT NULL CHECK(entry_open>0),
        exit_open REAL NOT NULL CHECK(exit_open>0),
        calendar_minutes INTEGER NOT NULL,
        closed_m15 INTEGER NOT NULL, verified_pauses INTEGER NOT NULL,
        exit_delay_minutes INTEGER NOT NULL,
        directional_bps REAL NOT NULL, long_benchmark_bps REAL NOT NULL,
        favorable_bps REAL NOT NULL, adverse_bps REAL NOT NULL,
        PRIMARY KEY(symbol,report_date,stage,metric),
        FOREIGN KEY(symbol,report_date,stage)
          REFERENCES squalincome_validation_cohorts(symbol,report_date,stage))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_dual24_metric"
               " ON squalincome_dual24_outcomes(metric,stage)")
    db.commit()


def update_dual24(db_path, now=None):
    """Idempotent add-only backfill from authentic pre-existing cohorts."""
    now = now or utcnow()
    db = connect(db_path)
    try:
        ensure_tables(db)
        try:
            cohorts = db.execute(
                "SELECT symbol,report_date,stage,cot_side,broker_symbol,"
                "entry_at,entry_open FROM squalincome_validation_cohorts"
            ).fetchall()
        except __import__("sqlite3").OperationalError:
            return {"outcomesAdded": 0}
        cache = {}
        added = 0
        for symbol, report_date, stage, side, broker, entry, opening in cohorts:
            try:
                start = parse_time(entry)
                if start > now or start + H24 + STEP > now:
                    continue
                if symbol not in cache:
                    cache[symbol] = latest(db, symbol)
                doc = cache[symbol]
                if not doc or doc.get("provider") != "ctrader" or doc.get("providerSymbol") != broker:
                    continue
                for metric in METRICS:
                    if db.execute(
                        "SELECT 1 FROM squalincome_dual24_outcomes"
                        " WHERE symbol=? AND report_date=? AND stage=? AND metric=?",
                        (symbol,report_date,stage,metric)).fetchone():
                        continue
                    result = _measurement(doc,symbol,start,opening,side,metric,now)
                    if result is None:
                        continue
                    with db:
                        cur = db.execute(
                            "INSERT OR IGNORE INTO squalincome_dual24_outcomes "
                            "(symbol,report_date,stage,metric,entry_at,exit_at,evaluated_at,"
                            "entry_open,exit_open,calendar_minutes,closed_m15,"
                            "verified_pauses,exit_delay_minutes,directional_bps,"
                            "long_benchmark_bps,favorable_bps,adverse_bps)"
                            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (symbol,report_date,stage,metric,start.isoformat(),
                             result["exit_at"],now.isoformat(),opening,
                             result["exit_open"],result["calendar_minutes"],
                             result["closed_m15"],result["verified_pauses"],
                             result["exit_delay_minutes"],result["directional_bps"],
                             result["long_benchmark_bps"],result["favorable_bps"],
                             result["adverse_bps"]))
                        added += int(cur.rowcount > 0)
            except (ValueError,KeyError,OverflowError,TypeError):
                continue
        return {"outcomesAdded":added}
    finally:
        db.close()


def dual24_status(db_path, now=None):
    """Aggregate only: no broker names, OHLC, trade entries or private tokens."""
    now = now or utcnow()
    db = connect(db_path)
    try:
        ensure_tables(db)
        try:
            cohort_rows = db.execute(
                "SELECT report_date,relationship,stage,entry_at "
                "FROM squalincome_validation_cohorts").fetchall()
        except __import__("sqlite3").OperationalError:
            cohort_rows = []
        rows = db.execute(
            "SELECT c.report_date,c.relationship,o.stage,o.metric,"
            "o.directional_bps,o.long_benchmark_bps,o.favorable_bps,"
            "o.adverse_bps,o.calendar_minutes,o.closed_m15,o.verified_pauses,"
            "o.exit_delay_minutes FROM squalincome_dual24_outcomes o "
            "JOIN squalincome_validation_cohorts c "
            "ON o.symbol=c.symbol AND o.report_date=c.report_date "
            "AND o.stage=c.stage").fetchall()
        potential = defaultdict(int)
        for week, relation, stage, at in cohort_rows:
            try:
                if parse_time(at) + H24 + STEP > now:
                    continue
            except (ValueError,TypeError):
                continue
            for metric in METRICS:
                potential[(metric,stage)] += 1
                if stage == "observation":
                    potential[(metric,"all")] += 1
                    potential[(metric,relation)] += 1
        groups = defaultdict(list)
        meta = defaultdict(list)
        for week, relation, stage, metric, direction, benchmark, favorable, adverse, duration, count, gaps, delay in rows:
            record = (relation,week,direction,benchmark,favorable,adverse)
            if stage == "observation":
                for name in ("all", relation):
                    groups[(metric,name)].append(record)
                    meta[(metric,name)].append((duration,count,gaps,delay))
            groups[(metric,stage)].append(record)
            meta[(metric,stage)].append((duration,count,gaps,delay))
        segments = []
        for metric in METRICS:
            for segment in SEGMENTS:
                sample = _statistics(groups[(metric,segment)])
                candidate = potential[(metric,segment)]
                measured = meta[(metric,segment)]
                n = len(measured)
                segments.append({
                    "metric":metric, "segment":segment,
                    "potentiallyMatureCohorts":candidate,
                    "unmeasuredCandidates":max(0,candidate-sample["samples"]),
                    "coveragePct":round(100*sample["samples"]/candidate,1) if candidate else None,
                    "meanElapsedHours":round(sum(m[0] for m in measured)/n/60,2) if n else None,
                    "meanVerifiedPauseCount":round(sum(m[2] for m in measured)/n,2) if n else None,
                    "delayedExits":sum(m[3]>0 for m in measured),
                    **sample
                })
        return {
            "schema":"remura-dual24-validation-v1",
            "mode":"research_only", "brokerHours":"user_verified_metal_pause_only",
            "noSyntheticCandles":True,
            "definitions":{
                "calendar24":"M15 open esattamente a 24h, o alla prima riapertura"
                             " entro 60 min solo durante una pausa verificata dei metalli",
                "trading96":"OPEN dopo 96 candele M15 autentiche e chiuse; pause incluse nel tempo trascorso"
            },
            "note":"Coorti 24h potenzialmente mature, non necessariamente verificabili: "
                   "pause e finestre incomplete rimangono senza esito. "
                   "Nessun dato futuro; spread, commissioni e slippage esclusi.",
            "cohorts":len(cohort_rows), "outcomes":len(rows), "segments":segments
        }
    finally:
        db.close()
