"""Read-only replay of archived, closed cTrader M15 through the offline CVD pilot.

No network, broker/API, SQLite writes, alerting, or order actions.
Summaries omit source prices, tick counts, broker IDs and individual events.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

from scripts import cvd_benchmark as benchmark
from scripts import cvd_divergence as detector

MAX_M15 = 4000
MAX_SESSIONS = 45
MAX_EPOCH = 9_007_199_254_740_991
KINDS = ("priceOnly", "cvdFiltered")
FIELDS = ("candidates", "matured", "pending", "favorable", "unfavorable", "neutral")


def _timestamp(raw):
    if not isinstance(raw, str) or len(raw) > 40:
        raise ValueError("invalid_timestamp")
    try:
        stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() != dt.timedelta(0):
            raise ValueError("non_utc_timestamp")
        t = round(stamp.timestamp() * 1000)
        if not 0 <= t < MAX_EPOCH or t % detector.STEP:
            raise ValueError("unaligned_timestamp")
        return t
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("invalid_timestamp") from exc


def _rows(doc, symbol):
    if not isinstance(doc, dict) or doc.get("schema") != "remura-price-v1":
        raise ValueError("invalid_schema")
    markets = doc.get("markets")
    if not isinstance(markets, dict) or set(markets) != {symbol}:
        raise ValueError("unapproved_market")
    market = markets[symbol]
    if (not isinstance(market, dict) or market.get("symbol") != symbol or
            symbol not in detector.PILOT or market.get("provider") != "ctrader" or
            not isinstance(market.get("providerSymbol"), str) or
            not 1 <= len(market["providerSymbol"].strip()) <= 100 or
            market.get("sourceTimeframe") != "M15" or
            market.get("timezone") != "UTC"):
        raise ValueError("unapproved_source")
    frames = market.get("timeframes")
    if not isinstance(frames, dict):
        raise ValueError("missing_timeframes")
    series = frames.get("M15")
    if not isinstance(series, list) or not 1 <= len(series) <= MAX_M15:
        raise ValueError("invalid_m15_size")
    out = []
    previous = -1
    for item in series:
        if not isinstance(item, dict):
            raise ValueError("invalid_bar")
        t = _timestamp(item.get("t"))
        if t <= previous:
            raise ValueError("unordered_or_duplicate")
        previous = t
        prices = [item.get(k) for k in ("o", "h", "l", "c")]
        if (any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0
                for x in prices) or
                item["h"] < max(item["o"], item["c"]) or
                item["l"] > min(item["o"], item["c"])):
            raise ValueError("invalid_ohlc")
        # Volume availability is assessed within the detector per session.
        volume = item.get("v")
        if volume is not None and (type(volume) is not int or
                                   not 0 <= volume <= MAX_EPOCH):
            raise ValueError("invalid_volume")
        row = {key: item[key] for key in ("o", "h", "l", "c")}
        row["t"] = t
        if "v" in item:
            row["v"] = volume
        out.append(row)
    return market, out


def _totals():
    return {field: 0 for field in FIELDS}


def _merge(total, part):
    if not isinstance(part, dict) or any(type(part.get(f)) is not int or
                                         part[f] < 0 for f in FIELDS):
        raise ValueError("invalid_benchmark_summary")
    if total["candidates"] + part["candidates"] > 10000:
        raise ValueError("too_many_events")
    for field in FIELDS:
        total[field] += part[field]
    if total["candidates"] != total["matured"] + total["pending"]:
        raise ValueError("maturity_mismatch")
    if total["matured"] != total["favorable"] + total["unfavorable"] + total["neutral"]:
        raise ValueError("outcome_mismatch")


def _view(total):
    return {**total,
            "favorableFraction": (
                round(total["favorable"] / total["matured"], 6)
                if total["matured"] >= 30 else None),
            "minimumMaturedForFraction": 30}


def analyze_document(doc, symbol, *, max_sessions=MAX_SESSIONS):
    """Analyze only UTC sessions available as of their own last closed bar."""
    if type(max_sessions) is not int or not 1 <= max_sessions <= MAX_SESSIONS:
        raise ValueError("invalid_session_limit")
    if symbol not in detector.PILOT:
        raise ValueError("unapproved_symbol")
    market, rows = _rows(doc, symbol)
    grouped = defaultdict(list)
    for bar in rows:
        day = dt.datetime.fromtimestamp(bar["t"]/1000,dt.timezone.utc).date()
        grouped[day].append(bar)
    day_keys = sorted(grouped)[-max_sessions:]
    totals = {kind: _totals() for kind in KINDS}
    controls = {offset: _totals() for offset in (3, 7, 13)}
    causes = {}
    complete_days = 0
    for day in day_keys:
        bars = grouped[day]
        # A midnight-to-close session may legitimately be shorter; don't
        # invent missing hours or compare pivots across the UTC day boundary.
        if not 15 <= len(bars) <= 96:
            causes["session_too_short"] = causes.get("session_too_short",0)+1
            continue
        subset = {**market, "frames": {"M15":bars,"H1":[],"H4":[]}}
        asof = bars[-1]["t"] + detector.STEP + 1000
        report = benchmark.evaluate(subset,now=asof,horizon_bars=4,movement_atr=0.1)
        if report["status"] != "ready":
            reason = report.get("cause", "unavailable")
            if reason not in ("partial","missing","invalid","insufficient",
                              "stale","sample_bounds","unsupported"):
                reason = "unavailable"
            causes[reason] = causes.get(reason,0)+1
            continue
        complete_days += 1
        for key in KINDS:
            _merge(totals[key],report[key])
        for entry in report["rotatedVolumes"]:
            if entry.get("offset") not in controls:
                raise ValueError("invalid_control_offset")
            _merge(controls[entry["offset"]],entry)
    return {
        "schema": "remura-cvd-archive-replay-v1",
        "status": "ready" if complete_days else "insufficient",
        "source": "private_cTrader_archived_M15_read_only",
        "sessionsAvailable":len(grouped),
        "sessionsConsidered":len(day_keys),
        "sessionsEligible":complete_days,
        "sessionsExcluded":len(day_keys)-complete_days,
        "exclusionCounts":{key:causes[key] for key in sorted(causes)},
        "priceOnly":_view(totals["priceOnly"]),
        "cvdFiltered":_view(totals["cvdFiltered"]),
        "rotatedVolumes":[{"offset":key,**_view(controls[key])} for key in controls],
        "outcomeMeaning":"forward_four_M15_closes_ATR_not_PnL",
        "statistics":"descriptive_correlated_not_walk_forward",
        "edge":"NOT_ESTABLISHED",
        "newBrokerCalls":0,
        "alertsEnabled":False,
    }
