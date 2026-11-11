#!/usr/bin/env python3
# REMURA v0.8.1 — TEST SINTETICI per validatore TELEMETRY.
# Aggiornamento: 11/11/2026 16:18 CET.
# I prezzi in questo file NON provengono da mercato: non sono risultati.
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_telemetry_v1.py")
spec = importlib.util.spec_from_file_location("remura_tv_validation", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

T0 = 1_800_000_000_000  # Timestamp simulato, NON dato reale.


def sample() -> dict:
    return {
        "schema": "remura.tv.flow.v1",
        "source": "TRADINGVIEW_INTRABAR_ESTIMATE",
        "indicator": "REMURA_ALL_IN_ONE_PREMIUM",
        "version": "0.8.1-lab",
        "event_type": "BAR_EVENT",
        "symbol": "FXCM:EURUSD",
        "feed": "FXCM",
        "timeframe": "5",
        "bar_open_ms": T0 - 300_000,
        "bar_close_ms": T0,
        "sent_clock_ms": T0 + 1000,
        "confirmed": True,
        "realtime": True,
        "ohlc": {
            "open": 1.110, "high": 1.112, "low": 1.109,
            "close": 1.111, "prev_close": 1.110,
            "atr14": 0.0012
        },
        "delta_intrabar": 2400,
        "effort": 4.8,
        "signed_result_atr": 0.012,
        "efficiency": 0.0025,
        "footprint": {
            "available": True,
            "buy": 1900, "sell": 1650, "delta": 250,
            "total": 3550, "delta_pct": 7.04,
            "poc": 1.111, "vah": 1.112, "val": 1.110,
            "imb_buy_rows": 3, "imb_sell_rows": 1
        },
        "levels": {
            "day1": 1.111, "day2": None, "day3": None,
            "previous_day": None, "week": 1.110,
            "current_month": 1.109, "previous_month": None
        },
        "level_scores": {"day1": 2400, "day2": None, "day3": None},
        "level_origin_ms": {
            "day1": T0, "day2": None, "day3": None,
            "previous_day": None, "week": T0 - 300_000,
            "current_month": T0 - 300_000, "previous_month": None
        },
        "events": {
            "peak": True, "er_positive": True, "er_negative": False,
            "day_level_action": "ADDED", "day_level_rank": 1,
            "evicted_day_price": None, "evicted_day_origin_ms": None,
            "retest_day1": False, "retest_day2": False,
            "retest_day3": False, "retest_previous_day": False
        },
        "quality": {
            "bar_closed": True,
            "source_type": "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS",
            "has_intrabar_delta": True,
            "has_footprint": True,
            "freshness_ms": 1000,
            "daily_anchor": "HL2",
            "lower_tf": "1"
        },
    }


class TelemetryValidatorTests(unittest.TestCase):
    def invalid(self, change) -> None:
        p = copy.deepcopy(sample())
        change(p)
        with self.assertRaises(mod.InvalidTelemetry):
            mod.validate_payload(p)

    def test_valid_and_event_key(self) -> None:
        p = sample()
        out = mod.validate_payload(p, received_ms=T0 + 5000)
        self.assertTrue(out["valid"])
        self.assertTrue(out["timely_for_prospective"])
        self.assertIn("FXCM:EURUSD|5|", out["event_key"])

    def test_stale_is_recorded_not_dropped(self) -> None:
        out = mod.validate_payload(sample(), received_ms=T0 + 150_000)
        self.assertFalse(out["timely_for_prospective"])
        self.assertEqual(out["lag_ms"], 150_000)

    def test_future_bar_rejected(self) -> None:
        self.assertRaises(mod.InvalidTelemetry, mod.validate_payload,
                          sample(), received_ms=T0 - 200_000)

    def test_unconfirmed_rejected(self) -> None:
        self.invalid(lambda p: p.update(confirmed=False))

    def test_historical_rejected(self) -> None:
        self.invalid(lambda p: p.update(realtime=False))

    def test_wrong_symbol_rejected(self) -> None:
        self.invalid(lambda p: p.update(symbol="CME:6E1!"))

    def test_missing_level_identity_rejected(self) -> None:
        self.invalid(lambda p: p["level_origin_ms"].update(day1=None))

    def test_invalid_effort_rejected(self) -> None:
        self.invalid(lambda p: p.update(effort=-1))

    def test_boolean_as_price_rejected(self) -> None:
        self.invalid(lambda p: p["ohlc"].update(close=True))

    def test_unavailable_footprint_requires_nulls(self) -> None:
        self.invalid(lambda p: p["footprint"].update(available=False))

    def test_heartbeat_with_event_rejected(self) -> None:
        self.invalid(lambda p: p.update(event_type="HEARTBEAT"))

    def test_er_without_peak_rejected(self) -> None:
        self.invalid(lambda p: p["events"].update(peak=False))

    def test_missing_rank_rejected(self) -> None:
        self.invalid(lambda p: p["events"].update(day_level_rank=None))

    def test_footprint_missing_allowed_if_null(self) -> None:
        p = sample()
        p["footprint"] = {k: (False if k == "available" else None)
                          for k in p["footprint"]}
        p["quality"]["has_footprint"] = False
        self.assertTrue(mod.validate_payload(p)["valid"])

    def test_disallow_nonfinite_delta(self) -> None:
        self.invalid(lambda p: p.update(delta_intrabar=float("nan")))

    def test_event_key_same_for_duplicate(self) -> None:
        a = mod.validate_payload(sample())["event_key"]
        b = mod.validate_payload(copy.deepcopy(sample()))["event_key"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
