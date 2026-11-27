#!/usr/bin/env python3
# REMURA v0.8.48 LAB — 14/11/2026 09:38 CET
"""Offline, isolated volume feature adapter. No network, trades or probability.
BTC is diagnostic only. Inputs are private D1 export rows; caller controls provenance.
No future candles used. Never log raw payloads.
"""
from collections import Counter
import json
from datetime import datetime, timezone
from math import isfinite

from remura_tv_bridge_preview_v1 import (
    BridgeInputError, EXPECTED_COLUMNS, MAX_EXPORT_ROWS, MAX_RAW_BYTES,
    labels_for, decode_export_row,
)
from validate_telemetry_v1 import LEVEL_NAMES, validate_payload
from volume_quality_v1 import diagnose

VERSION = "0.8.48-lab"
M5 = 300_000
BTC_START = int(datetime(2026, 11, 14, tzinfo=timezone.utc).timestamp()) * 1000
BTC_END = BTC_START + 2 * 86_400_000


def decode(row):
    """Reuse FX validator; admit only the separately authorized BTC pilot."""
    if not isinstance(row, dict) or set(row) != EXPECTED_COLUMNS:
        raise BridgeInputError("export_schema_mismatch")
    if row["symbol"] == "FXCM:EURUSD":
        p, parsed = decode_export_row(row)
        if p["feed"] != "FXCM":
            raise BridgeInputError("feed_mismatch")
    elif row["symbol"] == "BINANCE:BTCUSDT":
        received, raw = row["received_at_ms"], row["raw_json"]
        if (type(received) is not int or not BTC_START <= received < BTC_END
                or type(row["is_timely"]) is not int or row["is_timely"] != 0
                or type(raw) is not str or len(raw.encode("utf-8")) > MAX_RAW_BYTES):
            raise BridgeInputError("btc_transport_policy")
        p = json.loads(raw)
        parsed = validate_payload(p, received_ms=received, expected_symbol="BINANCE:BTCUSDT")
        if p["feed"] != "BINANCE" or parsed["lag_ms"] > 86_400_000:
            raise BridgeInputError("btc_feed_or_lag")
        matches = {"event_key": parsed["event_key"], **{
            k: p[k] for k in ("symbol", "version", "timeframe", "bar_close_ms", "event_type")
        }}
        if any(type(row[k]) is not type(v) or row[k] != v for k, v in matches.items()):
            raise BridgeInputError("btc_identity_mismatch")
    else:
        raise BridgeInputError("symbol_not_allowed")
    if p["bar_close_ms"] % M5 or p["bar_close_ms"] - p["bar_open_ms"] != M5:
        raise BridgeInputError("not_full_aligned_m5")
    if any(t is not None and t > p["bar_close_ms"] for t in p["level_origin_ms"].values()):
        raise BridgeInputError("future_level")
    return p, parsed


def sign(v):
    return None if v is None else (1 if v > 0 else -1 if v < 0 else 0)


def features(p, parsed, received):
    o, fp, e = p["ohlc"], p["footprint"], p["events"]
    atr = o["atr14"] if o["atr14"] and o["atr14"] > 0 else None
    delta_sign = sign(p["delta_intrabar"])
    price_sign = sign(o["close"] - o["open"])
    footprint_sign = sign(fp["delta"]) if fp["available"] else None
    missing = []
    for field in ("delta_intrabar", "effort", "signed_result_atr", "efficiency"):
        if p[field] is None:
            missing.append(field)
    if atr is None:
        missing.append("atr14")
    if not fp["available"]:
        missing.append("footprint")
    else:
        missing.extend("footprint." + k for k in fp if k != "available" and fp[k] is None)
    levels = []
    for name in LEVEL_NAMES:
        price, origin = p["levels"][name], p["level_origin_ms"][name]
        if price is None:
            continue
        prior = origin < p["bar_close_ms"]
        distance = (o["close"] - price) / atr if atr else None
        if distance is not None and not isfinite(distance):
            raise BridgeInputError("nonfinite_distance")
        levels.append({"name": name, "price": price, "origin_ms": origin,
                       "prior_to_bar_close": prior,
                       "range_intersects_prior_level": o["low"] <= price <= o["high"] if prior else None,
                       "close_distance_atr": distance,
                       "pine_retest_flag": e.get("retest_" + name)})
    hypotheses = []
    if delta_sign not in (None, 0) and price_sign not in (None, 0) and delta_sign != price_sign:
        hypotheses.append("PRICE_DELTA_DIRECTION_DISAGREEMENT")
    if e["er_positive"]:
        hypotheses.append("POSSIBLE_BUYING_EFFORT_ABSORPTION")
    if e["er_negative"]:
        hypotheses.append("POSSIBLE_SELLING_EFFORT_ABSORPTION")
    btc = p["symbol"] == "BINANCE:BTCUSDT"
    timely = parsed["timely_for_prospective"]
    return {
        "schema": "remura.tv.volume.features.v1", "version": VERSION,
        "symbol": p["symbol"], "timeframe": p["timeframe"], "bar_close_ms": p["bar_close_ms"],
        "received_at_ms": received, "latency_ms": parsed["lag_ms"],
        "cohort": "BTC_TRANSPORT_ONLY" if btc else "FX_RESEARCH_PREVIEW",
        "source": "TRADINGVIEW_CLASSIFIED_VOLUME_NOT_IDENTIFIED_INSTITUTIONAL_TRADES",
        "transport_timely": timely, "fx_timeliness_eligible": timely and not btc,
        "event_type": p["event_type"], "observed_labels": labels_for(p),
        "quality": "PARTIAL" if missing else "FIELDS_PRESENT_UNVERIFIED",
        "missing_fields": sorted(missing),
        "diagnostic_checks": diagnose(p),
        "observed": {
            "ohlc": dict(o), "delta_intrabar_estimate": p["delta_intrabar"],
            "delta_sign": delta_sign, "price_body_sign": price_sign,
            "effort_reported": p["effort"], "signed_result_atr_reported": p["signed_result_atr"],
            "efficiency_reported": p["efficiency"], "footprint": dict(fp),
            "footprint_delta_sign": footprint_sign,
            "daily_anchor": p["quality"]["daily_anchor"], "levels": levels,
        },
        # BTC cannot generate scientific hypotheses; FX hypotheses are not confirmations.
        "hypotheses": [] if btc else hypotheses,
        "confirmed_institutional_activity": False, "statistical_edge_validated": False,
        "verdict": "NO_OPERATIONAL_SIGNAL", "orders_enabled": False,
    }


def analyze_export(rows):
    """Quarantine entire conflicting bars, including event-type collisions.
    Counts of gaps refer only to the observed span, not session/source outages.
    An offline export does not establish authenticity or completeness.
    """
    if not isinstance(rows, list) or len(rows) > MAX_EXPORT_ROWS:
        raise BridgeInputError("export_row_limit")
    accepted, quarantined, counts = {}, set(), Counter()
    for row in rows:
        try:
            p, parsed = decode(row)
            view = features(p, parsed, row["received_at_ms"])
            key = (p["symbol"], p["timeframe"], p["bar_close_ms"])
            signature = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (ValueError, TypeError, KeyError, OverflowError):
            counts["INVALID_ROW"] += 1
            continue
        if key in quarantined:
            counts["CONFLICT_ROW"] += 1
            continue
        if key in accepted:
            old_sig, old_view = accepted[key]
            if old_sig != signature or old_view["received_at_ms"] != view["received_at_ms"]:
                del accepted[key]
                quarantined.add(key)
                counts["CONFLICT_ROW"] += 1
            else:
                counts["DUPLICATE_ROW"] += 1
            continue
        accepted[key] = (signature, view)
    observations = [accepted[k][1] for k in sorted(accepted)]
    continuity = {}
    for symbol in sorted({v["symbol"] for v in observations}):
        group = [v for v in observations if v["symbol"] == symbol]
        times = [v["bar_close_ms"] for v in group]
        expected = (times[-1] - times[0]) // M5 + 1
        continuity[symbol] = {
            "observed_bars": len(times), "first_close_ms": times[0], "last_close_ms": times[-1],
            "unobserved_slots_within_span": expected - len(times),
            "heartbeats": sum(v["event_type"] == "HEARTBEAT" for v in group),
            "bar_events": sum(v["event_type"] == "BAR_EVENT" for v in group),
            "timely_transport": sum(v["transport_timely"] for v in group),
            "coverage": "OBSERVED_SPAN_ONLY_NOT_EXPECTED_SESSION",
        }
    return {"version": VERSION, "counts": dict(counts),
            "quarantined_bars": len(quarantined), "continuity": continuity,
            "status": "NO_VALID_ROWS" if not observations else "OFFLINE_OBSERVATIONS_ONLY",
            "observations": observations, "no_trade": True}
