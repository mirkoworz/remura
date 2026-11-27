"""Synthetic-only CVD coverage: zero-new-event != absent broker/orderflow.

No real market data, broker calls, cloud, secrets or production imports.
"""
from datetime import datetime, timedelta, timezone
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import shark_cvd_scan_coverage as coverage
from scripts import cvd_divergence as detector

UTC = timezone.utc
DAY = datetime(2026, 11, 2, tzinfo=UTC)
KEY = b"test-only-cvd-coverage-private-hmac-not-for-production"


def stamp(dt):
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


def make_doc(*, count=20, symbol="EURUSD", confirmed=False):
    bars = []
    for i in range(count):
        lo = (10.0 if i == 10 else 9.7 if i == 22 else 10.4) if confirmed else 10.4
        bars.append({
            "t": stamp(DAY + timedelta(minutes=15*i)),
            "o": 10.8, "h": 11.2, "l": lo, "c": 11.0, "v": 100,
        })
    return {
        "symbol": symbol, "provider": "ctrader",
        "providerSymbol": "PRIVATE_TEST_BROKER_DO_NOT_EXPORT",
        "timezone": "UTC", "sourceTimeframe": "M15",
        "lastComplete": bars[-1]["t"],
        "timeframes": {"M15": bars, "H1": [], "H4": []},
    }


def capture(db, doc=None, *, symbol="EURUSD", count=20, minutes=1):
    source = make_doc(count=count, symbol=symbol) if doc is None else doc
    closed = DAY + timedelta(minutes=15*count)
    return coverage.record(
        db, symbol=symbol, slot_closed_at=stamp(closed),
        source_document=source, clock=closed+timedelta(minutes=minutes),
        secret=KEY)


class CvdCoverageTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        coverage.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()

    def test_empty_schema_is_unknown_and_no_fake_denominator(self):
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=6)))
        self.assertEqual(out["status"], "LOCAL_ATTEMPT_COVERAGE_ONLY")
        self.assertIsNone(out["markets"]["EURUSD"])
        self.assertIsNone(out["markets"]["XAUUSD"])
        self.assertEqual(out["negativeTradingControlsAdmissible"], 0)
        other = sqlite3.connect(":memory:")
        try:
            missing = coverage.audit(other, as_of=stamp(DAY+timedelta(hours=6)))
            self.assertEqual(missing["status"], "NO_SCAN_ATTEMPT_LEDGER")
            self.assertIsNone(missing["markets"]["EURUSD"])
        finally:
            other.close()

    def test_valid_detector_no_new_divergence_is_only_local_observation(self):
        source = make_doc()
        old = copy.deepcopy(source)
        saved = capture(self.db, source)
        self.assertEqual(saved["status"], "EVALUATED")
        self.assertEqual(saved["newConfirmationsOnThisClosedSlot"], 0)
        self.assertFalse(saved["isAProvenNegativeTradingControl"])
        self.assertEqual(source, old)
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=5,minutes=5)))
        stats = out["markets"]["EURUSD"]
        self.assertEqual(stats["recordedAttempts"], 1)
        self.assertEqual(stats["localZeroNewConfirmationSlots"], 1)
        self.assertEqual(stats["newTechnicalConfirmations"], 0)
        self.assertFalse(stats["noNewConfirmationIsVerifiedInstitutionalNegative"])
        self.assertIsNone(out["markets"]["XAUUSD"])
        self.assertEqual(out["brokerCalls"], 0)
        self.assertEqual(out["negativeTradingControlsAdmissible"], 0)
        raw = "\n".join(self.db.iterdump())
        self.assertNotIn(source["providerSymbol"], raw)
        self.assertNotIn(KEY.decode(), raw)
        self.assertNotIn('"o":', raw)
        serialized = json.dumps(out)
        self.assertNotIn("PRIVATE_TEST_BROKER", serialized)
        self.assertNotIn(KEY.decode(), serialized)

    def test_real_original_detector_confirmation_counted_once_per_closed_slot(self):
        doc = make_doc(count=25, confirmed=True)
        first = capture(self.db, doc, count=25)
        self.assertEqual(first["status"], "EVALUATED")
        self.assertEqual(first["newConfirmationsOnThisClosedSlot"], 1)
        later = make_doc(count=26, confirmed=True)
        second = capture(self.db, later, count=26)
        self.assertEqual(second["status"], "EVALUATED")
        self.assertEqual(second["newConfirmationsOnThisClosedSlot"], 0)
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=6,minutes=35)))
        stats = out["markets"]["EURUSD"]
        self.assertEqual(stats["recordedAttempts"], 2)
        self.assertEqual(stats["newTechnicalConfirmations"], 1)
        self.assertEqual(stats["localSlotsWithNewConfirmations"], 1)
        self.assertEqual(stats["localZeroNewConfirmationSlots"], 1)
        self.assertFalse(out["outOfSampleEdgeEstablished"])

    def test_missing_slot_and_explicit_unavailable_attempt_are_not_negatives(self):
        capture(self.db, count=20)  # 05:00
        # 05:15 calendar slot is missing entirely, no backfill.
        missing = coverage.record(
            self.db, symbol="EURUSD", slot_closed_at=stamp(DAY+timedelta(hours=5,minutes=30)),
            source_document=None, secret=KEY,
            clock=DAY+timedelta(hours=5,minutes=31))
        self.assertEqual(missing["status"], "NOT_EVALUABLE")
        self.assertIsNone(missing["newConfirmationsOnThisClosedSlot"])
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=5,minutes=50)))
        stats = out["markets"]["EURUSD"]
        self.assertEqual(stats["calendarSlotsSinceFirstVisibleAttempt"], 4)
        self.assertEqual(stats["recordedAttempts"], 2)
        self.assertEqual(stats["calendarSlotsWithoutRecordedAttempt"], 2)
        self.assertEqual(stats["locallyNotEvaluableAttempts"], 1)
        self.assertEqual(stats["localZeroNewConfirmationSlots"], 1)
        self.assertEqual(out["negativeTradingControlsAdmissible"], 0)
        self.assertIsNone(out["markets"]["XAUUSD"])

    def test_invalid_or_partial_candle_source_not_treated_as_no_event(self):
        gap = make_doc()
        gap["timeframes"]["M15"].pop(8)
        result = capture(self.db, gap)
        self.assertEqual(result["status"], "NOT_EVALUABLE")
        self.assertIsNone(result["newConfirmationsOnThisClosedSlot"])
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=5,minutes=5)))
        self.assertEqual(out["markets"]["EURUSD"]["locallyNotEvaluableAttempts"], 1)
        self.assertEqual(out["markets"]["EURUSD"]["localZeroNewConfirmationSlots"], 0)

    def test_no_future_asof_leakage_or_imagined_prior_activation(self):
        capture(self.db, count=20)
        capture(self.db, count=21)
        prior = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=5,minutes=10)))
        self.assertEqual(prior["markets"]["EURUSD"]["recordedAttempts"], 1)
        self.assertEqual(prior["markets"]["EURUSD"]["calendarSlotsSinceFirstVisibleAttempt"], 1)
        too_early = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=4,minutes=50)))
        self.assertIsNone(too_early["markets"]["EURUSD"])

    def test_duplicate_and_backfill_blocked_and_trigger_protected(self):
        capture(self.db)
        with self.assertRaisesRegex(ValueError, "duplicate_or_backfilled"):
            capture(self.db)
        capture(self.db, count=22)
        with self.assertRaisesRegex(ValueError, "duplicate_or_backfilled"):
            capture(self.db, count=21)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                f"DELETE FROM {coverage.TABLE} WHERE symbol='EURUSD'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                f"UPDATE {coverage.TABLE} SET reason='DATA_MISSING'")
        self.db.rollback()
        self.db.execute("DROP TRIGGER research_cvd_scan_no_delete")
        with self.assertRaisesRegex(ValueError, "immutability_triggers_missing"):
            coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=6)))

    def test_clock_broker_and_schema_fail_closed(self):
        for wrong in (0, True, -1):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=6)), days=wrong)
        doc = make_doc()
        doc["providerSymbol"] = "BROKER_OVERRIDE"
        with self.assertRaisesRegex(ValueError, "not_a_current_closed_m15_attempt"):
            coverage.record(
                self.db, symbol="EURUSD",
                slot_closed_at=stamp(DAY+timedelta(hours=5)),
                source_document=doc, secret=KEY,
                clock=DAY+timedelta(hours=5,minutes=5))
        with self.assertRaisesRegex(ValueError, "source_identity_or_slot"):
            capture(self.db, make_doc(symbol="XAUUSD"))
        with self.assertRaisesRegex(ValueError, "stable_private_hmac"):
            coverage.record(
                self.db, symbol="EURUSD",
                slot_closed_at=stamp(DAY+timedelta(hours=5)),
                source_document=None, secret=b"short",
                clock=DAY+timedelta(hours=5,minutes=1))
        with patch.object(coverage, "MAX_ROWS", 1):
            capture(self.db)
            with self.assertRaisesRegex(ValueError, "capacity_reached"):
                capture(self.db, count=21)

    def test_readonly_audit_does_not_mutate_sqlite(self):
        capture(self.db)
        mutations = self.db.total_changes
        self.db.execute("PRAGMA query_only=ON")
        out = coverage.audit(self.db, as_of=stamp(DAY+timedelta(hours=5,minutes=5)))
        self.assertEqual(out["markets"]["EURUSD"]["recordedAttempts"], 1)
        self.assertEqual(self.db.total_changes, mutations)
        self.assertFalse(out["outOfSampleEdgeEstablished"])


if __name__ == "__main__":
    unittest.main()
