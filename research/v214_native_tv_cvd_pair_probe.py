#!/usr/bin/env python3
"""REMURA A v21.4 LAB — OFFLINE diagnostic for TWO native v0.9.1 CVD envelopes.

NO ingestion, freeze, trade, provider authentication, broker data, network, or
signal admission. This is a STRICT SUBSET of the historical gateway contract,
not a substitute for its full JS validateCvdEnvelope() or its receiver clock.
The old 12 aggregated TEST receipts are never convertible into directions.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "remura.tv.flow.cvd.preview.v1"
SNAPSHOT_SCHEMA = "remura.tv.flow.cvd.snapshot.preview.v1"
MODEL = "D08_SEGMENT_PORT_V091"
VERSION = "0.9.1-cvd-lab"
NATIVE_KEYS = frozenset(("schema", "snapshot", "configuration", "cvd"))
CVD_KEYS = frozenset((
    "model", "intrabar_count", "complete", "continuous", "day_valid",
    "segment_id", "segment_bars", "day_key_ms", "raw_delta", "trusted_delta",
    "daily_cvd", "segment_cvd", "eligible", "price_bull", "price_bear",
    "cvd_bull", "cvd_bear", "pivot_close_ms",
))
MAX_BYTES = 20_000
M5_MS = 300_000
SOURCE_PIN = "58dc84e0de93b48eb5a6c596664d4d338548754a"
DECIMAL_V211 = re.compile(r"-?(?:0|[1-9]\d{0,11})(?:\.\d{1,6})?")
MAX_CVD = Decimal("999999999999.999999")


def _pairs(items: list[tuple[str, object]]) -> dict:
    out = {}
    for k, v in items:
        if k in out:
            raise ValueError("duplicate_native_json_key")
        out[k] = v
    return out


def _bounded_number(value: object) -> Decimal:
    if type(value) not in (int, Decimal):
        raise ValueError("native_cvd_non_numeric")
    amount = Decimal(value)
    if not amount.is_finite() or abs(amount) > MAX_CVD:
        raise ValueError("native_cvd_out_of_range")
    if not DECIMAL_V211.fullmatch(format(amount, "f")):
        raise ValueError("native_cvd_not_lossless_v211_decimal")
    return amount


def _native(raw: bytes) -> dict:
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        raise ValueError("native_source_missing_or_oversize")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
            parse_float=Decimal, parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("nonfinite_native_json")))
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("native_source_not_utf8_json") from None
    if type(payload) is not dict or set(payload) != NATIVE_KEYS or payload["schema"] != SCHEMA:
        raise ValueError("not_native_v091_cvd_envelope")
    s, cfg, c = payload["snapshot"], payload["configuration"], payload["cvd"]
    if (type(s) is not dict or type(cfg) is not dict or type(c) is not dict or
        set(c) != CVD_KEYS):
        raise ValueError("invalid_native_nested_envelope")
    if (s.get("schema") != SNAPSHOT_SCHEMA or s.get("version") != VERSION or
        s.get("symbol") != "FX:EURUSD" or s.get("feed") != "FX" or
        s.get("timeframe") != "5" or
        s.get("source") != "TRADINGVIEW_INTRABAR_ESTIMATE" or
        s.get("indicator") != "REMURA_ALL_IN_ONE_PREMIUM" or
        s.get("confirmed") is not True or s.get("realtime") is not True):
        raise ValueError("invalid_native_closed_eurusd_m5_identity")
    close = s.get("bar_close_ms")
    opened = s.get("bar_open_ms")
    if (type(close) is not int or type(opened) is not int or
        close < 1_000_000_000_000 or close % M5_MS or
        close - opened != M5_MS):
        raise ValueError("native_m5_timing_invalid")
    q = s.get("quality")
    if (type(q) is not dict or q.get("bar_closed") is not True or
        q.get("source_type") != "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS"):
        raise ValueError("native_proxy_quality_invalid")
    if (cfg.get("symbol") != "FX:EURUSD" or cfg.get("timeframe") != "5" or
        cfg.get("indicator_version") != VERSION or cfg.get("lower_tf") != "1" or
        cfg.get("cvd_left") != 2 or cfg.get("cvd_right") != 2 or
        cfg.get("cvd_warmup") != 12):
        raise ValueError("native_config_not_v091")
    if (c.get("model") != MODEL or c.get("complete") is not True or
        c.get("continuous") is not True or c.get("eligible") is not True or
        c.get("day_valid") is not True or
        type(c.get("segment_id")) is not int or c["segment_id"] < 1 or
        type(c.get("segment_bars")) is not int or c["segment_bars"] < 12 or
        type(c.get("day_key_ms")) is not int or
        c["day_key_ms"] > opened):
        raise ValueError("native_segment_not_continuous_eligible")
    for name in ("segment_cvd", "trusted_delta", "daily_cvd"):
        _bounded_number(c.get(name))
    return {"close": close, "cvd": c, "sha": hashlib.sha256(raw).hexdigest()}


def audit_native_pair(prior_raw: bytes, event_raw: bytes) -> dict:
    """Diagnostic-only; never creates a V21.1 event or a private decision."""
    a = _native(prior_raw)
    b = _native(event_raw)
    left, right = a["cvd"], b["cvd"]
    if b["close"] - a["close"] != M5_MS:
        raise ValueError("native_not_two_adjacent_closed_m5")
    if (left["segment_id"] != right["segment_id"] or
        left["day_key_ms"] != right["day_key_ms"] or
        right["segment_bars"] - left["segment_bars"] != 1):
        raise ValueError("native_cvd_reset_or_segment_gap")
    before = _bounded_number(left["segment_cvd"])
    after = _bounded_number(right["segment_cvd"])
    delta = after - before
    latest = _bounded_number(right["trusted_delta"])
    # No silently rounded/different series can enter the future bridge.
    if abs(delta - latest) > Decimal("0.000001"):
        raise ValueError("native_cvd_level_difference_disagrees_with_trusted_delta")
    return {
        "schema": "remura-a-v214-native-cvd-offline-compatibility-v1",
        "state": "TWO_CLOSED_M5_NATIVE_PROXY_VALUES_COMPATIBLE",
        "original_source_sha256": [a["sha"], b["sha"]],
        "bar_close_ms": [a["close"], b["close"]],
        "proxy_delta_sign_for_private_research":
            "LONG" if delta > 0 else "SHORT" if delta < 0 else "FLAT",
        "source_reference_commit": SOURCE_PIN,
        "full_original_js_gateway_validator_executed": False,
        "receiver_first_seen_authenticated": False,
        "real_payload_origin_authenticated": False,
        "prospective_decision_admitted": False,
        "frozen_for_outcomes": False,
        "scientific_alpha_established": False,
        "network_calls": 0,
    }


def _read_private(path: Path) -> bytes:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ValueError("private_input_symlink_rejected")
    candidate = candidate.resolve(strict=True)
    if candidate == ROOT or ROOT in candidate.parents or not candidate.is_file():
        raise ValueError("original_raw_must_remain_outside_repository")
    with candidate.open("rb") as f:
        raw = f.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("private_native_raw_bad_size")
    return raw


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-native-raw", type=Path)
    p.add_argument("--event-native-raw", type=Path)
    args = p.parse_args()
    if not args.prior_native_raw and not args.event_native_raw:
        print(json.dumps({
            "state": "NO_TWO_NATIVE_ORIGINALS_NO_DIRECTION",
            "admitted_forward_decisions": 0, "network_calls": 0,
            "files_written": 0
        }, sort_keys=True))
        return
    if not args.prior_native_raw or not args.event_native_raw:
        p.error("two ORIGINAL native files required, not aggregate receipts")
    try:
        report = audit_native_pair(
            _read_private(args.prior_native_raw),
            _read_private(args.event_native_raw))
    except (ValueError, OSError, TypeError, KeyError, OverflowError):
        p.error("Native pair rejected; private source details withheld")
    # Do not emit potential side, source SHA, or timestamps on stdout.
    print(json.dumps({
        "state": report["state"],
        "native_contract_subset_check": True,
        "receiver_first_seen_authenticated": False,
        "full_original_js_gateway_validator_executed": False,
        "admitted_forward_decisions": 0,
        "scientific_alpha_established": False,
        "files_written": 0, "network_calls": 0
    }, sort_keys=True))


if __name__ == "__main__":
    main()
