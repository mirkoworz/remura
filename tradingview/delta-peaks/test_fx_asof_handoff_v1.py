#!/usr/bin/env python3
# REMURA v0.8.50 LAB — 14/11/2026 10:46 CET — synthetic tests only.
import unittest
from test_volume_features_v1 import fixture, changed
from test_telemetry_v1 import T0
from volume_features_v1 import BTC_START, M5
from fx_asof_handoff_v1 import handoff

def good():
    def coherent(p):
        p["signed_result_atr"] = (p["ohlc"]["close"]-p["ohlc"]["open"])/p["ohlc"]["atr14"]
        p["efficiency"] = p["signed_result_atr"]/p["effort"]
        p["footprint"]["delta_pct"] = 100*250/3550
    return changed(fixture(), coherent)

def run(rows, decision=T0+5000):
    return handoff(rows, decision_ms=decision, bar_close_ms=T0)

class HandoffTests(unittest.TestCase):
    def test_descriptive_only(self):
        r=run([good()])
        self.assertEqual(r["status"],"DESCRIPTIVE_CANDIDATE_ONLY")
        self.assertIsNotNone(r["candidate"])
        for k in ("institutional_admissible","predictive_admissible","track_b_connected",
                  "orders_enabled","notifications_enabled"):
            self.assertFalse(r[k])
        self.assertEqual(r["configuration_status"],"ALERT_INPUTS_NOT_ATTESTED")

    def test_btc_excluded(self):
        r=run([fixture(BTC_START+M5,btc=True)])
        self.assertEqual(r["status"],"NO_CURRENT_ASOF_OBSERVATION")
        self.assertEqual(r["excluded_counts"]["OTHER_COHORT_EXCLUDED"],1)

    def test_future_receipt_not_leaked(self):
        r=run([good()],T0+4999)
        self.assertIsNone(r["candidate"])
        self.assertEqual(r["excluded_counts"]["NOT_KNOWN_AT_DECISION"],1)

    def test_later_conflict_not_retroactive(self):
        late=dict(good(),received_at_ms=T0+6000)
        r=run([good(),late])
        self.assertEqual(r["status"],"DESCRIPTIVE_CANDIDATE_ONLY")

    def test_no_old_bar_fallback(self):
        r=run([fixture(T0-M5)])
        self.assertEqual(r["status"],"NO_CURRENT_ASOF_OBSERVATION")

    def test_invalid_or_conflicting_blocks(self):
        r=run([good(),dict(good(),event_key="bad")])
        self.assertEqual(r["status"],"BLOCKED_INVALID_OR_CONFLICT")
        r=run([good(),dict(good(),received_at_ms=T0+4000)])
        self.assertEqual(r["status"],"BLOCKED_INVALID_OR_CONFLICT")

    def test_math_review_blocks(self):
        r=run([fixture()])
        self.assertEqual(r["status"],"BLOCKED_DIAGNOSTIC_REVIEW")
        self.assertIsNone(r["candidate"])

    def test_partial_not_imputed(self):
        def missing(p):
            p["footprint"]={k:False if k=="available" else None for k in p["footprint"]}
            p["quality"]["has_footprint"]=False
        r=run([changed(good(),missing)])
        self.assertEqual(r["status"],"PARTIAL_DESCRIPTIVE_ONLY")
        self.assertIsNone(r["candidate"]["observed"]["footprint"]["delta"])

    def test_late_row_blocked(self):
        late=dict(good(),received_at_ms=T0+130000,is_timely=0)
        r=run([late],T0+140000)
        self.assertEqual(r["status"],"BLOCKED_NOT_PROSPECTIVELY_TIMELY")

    def test_invalid_decision_window(self):
        for t in (T0-1,T0+M5,True):
            with self.assertRaises(ValueError):
                run([],t)

if __name__ == "__main__":
    unittest.main()
