#!/usr/bin/env python3
# REMURA v0.8.48 LAB — 14/11/2026 09:38 CET
"""Pure diagnostic arithmetic checks; not evidence of institutional trades.
Conservative comparison tolerances are provisional, not calibrated.
A missing input is not a failed test. No inference about unavailable footprint.
"""
from math import isclose, isfinite

CHECKS = (
    "FP_NONNEGATIVE", "FP_TOTAL", "FP_DELTA", "FP_DELTA_PCT",
    "FP_VALUE_AREA_ORDER", "SIGNED_RESULT_ATR", "EFFICIENCY",
    "ER_DELTA_DIRECTION", "RETEST_DAY1", "RETEST_DAY2",
    "RETEST_DAY3", "RETEST_PREVIOUS_DAY",
)


def compare(actual, expected, *, abs_tol=1e-6, rel_tol=1e-5):
    if actual is None or expected is None:
        return "NOT_EVALUABLE"
    if not isfinite(expected):
        return "NOT_EVALUABLE"
    return "CONSISTENT" if isclose(actual, expected, abs_tol=abs_tol, rel_tol=rel_tol) else "REVIEW"


def diagnose(p):
    """Return only fixed check names and statuses. Input must be schema-validated."""
    fp, o, e = p["footprint"], p["ohlc"], p["events"]
    out = dict.fromkeys(CHECKS, "NOT_EVALUABLE")
    if fp["available"]:
        buy, sell, total, delta = (fp[k] for k in ("buy", "sell", "total", "delta"))
        v = (buy, sell, total)
        if all(x is not None for x in v):
            out["FP_NONNEGATIVE"] = "CONSISTENT" if min(v) >= 0 else "REVIEW"
            out["FP_TOTAL"] = compare(total, buy + sell)
        if buy is not None and sell is not None:
            out["FP_DELTA"] = compare(delta, buy - sell)
        if total is not None and total > 0 and delta is not None:
            out["FP_DELTA_PCT"] = compare(fp["delta_pct"], 100 * (delta / total), abs_tol=0.001)
        elif total == 0:
            out["FP_DELTA_PCT"] = "NOT_APPLICABLE" if fp["delta_pct"] is None else "REVIEW"
        if all(fp[k] is not None for k in ("val", "poc", "vah")):
            out["FP_VALUE_AREA_ORDER"] = "CONSISTENT" if fp["val"] <= fp["poc"] <= fp["vah"] else "REVIEW"
    delta = p["delta_intrabar"]
    atr = o["atr14"]
    if delta is not None and atr is not None and atr > 0:
        # Pine uses unrounded prices. Avoid overclaiming near zero/very small ATR.
        direction = (delta > 0) - (delta < 0)
        expected = direction * (o["close"] - o["open"]) / atr
        out["SIGNED_RESULT_ATR"] = compare(p["signed_result_atr"], expected, abs_tol=0.002, rel_tol=0.005)
    if p["effort"] is not None and p["effort"] > 0 and p["signed_result_atr"] is not None:
        out["EFFICIENCY"] = compare(p["efficiency"], p["signed_result_atr"] / p["effort"],
                                    abs_tol=0.002, rel_tol=0.005)
    if e["er_positive"] or e["er_negative"]:
        if delta is not None:
            out["ER_DELTA_DIRECTION"] = "CONSISTENT" if (
                (e["er_positive"] and delta > 0) or (e["er_negative"] and delta < 0)) else "REVIEW"
    else:
        out["ER_DELTA_DIRECTION"] = "NOT_APPLICABLE"
    for name in ("day1", "day2", "day3", "previous_day"):
        key = "RETEST_" + name.upper()
        if not e["retest_" + name]:
            out[key] = "NOT_APPLICABLE"
            continue
        price, origin = p["levels"][name], p["level_origin_ms"][name]
        if price is not None and origin is not None:
            out[key] = "CONSISTENT" if (
                origin < p["bar_close_ms"] and o["low"] <= price <= o["high"]) else "REVIEW"
        else:
            out[key] = "REVIEW"
    return out
