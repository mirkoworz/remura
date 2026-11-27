#!/usr/bin/env python3
# REMURA v0.8.54 — synthetic regressions, 14/11/2026 CET.
import unittest
from test_volume_features_v1 import fixture, changed
from test_telemetry_v1 import T0
from volume_features_v1 import M5, BTC_START
from fx_outcome_readiness_v1 import readiness

def coherent(t=T0,heartbeat=False):
    def cfg(p):
        p["quality"].update(lower_tf="1",daily_anchor="HL2")
        p["signed_result_atr"]=(p["ohlc"]["close"]-p["ohlc"]["open"])/p["ohlc"]["atr14"]
        p["efficiency"]=p["signed_result_atr"]/p["effort"]
        p["footprint"]["delta_pct"]=100*250/3550
    return changed(fixture(t,heartbeat=heartbeat),cfg)

def run(rows,asof=T0+12*M5+120000):
    return readiness(rows,as_of_ms=asof)

class ReadinessTests(unittest.TestCase):
    def test_complete_horizons(self):
        r=run([coherent()]+[coherent(T0+i*M5,True) for i in range(1,13)])
        self.assertEqual(r["status"],"DESCRIPTIVE_READINESS_ONLY")
        for h in ("15","30","60"):
            self.assertEqual(r["horizons"][h]["event_counts"]["ANY_EVENT"]["COMPLETE"],1)
        self.assertFalse(r["scientific_admission"])
        self.assertFalse(r["orders_enabled"])

    def test_descriptive_comparison_only(self):
        r=run([coherent()]+[coherent(T0+i*M5,True) for i in range(1,13)])
        c=r["horizons"]["15"]["descriptive_comparison"]["ANY_EVENT"]
        self.assertEqual(c["complete_events"],1)
        self.assertEqual(c["matched_events"],1)
        self.assertEqual(c["median_signed_close_return_atr"],0.0)
        self.assertTrue(c["not_execution_return"])
        self.assertFalse(r["trading_edge_established"])

    def test_pending_vs_mature_missing(self):
        r=run([coherent()],T0+3*M5+120000)
        self.assertEqual(r["horizons"]["15"]["event_counts"]["ANY_EVENT"]["MISSING_BAR"],1)
        self.assertEqual(r["horizons"]["30"]["event_counts"]["ANY_EVENT"]["PENDING_MATURITY"],1)

    def test_future_rows_not_known(self):
        r=run([coherent(),coherent(T0+M5,True)],T0+5000)
        self.assertEqual(r["excluded_counts"]["NOT_KNOWN_AS_OF"],1)

    def test_btc_excluded(self):
        r=run([fixture(BTC_START+M5,btc=True)])
        self.assertEqual(r["status"],"NO_FX_OBSERVATIONS")

    def test_invalid_and_conflict(self):
        self.assertEqual(run([dict(coherent(),event_key="bad")])["status"],"BLOCKED_INVALID_OR_CONFLICT")
        self.assertEqual(run([coherent(),dict(coherent(),received_at_ms=T0+4000)])["status"],"BLOCKED_INVALID_OR_CONFLICT")

    def test_config_mismatch(self):
        r=run([changed(coherent(),lambda p:p["quality"].update(daily_anchor="POC FOOTPRINT"))])
        self.assertEqual(r["status"],"BLOCKED_CONFIG_METADATA_MISMATCH")

    def test_review_not_complete(self):
        r=run([changed(coherent(),lambda p:p.update(efficiency=100))])
        self.assertEqual(r["horizons"]["15"]["event_counts"]["ANY_EVENT"]["DIAGNOSTIC_REVIEW"],1)

    def test_baseline_match(self):
        r=run([coherent()]+[coherent(T0+i*M5,True) for i in range(1,13)])
        c=r["horizons"]["15"]["event_counts"]["ANY_EVENT"]
        # T0 and T0+5m belong to the same fixed UTC session in this fixture.
        self.assertEqual(c["MATCHED_BASELINE"],1)

if __name__=="__main__":
    unittest.main()
