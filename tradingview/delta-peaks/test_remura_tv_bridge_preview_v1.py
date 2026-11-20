#!/usr/bin/env python3
# REMURA v0.8.15 TEST — 13/11/2026, ore 13:01 CET
# Esclusivamente fixture sintetiche FXCM:EURUSD, no API, scritture, ordini.
import copy
import json
import unittest

from remura_tv_bridge_preview_v1 import (
    BridgeInputError, decode_export_row, preview_record, preview_export,
)
from test_telemetry_v1 import T0, sample


def row(p=None, received_at_ms=T0 + 5000, is_timely=1):
    p = copy.deepcopy(p if p is not None else sample())
    return {
        "event_key": "|".join((
            p["symbol"], p["timeframe"], str(p["bar_close_ms"]),
            p["version"], p["event_type"],
        )),
        "received_at_ms": received_at_ms,
        "bar_close_ms": p["bar_close_ms"],
        "symbol": p["symbol"],
        "timeframe": p["timeframe"],
        "event_type": p["event_type"],
        "version": p["version"],
        "is_timely": is_timely,
        "raw_json": json.dumps(p, separators=(",", ":")),
    }


class BridgeTests(unittest.TestCase):
    def test_event_is_observation_not_long_short(self):
        x = preview_record(row())
        self.assertEqual(x["status"], "OBSERVATION_ONLY")
        self.assertEqual(x["verdict"], "NESSUN_SEGNALE_OPERATIVO")
        self.assertIn("EFFORT_RESULT_POSITIVE", x["event_labels"])
        self.assertIn("DAY_ADDED", x["event_labels"])
        self.assertEqual(x["close"], 1.111)
        self.assertFalse(x["proof_of_institutional_activity"])
        self.assertFalse(x["statistical_edge_validated"])
        self.assertFalse(x["orders_enabled"])

    def test_proxy_source_never_called_cme(self):
        x = preview_record(row())
        self.assertIn("NOT_INSTITUTIONAL", x["source"])
        self.assertNotIn("TRADE", x["verdict"])

    def test_d1_columns_and_payload_must_match(self):
        for field, value in (
            ("event_key", "bad"), ("symbol", "CME:6E1!"),
            ("timeframe", "15"), ("bar_close_ms", T0 + 1),
            ("event_type", "HEARTBEAT"), ("version", "0.8.2-lab"),
        ):
            x = row()
            x[field] = value
            with self.subTest(field=field), self.assertRaises(BridgeInputError):
                decode_export_row(x)

    def test_d1_is_timely_must_equal_real_receiver_window(self):
        stale = row(received_at_ms=T0 + 150_000, is_timely=0)
        out = preview_record(stale)
        self.assertEqual(out["status"], "LATE_NOT_PROSPECTIVE")
        self.assertFalse(out["prospective_eligible"])
        with self.assertRaises(BridgeInputError):
            decode_export_row(row(received_at_ms=T0 + 150_000, is_timely=1))

    def test_missing_receipt_fails(self):
        x = row()
        x["received_at_ms"] = None
        with self.assertRaises(BridgeInputError):
            decode_export_row(x)

    def test_bad_stored_timely_fails(self):
        for bad in (None, True, False, "1", 2, -1):
            x = row()
            x["is_timely"] = bad
            with self.subTest(bad=bad), self.assertRaises(BridgeInputError):
                decode_export_row(x)

    def test_partial_footprint_cannot_be_green(self):
        p = sample()
        p["footprint"] = {k: (False if k == "available" else None)
                          for k in p["footprint"]}
        p["quality"]["has_footprint"] = False
        x = preview_record(row(p))
        self.assertEqual(x["status"], "PARTIAL_OBSERVATION")
        self.assertIn("FOOTPRINT_NOT_AVAILABLE", x["reasons"])
        self.assertIsNone(x["poc_if_available"])

    def test_absent_atr_partial_not_operational(self):
        p = sample()
        p["ohlc"]["atr14"] = None
        x = preview_record(row(p))
        self.assertIn("ATR_NOT_AVAILABLE", x["reasons"])

    def test_heartbeat_is_not_event(self):
        p = sample()
        p["events"].update({
            "peak": False, "er_positive": False, "day_level_action": "NONE",
            "day_level_rank": None,
        })
        p["event_type"] = "HEARTBEAT"
        x = preview_record(row(p))
        self.assertEqual(x["event_labels"], [])
        self.assertIn("BASELINE_BAR_NOT_A_SIGNAL", x["reasons"])

    def test_invalid_source_is_rejected(self):
        p = sample()
        p["source"] = "CME_REAL_INSTITUTIONAL"
        with self.assertRaises(BridgeInputError):
            preview_record(row(p))

    def test_raw_json_synthetic_not_market_is_rejected(self):
        x = row()
        x["raw_json"] = '{"synthetic":true,"test_only":true}'
        with self.assertRaises(BridgeInputError):
            preview_record(x)

    def test_duplicate_rows_not_counted_twice(self):
        out = preview_export([row(), row()])
        self.assertEqual(len(out["observations"]), 1)
        self.assertEqual(out["counts"]["DUPLICATE_SKIPPED"], 1)

    def test_conflicting_duplicate_is_quarantined_not_a_cherry_picked_signal(self):
        first = row()
        second_payload = sample()
        second_payload["ohlc"]["close"] = 1.1105
        second = row(second_payload)
        out = preview_export([first, second])
        self.assertEqual(out["observations"], [])
        self.assertEqual(out["counts"]["CONFLICTING_DUPLICATE_QUARANTINED"], 1)
        self.assertEqual(out["counts"]["OBSERVATION_ONLY"], 0)

    def test_conflict_remains_quarantined_after_more_duplicates(self):
        a = row()
        b_p = sample()
        b_p["ohlc"]["close"] = 1.1105
        out = preview_export([a, row(b_p), a])
        self.assertEqual(out["observations"], [])
        self.assertEqual(out["counts"]["CONFLICTING_DUPLICATE_QUARANTINED"], 2)

    def test_invalid_row_quarantined_without_echo(self):
        x = row()
        x["bad_secret_field"] = "should-not-appear"
        output = preview_export([x, row()])
        self.assertEqual(output["counts"]["REJECTED_INVALID"], 1)
        self.assertNotIn("should-not-appear", json.dumps(output))
        self.assertEqual(len(output["observations"]), 1)

    def test_missing_extra_metadata_rejected(self):
        for field in ("event_key", "raw_json", "is_timely"):
            x = row()
            del x[field]
            with self.subTest(field=field), self.assertRaises(BridgeInputError):
                preview_record(x)

    def test_nan_input_rejected(self):
        x = row()
        x["raw_json"] = x["raw_json"].replace("2400", "NaN", 1)
        with self.assertRaises(BridgeInputError):
            preview_record(x)

    def test_file_size_guard(self):
        x = row()
        x["raw_json"] = " " * 20_001
        with self.assertRaises(BridgeInputError):
            preview_record(x)

    def test_batch_is_never_trading_signal(self):
        out = preview_export([row()])
        self.assertTrue(out["no_trade"])
        self.assertTrue(out["prospective_validation_still_required"])
        self.assertEqual(out["row_count"], 1)

    def test_batch_row_limit(self):
        with self.assertRaises(BridgeInputError):
            preview_export([None] * 10_001)


if __name__ == "__main__":
    unittest.main()
