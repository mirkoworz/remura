#!/usr/bin/env python3
# REMURA v0.8.49 LAB — 14/11/2026 10:02 CET
"""Sequential diagnostics only, using earlier closed snapshots.
Pine lookback default is 30, but alert input snapshot is not transmitted.
No assumption that default settings are active. No predictions or orders.
"""
from collections import Counter, defaultdict, deque
from statistics import mean
from math import isfinite
from volume_quality_v1 import compare

M5 = 300_000
DEFAULT_LOOKBACK = 30

def level_id(level):
    # Rank can change; previous-day tracker is independently reset.
    family = "PREVIOUS_DAY" if level["name"] == "previous_day" else "DAY"
    return family, level["origin_ms"], level["price"]

def sequential_diagnostics(observations):
    """Count per-symbol diagnostics; never bridge missing or late bars.
    Conditional effort reconstruction assumes default period and complete history.
    Retest checks only reported flags, not absent events (toggles unknown).
    """
    grouped = defaultdict(list)
    for v in observations:
        grouped[(v["symbol"], v["timeframe"])].append(v)
    total = Counter()
    for stream in grouped.values():
        history = deque(maxlen=DEFAULT_LOOKBACK)
        prev = None
        for v in sorted(stream, key=lambda x: x["bar_close_ms"]):
            consecutive = (prev is not None and
                           v["bar_close_ms"] - prev["bar_close_ms"] == M5 and
                           v["transport_timely"] and prev["transport_timely"])
            if not consecutive:
                history.clear()
            o = v["observed"]
            delta = o["delta_intrabar_estimate"]
            if (v["transport_timely"] and len(history) == DEFAULT_LOOKBACK and
                    delta is not None and all(x is not None for x in history)):
                baseline = mean(history)
                expected = abs(delta)/baseline if baseline > 0 else None
                status = compare(o["effort_reported"], expected, abs_tol=0.002, rel_tol=0.005)
            else:
                status = "NOT_EVALUABLE"
            total["EFFORT_DEFAULT30_" + status] += 1
            # Only compare a level known in the previous bar. Moves to another
            # daily rank preserve its original touch state; previous-day separate.
            prior = defaultdict(list)
            if consecutive:
                for level in prev["observed"]["levels"]:
                    if level["name"] in ("day1", "day2", "day3", "previous_day"):
                        prior[level_id(level)].append(level)
            for level in o["levels"]:
                if not level.get("pine_retest_flag"):
                    continue
                candidates = prior.get(level_id(level), [])
                if len(candidates) != 1:
                    total["RETEST_NEW_VISIT_NOT_EVALUABLE"] += 1
                    continue
                old = candidates[0]
                touched = old["range_intersects_prior_level"]
                # Level just born on prior bar was not eligible for a touch.
                if old["origin_ms"] == prev["bar_close_ms"] and old["name"] != "previous_day":
                    touched = False
                if touched is None:
                    result = "NOT_EVALUABLE"
                elif touched:
                    result = "REVIEW"
                else:
                    result = "CONSISTENT"
                total["RETEST_NEW_VISIT_" + result] += 1
            if v["transport_timely"]:
                history.append(abs(delta) if delta is not None else None)
            else:
                history.clear()
            prev = v
    return {
        "counts": dict(sorted(total.items())),
        "effort_assumption": "DEFAULT_30_UNVERIFIED_ALERT_INPUTS",
        "lookback_bars": DEFAULT_LOOKBACK,
        "retest_assumption": "SAME_LEVEL_IDENTITY_ADJACENT_BARS_ONLY",
        "no_prediction": True,
    }
