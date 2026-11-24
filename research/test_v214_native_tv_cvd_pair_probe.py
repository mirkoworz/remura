"""REMURA A v21.4: NEW synthetic-only native closed-M5 bridge tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v214_native_tv_cvd_pair_probe import (
    audit_native_pair, _read_private, ROOT, SOURCE_PIN,
)

UTC = timezone.utc
PRIOR = datetime(2026, 11, 23, 4, 35, tzinfo=UTC)
M5 = timedelta(minutes=5)


def payload(end, *, level=2800, trusted=100, segment=12):
    close = int(end.timestamp() * 1000)
    day = int(datetime(2026, 11, 23, 0, 0, tzinfo=UTC).timestamp() * 1000)
    return {
        "schema": "remura.tv.flow.cvd.preview.v1",
        "snapshot": {
            "schema": "remura.tv.flow.cvd.snapshot.preview.v1",
            "version": "0.9.1-cvd-lab", "symbol": "FX:EURUSD",
            "feed": "FX", "timeframe": "5",
            "source": "TRADINGVIEW_INTRABAR_ESTIMATE",
            "indicator": "REMURA_ALL_IN_ONE_PREMIUM",
            "bar_open_ms": close - 300000, "bar_close_ms": close,
            "sent_clock_ms": close + 2000,
            "confirmed": True, "realtime": True,
            "quality": {
                "bar_closed": True, "source_type": "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS",
                "lower_tf": "1", "daily_anchor": "HL2"
            }
        },
        "configuration": {
            "symbol": "FX:EURUSD", "timeframe": "5",
            "indicator_version": "0.9.1-cvd-lab", "lower_tf": "1",
            "cvd_left": 2, "cvd_right": 2, "cvd_warmup": 12
        },
        "cvd": {
            "model": "D08_SEGMENT_PORT_V091",
            "intrabar_count": 5, "complete": True, "continuous": True,
            "day_valid": True, "segment_id": 17,
            "segment_bars": segment, "day_key_ms": day,
            "raw_delta": trusted, "trusted_delta": trusted,
            "daily_cvd": level, "segment_cvd": level,
            "eligible": True, "price_bull": False, "price_bear": False,
            "cvd_bull": False, "cvd_bear": False,
            "pivot_close_ms": None
        }
    }


def raw(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def pair():
    return payload(PRIOR, level=2800, trusted=200, segment=12), payload(
        PRIOR + M5, level=2900, trusted=100, segment=13)


class NewA214NativeCompatibility(unittest.TestCase):
    def test_two_adjacent_original_native_proxy_m5_values_only_not_a_trade(self):
        prior, event = pair()
        a, b = raw(prior), raw(event)
        got = audit_native_pair(a, b)
        self.assertEqual(got["state"], "TWO_CLOSED_M5_NATIVE_PROXY_VALUES_COMPATIBLE")
        self.assertEqual(got["proxy_delta_sign_for_private_research"], "LONG")
        self.assertEqual(got["source_reference_commit"], SOURCE_PIN)
        self.assertEqual(got["original_source_sha256"],
                         [hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()])
        self.assertFalse(got["full_original_js_gateway_validator_executed"])
        self.assertFalse(got["receiver_first_seen_authenticated"])
        self.assertFalse(got["prospective_decision_admitted"])
        self.assertFalse(got["scientific_alpha_established"])

    def test_exact_raw_bytes_are_hashed_without_provenance_forgery(self):
        a, b = pair()
        compact = raw(a)
        pretty = json.dumps(a, indent=2).encode()
        first, second = audit_native_pair(compact, raw(b)), audit_native_pair(pretty, raw(b))
        self.assertEqual(first["proxy_delta_sign_for_private_research"],
                         second["proxy_delta_sign_for_private_research"])
        self.assertNotEqual(first["original_source_sha256"][0],
                            second["original_source_sha256"][0])

    def test_old_aggregate_test_receipt_cannot_become_directional_pair(self):
        old = raw({"schema": "remura-v203-tradingview-test-receipt-real-proof",
                   "result": {"valid_unique_bars": 12}})
        with self.assertRaisesRegex(ValueError, "not_native_v091"):
            audit_native_pair(old, raw(pair()[1]))

    def test_require_closed_adjacent_and_same_continuous_segment(self):
        prior, event = pair()
        checks = [
            (lambda e: e["snapshot"].update({"bar_close_ms":
                        e["snapshot"]["bar_close_ms"] + 300000}), "adjacent"),
            (lambda e: e["cvd"].update({"segment_id": 18}), "reset"),
            (lambda e: e["cvd"].update({"segment_bars": 14}), "reset"),
            (lambda e: e["cvd"].update({"day_key_ms": e["cvd"]["day_key_ms"] + 86400000}), "reset"),
            (lambda e: e["cvd"].update({"continuous": False}), "continuous"),
            (lambda e: e["cvd"].update({"eligible": False}), "continuous"),
        ]
        for mutate, message in checks:
            changed = copy.deepcopy(event)
            mutate(changed)
            with self.subTest(message=message), self.assertRaises(ValueError):
                audit_native_pair(raw(prior), raw(changed))

    def test_reject_delta_disagreement_duplicate_keys_and_wrong_source(self):
        prior, event = pair()
        event["cvd"]["trusted_delta"] = 999
        with self.assertRaisesRegex(ValueError, "disagrees"):
            audit_native_pair(raw(prior), raw(event))
        prior, event = pair()
        event["snapshot"]["symbol"] = "FXCM:EURUSD"
        with self.assertRaisesRegex(ValueError, "identity"):
            audit_native_pair(raw(prior), raw(event))
        with self.assertRaisesRegex(ValueError, "duplicate_native_json_key"):
            audit_native_pair(b'{"schema":"x","schema":"y"}', raw(event))
        prior, event = pair()
        with self.assertRaisesRegex(ValueError, "non_numeric"):
            event["cvd"]["segment_cvd"] = "infinite"
            audit_native_pair(raw(prior), raw(event))

    def test_cli_defaults_inert_and_real_files_must_remain_private(self):
        script = Path(__file__).with_name("v214_native_tv_cvd_pair_probe.py")
        out = subprocess.check_output([sys.executable, str(script)], text=True)
        self.assertEqual(json.loads(out)["state"], "NO_TWO_NATIVE_ORIGINALS_NO_DIRECTION")
        self.assertEqual(json.loads(out)["admitted_forward_decisions"], 0)
        with self.assertRaisesRegex(ValueError, "outside_repository"):
            _read_private(Path(__file__))
        with tempfile.TemporaryDirectory() as base:
            prior, event = pair()
            filepath = Path(base) / "source.json"
            filepath.write_bytes(raw(prior))
            self.assertEqual(_read_private(filepath), raw(prior))
            link = Path(base) / "pointer.json"
            link.symlink_to(filepath)
            with self.assertRaisesRegex(ValueError, "symlink_rejected"):
                _read_private(link)


if __name__ == "__main__":
    unittest.main()
