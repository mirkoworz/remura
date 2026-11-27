"""REMURA Track B: future scientific sample gate never invents an edge.

All data are fabricated OHLC on isolated temporary SQLite. This tests ONLY
admission policy and local archive proof, not a market model or trading result.
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

from scripts import shark_first_invocation as first
from scripts import shark_price_only_compact as compact
from scripts import shark_sample_admission as admission
from scripts import shark_scan_failures as failures
from test_shark_price_only_compact import prepared
from test_shark_staging_scan import fixture,NOW,stamp


class SampleAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="remura-admissibility-")
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"synthetic.sqlite"
        fixture(self.path,with_cot=True,all_priced=True,m15_count=1024)
        self.asof="2026-11-04T11:33:00Z"

    def read(self, *, when=None, days=1):
        with sqlite3.connect(
                "file:%s?mode=ro" % self.path,uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            return admission.audit(db,as_of=when or self.asof,days=days)

    def _start(self, *, when=None):
        return first.first_invocation(
            self.path,clock=when or NOW-timedelta(minutes=1))

    def _seal(self, *, unknown=False, no_volume=False, targeted=False):
        with sqlite3.connect(self.path) as db:
            compact.ensure_schema(db)
            rows=prepared(db)
            if unknown:
                missing=rows[-1]
                rows[-1]=compact.missing_row(
                    symbol=missing[0],scan_at=stamp(NOW),
                    clock=NOW+timedelta(seconds=2))
            if no_volume:
                row=list(rows[-2])
                self.assertEqual(row[4],"PRICE_CONTEXT_READY")
                row[14]=0
                rows[-2]=tuple(row)
            with db:
                db.execute("BEGIN")
                return compact.seal(
                    db,rows[:2] if targeted else rows,full=not targeted,
                    clock=NOW+timedelta(seconds=6))

    def test_no_archive_is_not_an_imaginary_zero_sample(self):
        out=self.read()
        self.assertEqual(out["status"],"NO_FINALIZED_ADMISSIBLE_POPULATION")
        self.assertIsNone(out["fullBatchMarketCells"])
        self.assertIsNone(out["priceContextDescriptiveCandidates"])
        self.assertIsNone(out["recordingOpportunities"])
        self.assertEqual(out["institutionalCohortsAdmissible"],0)
        self.assertFalse(out["tradingEdgeEstablished"])

    def test_full_archive_without_start_witness_is_not_admitted(self):
        self._seal()
        out=self.read()
        self.assertEqual(out["status"],"START_WITNESS_UNAVAILABLE")
        self.assertEqual(out["fullBatchMarketCells"],34)
        self.assertIsNone(out["priceContextDescriptiveCandidates"])
        self.assertEqual(out["exclusionReasons"],
                         {"START_WITNESS_UNAVAILABLE":34})
        self.assertEqual(out["netWalkForwardOutcomesAdmissible"],0)

    def test_all_34_valid_local_price_contexts_are_only_descriptive(self):
        self._start()
        self._seal()
        out=self.read()
        self.assertEqual(
            out["status"],
            "PRICE_ONLY_DESCRIPTIVE_AUDITED_INSTITUTIONAL_GATE_CLOSED")
        self.assertEqual(out["recordingOpportunities"],1)
        self.assertEqual(out["verifiedFullScanSlots"],1)
        self.assertEqual(out["fullBatchMarketCells"],34)
        self.assertEqual(out["priceContextDescriptiveCandidates"],34)
        self.assertEqual(out["priceContextWithCompleteTickVolume"],34)
        self.assertEqual(out["excludedMarketCells"],0)
        self.assertEqual(out["exclusionReasons"],{})
        self.assertEqual(out["institutionalCohortsAdmissible"],0)
        self.assertEqual(out["netWalkForwardOutcomesAdmissible"],0)
        self.assertEqual(out["cvdDivergenceEventsAdmissible"],0)
        self.assertFalse(out["sameSourceValueVersionsForCOTWitnessedInTheseRows"])
        self.assertFalse(out["cvdDivergenceDetectionTimeWitnessed"])
        self.assertFalse(out["spreadSlippageExecutionCostsObserved"])
        self.assertFalse(out["independentOutOfSampleValidated"])
        self.assertFalse(out["tradingEdgeEstablished"])
        self.assertEqual(out["brokerCalls"],0)
        self.assertFalse(out["notificationsEnabled"])
        self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",json.dumps(out))

    def test_unknown_market_and_missing_volume_are_not_same_exclusion(self):
        self._start()
        self._seal(unknown=True,no_volume=True)
        out=self.read()
        self.assertEqual(out["fullBatchMarketCells"],34)
        self.assertEqual(out["priceContextDescriptiveCandidates"],33)
        self.assertEqual(out["priceContextWithCompleteTickVolume"],32)
        self.assertEqual(out["priceContextWithoutCompleteTickVolume"],1)
        self.assertEqual(out["excludedMarketCells"],1)
        self.assertEqual(out["exclusionReasons"],{
            "MARKET_OBSERVATION_UNKNOWN":1})
        self.assertEqual(out["institutionalCohortsAdmissible"],0)

    def test_targeted_archive_does_not_count_toward_full_denominator(self):
        self._start()
        self._seal(targeted=True)
        out=self.read()
        self.assertEqual(out["verifiedFullScanSlots"],0)
        self.assertEqual(out["unrecordedCalendarSlots"],1)
        self.assertEqual(out["fullBatchMarketCells"],0)
        self.assertEqual(out["priceContextDescriptiveCandidates"],0)
        self.assertEqual(out["netWalkForwardOutcomesAdmissible"],0)

    def test_startup_partial_slot_excluded_and_absence_not_an_error(self):
        self._start(when=NOW)
        self._seal()
        out=self.read(when="2026-11-04T12:05:00Z")
        self.assertEqual(out["recordingOpportunities"],2)
        self.assertEqual(out["verifiedFullScanSlots"],0)
        self.assertEqual(out["fullBatchMarketCells"],0)
        self.assertEqual(out["unrecordedCalendarSlots"],2)
        self.assertEqual(out["priceContextDescriptiveCandidates"],0)
        self.assertFalse(out["calendarGapsEquatedToObservedErrors"])

    def test_logged_failure_is_separate_from_missing_calendar_slot(self):
        self._start()
        failures.record(
            self.path,stage="COMPACT_SCAN",
            exc=sqlite3.OperationalError(
                "research_source_changed_before_atomic_commit"),
            started_at=NOW,logged_at=NOW+timedelta(seconds=1))
        out=self.read()
        self.assertEqual(out["observedFailures"]["observedReasons"],
                         {"SOURCE_CHANGED":1})
        self.assertEqual(out["unrecordedCalendarSlots"],1)
        self.assertIsNone(out["priceContextDescriptiveCandidates"])
        self.assertFalse(out["observedFailures"][
            "calendarMissingSlotsAttributedToErrors"])
        self.assertFalse(out["calendarGapsEquatedToObservedErrors"])

    def test_corrupted_archive_fails_closed_no_quiet_exclusion(self):
        self._start()
        self._seal()
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER research_compact_no_update")
            db.execute(
                f"UPDATE {compact.TABLE} SET payload_sha256=?",
                ("0"*64,))
            compact.ensure_schema(db)  # re-add immutable trigger for audit
        with self.assertRaises(ValueError):
            self.read()

    def test_future_sealing_is_not_backdated_to_earlier_asof(self):
        self._start()
        self._seal()
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER research_compact_no_update")
            db.execute(
                f"UPDATE {compact.TABLE} SET sealed_at=?",
                ("2026-11-04T12:00:00.000000Z",))
            compact.ensure_schema(db)
        with self.assertRaisesRegex(ValueError,
                                    "batch_time_invalid_for_historical_asof"):
            self.read()

    def test_no_mutation_and_utc_bounded_window(self):
        self._start()
        self._seal()
        with sqlite3.connect(self.path) as db:
            tables_before=db.execute(
                "SELECT count(*) FROM sqlite_master").fetchone()[0]
        out=self.read()
        self.assertTrue(out["fullBatchSHAAndMarketScopeVerified"])
        with sqlite3.connect(self.path) as db:
            tables_after=db.execute(
                "SELECT count(*) FROM sqlite_master").fetchone()[0]
            self.assertEqual(tables_before,tables_after)
        for invalid in (0,8,True,1.5,"7"):
            with self.subTest(days=invalid):
                with self.assertRaisesRegex(ValueError,
                                            "invalid_admission_window"):
                    self.read(days=invalid)
        with self.assertRaises(ValueError):
            self.read(when="2026-11-04T11:33:00") # no timezone

if __name__=="__main__":
    unittest.main()
