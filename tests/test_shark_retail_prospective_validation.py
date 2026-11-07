"""Adversarial retail prospective readiness: no live data, no profit claims."""
from __future__ import annotations

from datetime import timedelta
import json
import sqlite3
import unittest

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_retail_prospective_validation as study
from scripts import shark_original_decision_atomic_gate as atomic
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ, RECORDED
from test_shark_signal_ingest_decision_link import setup_case, NOW, OBS
from test_shark_original_decision_atomic_gate import new_history


class RetailProspectiveStudyTests(unittest.TestCase):
    def setUp(self):
        self.db, _, self.price = setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)
        self.snapshot = original_pair()

    def tearDown(self):
        self.db.close()

    def capture(self, *, six=True):
        retail.capture_pair(
            self.db, original_snapshot=self.snapshot,
            file_read_at=READ, clock=RECORDED,
            research_numeric_features=six)

    def decide(self, *, inbox=True):
        atomic.record_new(self.db, insert_history=new_history,
                          original_document=self.price, clock=NOW,
                          research_retail_inbox=inbox)

    def audit(self, as_of=None):
        return study.audit(self.db, as_of=as_of or NOW)

    def test_complete_before_decision_and_read_only(self):
        self.capture()
        self.decide()
        changes = self.db.total_changes
        out = self.audit()
        self.assertEqual(out["pilotDecisionsAsOf"], 1)
        self.assertEqual(out["coverage"]["COMPLETE_LOCAL_RESEARCH_CONTEXT"], 1)
        self.assertEqual(out["distinctLocalRetailReceiptsLinked"], 1)
        self.assertEqual(out["distinctObservedUtcWeeksUpperBound"], 1)
        self.assertEqual(out["independentMarketSamplesProven"], 0)
        self.assertFalse(out["retailIncrementalPredictiveValueMeasured"])
        self.assertEqual(out["outcomesRead"], 0)
        self.assertEqual(out["costsRead"], 0)
        self.assertEqual(changes, self.db.total_changes)
        self.assertNotIn("features", out)
        self.assertNotIn("EURUSD", str(out))
        self.assertNotIn("62.5", str(out))

    def test_missing_numeric_not_negative_or_zero(self):
        self.capture(six=False)
        self.decide()
        out = self.audit()
        self.assertEqual(
            out["coverage"]["UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN"], 1)
        self.assertEqual(out["distinctLocalRetailReceiptsLinked"], 0)
        self.assertFalse(out["edgeEstablished"])

    def test_missing_original_link_not_imputed_from_newest_receipt(self):
        self.capture()
        self.decide(inbox=False)
        out = self.audit()
        self.assertEqual(out["coverage"]["UNKNOWN_NO_ORIGINAL_RETAIL_LINK"], 1)
        self.assertEqual(out["distinctLocalRetailReceiptsLinked"], 0)

    def test_asof_prior_to_observation_excludes_future_decision(self):
        self.capture()
        self.decide()
        out = self.audit(as_of=OBS-timedelta(seconds=1))
        self.assertEqual(out["pilotDecisionsAsOf"], 0)

    def test_asof_at_observation_cannot_read_future_link(self):
        self.capture()
        self.decide()
        out = self.audit(as_of=OBS)
        self.assertEqual(out["coverage"]["UNKNOWN_LINK_NOT_YET_KNOWN_ASOF"], 1)

    def test_modified_link_clock_rejected_despite_drop_protection(self):
        self.capture()
        self.decide()
        self.db.execute("DROP TRIGGER research_retail_context_update")
        self.db.execute(
            f"UPDATE {retail.LINK} SET linked_at='2026-11-10T12:00:00+00:00'")
        self.db.commit()
        out = self.audit(as_of=NOW+timedelta(days=2))
        self.assertEqual(out["coverage"]["REJECTED_CAUSALITY_OR_INTEGRITY"], 1)

    def test_modified_link_symbol_rejected_even_with_valid_feature_sha(self):
        self.capture()
        self.decide()
        self.db.execute("DROP TRIGGER research_retail_context_update")
        self.db.execute(f"UPDATE {retail.LINK} SET symbol='XAUUSD'")
        self.db.commit()
        self.assertEqual(
            self.audit()["coverage"]["REJECTED_CAUSALITY_OR_INTEGRITY"], 1)

    def test_tampered_numeric_values_rejected_not_called_missing(self):
        self.capture()
        self.decide()
        self.db.execute("DROP TRIGGER research_retail_features_no_update")
        self.db.execute(f"UPDATE {numeric.TABLE} SET long_pct=63 "
                        "WHERE symbol='EURUSD'")
        self.db.commit()
        self.assertEqual(
            self.audit()["coverage"]["REJECTED_CAUSALITY_OR_INTEGRITY"], 1)

    def test_no_research_tables_does_not_autocreate_anything(self):
        self.db.execute(f"DROP TABLE {numeric.TABLE}")
        self.db.commit()
        self.decide(inbox=False)
        count = self.db.execute(
            "SELECT count(*) FROM sqlite_master").fetchone()[0]
        self.assertEqual(
            self.audit()["coverage"]["UNKNOWN_NUMERIC_ARCHIVE_NOT_ENABLED"], 1)
        self.assertEqual(
            count, self.db.execute("SELECT count(*) FROM sqlite_master").fetchone()[0])

    def test_prospective_study_plan_has_no_outcome_or_oos_execution(self):
        self.assertEqual(study.PRESPECIFIED_COMPARISON["scoreAndPnlStatus"],
                         "NOT_MEASURED")
        self.assertEqual(study.MIN_COHORTS_PER_FOLD, 30)
        self.assertEqual(study.MIN_COT_WEEKS_PER_FOLD, 8)
        self.assertEqual(study.FOLDS, ("train", "validation", "test"))
        self.assertEqual(self.audit()["pilotDecisionsAsOf"], 0)

    def test_synthetic_exact_4500_rows_backup_restore_and_bytes(self):
        out = study.synthetic_storage_probe()
        # Sanitized reproducible measured bytes in the existing CI log.
        print("REMURA_RETAIL_SYNTHETIC_STORAGE=" +
              json.dumps(out, sort_keys=True))
        self.assertEqual(out["featureRows"], 4500)
        self.assertEqual(out["originalReceiptRows"], 4500)
        self.assertEqual(out["backupRestoreIntegrity"], "OK")
        self.assertGreater(out["mainDbBytes"], 0)
        self.assertGreater(out["restoredBackupBytes"], 0)
        self.assertFalse(out["oracleFreeTierQuotaCertified"])
        self.assertFalse(out["liveDbTotalStorageEstimated"])


if __name__ == "__main__":
    unittest.main()
