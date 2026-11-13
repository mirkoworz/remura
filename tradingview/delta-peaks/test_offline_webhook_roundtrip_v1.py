#!/usr/bin/env python3
# REMURA v0.8.16 — 13/11/2026, ore 13:13 CET
# All data synthetic. Executes Node gateway with fake D1, no real network/cloud.
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import unittest

from remura_tv_bridge_preview_v1 import preview_export

NODE_FIXTURE = Path(__file__).parent / "gateway-lab" / "offline_webhook_roundtrip.mjs"


class FullOfflineRoundtripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        process = subprocess.run(
            ["node", str(NODE_FIXTURE)], text=True,
            capture_output=True, check=True, timeout=20,
        )
        cls.fixture = json.loads(process.stdout)
        cls.results = preview_export(cls.fixture["rows"])

    def test_confirmed_simulation_not_live_data(self):
        self.assertEqual(self.fixture["mode"], "SYNTHETIC_LOCAL_NODE_WORKER_FAKE_D1")
        self.assertEqual(self.fixture["record_count"], 3)
        self.assertEqual(self.results["row_count"], 3)
        self.assertFalse(self.fixture["duplicate_stored"])
        self.assertTrue(self.fixture["invalid_ip_rejected"])

    def test_three_snapshots_validate_against_real_contract(self):
        self.assertEqual(self.results["counts"].get("REJECTED_INVALID", 0), 0)
        self.assertEqual(len(self.results["observations"]), 3)
        self.assertTrue(all(x["source"].endswith("NOT_INSTITUTIONAL")
                            for x in self.results["observations"]))

    def test_one_late_and_two_timely_snapshots(self):
        self.assertEqual(self.results["counts"]["LATE_NOT_PROSPECTIVE"], 1)
        self.assertEqual(self.results["counts"]["OBSERVATION_ONLY"], 2)
        self.assertEqual(sum(x["prospective_eligible"]
                             for x in self.results["observations"]), 2)

    def test_heartbeat_reserved_for_baseline_never_buy_sell(self):
        heartbeats = [x for x in self.results["observations"]
                      if x["event_type"] == "HEARTBEAT"]
        self.assertEqual(len(heartbeats), 1)
        self.assertEqual(heartbeats[0]["event_labels"], [])
        self.assertIn("BASELINE_BAR_NOT_A_SIGNAL", heartbeats[0]["reasons"])

    def test_event_classification_is_not_trade_instruction(self):
        for x in self.results["observations"]:
            self.assertEqual(x["verdict"], "NESSUN_SEGNALE_OPERATIVO")
            self.assertFalse(x["proof_of_institutional_activity"])
            self.assertFalse(x["statistical_edge_validated"])
            self.assertFalse(x["orders_enabled"])
        real_event = next(x for x in self.results["observations"]
                          if x["event_type"] == "BAR_EVENT" and
                          x["prospective_eligible"])
        self.assertIn("EFFORT_RESULT_POSITIVE", real_event["event_labels"])
        self.assertIn("DAY_ADDED", real_event["event_labels"])

    def test_corrupted_d1_columns_cannot_be_silent_success(self):
        rows = copy.deepcopy(self.fixture["rows"])
        rows[0]["is_timely"] = 0
        res = preview_export(rows)
        self.assertEqual(res["counts"]["REJECTED_INVALID"], 1)
        self.assertEqual(len(res["observations"]), 2)

    def test_no_token_or_private_secrets_in_observation_output(self):
        dumped = json.dumps(self.results)
        self.assertNotIn("OFFLINE_ONLY_synthetic_token", dumped)
        self.assertNotIn("WEBHOOK_TOKEN_SHA256", dumped)
        self.assertNotIn("raw_json", dumped)

    def test_same_event_conflicting_snapshot_quarantined(self):
        rows = copy.deepcopy(self.fixture["rows"])
        conflict = copy.deepcopy(rows[0])
        parsed = json.loads(conflict["raw_json"])
        parsed["ohlc"]["close"] = 1.1105
        conflict["raw_json"] = json.dumps(parsed)
        out = preview_export(rows + [conflict])
        self.assertEqual(out["counts"]["CONFLICTING_DUPLICATE_QUARANTINED"], 1)
        self.assertEqual(len(out["observations"]), 2)


if __name__ == "__main__":
    unittest.main()
