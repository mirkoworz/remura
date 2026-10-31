#!/usr/bin/env python3
"""REMURA Shark Science Lab: offline, read-only M15 hypothesis comparison.

This is a research baseline, NOT a trading signal or an execution simulator.
Only closed, broker-consistent candles provided by the caller are accepted.
Signals use data up to the close; theoretical entries use the next bar open.
No network, database, positions, API tokens, or writes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

STEP = dt.timedelta(minutes=15)
MIN_TRADES = 30
MIN_WEEKS = 8
STRATEGIES = ("breakout", "pullback")


def _time(value):
    if isinstance(value, dt.datetime):
        stamp = value
    elif isinstance(value, str):
        stamp = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError("invalid_timestamp")
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timestamp_requires_timezone")
    return stamp.astimezone(dt.timezone.utc)


def _bars(rows, as_of):
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValueError("invalid_m15_rows")
    now = _time(as_of)
    out = []
    for bar in rows:
        if not isinstance(bar, dict):
            raise ValueError("invalid_candle")
        t = _time(bar.get("t"))
        if int(t.timestamp()) % 900:
            raise ValueError("unaligned_m15")
        try:
            prices = tuple(float(bar[k]) for k in ("o", "h", "l", "c"))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid_ohlc") from exc
        o, h, l, c = prices
        if (not all(math.isfinite(x) and x > 0 for x in prices)
                or h < max(o, l, c) or l > min(o, h, c)):
            raise ValueError("invalid_ohlc")
        if t + STEP > now:
            raise ValueError("incomplete_or_future_bar")
        if out and t <= out[-1][0]:
            raise ValueError("out_of_order_or_duplicate")
        out.append((t, o, h, l, c))
    return out


def _continuous(bars, first, last):
    return all(bars[i][0] - bars[i - 1][0] == STEP
               for i in range(first + 1, last + 1))


def _mean_close(bars, ending, count):
    return sum(bar[4] for bar in bars[ending - count + 1:ending + 1]) / count


def _direction(bars, i, strategy, lookback):
    """No access to bars after i: the hypothesis is observable at candle close."""
    if strategy == "breakout":
        if i < lookback or not _continuous(bars, i - lookback, i):
            return 0
        previous = bars[i - lookback:i]
        if bars[i][4] > max(b[2] for b in previous):
            return 1
        if bars[i][4] < min(b[3] for b in previous):
            return -1
        return 0
    # Long/short recovery of 10-bar mean aligned with 30-bar mean.
    if i < 30 or not _continuous(bars, i - 30, i):
        return 0
    slow = _mean_close(bars, i, 30)
    fast = _mean_close(bars, i, 10)
    old_fast = _mean_close(bars, i - 1, 10)
    if bars[i][4] > fast > slow and bars[i - 1][4] <= old_fast:
        return 1
    if bars[i][4] < fast < slow and bars[i - 1][4] >= old_fast:
        return -1
    return 0


def _week(t):
    y, w, _ = t.isocalendar()
    return f"{y:04d}-W{w:02d}"


def _metrics(trades):
    n = len(trades)
    if not n:
        return {"trades": 0, "weeks": 0, "netMeanBps": None,
                "netTotalBps": None, "winRatePct": None,
                "profitFactor": None, "maxDrawdownBps": None,
                "evidence": "insufficient"}
    net = [trade["netBps"] for trade in trades]
    winners = sum(x > 0 for x in net)
    gains = sum(x for x in net if x > 0)
    losses = -sum(x for x in net if x < 0)
    equity = peak = drawdown = 0.0
    for x in net:
        equity += x
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    weeks = len({_week(trade["entryAt"]) for trade in trades})
    return {"trades": n, "weeks": weeks,
            "netMeanBps": round(sum(net) / n, 4),
            "netTotalBps": round(sum(net), 4),
            "winRatePct": round(100 * winners / n, 2),
            "profitFactor": round(gains / losses, 4) if losses else None,
            "maxDrawdownBps": round(drawdown, 4),
            # A sufficient sample is still exploratory, not validated.
            "evidence": "insufficient" if n < MIN_TRADES or weeks < MIN_WEEKS
                        else "exploratory"}


def evaluate(rows, *, as_of, round_trip_cost_bps, strategy="breakout",
             hold_bars=4, lookback=12):
    """Evaluate a frozen hypothesis. Returns aggregate metrics, never a live order.

    round_trip_cost_bps must represent spread + commissions + slippage
    paid for entry and exit together, measured in basis points of price.
    No intrabar SL/TP is simulated; exit is a closed M15 bar's close.
    """
    if strategy not in STRATEGIES:
        raise ValueError("unsupported_strategy")
    if (type(hold_bars) is not int or not 1 <= hold_bars <= 96
            or type(lookback) is not int or not 5 <= lookback <= 96):
        raise ValueError("invalid_parameters")
    try:
        cost = float(round_trip_cost_bps)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("explicit_round_trip_cost_required") from exc
    if not math.isfinite(cost) or cost <= 0:
        raise ValueError("explicit_positive_cost_required")
    bars = _bars(rows, as_of)
    samples = []
    first = max(lookback, 30 if strategy == "pullback" else lookback)
    i = first
    while i + hold_bars < len(bars):
        direction = _direction(bars, i, strategy, lookback)
        entry_i = i + 1
        exit_i = i + hold_bars
        if (direction and _continuous(bars, i, exit_i)
                and _week(bars[entry_i][0]) == _week(bars[exit_i][0])):
            entry, exit_close = bars[entry_i][1], bars[exit_i][4]
            gross = direction * (exit_close - entry) * 10000 / entry
            samples.append({"entryAt": bars[entry_i][0], "exitAt": bars[exit_i][0] + STEP,
                            "side": direction, "grossBps": round(gross, 6),
                            "netBps": round(gross - cost, 6)})
            # Non-overlapping hypothetical positions.
            i = exit_i + 1
        else:
            i += 1
    distinct_weeks = sorted({_week(t["entryAt"]) for t in samples})
    holdout_count = max(1, (len(distinct_weeks) + 3) // 4) if distinct_weeks else 0
    holdout_weeks = set(distinct_weeks[-holdout_count:]) if holdout_count else set()
    training = [t for t in samples if _week(t["entryAt"]) not in holdout_weeks]
    holdout = [t for t in samples if _week(t["entryAt"]) in holdout_weeks]
    return {"schema": "remura-shark-science-v1", "strategy": strategy,
            "timeframe": "M15", "execution": "next_bar_open_to_closed_bar_close",
            "holdBars": hold_bars, "lookback": lookback,
            "roundTripCostBps": cost, "asOf": _time(as_of).isoformat(),
            "assumptions": ["single_broker_input_required", "hypothetical_fills",
                            "fixed_estimated_costs", "no_intrabar_stops",
                            "no_future_features", "no_automatic_orders"],
            "all": _metrics(samples), "train": _metrics(training),
            "holdout": _metrics(holdout),
            "verdict": "research_only_never_live_signal"}


def main():
    parser = argparse.ArgumentParser(description="Offline REMURA M15 hypothesis study")
    parser.add_argument("--input", required=True, help="Local JSON of M15 rows or cTrader price document")
    parser.add_argument("--as-of", required=True, help="UTC timestamp after all included bar closes")
    parser.add_argument("--cost-bps", required=True, type=float,
                        help="Positive estimated round-trip spread+slippage+fees in bps")
    parser.add_argument("--strategy", choices=STRATEGIES, default="breakout")
    args = parser.parse_args()
    file = Path(args.input)
    if not file.is_file() or file.stat().st_size > 8_000_000:
        parser.error("input_missing_or_too_large")
    doc = json.loads(file.read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        if doc.get("provider") != "ctrader" or not doc.get("providerSymbol"):
            parser.error("single_verified_ctrader_provider_required")
        rows = doc.get("timeframes", {}).get("M15")
    else:
        rows = doc
    # No raw price or trade records are printed.
    print(json.dumps(evaluate(rows, as_of=args.as_of,
                              round_trip_cost_bps=args.cost_bps,
                              strategy=args.strategy), indent=2))


if __name__ == "__main__":
    main()
