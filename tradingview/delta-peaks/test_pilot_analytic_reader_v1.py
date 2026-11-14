#!/usr/bin/env python3
# REMURA v0.8.47 LAB — 14/11/2026 09:32 CET. Synthetic and mocked only.
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "gateway-lab"))
import pilot_analytic_reader_v1 as m
from test_volume_features_v1 import fixture

T = m.FIRST_CLOSE
N = T + 2*m.M5 + 120_000


def envelope(rows):
    return {"success": True, "result": [{"success": True, "results": rows}]}


def report(rows):
    return m.aggregate(envelope(rows), T, T+2*m.M5, N)


class AnalyticReaderTests(unittest.TestCase):
    def test_complete_window(self):
        r = report([fixture(T, btc=True), fixture(T+m.M5, btc=True, heartbeat=True),
                    fixture(T+2*m.M5, btc=True)])
        self.assertEqual(r["status"], "COMPLETE_WINDOW")
        self.assertEqual(r["valid_unique_bars"], 3)
        self.assertEqual(r["bar_events"], 2)
        self.assertEqual(r["heartbeats"], 1)
        self.assertEqual(r["footprint_available_bars"], 3)
        self.assertEqual(r["observed_label_counts"]["DELTA_PEAK"], 2)
        self.assertEqual(r["cohort"], "BTC_TRANSPORT_ONLY")
        self.assertFalse(r["orders_enabled"])

    def test_leading_trailing_gaps(self):
        r = report([fixture(T+m.M5, btc=True)])
        self.assertEqual(r["status"], "INCOMPLETE_WINDOW")
        self.assertEqual(r["unobserved_valid_slots"], 2)

    def test_empty_distinct_from_failure(self):
        self.assertEqual(report([])["status"], "NO_MATCHING_ROWS")
        with self.assertRaises(m.AuditError):
            m.aggregate({}, T, T+2*m.M5, N)

    def test_invalid_and_collision_are_not_complete(self):
        bad = fixture(T, btc=True)
        bad["is_timely"] = 1
        self.assertEqual(report([bad])["status"], "INVALID_OR_CONFLICTING_ROWS")
        r = report([fixture(T, btc=True), fixture(T, btc=True, heartbeat=True)])
        self.assertEqual(r["quarantined_bars"], 1)
        self.assertEqual(r["status"], "INVALID_OR_CONFLICTING_ROWS")

    def test_scope_contamination_rejected(self):
        for row in (fixture(T), fixture(T-m.M5, btc=True),
                    dict(fixture(T, btc=True), received_at_ms=N+1)):
            with self.assertRaises(m.AuditError):
                report([row])

    def test_sentinel_fails_closed(self):
        with self.assertRaises(m.AuditError):
            report([fixture(T, btc=True)] * (m.LIMIT+1))

    def test_output_has_no_payload_or_price(self):
        r = report([fixture(T, btc=True)])
        s = json.dumps(r)
        for key in ("raw_json", "event_key", "ohlc", "received_at_ms", "poc", "1.111"):
            if key == "raw_json":
                self.assertFalse(r["raw_json_logged"])
            else:
                self.assertNotIn(key, s)

    def test_window_mature_and_bounded(self):
        self.assertEqual(m.window(N), (T, T+2*m.M5))
        a,b = m.window(m.BTC_END+60_000)
        self.assertEqual(b, m.BTC_END-m.M5)
        self.assertEqual((b-a)//m.M5+1, m.MAX_SLOTS)
        with self.assertRaises(m.AuditError):
            m.window(T)

    def test_no_network_without_explicit(self):
        with patch.object(m,"api_request") as api:
            with self.assertRaises(m.AuditError):
                m.read_live("", "", now_ms=N)
            api.assert_not_called()

    def test_only_verified_test_select(self):
        ids = {m.MAIN_DB:"main-id",m.TEST_DB:"test-id"}
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="mock"),
              patch.object(m,"inspect_verified_inventory",return_value=ids),
              patch.object(m,"api_request",side_effect=[{},envelope([])]) as api):
            self.assertEqual(m.read_live("","",now_ms=N,explicit=True)["status"],"NO_MATCHING_ROWS")
        self.assertEqual(api.call_count,2)
        method,path,token,body = api.call_args.args
        self.assertEqual(method,"POST")
        self.assertTrue(path.endswith("/test-id/query"))
        self.assertTrue(body["sql"].startswith("SELECT "))
        self.assertEqual(body["params"], [m.SYMBOL,"5",T,T+2*m.M5,N,"0.8.1-lab",m.LIMIT+1])

    def test_identical_db_rejected(self):
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="mock"),
              patch.object(m,"inspect_verified_inventory",return_value={m.MAIN_DB:"same",m.TEST_DB:"same"}),
              patch.object(m,"api_request",return_value={}) as api):
            with self.assertRaises(m.AuditError):
                m.read_live("","",now_ms=N,explicit=True)
        self.assertEqual(api.call_count,1)


if __name__ == "__main__":
    unittest.main()
