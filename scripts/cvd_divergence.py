"""Offline causal price/CVD-proxy M15 detector, parity target for the JS pilot.

No broker/network, database, orders, notifications, or side effects.
CVD is close-location-value multiplied by quote tick volume, NOT real
buyer/seller aggressor volume. UTC epochs in milliseconds, bars CLOSED.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

STEP = 900_000
DAY = 86_400_000
VERSION = "cvd-divergence-proxy-m15-v1"
PILOT = frozenset(("EURUSD", "XAUUSD"))
DEFAULTS = {
    "left": 2, "right": 2, "minSeparation": 3, "maxSeparation": 36,
    "atrPeriod": 14, "minPriceAtr": 0.1, "minCvdFraction": 0.04,
}
SAFE_INT = 2**53 - 1


def finite(value: Any) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def iso(ms: int | float) -> str:
    stamp = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond // 1000:03d}Z"


def unavailable(status: str, reason: str, now: Any, **extra: Any) -> dict[str, Any]:
    return {
        "status": status, "reason": reason,
        "asOf": iso(now) if finite(now) else None,
        "method": "CLV × tick volume cTrader (proxy, non volume eseguito)",
        "algorithm": VERSION, "events": [], **extra,
    }


def parameters(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    p = {**DEFAULTS, **(raw or {})}
    for key in ("left", "right", "minSeparation", "maxSeparation", "atrPeriod"):
        n = p.get(key)
        if type(n) is not int or not 1 <= n <= 100:
            raise ValueError("invalid_parameter_" + key)
    if p["minSeparation"] > p["maxSeparation"] or p["left"] > 12 or p["right"] > 12:
        raise ValueError("invalid_pivot_window")
    for key in ("minPriceAtr", "minCvdFraction"):
        n = p.get(key)
        if not finite(n) or not 0 <= n < 1:
            raise ValueError("invalid_tolerance_" + key)
    return p


def _pivot(rows: list[dict[str, Any]], index: int, field: str, left: int, right: int) -> bool:
    value = rows[index][field]
    return all(
        value > rows[j][field] if field == "h" else value < rows[j][field]
        for j in range(index - left, index + right + 1) if j != index
    )


def _atr(rows: list[dict[str, Any]], index: int, period: int) -> float | None:
    if index < period:
        return None
    total = 0.0
    for i in range(index - period + 1, index + 1):
        bar, previous = rows[i], rows[i-1]
        total += max(bar["h"] - bar["l"], abs(bar["h"] - previous["c"]),
                     abs(bar["l"] - previous["c"]))
    return total / period


def _flow(market: dict[str, Any], now: int | float) -> dict[str, Any]:
    all_rows = market.get("frames", {}).get("M15") or []
    last = all_rows[-1] if all_rows else None
    if last is None:
        return {"status": "missing", "reason": "Candele M15 assenti."}
    close_at = last["t"] + STEP
    if close_at > now + 300_000 or now - close_at > 90 * 60_000:
        return {"status": "stale", "reason": "Ultima M15 troppo vecchia: non ricostruiamo un CVD live."}
    day = iso(last["t"])[:10]
    rows = [bar for bar in all_rows if iso(bar["t"])[:10] == day]
    if len(rows) < 8:
        return {"status": "missing", "reason": "Servono almeno 8 M15 della sessione UTC."}
    if any(type(bar["v"]) is not int or not 0 <= bar["v"] <= SAFE_INT for bar in rows):
        return {"status": "missing", "reason": "Alcune M15 non contengono tick volume valido."}
    cumulative = 0.0
    points = []
    previous = None
    gaps = 0
    for bar in rows:
        if previous is not None and bar["t"] - previous != STEP:
            gaps += 1
        spread = bar["h"] - bar["l"]
        clv = max(-1.0, min(1.0, (2*bar["c"]-bar["h"]-bar["l"])/spread)) if spread > 0 else 0.0
        delta = bar["v"] * clv
        cumulative += delta
        points.append({"t": bar["t"], "delta": delta, "cvd": cumulative})
        previous = bar["t"]
    if rows[0]["t"] % DAY != 0 or gaps:
        return {"status": "partial", "reason": "Sessione UTC parziale o con gap: CVD N/D per non sommare dati incompleti."}
    return {"status": "ok", "day": day, "points": points}


def analyze(market: dict[str, Any] | None, *, now: int | float,
            settings: dict[str, Any] | None = None) -> dict[str, Any]:
    p = parameters(settings)
    if not finite(now) or now < 0:
        return unavailable("invalid", "Ora di scansione non valida.", now)
    if not isinstance(market, dict) or market.get("symbol") not in PILOT:
        return unavailable("unsupported", "Pilota limitato a EURUSD e XAUUSD.", now)
    if market.get("provider") != "ctrader" or not isinstance(market.get("providerSymbol"), str) or not market["providerSymbol"].strip():
        return unavailable("missing", "Fonte/broker cTrader non verificato.", now)
    rows = market.get("frames", {}).get("M15")
    if not isinstance(rows, list) or not rows:
        return unavailable("missing", "Non esistono M15 chiuse.", now)
    prev = -math.inf
    for bar in rows:
        if not isinstance(bar, dict):
            return unavailable("invalid", "Orari o OHLC non confermati.", now)
        t = bar.get("t")
        prices = [bar.get(field) for field in ("o", "h", "l", "c")]
        if (not finite(t) or t % STEP != 0 or t <= prev or t + STEP > now or
            not all(finite(v) and v > 0 for v in prices) or
            bar["h"] < max(bar["o"], bar["c"]) or
            bar["l"] > min(bar["o"], bar["c"]) or
            bar["h"] < bar["l"]):
            return unavailable("invalid", "Orari o OHLC non confermati.", now)
        volume = bar.get("v")
        if type(volume) is not int or not 0 <= volume <= SAFE_INT:
            return unavailable("missing", "Tick volume non disponibile o invalido.", now)
        prev = t
    flow = _flow(market, now)
    if flow["status"] != "ok":
        return unavailable(flow["status"], flow["reason"], now)
    day = flow["day"]
    current = [bar for bar in rows if iso(bar["t"])[:10] == day]
    pts = flow["points"]
    if len(current) != len(pts) or any(bar["t"] != point["t"] for bar, point in zip(current, pts)):
        return unavailable("invalid", "Allineamento candele/CVD incoerente.", now)
    if len(current) < max(p["atrPeriod"] + 1, p["left"] + p["right"] + 2, 8):
        return unavailable("insufficient", "Sessione troppo breve per pivot e ATR.", now)
    highs = []
    lows = []
    for i in range(p["left"], len(current) - p["right"]):
        if _pivot(current, i, "h", p["left"], p["right"]):
            highs.append(i)
        if _pivot(current, i, "l", p["left"], p["right"]):
            lows.append(i)
    events = []
    for kind, pivots in (("bearish_regular", highs), ("bullish_regular", lows)):
        for k in range(1, len(pivots)):
            a, b = pivots[k-1], pivots[k]
            known = b + p["right"]
            if not p["minSeparation"] <= b-a <= p["maxSeparation"]:
                continue
            atr = _atr(current, known, p["atrPeriod"])
            if not finite(atr) or atr <= 0:
                continue
            ticks = sum(current[j]["v"] for j in range(a+1, known+1))
            if ticks <= 0:
                continue
            price_a = current[a]["h" if kind == "bearish_regular" else "l"]
            price_b = current[b]["h" if kind == "bearish_regular" else "l"]
            cvd_a, cvd_b = pts[a]["cvd"], pts[b]["cvd"]
            price_limit = atr * p["minPriceAtr"]
            cvd_limit = ticks * p["minCvdFraction"]
            match = (
                price_b > price_a + price_limit and cvd_b < cvd_a - cvd_limit
                if kind == "bearish_regular" else
                price_b < price_a - price_limit and cvd_b > cvd_a + cvd_limit
            )
            if not match:
                continue
            confirmed = current[known]["t"] + STEP
            if confirmed > now:
                continue
            broker = market["providerSymbol"].strip()
            identifier = "|".join(map(str, (
                VERSION, "ctrader", broker, market["symbol"], "M15",
                day, kind, current[a]["t"], current[b]["t"],
            )))
            events.append({
                "id": identifier, "algorithm": VERSION,
                "symbol": market["symbol"], "provider": "ctrader",
                "providerSymbol": broker, "timeframe": "M15",
                "sessionUtc": day, "type": kind,
                "side": "bearish" if kind == "bearish_regular" else "bullish",
                "state": "confirmed_technical_not_trade_signal",
                "first": {"pivotAt": iso(current[a]["t"]), "price": price_a, "cvdProxy": cvd_a},
                "second": {"pivotAt": iso(current[b]["t"]), "price": price_b, "cvdProxy": cvd_b},
                "confirmedAt": iso(confirmed),
                "threshold": {
                    "atr14OrConfigured": atr, "price": price_limit,
                    "tickVolumeBetweenAndConfirmation": ticks,
                    "cvdProxy": cvd_limit,
                },
                "note": "Divergenza tecnica fra prezzo e proxy CLV×tick volume; non prova pressione buy/sell reale.",
            })
    events.sort(key=lambda e: (e["confirmedAt"], e["id"]))
    return {
        "status": "ok",
        "reason": ("Divergenze tecniche confermate sui dati chiusi." if events else
                   "Nessuna divergenza confermata nel campione disponibile."),
        "asOf": iso(now),
        "method": "CLV × tick volume cTrader (proxy, non volume eseguito)",
        "algorithm": VERSION, "sessionUtc": day,
        "candles": len(current), "events": events,
        "notificationEnabled": False, "persistenceEnabled": False,
        "caveat": "Il proxy dipende anche dal prezzo: valore predittivo e latenza degli avvisi non ancora validati.",
    }
