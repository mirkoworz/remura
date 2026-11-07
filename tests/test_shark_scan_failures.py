"""REMURA Track B: actual-only failure provenance, no invented gap cause.

All state is synthetic SQLite in a TemporaryDirectory. No server, broker,
cloud, credentials, real source data, trade orders, or LIVE writes.
"""
from __future__ import annotations

from datetime import timedelta
import json
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
from scripts import shark_scan_failures as failures
from scripts import shark_prospective_coverage as coverage
from scripts import shark_price_only_compact as compact
from test_shark_staging_scan import fixture,NOW,stamp

OPT_IN={
    "REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1",
    "REMURA_SHARK_COMPACT_RESEARCH_ACK":"ACK_UNVALIDATED_PROSPECTIVE_RESEARCH",
}


class ObservedFailureLedgerTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix="remura-failure-ledger-")
        self.addCleanup(self.scratch.cleanup)
        self.path=Path(self.scratch.name)/"price-synthetic.sqlite"
        fixture(self.path,with_cot=False,all_priced=False,m15_count=512)

    def _read(self, at):
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA query_only=ON")
            return failures.summary(db,as_of=stamp(at))

    def test_ledger_absent_is_unknown_not_zero(self):
        result=self._read(NOW+timedelta(hours=1))
        self.assertEqual(result["status"],"NO_FAILURE_LEDGER")
        self.assertIsNone(result["observedFailureCount"])
        self.assertIsNone(result["observedReasons"])
        self.assertFalse(result["fullFailureTelemetryCertified"])
        self.assertFalse(result["calendarMissingSlotsAttributedToErrors"])

    def test_reason_allowlist_never_promotes_unknown_to_source_collision(self):
        tests=(
            (sqlite3.OperationalError(
                "research_source_changed_before_atomic_commit"),"COMPACT_SCAN",
             "SOURCE_CHANGED"),
            (sqlite3.OperationalError("database is locked"),"COMPACT_SCAN",
             "SQLITE_BUSY"),
            (sqlite3.OperationalError("database table is locked"),"ACTIVATION",
             "SQLITE_BUSY"),
            (sqlite3.OperationalError("database is locked: PRIVATE_TOKEN"),
             "COMPACT_SCAN","SQLITE_OTHER"),
            (sqlite3.OperationalError("disk I/O error"),"COMPACT_SCAN",
             "SQLITE_OTHER"),
            (ValueError("PRIVATE_SECRET_123"),"ACTIVATION",
             "WITNESS_INVALID"),
            (KeyError("ACCOUNT_ID"),"COMPACT_SCAN","SCAN_INVALID"),
            (RuntimeError("PRIVATE_BROKER_OHLC"),"COMPACT_SCAN","OTHER_ERROR"),
        )
        for exc,stage,expected in tests:
            with self.subTest(stage=stage,kind=expected):
                self.assertEqual(failures.reason(exc,stage=stage),expected)
        with self.assertRaises(ValueError):
            failures.reason(ValueError("secret"),stage="UNKNOWN")

    def test_actual_failed_scans_stay_append_only_and_disclose_no_secrets(self):
        started=NOW+timedelta(minutes=1)
        for idx,(exc,stage) in enumerate((
            (sqlite3.OperationalError(
                "research_source_changed_before_atomic_commit"),"COMPACT_SCAN"),
            (sqlite3.OperationalError("database is locked"),"ACTIVATION"),
            (RuntimeError("PRIVATE_BROKER_OHLC"),"COMPACT_SCAN"),
        )):
            result=failures.record(
                self.path,stage=stage,exc=exc,
                started_at=started+timedelta(seconds=idx),
                logged_at=started+timedelta(seconds=idx+1))
            self.assertEqual(result["status"],"OBSERVED_FAILURE_RECORDED")
            self.assertEqual(result["eventId"],idx+1)
        audited=self._read(NOW+timedelta(hours=1))
        self.assertEqual(audited["observedFailureCount"],3)
        self.assertEqual(audited["observedReasons"],{
            "OTHER_ERROR":1,"SOURCE_CHANGED":1,"SQLITE_BUSY":1,
        })
        with sqlite3.connect(self.path) as db:
            records=db.execute(
                f"SELECT started_at,logged_at,stage,reason_code "
                f"FROM {failures.TABLE}").fetchall()
            content=json.dumps(records)+json.dumps(audited)
            self.assertNotIn("PRIVATE",content)
            self.assertNotIn("ACCOUNT_ID",content)
            self.assertNotIn("BROKER_OHLC",content)
            for sql in (f"UPDATE {failures.TABLE} SET reason_code='OTHER_ERROR'",
                        f"DELETE FROM {failures.TABLE}"):
                with self.assertRaisesRegex(sqlite3.IntegrityError,
                                            "immutable_research_failure"):
                    db.execute(sql)

    def test_busy_ledger_cannot_erase_original_failure_or_claim_count(self):
        # Even a tiny separate log commit can fail while another writer owns
        # SQLite. Never replace a true scanner exception with a telemetry one.
        with sqlite3.connect(self.path,isolation_level=None) as writer:
            writer.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                failures.record(
                    self.path,stage="COMPACT_SCAN",
                    exc=sqlite3.OperationalError("database is locked"),
                    started_at=NOW,logged_at=NOW)
            writer.rollback()
        self.assertIsNone(self._read(NOW+timedelta(hours=1))[
            "observedFailureCount"])

    def test_server_source_race_is_logged_but_original_exception_survives(self):
        error=sqlite3.OperationalError(
            "research_source_changed_before_atomic_commit")
        with patch.object(server,"utcnow",
                          side_effect=[NOW+timedelta(seconds=2),
                                       NOW+timedelta(seconds=3)]):
            with patch.object(first.witness,"_clock",
                              return_value=NOW+timedelta(seconds=2)):
                with patch.object(
                        scanner,"scan_once_with_compact_price_only_research",
                        side_effect=error):
                    with self.assertRaisesRegex(sqlite3.OperationalError,
                                                "source_changed"):
                        server.observe_periodic_squalincome(self.path,env=OPT_IN)
        result=self._read(NOW+timedelta(hours=1))
        self.assertEqual(result["observedFailureCount"],1)
        self.assertEqual(result["observedReasons"],{"SOURCE_CHANGED":1})
        with sqlite3.connect(self.path) as db:
            self.assertIsNotNone(first.read(db))
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name=?",
                (compact.TABLE,)).fetchone())
            audit=coverage.audit(db,as_of=stamp(NOW+timedelta(hours=1)))
            self.assertEqual(audit["observedScanFailures"]["observedReasons"],
                             {"SOURCE_CHANGED":1})
            self.assertFalse(audit["observedScanFailures"][
                "calendarMissingSlotsAttributedToErrors"])
            self.assertGreater(audit["unrecordedCalendarSlots"],0)

    def test_server_ledger_failure_preserves_initial_sqlite_error(self):
        cause=sqlite3.OperationalError(
            "research_source_changed_before_atomic_commit")
        with patch.object(first,"first_invocation",
                          return_value={"status":"EXISTING_FIRST_INVOCATION"}):
            with patch.object(
                    scanner,"scan_once_with_compact_price_only_research",
                    side_effect=cause):
                with patch.object(
                        failures,"record",
                        side_effect=sqlite3.OperationalError("database is locked")):
                    with self.assertRaisesRegex(sqlite3.OperationalError,
                                                "research_source_changed"):
                        server.observe_periodic_squalincome(self.path,env=OPT_IN)
        # Only an observed local log attempt failed; do NOT claim to have
        # recorded a failure or infer its cause from a missing batch.
        self.assertIsNone(self._read(NOW+timedelta(hours=1))[
            "observedFailureCount"])

    def test_legacy_route_does_not_create_failure_ledger(self):
        with patch.object(server,"observe_squalincome",
                          side_effect=RuntimeError("legacy_failure")):
            with self.assertRaisesRegex(RuntimeError,"legacy_failure"):
                server.observe_periodic_squalincome(self.path,env={})
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute(
                "SELECT name FROM sqlite_master WHERE name=?",
                (failures.TABLE,)).fetchone())

    def test_invalid_window_and_tampered_trigger_fail_closed(self):
        failures.record(
            self.path,stage="COMPACT_SCAN",
            exc=RuntimeError("generic"),started_at=NOW,logged_at=NOW)
        with sqlite3.connect(self.path) as db:
            for days in (0,8,True,1.5):
                with self.subTest(days=days):
                    with self.assertRaisesRegex(ValueError,
                                                "invalid_failure_window"):
                        failures.summary(db,as_of=stamp(NOW),days=days)
            db.execute(f"DROP TRIGGER {failures.TRIGGERS[0]}")
        with self.assertRaisesRegex(ValueError,"triggers_missing"):
            self._read(NOW+timedelta(hours=1))

if __name__=="__main__":
    unittest.main()
