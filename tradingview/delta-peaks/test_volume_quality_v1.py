#!/usr/bin/env python3
# REMURA v0.8.48 — synthetic regressions only, 14/11/2026 09:38 CET.
import unittest
from test_telemetry_v1 import sample, T0
from volume_quality_v1 import diagnose, compare


class QualityTests(unittest.TestCase):
    def test_consistent_arithmetic(self):
        p = sample()
        p.update(signed_result_atr=(p["ohlc"]["close"]-p["ohlc"]["open"])/p["ohlc"]["atr14"])
        p["efficiency"] = p["signed_result_atr"]/p["effort"]
        p["footprint"]["delta_pct"] = 100*250/3550
        r = diagnose(p)
        for k in ("FP_NONNEGATIVE","FP_TOTAL","FP_DELTA","FP_DELTA_PCT",
                  "FP_VALUE_AREA_ORDER","SIGNED_RESULT_ATR","EFFICIENCY","ER_DELTA_DIRECTION"):
            self.assertEqual(r[k],"CONSISTENT",k)

    def test_missing_footprint_not_failure(self):
        p = sample()
        p["footprint"] = {k: False if k=="available" else None for k in p["footprint"]}
        r = diagnose(p)
        self.assertTrue(all(v=="NOT_EVALUABLE" for k,v in r.items() if k.startswith("FP_")))

    def test_inconsistent_footprint(self):
        p = sample()
        p["footprint"].update(total=1,delta=100,delta_pct=10,poc=0)
        r = diagnose(p)
        for k in ("FP_TOTAL","FP_DELTA","FP_DELTA_PCT","FP_VALUE_AREA_ORDER"):
            self.assertEqual(r[k],"REVIEW",k)

    def test_zero_volume(self):
        p = sample()
        p["footprint"].update(buy=0,sell=0,total=0,delta=0,delta_pct=None)
        self.assertEqual(diagnose(p)["FP_DELTA_PCT"],"NOT_APPLICABLE")
        p["footprint"]["delta_pct"]=0
        self.assertEqual(diagnose(p)["FP_DELTA_PCT"],"REVIEW")

    def test_er_arithmetic_mismatch(self):
        p = sample()
        p.update(delta_intrabar=-100,signed_result_atr=1,efficiency=0)
        r = diagnose(p)
        for k in ("SIGNED_RESULT_ATR","EFFICIENCY","ER_DELTA_DIRECTION"):
            self.assertEqual(r[k],"REVIEW",k)

    def test_missing_atr_not_evaluable(self):
        p = sample()
        p["ohlc"]["atr14"] = None
        self.assertEqual(diagnose(p)["SIGNED_RESULT_ATR"],"NOT_EVALUABLE")

    def test_retest_same_bar_or_outside(self):
        p = sample()
        p["events"]["retest_day1"] = True
        self.assertEqual(diagnose(p)["RETEST_DAY1"],"REVIEW")
        p["level_origin_ms"]["day1"] = T0-300000
        self.assertEqual(diagnose(p)["RETEST_DAY1"],"CONSISTENT")
        p["levels"]["day1"] = 10
        self.assertEqual(diagnose(p)["RETEST_DAY1"],"REVIEW")

    def test_tolerance_and_nonfinite(self):
        self.assertEqual(compare(1,1.0000001),"CONSISTENT")
        self.assertEqual(compare(1,float("inf")),"NOT_EVALUABLE")
        self.assertEqual(compare(None,1),"NOT_EVALUABLE")

if __name__ == "__main__":
    unittest.main()
