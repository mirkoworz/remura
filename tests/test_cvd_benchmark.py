"""CVD proxy research benchmark safety checks; synthetic, no broker/API."""
import copy
import json
import unittest

from scripts import cvd_benchmark as bench
from scripts import cvd_divergence as engine

DAY_START=1793577600000
STEP=engine.STEP


def synthetic(bars=45, volume=100):
    rows=[]
    for i in range(bars):
        low=10.0 if i==10 else 9.7 if i==22 else 10.4
        rows.append({
            "t":DAY_START+i*STEP,"o":10.8,
            "h":11.2,"l":low,"c":11.0,"v":volume,
        })
    return {"symbol":"EURUSD","provider":"ctrader",
            "providerSymbol":"SECRET_BROKER_ID",
            "frames":{"M15":rows,"H1":[],"H4":[]}}


def now(m):
    return m["frames"]["M15"][-1]["t"]+STEP+1000


class BenchmarkSafetyTests(unittest.TestCase):
    def test_fixed_price_only_comparator_contains_cvd_subset(self):
        market=synthetic()
        saved=copy.deepcopy(market)
        result=bench.evaluate(market,now=now(market),horizon_bars=4)
        self.assertEqual(result["status"],"ready")
        self.assertGreaterEqual(result["priceOnly"]["candidates"],1)
        self.assertEqual(result["cvdFiltered"]["candidates"],1)
        self.assertGreaterEqual(result["priceOnly"]["candidates"],
                                result["cvdFiltered"]["candidates"])
        self.assertEqual(result["cvdFiltered"]["matured"],1)
        self.assertIsNone(result["cvdFiltered"]["favorableFraction"])
        self.assertEqual(result["cvdFiltered"]["favorable"]+
                         result["cvdFiltered"]["unfavorable"]+
                         result["cvdFiltered"]["neutral"],1)
        self.assertEqual(len(result["rotatedVolumes"]),3)
        self.assertEqual([x["offset"] for x in result["rotatedVolumes"]],[3,7,13])
        self.assertEqual(market,saved,"never mutate raw tick data")
        self.assertNotIn("SECRET_BROKER_ID",json.dumps(result))
        self.assertEqual(result["realMarketAdvantage"],"NOT_ESTABLISHED")
        self.assertEqual(result["outcomeMeaning"],
                         "future_close_atr_direction_not_profit")
        self.assertFalse(result["alertsEnabled"])

    def test_confirmation_vs_future_outcome_is_causal(self):
        base=synthetic()
        after_pivot=copy.deepcopy(base)
        after_pivot["frames"]["M15"]=after_pivot["frames"]["M15"][:25]
        earlier=bench.evaluate(after_pivot,now=now(after_pivot),horizon_bars=4)
        self.assertEqual(earlier["status"],"ready")
        self.assertEqual(earlier["cvdFiltered"]["candidates"],1)
        self.assertEqual(earlier["cvdFiltered"]["matured"],0)
        self.assertEqual(earlier["cvdFiltered"]["pending"],1)
        # The same identified divergence is evaluated only after four
        # ADDITIONAL CLOSED M15 candles, never at the detection timestamp.
        later=copy.deepcopy(base)
        later["frames"]["M15"]=later["frames"]["M15"][:29]
        mature=bench.evaluate(later,now=now(later),horizon_bars=4)
        self.assertEqual(mature["cvdFiltered"]["candidates"],1)
        self.assertEqual(mature["cvdFiltered"]["matured"],1)
        self.assertEqual(mature["cvdFiltered"]["pending"],0)

    def test_price_only_still_exists_with_zero_volume_but_cvd_does_not(self):
        m=synthetic(volume=0)
        result=bench.evaluate(m,now=now(m))
        self.assertEqual(result["status"],"ready")
        self.assertGreaterEqual(result["priceOnly"]["candidates"],1)
        self.assertEqual(result["cvdFiltered"]["candidates"],0)
        self.assertEqual(result["cvdFiltered"]["matured"],0)
        self.assertEqual(result["cvdFiltered"]["favorableFraction"],None)

    def test_gaps_stale_or_unknown_market_cannot_be_scored(self):
        m=synthetic()
        m["frames"]["M15"].pop(4)
        report=bench.evaluate(m,now=now(m))
        self.assertEqual(report["status"],"unavailable")
        self.assertEqual(report["cause"],"partial")
        m=synthetic()
        report=bench.evaluate(m,now=now(m)+95*60*1000)
        self.assertEqual(report["status"],"unavailable")
        self.assertEqual(report["cause"],"stale")
        m=synthetic()
        m["provider"]="unknown"
        self.assertEqual(bench.evaluate(m,now=now(m))["status"],"unavailable")

    def test_negative_controls_are_deterministic_and_bounded(self):
        m=synthetic()
        for i,row in enumerate(m["frames"]["M15"]):
            row["v"]=(i*i*37)%257
        copy_before=copy.deepcopy(m)
        a=bench.evaluate(m,now=now(m))
        b=bench.evaluate(m,now=now(m))
        self.assertEqual(a,b)
        self.assertEqual(m,copy_before)
        self.assertEqual(len(a["rotatedVolumes"]),3)
        for v in a["rotatedVolumes"]:
            self.assertLessEqual(v["candidates"],a["priceOnly"]["candidates"])
            self.assertEqual(v["pending"]+v["matured"],v["candidates"])
        self.assertEqual(a["controlMeaning"],
                         "three_fixed_volume_rotations_not_permutation_test")

    def test_guardrails_reject_invalid_horizon_or_threshold(self):
        m=synthetic()
        for h in (0,-1,17,True,1.5):
            with self.assertRaises(ValueError):
                bench.evaluate(m,now=now(m),horizon_bars=h)
        for threshold in (-0.1,0,1,float("nan"),True):
            with self.assertRaises(ValueError):
                bench.evaluate(m,now=now(m),movement_atr=threshold)

    def test_no_results_are_rate_estimates_on_tiny_samples(self):
        m=synthetic()
        out=bench.evaluate(m,now=now(m))
        for key in ("priceOnly","cvdFiltered"):
            summary=out[key]
            self.assertLess(summary["matured"],30)
            self.assertIsNone(summary["favorableFraction"])
            self.assertEqual(summary["minimumMaturedForFraction"],30)

if __name__=="__main__":
    unittest.main()
