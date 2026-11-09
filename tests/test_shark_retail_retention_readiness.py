"""Offline retention/capacity regression on disposable synthetic SQLite.

Replays the actual two Squalincome history-pruning SQL shapes; demonstrates
that FIRST-SEEN links survive after the original row is deleted. No API,
provider data, LIVE filesystem, backup or service configuration changes.
"""
from __future__ import annotations

from datetime import timedelta
import sqlite3
import unittest

from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_retail_retention_readiness as readiness
from test_shark_original_decision_atomic_gate import new_history
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ,RECORDED
from test_shark_signal_ingest_decision_link import setup_case,OBS,NOW


class OriginalHistoryRetentionTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.doc=setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)
        retail.capture_pair(
            self.db,original_snapshot=original_pair(),
            file_read_at=READ,clock=RECORDED,
            research_numeric_features=True)
        result=atomic.record_new(
            self.db,insert_history=new_history,
            original_document=self.doc,clock=NOW,
            research_retail_inbox=True)
        self.assertEqual(result["retailFirstSeen"],
                         "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT")
        self.hid=self.db.execute(
            "SELECT id FROM squalincome_history").fetchone()[0]

    def tearDown(self):
        self.db.close()

    def check(self,**kwargs):
        return readiness.audit(
            self.db,history_keep_days=kwargs.pop("history_keep_days",30),
            history_max_per_symbol=kwargs.pop(
                "history_max_per_symbol",720),**kwargs)

    def test_28_week_protocol_exceeds_original_30_day_and_720_row_caps(self):
        before=self.db.total_changes
        report=self.check()
        self.assertEqual(self.db.total_changes,before)
        self.assertEqual(report["status"],
                         "NO_GO_ORIGINAL_PROOF_RETENTION_OR_CAPACITY")
        self.assertEqual(report["frozenRetailStudyWeeks"],28)
        self.assertEqual(report["studyDaysRequired"],196)
        self.assertEqual(report["scenarioTwoMarketReceiptRows"],28224)
        self.assertEqual(report["maxResearchFirstSeenReceiptRows"],15000)
        self.assertEqual(report["maxResearchNumericRows"],4500)
        for key in ("originalHistoryDaysShorterThanStudy",
                    "originalHistoryRowCapBelowQuarterHourScenario",
                    "retailReceiptCapBelowCollectorScenario",
                    "retailNumericCapBelowCollectorScenario"):
            self.assertTrue(report[key])
        self.assertEqual(report["orphanedRetailHistoryLinks"],0)
        self.assertEqual(report["orphanedIngestHistoryLinks"],0)
        self.assertFalse(report["retailFirstSeenLiveAuthorized"])
        self.assertFalse(report["edgeEstablished"])

    def test_native_30_day_purge_leaves_orphan_retail_and_ingest_links(self):
        self.assertEqual(
            numeric.read_linked(self.db,history_id=self.hid)["status"],
            "LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH")
        # Same original observation retention SQL as signals_monitor._scan_once
        with self.db:
            self.db.execute(
                "DELETE FROM squalincome_history WHERE observed_at < ?",
                ((OBS+timedelta(days=31)
                  -timedelta(days=30)).isoformat(),))
        report=self.check()
        self.assertEqual(report["orphanedRetailHistoryLinks"],1)
        self.assertEqual(report["orphanedIngestHistoryLinks"],1)
        self.assertEqual(
            numeric.read_linked(self.db,history_id=self.hid)["status"],
            "UNKNOWN_NO_ORIGINAL_RETAIL_LINK")
        self.assertFalse(report["retailFirstSeenLiveAuthorized"])

    def test_native_per_symbol_720_row_prune_can_orphan_original_id(self):
        self.db.executemany(
            "INSERT INTO squalincome_history(symbol,observed_at) VALUES(?,?)",
            [("EURUSD",(OBS+timedelta(minutes=15*i)).isoformat())
             for i in range(1,721)])
        self.db.commit()
        # Exact native per-symbol bounded-history delete shape.
        with self.db:
            self.db.execute(
                "DELETE FROM squalincome_history WHERE symbol=? AND id NOT IN"
                " (SELECT id FROM squalincome_history WHERE symbol=?"
                " ORDER BY id DESC LIMIT ?)",
                ("EURUSD","EURUSD",720))
        report=self.check()
        self.assertEqual(report["orphanedRetailHistoryLinks"],1)
        self.assertEqual(report["orphanedIngestHistoryLinks"],1)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],720)

    def test_missing_schema_is_unknown_not_false_zero_or_live_go(self):
        db=sqlite3.connect(":memory:")
        try:
            x=readiness.audit(
                db,history_keep_days=365,
                history_max_per_symbol=100000,
                retail_cycle_minutes=120)
            self.assertEqual(x["status"],
                             "NO_GO_ORIGINAL_PROOF_RETENTION_OR_CAPACITY")
            self.assertIsNone(x["orphanedRetailHistoryLinks"])
            self.assertIsNone(x["orphanedIngestHistoryLinks"])
            self.assertIn("squalincome_history",x["missingResearchTables"])
        finally:
            db.close()

    def test_hypothetically_sufficient_caps_are_policy_only_not_real_go(self):
        x=self.check(
            history_keep_days=365,
            history_max_per_symbol=20000,
            retail_cycle_minutes=120)
        self.assertEqual(x["status"],
                         "POLICY_SCENARIO_ONLY_NOT_LIVE_AUTHORIZATION")
        self.assertFalse(x["retailFirstSeenLiveAuthorized"])
        self.assertFalse(x["liveCapacityOrCostVerified"])
        self.assertFalse(x["edgeEstablished"])

    def test_bad_capacity_arguments_fail_without_writes(self):
        before=self.db.total_changes
        for args in (
            dict(history_keep_days=True,history_max_per_symbol=720),
            dict(history_keep_days=30,history_max_per_symbol=0),
            dict(history_keep_days=30,history_max_per_symbol=720,
                 retail_cycle_minutes=0),
        ):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    readiness.audit(self.db,**args)
        self.assertEqual(self.db.total_changes,before)


if __name__=="__main__":
    unittest.main()
