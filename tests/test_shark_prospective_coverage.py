"""No fabricated retrospective denominator in REMURA prospective research.

All tests use SQLite in TemporaryDirectory; no broker/OCI/network/live access.
"""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from scripts import shark_price_only_compact as compact
from scripts import shark_prospective_coverage as coverage
from test_shark_price_only_compact import prepared
from test_shark_staging_scan import fixture, NOW, stamp


class ProspectiveCoverageTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix="remura-coverage-")
        self.addCleanup(self.scratch.cleanup)
        self.path=Path(self.scratch.name)/"synthetic.sqlite"
        fixture(self.path,with_cot=False,all_priced=True,m15_count=512)

    def _read(self, **kw):
        with sqlite3.connect(
                "file:%s?mode=ro" % self.path,uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            return coverage.audit(db,**kw)

    def _seal(self,unknown=False,targeted=False):
        with sqlite3.connect(self.path) as db:
            compact.ensure_schema(db)
            rows=prepared(db)
            if unknown:
                row=rows.pop()
                rows.append(compact.missing_row(
                    symbol=row[0],scan_at=stamp(NOW),
                    clock=NOW+timedelta(seconds=2)))
            with db:
                db.execute("BEGIN")
                report=compact.seal(
                    db,rows[:2] if targeted else rows,
                    full=not targeted,
                    clock=NOW+timedelta(seconds=6))
            return report

    def test_absent_table_is_not_zero_coverage(self):
        result=self._read(as_of=stamp(NOW+timedelta(hours=1)))
        self.assertEqual(result["status"],"NO_RESEARCH_TABLE")
        self.assertIsNone(result["recordingOpportunities"])
        self.assertIsNone(result["unrecordedCalendarSlots"])
        self.assertFalse(result["preFirstBatchCoverageKnown"])
        self.assertEqual(result["brokerCalls"],0)
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name=?",
                (compact.TABLE,)).fetchone())

    def test_targeted_only_is_not_full_population(self):
        self._seal(targeted=True)
        report=self._read(as_of=stamp(NOW+timedelta(hours=1)))
        self.assertEqual(report["status"],"NO_FINALIZED_FULL_BATCH")
        self.assertIsNone(report["recordingOpportunities"])
        self.assertFalse(report["statisticalCompletenessCertified"] if
                         "statisticalCompletenessCertified" in report else False)

    def test_unfinished_slot_is_not_reported_missing(self):
        self._seal()
        # Original scan is at 11:16 UTC, slot started 11:15.
        # At 11:30 the slot just closed, but seal grace not exhausted.
        earlier=self._read(as_of="2026-11-04T11:30:00Z")
        self.assertEqual(earlier["status"],"NO_FINALIZED_FULL_BATCH")
        after=self._read(as_of="2026-11-04T11:33:00Z")
        self.assertEqual(after["recordingOpportunities"],1)
        self.assertEqual(after["verifiedFullScanSlots"],1)
        self.assertEqual(after["unrecordedCalendarSlots"],0)

    def test_only_post_first_recorded_calendar_gaps_are_marked(self):
        self._seal()
        report=self._read(as_of="2026-11-04T12:05:00Z")
        self.assertEqual(report["firstKnownFullBatchSlot"],
                         "2026-11-04T11:15:00Z")
        self.assertEqual(report["recordingOpportunities"],3)
        self.assertEqual(report["verifiedFullScanSlots"],1)
        self.assertEqual(report["unrecordedCalendarSlots"],2)
        self.assertEqual(report["firstMissingSlotExamples"],[
            "2026-11-04T11:30:00Z","2026-11-04T11:45:00Z"])
        self.assertEqual(report["verifiedMarketCells"],34)
        self.assertEqual(report["unknownMarketCellsInsideRecordedBatches"],0)
        self.assertFalse(report["activationTimeCertified"])
        self.assertFalse(report["statisticalCompletenessCertified"])
        self.assertFalse(report["calendarCadenceIsMarketOpportunityCoverage"])
        self.assertFalse(report["realIngestInterferenceProven"])
        self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",json.dumps(report))

    def test_unknown_market_cell_is_not_a_missing_full_scan(self):
        sealed=self._seal(unknown=True)
        self.assertEqual(sealed["unverifiableMarketObservations"],1)
        report=self._read(as_of="2026-11-04T11:33:00Z")
        self.assertEqual(report["verifiedFullScanSlots"],1)
        self.assertEqual(report["unrecordedCalendarSlots"],0)
        self.assertEqual(report["unknownMarketCellsInsideRecordedBatches"],1)
        self.assertEqual(report["priceContextReadyCells"],33)

    def test_missing_examples_are_bounded_and_window_truncated(self):
        self._seal()
        after=self._read(as_of="2026-11-14T12:05:00Z",days=1)
        self.assertTrue(after["auditWindowTruncated"])
        self.assertEqual(after["recordingOpportunities"],96)
        self.assertEqual(after["verifiedFullScanSlots"],0)
        self.assertEqual(after["unrecordedCalendarSlots"],96)
        self.assertEqual(len(after["firstMissingSlotExamples"]),12)
        self.assertEqual(after["omittedMissingSlotExamples"],84)
        self.assertFalse(after["preFirstBatchCoverageKnown"])

    def test_capacity_invalid_and_utc_clock_requirements(self):
        for days in (0,8,True,1.5,"7"):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError,"invalid_coverage_days"):
                    self._read(as_of="2026-11-04T12:05:00Z",days=days)
        with self.assertRaises(ValueError):
            self._read(as_of="bad-date")
        with self.assertRaises(ValueError):
            self._read(as_of="2026-11-04T12:05:00")

    def test_corrupt_immutable_batch_is_not_counted(self):
        self._seal()
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER research_compact_no_update")
            db.execute(
                "UPDATE research_price_only_batches SET payload_sha256=?",
                ("0"*64,))
        with self.assertRaises(ValueError):
            self._read(as_of="2026-11-04T12:05:00Z")

    def test_audit_does_not_write_to_sqlite_or_create_tables(self):
        self._seal()
        with sqlite3.connect(self.path) as db:
            before=db.execute("PRAGMA data_version").fetchone()[0]
            count=db.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
        _=self._read(as_of="2026-11-04T12:05:00Z")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute("PRAGMA data_version").fetchone()[0],before)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master").fetchone()[0],count)


if __name__=="__main__":
    unittest.main()
