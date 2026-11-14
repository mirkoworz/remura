#!/usr/bin/env python3
# REMURA v0.8.67 — synthetic ONLY.
import copy,json,unittest
from test_cvd_telemetry_preview_v1 import fixture,T0,VERSION,SYMBOL,M5
from cvd_telemetry_preview_v1 import validate
from cvd_outcome_readiness_v1 import summarize
from unittest.mock import patch

def bars(n=16,*,gap=None):
    out=[]
    for i in range(n):
        if i==gap: continue
        t=T0+i*M5
        e=fixture();p=e["snapshot"];c=e["cvd"]
        p.update(bar_close_ms=t,bar_open_ms=t-M5,sent_clock_ms=t+1000)
        for key,value in p["level_origin_ms"].items():
            if value is not None: p["level_origin_ms"][key]=value+i*M5
        p["ohlc"].update(close=1.110+i*.0001, high=1.115,low=1.109,atr14=.001)
        c.update(price_bull=i in (0,1),cvd_bull=i==0,pivot_close_ms=t-2*M5 if i in (0,1) else None)
        v=validate(e,received_ms=t+5000)
        row={"bar_close_ms":t,"received_at_ms":t+5000,"symbol":SYMBOL,"version":VERSION,"event_key":v["event_key"]}
        out.append((row,e,v))
    return out

class OutcomeTests(unittest.TestCase):
    @patch("cvd_outcome_readiness_v1.diagnose",return_value={})
    def test_matched_same_direction_and_horizon(self,_):
        r=summarize(bars(),as_of_ms=T0+15*M5+120000)
        h=r["horizons"]["60"]
        self.assertEqual(h["matched_selected"],1)
        self.assertAlmostEqual(h["paired_descriptive_difference_atr"],0)
        self.assertEqual(r["horizons"]["240"]["counts"]["CVD_SELECTED"]["PENDING_MATURITY"],1)
        self.assertFalse(r["trading_edge_established"])
    @patch("cvd_outcome_readiness_v1.diagnose",return_value={})
    def test_missing_bar_not_interpolated(self,_):
        h=summarize(bars(gap=4),as_of_ms=T0+15*M5+120000)["horizons"]["60"]
        self.assertEqual(h["counts"]["CVD_SELECTED"]["MISSING_BAR"],1)
        self.assertIsNone(h["paired_descriptive_difference_atr"])
    @patch("cvd_outcome_readiness_v1.diagnose",return_value={})
    def test_cutoff_and_direction_separate(self,_):
        r=summarize(bars(),as_of_ms=T0+12*M5)
        self.assertEqual(r["horizons"]["60"]["counts"]["CVD_SELECTED"]["PENDING_MATURITY"],1)
        self.assertEqual(r["bars"],12)
    @patch("cvd_outcome_readiness_v1.diagnose",return_value={"x":"REVIEW"})
    def test_diagnostic_blocks(self,_):
        r=summarize(bars(),as_of_ms=T0+15*M5+120000)
        self.assertEqual(r["horizons"]["60"]["counts"]["CVD_SELECTED"]["DIAGNOSTIC_REVIEW"],1)
    def test_empty_unknown(self):
        r=summarize([],as_of_ms=T0)
        self.assertEqual(r["status"],"NO_OBSERVATIONS")
        self.assertIsNone(r["horizons"]["60"]["paired_descriptive_difference_atr"])
if __name__=="__main__":
    unittest.main()
