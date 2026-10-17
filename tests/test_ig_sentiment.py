"""Offline validation of the optional IG sentiment collector (no API keys)."""
import unittest
from unittest.mock import patch

from scripts.update_ig import MARKET_IDS, collect, finite_percent, parse_sentiments


class TestIgSentiment(unittest.TestCase):
    def setUp(self):
        self.time = "2026-10-17T08:00:00Z"

    def test_percentages_must_be_finite_and_bounded(self):
        for value in (None, "NaN", "Inf", -1, 101, True, ""):
            self.assertIsNone(finite_percent(value))
        self.assertEqual(finite_percent("22.5"), 22.5)

    def test_only_valid_known_market_groups_are_published(self):
        payload = {"clientSentiments": [
            {"marketId": "EURUSD", "longPositionPercentage": 78, "shortPositionPercentage": 22},
            {"marketId": "GBPUSD", "longPositionPercentage": 91, "shortPositionPercentage": 50},
            {"marketId": "USDJPY", "longPositionPercentage": 0, "shortPositionPercentage": 0},
            {"marketId": "UNKNOWN", "longPositionPercentage": 70, "shortPositionPercentage": 30},
            {"marketId": "GOLD", "longPositionPercentage": 33.1, "shortPositionPercentage": 66.9},
        ]}
        parsed = parse_sentiments(payload, self.time)
        self.assertEqual(set(parsed), {"EURUSD", "XAUUSD"})
        self.assertEqual(parsed["EURUSD"]["metric"], "client_positions")
        self.assertEqual(parsed["XAUUSD"]["marketId"], "GOLD")

    def test_missing_array_is_not_a_valid_ig_response(self):
        with self.assertRaises(ValueError):
            parse_sentiments({"sentiments": []}, self.time)

    @patch("scripts.update_ig.request_json")
    def test_collect_uses_authenticated_read_only_endpoint(self, req):
        req.side_effect = [
            ({}, {"CST": "temporary-cst", "X-SECURITY-TOKEN": "temporary-xst"}),
            ({"clientSentiments": [{"marketId": "EURUSD",
               "longPositionPercentage": 60, "shortPositionPercentage": 40}]}, {}),
        ]
        result = collect("test-key", "test-user", "test-password", "demo")
        self.assertEqual(result["symbols"]["EURUSD"]["lPct"], 60)
        self.assertIn("/session", req.call_args_list[0].args[0])
        self.assertIn("/clientsentiment?marketIds=", req.call_args_list[1].args[0])
        self.assertEqual(req.call_args_list[1].args[1]["VERSION"], "1")
        self.assertEqual(req.call_args_list[1].args[1]["CST"], "temporary-cst")
        self.assertGreaterEqual(len(MARKET_IDS), 28)


if __name__ == "__main__":
    unittest.main()
