#!/usr/bin/env python3
# REMURA v0.8.51 LAB — 14/11/2026 10:55 CET
"""Frozen EURUSD pilot-configuration contract, offline candidate only.
A hash identifies declared configuration, not authenticated TradingView inputs.
No change to v1 live payload, no admission to scientific or operational cohorts.
"""
from hashlib import sha256
import json
from math import isfinite

SCHEMA = "remura.tv.fx.config.preview.v1"
REFERENCE = {
    "symbol": "FXCM:EURUSD", "timeframe": "5", "indicator_version": "0.8.1-lab",
    "lower_tf": "1", "lookback": 30, "multiplier": 3.5,
    "max_efficiency": 0.07, "min_peak_gap": 6,
    "fp_ticks": 10, "fp_value_area_pct": 70, "fp_imbalance_pct": 300.0,
    "daily_min_effort": 1.5, "daily_anchor": "HL2",
    "show_daily_levels": True, "show_prev_day": True,
    "telemetry_enabled": True, "telemetry_heartbeat": True,
}

def inspect_declared_config(declared):
    if not isinstance(declared, dict) or set(declared) != set(REFERENCE):
        raise ValueError("unexpected_config_fields")
    normalized = {}
    for key, expected in REFERENCE.items():
        v = declared[key]
        if type(expected) is float:
            if type(v) not in (int, float) or not isfinite(v):
                raise ValueError("invalid_config_numeric")
            v = float(v)
        elif type(v) is not type(expected):
            raise ValueError("invalid_config_type")
        normalized[key] = v
    differences = sorted(k for k,v in normalized.items() if v != REFERENCE[k])
    canonical = json.dumps({"schema": SCHEMA, "parameters": normalized},
                           sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "schema": SCHEMA,
        "declared_config_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        "reference_match": not differences,
        "different_fields": differences,
        "status": "DECLARED_REFERENCE_MATCH" if not differences else "DECLARED_CONFIG_MISMATCH",
        "effective_alert_inputs_attested": False,
        "scientific_admission": False, "orders_enabled": False,
    }

def compare_v1_fields(payload, declared):
    """Compare only fields already available in v1. Never infer absent inputs."""
    result = inspect_declared_config(declared)
    if not isinstance(payload, dict) or not isinstance(payload.get("quality"), dict):
        raise ValueError("invalid_payload_metadata")
    quality = payload["quality"]
    observed = {
        "symbol": payload.get("symbol"), "timeframe": payload.get("timeframe"),
        "indicator_version": payload.get("version"),
        "lower_tf": quality.get("lower_tf"), "daily_anchor": quality.get("daily_anchor"),
    }
    differences = sorted(k for k,v in observed.items() if v != declared[k])
    result.update(
        v1_observed_fields=sorted(observed),
        v1_difference_fields=differences,
        unobservable_from_v1=sorted(set(REFERENCE)-set(observed)),
        v1_fields_match=not differences,
    )
    return result
