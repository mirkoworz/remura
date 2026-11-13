#!/usr/bin/env python3
# REMURA v0.8.15 LAB — 13/11/2026, ore 13:00 CET
# SOLO OFFLINE: esportazione D1 -> osservazioni spiegabili, NO network/ordini.
"""Adapt an offline D1 JSONL export to a NON-TRADING REMURA observation preview.

Never interpret FXCM-intrabar classification as institutional executions.
Requires REAL receiver timestamps + exact D1 identity matching; excludes
late/invalid/duplicate data from prospective observations. It is not a
live D1 connector, signal generator, or verified edge.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from validate_telemetry_v1 import InvalidTelemetry, validate_payload

VERSION = "0.8.15-lab"
OUTPUT_SCHEMA = "remura.tv.observation.preview.v1"
EXPECTED_COLUMNS = frozenset({
    "event_key", "received_at_ms", "bar_close_ms", "symbol",
    "timeframe", "event_type", "version", "is_timely", "raw_json",
})
MAX_RAW_BYTES = 20_000
MAX_EXPORT_ROWS = 10_000
EVENT_LABELS = {
    "peak": "DELTA_PEAK",
    "er_positive": "EFFORT_RESULT_POSITIVE",
    "er_negative": "EFFORT_RESULT_NEGATIVE",
    "retest_day1": "RETEST_DAY1",
    "retest_day2": "RETEST_DAY2",
    "retest_day3": "RETEST_DAY3",
    "retest_previous_day": "RETEST_PREVIOUS_DAY",
}


class BridgeInputError(ValueError):
    pass


def decode_export_row(row: object) -> tuple[dict, dict]:
    if not isinstance(row, dict) or set(row) != EXPECTED_COLUMNS:
        raise BridgeInputError("export_schema_mismatch")
    if type(row["raw_json"]) is not str:
        raise BridgeInputError("raw_json_invalid")
    if len(row["raw_json"].encode("utf-8")) > MAX_RAW_BYTES:
        raise BridgeInputError("raw_json_too_large")
    if type(row["is_timely"]) is not int or row["is_timely"] not in (0, 1):
        raise BridgeInputError("stored_timeliness_invalid")
    if type(row["received_at_ms"]) is not int:
        raise BridgeInputError("receiver_timestamp_invalid")
    try:
        # Reject JSON NaN/Infinity explicitly (Python json accepts them by default).
        def reject_constant(_value: str):
            raise ValueError("nonfinite")
        p = json.loads(row["raw_json"], parse_constant=reject_constant)
        parsed = validate_payload(p, received_ms=row["received_at_ms"])
    except (ValueError, TypeError, KeyError, InvalidTelemetry) as exc:
        raise BridgeInputError("payload_validation_failed") from None
    required_matches = {
        "event_key": parsed["event_key"],
        "bar_close_ms": p["bar_close_ms"],
        "symbol": p["symbol"],
        "timeframe": p["timeframe"],
        "event_type": p["event_type"],
        "version": p["version"],
        "is_timely": int(parsed["timely_for_prospective"]),
    }
    if any(type(row[k]) is not type(v) or row[k] != v
           for k, v in required_matches.items()):
        raise BridgeInputError("d1_identity_or_timeliness_mismatch")
    return p, parsed


def labels_for(p: dict) -> list[str]:
    ev = p["events"]
    labels = [name for field, name in EVENT_LABELS.items() if ev[field]]
    if ev["day_level_action"] != "NONE":
        labels.append("DAY_" + ev["day_level_action"])
    return sorted(labels)


def preview_record(row: object) -> dict:
    p, parsed = decode_export_row(row)
    tags = labels_for(p)
    footprint = p["footprint"]
    timely = bool(parsed["timely_for_prospective"])
    missing = []
    if not p["quality"]["has_intrabar_delta"]:
        missing.append("DELTA_NOT_AVAILABLE")
    if not footprint["available"]:
        missing.append("FOOTPRINT_NOT_AVAILABLE")
    if p["ohlc"]["atr14"] is None or p["ohlc"]["atr14"] <= 0:
        missing.append("ATR_NOT_AVAILABLE")
    if not timely:
        state = "LATE_NOT_PROSPECTIVE"
        reasons = ["RECEIPT_OUTSIDE_PRE_REGISTERED_WINDOW"]
    elif missing:
        state = "PARTIAL_OBSERVATION"
        reasons = sorted(missing)
    else:
        state = "OBSERVATION_ONLY"
        reasons = ["NO_VALIDATED_EDGE"]
    if p["event_type"] == "HEARTBEAT":
        reasons = [*reasons, "BASELINE_BAR_NOT_A_SIGNAL"]
    # Full source and raw_json remain in the private D1 export, not this view.
    return {
        "schema": OUTPUT_SCHEMA,
        "version": VERSION,
        "event_key": parsed["event_key"],
        "symbol": p["symbol"],
        "timeframe": p["timeframe"],
        "bar_close_ms": p["bar_close_ms"],
        "received_at_ms": row["received_at_ms"],
        "latency_ms": parsed["lag_ms"],
        "source": "TRADINGVIEW_FXCM_INTRABAR_PROXY_NOT_INSTITUTIONAL",
        "event_type": p["event_type"],
        "event_labels": tags,
        "close": p["ohlc"]["close"],
        "delta_intrabar_estimate": p["delta_intrabar"],
        "footprint_available": footprint["available"],
        "poc_if_available": footprint["poc"] if footprint["available"] else None,
        "levels": dict(p["levels"]),
        "daily_anchor": p["quality"]["daily_anchor"],
        "prospective_eligible": timely,
        "status": state,
        "reasons": reasons,
        "verdict": "NESSUN_SEGNALE_OPERATIVO",
        "proof_of_institutional_activity": False,
        "statistical_edge_validated": False,
        "orders_enabled": False,
    }


def preview_export(rows: list[object]) -> dict:
    if not isinstance(rows, list) or len(rows) > MAX_EXPORT_ROWS:
        raise BridgeInputError("export_row_limit_exceeded")
    # Identical repeats are ignored; conflicting payloads sharing one event_key
    # quarantine the entire key, never silently keeping a convenient version.
    seen: dict[str, tuple[str, dict]] = {}
    conflicted = set()
    counts = Counter()
    for row in rows:
        try:
            view = preview_record(row)
        except BridgeInputError:
            counts["REJECTED_INVALID"] += 1
            continue
        key = view["event_key"]
        if key in conflicted:
            counts["CONFLICTING_DUPLICATE_QUARANTINED"] += 1
            continue
        if key in seen:
            previous_raw, previous_view = seen[key]
            if previous_raw == row["raw_json"]:
                counts["DUPLICATE_SKIPPED"] += 1
            else:
                counts["CONFLICTING_DUPLICATE_QUARANTINED"] += 1
                counts[previous_view["status"]] -= 1
                del seen[key]
                conflicted.add(key)
            continue
        seen[key] = (row["raw_json"], view)
        counts[view["status"]] += 1
    events = [value[1] for value in seen.values()]
    return {
        "schema": "remura.tv.preview.batch.v1",
        "version": VERSION,
        "mode": "OFFLINE_EXPORT_ONLY_NO_LIVE_CONNECTOR",
        "source": "TRADINGVIEW_INTRABAR_ESTIMATE_NOT_CME",
        "row_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "observations": events,
        "prospective_validation_still_required": True,
        "no_trade": True,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="REMURA D1 -> preview offline: NON operativo")
    p.add_argument("export_jsonl", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        raw = args.export_jsonl.read_text(encoding="utf-8")
        lines = [line for line in raw.splitlines() if line.strip()]
        if len(lines) > MAX_EXPORT_ROWS:
            raise BridgeInputError("export_row_limit_exceeded")
        rows = [json.loads(line) for line in lines]
        result = preview_export(rows)
        encoded = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded)
        # Missing, late or invalid data may not be declared ready or safe.
        return 2 if result["counts"].get("REJECTED_INVALID", 0) else 0
    except (OSError, UnicodeError, ValueError, TypeError):
        print("REMURA_TV_PREVIEW=INVALID_INPUT", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
