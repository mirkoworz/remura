#!/usr/bin/env python3
"""REMURA 1.43 candidate: read-only evidence of recurring M15 session gaps.

This module is diagnostic only. Never fills candles, changes existing forward
validation outcomes or asserts that a broker officially closes at these times.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from collections import defaultdict
from pathlib import Path

from price_feed import parse_time, utcnow
from price_store import latest

UTC = dt.timezone.utc
METALS = ("XAGUSD", "XAUUSD")
LOOKBACK_DAYS = 14
MAX_SHORT_GAP_BARS = 8
MIN_MATCHING_DAYS = 3


def inspect_market(doc, now=None):
    now = (now or utcnow()).astimezone(UTC)
    empty = {
        "status": "unavailable", "shortGapCount": 0,
        "patterns": [], "recurringCandidate": False
    }
    if not isinstance(doc, dict) or doc.get("provider") != "ctrader":
        return empty
    frames = doc.get("timeframes")
    raw = frames.get("M15") if isinstance(frames, dict) else None
    if not isinstance(raw, list) or len(raw) < 2:
        return empty
    timestamps = []
    previous = None
    try:
        for bar in raw:
            stamp = parse_time(bar["t"]).astimezone(UTC)
            if (int(stamp.timestamp()) % 900
                    or (previous is not None and stamp <= previous)):
                return {**empty, "status": "invalid_timestamps"}
            # Never use a candle that has not completely closed.
            if stamp + dt.timedelta(minutes=15) <= now:
                timestamps.append(stamp)
            previous = stamp
    except (TypeError, ValueError, KeyError, OverflowError, AttributeError):
        return {**empty, "status": "invalid_timestamps"}
    if len(timestamps) < 2:
        return empty
    cutoff = now - dt.timedelta(days=LOOKBACK_DAYS)
    patterns = defaultdict(set)
    count = 0
    for before, after in zip(timestamps, timestamps[1:]):
        diff = int((after - before).total_seconds() / 900) - 1
        if not 1 <= diff <= MAX_SHORT_GAP_BARS:
            continue  # weekend or long interruption is NOT a daily-break candidate
        missing_start = before + dt.timedelta(minutes=15)
        if missing_start < cutoff or missing_start > now:
            continue
        count += 1
        signature = (missing_start.strftime("%H:%M"), diff)
        patterns[signature].add(missing_start.date().isoformat())
    groups = [
        {"startUtc": time, "missingM15": bars, "observedDays": len(dates)}
        for (time, bars), dates in patterns.items()
    ]
    groups.sort(key=lambda x: (-x["observedDays"], x["startUtc"], x["missingM15"]))
    return {
        "status": "observed", "shortGapCount": count, "patterns": groups[:5],
        "recurringCandidate": any(x["observedDays"] >= MIN_MATCHING_DAYS
                                  for x in groups)
    }


def session_gap_overview(db_path, now=None):
    """Aggregate-only read; no OHLC, provider symbol, account or credentials."""
    now = (now or utcnow()).astimezone(UTC)
    output = {"schema": "remura-session-gap-diagnostics-v1",
              "mode": "diagnostic_only",
              "checkedAt": now.isoformat(),
              "brokerHoursConfirmed": False,
              "warning": "Ripetizione compatibile con pausa del broker, "
                         "non conferma ufficiale. Nessuna statistica ricalcolata.",
              "markets": []}
    db_file = Path(db_path).expanduser().resolve()
    if not db_file.is_file():
        return output
    db = sqlite3.connect("file:" + str(db_file) + "?mode=ro", uri=True)
    try:
        for symbol in METALS:
            info = inspect_market(latest(db, symbol), now)
            output["markets"].append({"symbol": symbol, **info})
    finally:
        db.close()
    common = None
    for market in output["markets"]:
        choices = {(p["startUtc"], p["missingM15"])
                   for p in market["patterns"]
                   if p["observedDays"] >= MIN_MATCHING_DAYS}
        common = choices if common is None else common.intersection(choices)
    output["bothMetalsSamePattern"] = bool(common)
    return output
