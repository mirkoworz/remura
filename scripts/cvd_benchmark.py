"""Offline matched price-pivot vs CVD-proxy research gate, no trading actions.

This is a one-session technical follow-through experiment, NOT a return
backtest, strategy, independent samples, or evidence about institutions.
No input prices/symbols are written to disk or returned in summaries.
"""
from __future__ import annotations

from typing import Any

from scripts import cvd_divergence as d

MAX_OUTCOME = 16
MAX_CANDLES = 96


def _pivot_candidates(market: dict[str, Any], bars: list[dict[str, Any]],
                      p: dict[str, Any], now: int | float) -> list[dict[str, Any]]:
    """Same causal pivot, min separation, price ATR rules as detector."""
    highs, lows = [], []
    for i in range(p["left"], len(bars)-p["right"]):
        if d._pivot(bars, i, "h", p["left"], p["right"]):
            highs.append(i)
        if d._pivot(bars, i, "l", p["left"], p["right"]):
            lows.append(i)
    events = []
    day = d.iso(bars[-1]["t"])[:10]
    broker = market["providerSymbol"].strip()
    for kind, pivots in (("bearish_regular", highs), ("bullish_regular", lows)):
        for pos in range(1, len(pivots)):
            a, b = pivots[pos-1], pivots[pos]
            known = b + p["right"]
            if not p["minSeparation"] <= b-a <= p["maxSeparation"]:
                continue
            atr = d._atr(bars, known, p["atrPeriod"])
            if atr is None or atr <= 0:
                continue
            field = "h" if kind == "bearish_regular" else "l"
            aa, bb = bars[a][field], bars[b][field]
            price_pass = (bb > aa + atr*p["minPriceAtr"] if kind == "bearish_regular"
                          else bb < aa - atr*p["minPriceAtr"])
            if not price_pass:
                continue
            confirmation = bars[known]["t"] + d.STEP
            if confirmation > now:
                continue
            identifier = "|".join(map(str, (
                d.VERSION, "ctrader", broker, market["symbol"], "M15",
                day, kind, bars[a]["t"], bars[b]["t"],
            )))
            events.append({"id": identifier, "known": known, "atr": atr,
                           "side": -1 if kind == "bearish_regular" else 1})
    return events


def _summary(candidates: list[dict[str, Any]], bars: list[dict[str, Any]],
             selected_ids: set[str], horizon: int, movement: float) -> dict[str, Any]:
    eligible = [e for e in candidates if e["id"] in selected_ids]
    matured = 0
    favorable = unfavorable = neutral = 0
    for e in eligible:
        end = e["known"] + horizon
        if end >= len(bars):
            continue
        matured += 1
        forward = (bars[end]["c"]-bars[e["known"]]["c"]) * e["side"] / e["atr"]
        if forward >= movement:
            favorable += 1
        elif forward <= -movement:
            unfavorable += 1
        else:
            neutral += 1
    # A small one-day observation must not be presented as a success percentage.
    return {
        "candidates": len(eligible), "matured": matured,
        "pending": len(eligible)-matured,
        "favorable": favorable, "unfavorable": unfavorable, "neutral": neutral,
        "favorableFraction": round(favorable/matured, 6) if matured >= 30 else None,
        "minimumMaturedForFraction": 30,
    }


def _rotate(market: dict[str, Any], distance: int) -> dict[str, Any]:
    """One deterministic negative control: rotate volumes, preserve price/bars."""
    source = market["frames"]["M15"]
    volume = [bar["v"] for bar in source]
    shift = distance % len(source)
    shuffled = [dict(bar, v=volume[(i+shift)%len(source)])
                for i,bar in enumerate(source)]
    result = dict(market)
    result["frames"] = dict(market["frames"], M15=shuffled)
    return result


def evaluate(market: dict[str, Any], *, now: int | float,
             settings: dict[str, Any] | None = None,
             horizon_bars: int = 4,
             movement_atr: float = 0.1) -> dict[str, Any]:
    """Price-pivot baseline vs its CVD-filtered subset, with no forecast claim.

    Technical 'favorable' = directional change in CLOSE after fixed horizon,
    scaled by the ATR known at confirmation. This is NOT PnL; overlapping
    candidates are correlated and fees, spread, stop loss and risk absent.
    """
    if type(horizon_bars) is not int or not 1 <= horizon_bars <= MAX_OUTCOME:
        raise ValueError("invalid_horizon")
    if not d.finite(movement_atr) or not 0 < movement_atr < 1:
        raise ValueError("invalid_movement")
    p = d.parameters(settings)
    main = d.analyze(market, now=now, settings=p)
    if main["status"] != "ok":
        return {"status": "unavailable", "cause": main["status"],
                "priceOnly": None, "cvdFiltered": None,
                "rotatedVolumes": None, "realMarketAdvantage": "NOT_ESTABLISHED"}
    day = main["sessionUtc"]
    bars = [row for row in market["frames"]["M15"]
            if d.iso(row["t"])[:10] == day]
    if len(bars) > MAX_CANDLES or len(bars) < p["atrPeriod"]+1:
        return {"status": "unavailable", "cause": "sample_bounds",
                "priceOnly": None, "cvdFiltered": None,
                "rotatedVolumes": None, "realMarketAdvantage": "NOT_ESTABLISHED"}
    candidates = _pivot_candidates(market,bars,p,now)
    baseline_ids = {e["id"] for e in candidates}
    cvd_ids = {event["id"] for event in main["events"]}
    if not cvd_ids <= baseline_ids:
        raise ValueError("detector_baseline_mismatch")
    # Rotated volumes are a sensitivity/negative control, NOT a statistical
    # permutation-test p-value. Use pre-specified fixed offsets and no tuning.
    controls = []
    for offset in (3,7,13):
        # Rotate only this session; adding an earlier day would alter the
        # meaning of the negative control and session reset.
        partial = dict(market)
        partial["frames"] = dict(market["frames"], M15=bars)
        rotated = _rotate(partial,offset)
        negative = d.analyze(rotated,now=now,settings=p)
        if negative["status"]!="ok":
            raise ValueError("rotation_cvd_unavailable")
        control_ids = {item["id"] for item in negative["events"]}
        if not control_ids <= baseline_ids:
            raise ValueError("rotation_baseline_mismatch")
        controls.append({"offset":offset, **_summary(
            candidates,bars,control_ids,horizon_bars,movement_atr)})
    return {
        "status": "ready", "schema": "remura-cvd-research-v1",
        "sessionUtc": day, "candles": len(bars),
        "horizonBars": horizon_bars, "movementAtr": movement_atr,
        "priceOnly": _summary(candidates,bars,baseline_ids,horizon_bars,movement_atr),
        "cvdFiltered": _summary(candidates,bars,cvd_ids,horizon_bars,movement_atr),
        "rotatedVolumes": controls,
        "controlMeaning": "three_fixed_volume_rotations_not_permutation_test",
        "outcomeMeaning": "future_close_atr_direction_not_profit",
        "realMarketAdvantage": "NOT_ESTABLISHED",
        "eventsPersisted": False, "alertsEnabled": False,
    }
