"""Small, synthetic-only cost probe contract; no network or LIVE files."""
from __future__ import annotations

import json
import math
import sqlite3
import unittest
from unittest.mock import patch

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

    def test_capacity_gate_is_read_only_and_never_claims_account_billing(self):
        with sqlite3.connect(":memory:") as db:
            absent=prefix.capacity_status(db,ledger="main")
            self.assertEqual(absent["status"],"LEDGER_NOT_CREATED")
            self.assertIsNone(absent["currentRows"])
            self.assertFalse(absent["storageBillingCertified"])
            prefix._main_schema(db)
            for i in range(8):
                db.execute(
                    f"INSERT INTO {prefix.MAIN_TABLE} "
                    "(symbol,report_date,price_time,observed_at,"
                    "m15_closed_at,prefix_sha256,recorded_at,"
                    "schema_version) VALUES (?,?,?,?,?,?,?,?)",
                    ("EURUSD","2026-10-27","2026-11-04T11:00:00Z",
                     "2026-11-04T11:16:00Z",str(i),"0"*64,
                     "2026-11-04T11:16:02Z",prefix.VERSION))
            with patch.object(prefix,"MAX_MAIN_ROWS",10):
                before=db.total_changes
                db.execute("PRAGMA query_only=ON")
                try:
                    state=prefix.capacity_status(db,ledger="main")
                    self.assertEqual(state["status"],"WARNING_80_PERCENT")
                    self.assertEqual(state["currentRows"],8)
                    self.assertEqual(state["remainingRows"],2)
                    self.assertEqual(state["capacityPercent"],80)
                    self.assertFalse(state["liveAccountUsageKnown"])
                finally:
                    db.execute("PRAGMA query_only=OFF")
                self.assertEqual(db.total_changes,before)
                for i in (8,9):
                    db.execute(
                        f"INSERT INTO {prefix.MAIN_TABLE} "
                        "(symbol,report_date,price_time,observed_at,"
                        "m15_closed_at,prefix_sha256,recorded_at,"
                        "schema_version) VALUES (?,?,?,?,?,?,?,?)",
                        ("EURUSD","2026-10-27","2026-11-04T11:00:00Z",
                         "2026-11-04T11:16:00Z",str(i),"0"*64,
                         "2026-11-04T11:16:02Z",prefix.VERSION))
                self.assertEqual(prefix.capacity_status(
                    db,ledger="main")["status"],"AT_HARD_LIMIT")
            self.assertEqual(prefix.capacity_status(
                db,ledger="private")["status"],"LEDGER_NOT_CREATED")
            with self.assertRaises(ValueError):
                prefix.capacity_status(db,ledger="bad_scope")

    def test_reject_unbounded_microbenchmark(self):
        for k in (0,1,13,True,None,2.5,"2"):
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    probe.probe(pairs=k)


if __name__=="__main__":
    unittest.main()
