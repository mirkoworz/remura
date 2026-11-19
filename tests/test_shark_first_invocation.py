"""First actual opt-in periodic entry witness: synthetic-only tests.

No production database, cloud account, broker API, scheduler or LIVE changes.
The witness is deliberately NOT an assertion about feature-flag switch time.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

import private_server as server
import signals_monitor as scanner
from scripts import shark_first_invocation as first
from scripts import shark_prospective_coverage as audit
from scripts import shark_price_only_compact as compact
from test_shark_staging_scan import fixture,NOW,stamp
from test_shark_price_only_compact import prepared

ON={
 "REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1",
 "REMURA_SHARK_COMPACT_RESEARCH_ACK":"ACK_UNVALIDATED_PROSPECTIVE_RESEARCH",
}


class FirstInvocationTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix="remura-first-invocation-")
        self.addCleanup(self.scratch.cleanup)
        self.db=Path(self.scratch.name)/"research.sqlite"
        fixture(self.db,with_cot=False,all_priced=True,m15_count=1024)

    def _audit(self,at):
        db=sqlite3.connect(self.db)
        try:
            db.execute("PRAGMA query_only=ON")
            return audit.audit(db,as_of=at)
        finally:
            db.close()

    def test_first_attempt_is_committed_before_scan_and_immutable(self):
        entered=NOW+timedelta(seconds=2)
        init=first.first_invocation(self.db,clock=entered)
        self.assertEqual(init["status"],"FIRST_INVOCATION_WITNESSED")
        self.assertEqual(init["observedAt"],stamp(entered).replace(
            "Z",".000000Z"))
        later=first.first_invocation(self.db,clock=entered+timedelta(days=1))
        self.assertEqual(later["status"],"EXISTING_FIRST_INVOCATION")
        self.assertEqual(later["observedAt"],init["observedAt"])
        with sqlite3.connect(self.db) as db:
            self.assertEqual(first.read(db,at=entered),init["observedAt"])
            with self.assertRaisesRegex(sqlite3.IntegrityError,"immutable"):
                db.execute(f"DELETE FROM {first.TABLE}")
            with self.assertRaisesRegex(sqlite3.IntegrityError,"immutable"):
                db.execute(f"UPDATE {first.TABLE} SET observed_at='2020'")
            self.assertEqual(db.execute(
                f"SELECT count(*) FROM {first.TABLE}").fetchone()[0],1)

    def test_db_path_must_exist_and_fail_closed(self):
        path=Path(self.scratch.name)/"never-existing.sqlite"
        with self.assertRaises(sqlite3.OperationalError):
            first.first_invocation(path,clock=NOW)
        self.assertFalse(path.exists())

    def test_existing_research_before_first_witness_is_rejected(self):
        with sqlite3.connect(self.db) as db:
            compact.ensure_schema(db)
            rows=prepared(db)
            with db:
                db.execute("BEGIN")
                compact.seal(db,rows,full=True,clock=NOW+timedelta(seconds=6))
        with self.assertRaisesRegex(ValueError,"research_batches_precede"):
            first.first_invocation(self.db,clock=NOW+timedelta(minutes=1))
        with sqlite3.connect(self.db) as db:
            self.assertIsNone(first.read(db))

    def test_future_time_and_missing_triggers_are_rejected(self):
        first.first_invocation(self.db,clock=NOW)
        with sqlite3.connect(self.db) as db:
            with self.assertRaisesRegex(ValueError,"in_future"):
                first.read(db,at=NOW-timedelta(hours=1))
            db.execute(f"DROP TRIGGER {first.TRIGGER_UPDATE}")
        with self.assertRaisesRegex(ValueError,"triggers_missing"):
            first.first_invocation(self.db,clock=NOW+timedelta(minutes=1))

    def test_activation_only_without_any_batch_exposes_post_start_gap(self):
        first.first_invocation(self.db,clock=NOW)
        # Just after the FIRST recorded invocation, no whole 15m slot after
        # activation has had 15m + grace to mature: denominator remains N/D.
        in_flight=self._audit("2026-11-04T11:33:00Z")
        self.assertEqual(in_flight["status"],
                         "NO_FINALIZED_EXPECTED_SLOTS_AFTER_START")
        self.assertIsNone(in_flight["recordingOpportunities"])
        later=self._audit("2026-11-04T11:49:00Z")
        self.assertEqual(later["status"],"WITNESSED_CALENDAR_COVERAGE_AUDITED")
        self.assertTrue(later["firstEnabledScannerInvocationWitnessed"])
        self.assertFalse(later["configurationSwitchTimeKnown"])
        self.assertEqual(later["recordingOpportunities"],1)
        self.assertEqual(later["verifiedFullScanSlots"],0)
        self.assertEqual(later["unrecordedCalendarSlots"],1)
        self.assertEqual(later["firstMissingSlotExamples"],
                         ["2026-11-04T11:30:00.000000Z"])
        self.assertFalse(later["continuousEnablementEstablished"])

    def test_batch_in_startup_slot_is_not_retrospective_denominator(self):
        first.first_invocation(self.db,clock=NOW)
        with sqlite3.connect(self.db) as db:
            compact.ensure_schema(db)
            rows=prepared(db)
            with db:
                db.execute("BEGIN")
                compact.seal(db,rows,full=True,clock=NOW+timedelta(seconds=6))
        result=self._audit("2026-11-04T12:05:00Z")
        self.assertEqual(result["firstKnownFullBatchSlot"],
                         "2026-11-04T11:15:00.000000Z")
        self.assertEqual(result["examinedFromSlot"],
                         "2026-11-04T11:30:00.000000Z")
        self.assertEqual(result["recordingOpportunities"],2)
        self.assertEqual(result["verifiedFullScanSlots"],0)
        self.assertEqual(result["unrecordedCalendarSlots"],2)
        self.assertFalse(result["statisticalCompletenessCertified"])

    def test_real_feature_gate_aborts_when_scanner_raises_after_first_commit(self):
        with patch.object(first.witness,"_clock",return_value=NOW):
            with patch.object(scanner,
                              "scan_once_with_compact_price_only_research",
                              side_effect=RuntimeError("synthetic_fail")):
                with self.assertRaisesRegex(RuntimeError,"synthetic_fail"):
                    server.observe_periodic_squalincome(self.db,env=ON)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(first.read(db,at=NOW),stamp(NOW).replace(
                "Z",".000000Z"))
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name=?",
                (compact.TABLE,)).fetchone())
        # A failed scan still has an observable FIRST attempt, but NO
        # valid batch; no trading history was created retrospectively.

if __name__=="__main__":
    unittest.main()
