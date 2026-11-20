#!/usr/bin/env python3
# REMURA v0.8.50 LAB — 14/11/2026 10:46 CET
"""D -> B research handoff candidate, pure offline and not wired into Track B.
Caller supplies a private D1 export and an explicit decision timestamp.
Neither caller input nor schema validation independently attests provenance.
No future rows, fallback to old bars, institutional attribution or orders.
"""
from collections import Counter

from volume_features_v1 import analyze_export
from remura_tv_bridge_preview_v1 import MAX_EXPORT_ROWS

SCHEMA = "remura.tv.fx.asof.preview.v1"
M5 = 300_000
SYMBOL = "FXCM:EURUSD"

def handoff(rows, *, decision_ms, bar_close_ms):
    if (type(decision_ms) is not int or type(bar_close_ms) is not int
            or bar_close_ms <= 1_000_000_000_000 or bar_close_ms % M5
            or not bar_close_ms <= decision_ms < bar_close_ms + M5):
        raise ValueError("invalid_decision_window")
    if not isinstance(rows, list) or len(rows) > MAX_EXPORT_ROWS:
        raise ValueError("invalid_export_size")
    counts = Counter()
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            counts["MALFORMED_METADATA"] += 1
            continue
        if row.get("symbol") != SYMBOL or row.get("timeframe") != "5":
            counts["OTHER_COHORT_EXCLUDED"] += 1
            continue
        received, close = row.get("received_at_ms"), row.get("bar_close_ms")
        if type(received) is not int or type(close) is not int:
            counts["MALFORMED_METADATA"] += 1
            continue
        if received > decision_ms or close > decision_ms:
            counts["NOT_KNOWN_AT_DECISION"] += 1
            continue
        if close != bar_close_ms:
            counts["OTHER_BAR_EXCLUDED"] += 1
            continue
        selected.append(row)
    result = analyze_export(selected)
    observations = result["observations"]
    blocked = result["counts"].get("INVALID_ROW", 0) or result["quarantined_bars"]
    view = observations[0] if len(observations) == 1 and not blocked else None
    checks = {} if view is None else view["diagnostic_checks"]
    if blocked:
        status = "BLOCKED_INVALID_OR_CONFLICT"
    elif view is None:
        status = "NO_CURRENT_ASOF_OBSERVATION"
    elif not view["fx_timeliness_eligible"]:
        status = "BLOCKED_NOT_PROSPECTIVELY_TIMELY"
    elif any(v == "REVIEW" for v in checks.values()):
        status = "BLOCKED_DIAGNOSTIC_REVIEW"
    elif view["missing_fields"]:
        status = "PARTIAL_DESCRIPTIVE_ONLY"
    else:
        status = "DESCRIPTIVE_CANDIDATE_ONLY"
    admitted = status in ("PARTIAL_DESCRIPTIVE_ONLY", "DESCRIPTIVE_CANDIDATE_ONLY")
    # Never release unverified parameters or assert that the experiment matches
    # the frozen protocol. A future attested configuration is required.
    return {
        "schema": SCHEMA, "version": "0.8.50-lab",
        "symbol": SYMBOL, "bar_close_ms": bar_close_ms,
        "decision_ms": decision_ms, "status": status,
        "excluded_counts": dict(sorted(counts.items())),
        "selected_count": len(selected),
        "source_counts": result["counts"],
        "candidate": None if not admitted else {
            "received_at_ms": view["received_at_ms"],
            "event_type": view["event_type"],
            "observed_labels": view["observed_labels"],
            "missing_fields": view["missing_fields"],
            "observed": view["observed"],
            "diagnostic_checks": checks,
        },
        "configuration_status": "ALERT_INPUTS_NOT_ATTESTED",
        "provenance_status": "CALLER_EXPORT_NOT_INDEPENDENTLY_ATTESTED",
        "institutional_admissible": False,
        "predictive_admissible": False,
        "track_b_connected": False,
        "orders_enabled": False,
        "notifications_enabled": False,
    }
