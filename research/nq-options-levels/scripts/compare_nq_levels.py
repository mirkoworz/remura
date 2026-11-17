#!/usr/bin/env python3
"""Offline exploratory NQ zones vs previous-day QQQ GEX proxy. No trading/network."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ANCHORS = ("call_wall", "gamma_flip", "put_wall")

def utc_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)

def compare(manual, reference):
    if manual.get("instrument") != "NQ" or reference.get("symbol") != "QQQ":
        raise ValueError("only manual NQ vs QQQ-derived proxy supported")
    if reference.get("price_basis") != "NDX_index_proxy_not_NQ_futures":
        raise ValueError("reference price basis must be explicit")
    session = datetime.strptime(manual["session_date"], "%Y-%m-%d").date()
    ref_at = utc_timestamp(reference["as_of_utc"])
    if ref_at.date() >= session:
        raise ValueError("only previous-day GEX snapshots are permitted")
    levels = manual.get("levels")
    if (not isinstance(levels, list) or not levels or
        any(type(x) not in (int, float) or x <= 0 for x in levels) or
        len(levels) != len(set(levels)) or levels != sorted(levels, reverse=True)):
        raise ValueError("levels must be unique, positive, descending numbers")
    if manual.get("published_at_utc") is not None:
        utc_timestamp(manual["published_at_utc"])
    anchors = {}
    for key in ANCHORS:
        val = reference.get(key)
        if type(val) not in (int, float) or val <= 0:
            raise ValueError("invalid reference "+key)
        anchors[key] = float(val)
    comparisons = []
    for level in levels:
        best = min(ANCHORS, key=lambda k: (abs(level-anchors[k]), ANCHORS.index(k)))
        comparisons.append({
            "nq_operational_zone": level,
            "nearest_proxy_anchor": best,
            "proxy_anchor_level": anchors[best],
            "signed_distance_points": round(level-anchors[best], 2),
            "absolute_distance_points": round(abs(level-anchors[best]), 2),
        })
    return {
        "study": "REMURA_NQ_OPTIONS_REVERSE_ENGINEERING",
        "session_date": session.isoformat(),
        "reference_provider": reference.get("provider", "UNKNOWN"),
        "reference_as_of_utc": ref_at.isoformat().replace("+00:00","Z"),
        "reference_basis": reference["price_basis"],
        "manual_levels_published_at_verified": False,
        "causal_status": "EXPLORATORY_ONLY_NO_VERIFIED_FIRST_SEEN",
        "performance_claim": "NONE",
        "warning": "NDX index proxy vs NQ futures: point distances do not prove shared methodology.",
        "comparisons": comparisons,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manual", type=Path)
    p.add_argument("reference", type=Path)
    args = p.parse_args()
    with args.manual.open(encoding="utf-8") as f:
        manual = json.load(f)
    with args.reference.open(encoding="utf-8") as f:
        reference = json.load(f)
    print(json.dumps(compare(manual, reference), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
