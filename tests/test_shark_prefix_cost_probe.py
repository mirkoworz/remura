"""Small, synthetic-only cost probe contract; no network or LIVE files."""
from __future__ import annotations

import json
import math
import unittest

from scripts import shark_cvd_prefix_lineage as prefix
from scripts import shark_prefix_cost_probe as probe


class PrefixCostProbeTests(unittest.TestCase):
    def test_probe_verifies_atomic_new_rows_and_default_off(self):
        out=probe.probe(pairs=2)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["scope"],probe.SCOPE)
        self.assertEqual(out["pairedRoundsPerMode"],2)
        self.assertGreater(out["main"]["newPrefixRowsPerOriginalSignal"],0)
        self.assertLessEqual(
            out["main"]["newPrefixRowsPerOriginalSignal"],
            prefix.MAX_CUTOFFS)
        self.assertEqual(out["private"]["newPrefixRowsPerNewCvdEvent"],1)
        self.assertGreaterEqual(out["main"]["extraMedianSQLitePageBytes"],0)
        self.assertGreaterEqual(out["private"]["extraMedianSQLitePageBytes"],0)
        for part in ("main","private"):
            self.assertEqual(out[part]["additionalBrokerCalls"],0)
            for mode in ("legacy","optIn"):
                self.assertEqual(out[part][mode]["n"],2)
                self.assertGreater(out[part][mode]["medianWallMs"],0)
                self.assertGreater(out[part][mode]["medianCpuMs"],0)
                self.assertGreater(out[part][mode]["medianPageBytes"],0)
        self.assertEqual(
            out["maxHypotheticalPilotRowsPerDayAtOneSignalPer15mPerMarket"],
            2*96*7)
        self.assertEqual(out["mainArchiveCapacityRows"],15000)
        self.assertFalse(out["performanceOrBillingCertifiedForOracle"])
        self.assertFalse(out["liveIngestInterferenceTested"])
        self.assertFalse(out["institutionalEdgeEstablished"])
        self.assertFalse(out["rssAttributableOnlyToNewFeature"])
        self.assertFalse(out["ordersEnabled"])
        self.assertFalse(out["alertsEnabled"])

    def test_budget_and_json_never_reveal_private_fixture(self):
        out=probe.probe(pairs=2)
        encoded=json.dumps(out,sort_keys=True)
        for secret in ("PRIVATE_FAKE_BROKER_IDENTIFIER","099741",
                       "source_document","hmac_secret","secretValue",
                       "providerSymbol","sourceDocument","cotReports",
                       "EURUSD","XAUUSD","tradeProfit"):
            self.assertNotIn(secret,encoded)
        self.assertTrue(math.isfinite(
            out["hypotheticalDaysToReachCapacityAtThisNonObservedUpperBound"]))

    def test_reject_unbounded_microbenchmark(self):
        for k in (0,1,13,True,None,2.5,"2"):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    probe.probe(pairs=k)


if __name__=="__main__":
    unittest.main()
