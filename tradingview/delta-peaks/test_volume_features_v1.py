#!/usr/bin/env python3
# REMURA v0.8.46 LAB — 14/11/2026 08:14 CET. Synthetic fixtures only.
import json
import unittest

from test_telemetry_v1 import sample, T0
from test_remura_tv_bridge_preview_v1 import row
from volume_features_v1 import analyze_export, BTC_START, BTC_END, M5


def fixture(close=T0, btc=False, heartbeat=False):
    p = sample()
    if btc:
        p.update(symbol="BINANCE:BTCUSDT", feed="BINANCE")
    p.update(bar_open_ms=close-M5, bar_close_ms=close, sent_clock_ms=close+1000)
    p["level_origin_ms"] = {k: None if t is None else t-T0+close
                            for k,t in p["level_origin_ms"].items()}
    if heartbeat:
        p["events"].update(peak=False, er_positive=False, day_level_action="NONE",
                           day_level_rank=None)
        p["event_type"] = "HEARTBEAT"
    return row(p, received_at_ms=close+5000, is_timely=0 if btc else 1)


def changed(r, fn):
    p = json.loads(r["raw_json"])
    fn(p)
    r["raw_json"] = json.dumps(p)
    return r


class FeatureTests(unittest.TestCase):
    def test_fx_observations_and_hypotheses(self):
        v = analyze_export([fixture()])["observations"][0]
        self.assertIn("POSSIBLE_BUYING_EFFORT_ABSORPTION", v["hypotheses"])
        self.assertEqual(v["observed"]["footprint"]["imb_buy_rows"], 3)
        self.assertEqual(v["observed"]["delta_intrabar_estimate"], 2400)
        self.assertTrue(v["fx_timeliness_eligible"])
        self.assertFalse(v["confirmed_institutional_activity"])
        self.assertFalse(v["statistical_edge_validated"])
        self.assertFalse(v["orders_enabled"])

    def test_btc_never_fx_research(self):
        v = analyze_export([fixture(BTC_START+M5, btc=True)])["observations"][0]
        self.assertEqual(v["cohort"], "BTC_TRANSPORT_ONLY")
        self.assertTrue(v["transport_timely"])
        self.assertFalse(v["fx_timeliness_eligible"])
        self.assertEqual(v["hypotheses"], [])

    def test_btc_window_and_timely_guard(self):
        for r in (fixture(BTC_END, btc=True), fixture(BTC_START-M5, btc=True),
                  dict(fixture(BTC_START+M5, btc=True), is_timely=1)):
            self.assertEqual(analyze_export([r])["counts"], {"INVALID_ROW": 1})

    def test_btc_metadata_mismatch(self):
        r = fixture(BTC_START+M5, btc=True)
        r["event_key"] = "wrong"
        self.assertEqual(analyze_export([r])["counts"], {"INVALID_ROW": 1})

    def test_wrong_feed(self):
        for r in (fixture(), fixture(BTC_START+M5, btc=True)):
            changed(r, lambda p: p.update(feed="OTHER"))
            self.assertEqual(analyze_export([r])["counts"], {"INVALID_ROW": 1})

    def test_heartbeat_not_a_signal(self):
        v = analyze_export([fixture(heartbeat=True)])["observations"][0]
        self.assertEqual(v["observed_labels"], [])
        self.assertEqual(v["verdict"], "NO_OPERATIONAL_SIGNAL")

    def test_missing_not_zero(self):
        def partial(p):
            p.update(delta_intrabar=None, effort=None)
            p["quality"]["has_intrabar_delta"] = False
            p["ohlc"]["atr14"] = None
            p["footprint"] = {k: False if k=="available" else None for k in p["footprint"]}
            p["quality"]["has_footprint"] = False
        v = analyze_export([changed(fixture(), partial)])["observations"][0]
        self.assertEqual(v["quality"], "PARTIAL")
        self.assertIsNone(v["observed"]["delta_sign"])
        self.assertIsNone(v["observed"]["footprint"]["delta"])
        self.assertIn("footprint", v["missing_fields"])

    def test_no_same_bar_retest(self):
        v = analyze_export([fixture()])["observations"][0]
        levels = {l["name"]: l for l in v["observed"]["levels"]}
        self.assertIsNone(levels["day1"]["range_intersects_prior_level"])
        self.assertTrue(levels["week"]["range_intersects_prior_level"])

    def test_future_level_invalid(self):
        r = changed(fixture(), lambda p: p["level_origin_ms"].update(day1=T0+M5))
        self.assertEqual(analyze_export([r])["counts"], {"INVALID_ROW": 1})

    def test_gap_and_order(self):
        result = analyze_export([fixture(T0+2*M5), fixture(T0, heartbeat=True)])
        c = result["continuity"]["FXCM:EURUSD"]
        self.assertEqual(c["unobserved_slots_within_span"], 1)
        self.assertEqual(c["heartbeats"], 1)
        self.assertEqual(c["bar_events"], 1)
        self.assertEqual(result["observations"][0]["bar_close_ms"], T0)

    def test_cross_type_collision_quarantined(self):
        result = analyze_export([fixture(), fixture(heartbeat=True), fixture()])
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["quarantined_bars"], 1)
        self.assertEqual(result["counts"]["CONFLICT_ROW"], 2)

    def test_duplicate_and_separation(self):
        r = fixture()
        out = analyze_export([r, r, fixture(BTC_START+M5, btc=True)])
        self.assertEqual(out["counts"]["DUPLICATE_ROW"], 1)
        self.assertEqual(len(out["continuity"]), 2)

    def test_empty_or_invalid_not_healthy(self):
        self.assertEqual(analyze_export([])["status"], "NO_VALID_ROWS")
        out = analyze_export([{"private": "do-not-echo"}])
        self.assertNotIn("do-not-echo", json.dumps(out))
        self.assertEqual(out["status"], "NO_VALID_ROWS")

    def test_delta_disagreement_not_trade(self):
        r = changed(fixture(), lambda p: p["ohlc"].update(close=1.1095))
        v = analyze_export([r])["observations"][0]
        self.assertIn("PRICE_DELTA_DIRECTION_DISAGREEMENT", v["hypotheses"])
        self.assertEqual(v["verdict"], "NO_OPERATIONAL_SIGNAL")


if __name__ == "__main__":
    unittest.main()
