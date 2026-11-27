"""Synthetic-only OFFLINE tests: no Oracle, real broker, money or returns."""
from __future__ import annotations

from datetime import timedelta
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_cvd_same_source_adapter as adapter
from scripts import shark_cvd_scan_coverage as scan
from scripts import shark_cvd_source_lineage as lineage
from test_shark_cvd_same_source_preflight import (
    AT, SLOT, SECRET, inputs, stamp, update_row,
)

KEY = b"synthetic-private-hmac-key-only-for-tests-2026"


class InterruptedCommit(sqlite3.Connection):
    fail_next = False

    def commit(self):
        if self.fail_next:
            self.fail_next = False
            raise SystemExit("power_loss_before_commit")
        return super().commit()


class SameSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        scan.ensure_schema(self.db)
        self.clock = patch.object(adapter, "_utc_now", return_value=AT)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.db.close()

    def run_adapter(self, rows=None, docs=None, db=None):
        if rows is None:
            rows, docs = inputs()
        return adapter.capture(self.db if db is None else db, rows, docs,
                               secret=KEY, enabled=True)

    def records(self, db=None):
        return (self.db if db is None else db).execute(
            "SELECT symbol,closed_at,state,new_confirmations,source_hmac "
            "FROM " + scan.TABLE + " ORDER BY symbol").fetchall()

    def test_disabled_by_default_without_any_database_access(self):
        result = adapter.capture(None, None, None, secret=None)
        self.assertEqual(result["status"], "DISABLED_BY_DEFAULT")
        self.assertEqual(result["scanAttemptsRecorded"], 0)
        self.assertFalse(result["liveEnabled"])
        self.assertEqual(self.records(), [])

    def test_original_document_same_sha_hmac_and_full_denominator(self):
        rows,docs=inputs()
        unchanged=copy.deepcopy(docs)
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("broker_request_forbidden")):
            out=self.run_adapter(rows,docs)
        self.assertEqual(unchanged,docs)
        self.assertEqual(out["priceDenominatorInput"],34)
        self.assertEqual(out["cvdPilotMarkets"],2)
        self.assertEqual(out["cvdMarketsUncovered"],32)
        self.assertEqual(out["scanAttemptsRecorded"],2)
        self.assertTrue(out["missingOrZeroNewIsNotNegativeControl"])
        self.assertFalse(out["tradingEdgeEstablished"])
        seen=self.records()
        self.assertEqual([r[0] for r in seen],["EURUSD","XAUUSD"])
        for symbol,closed,state,count,mac in seen:
            self.assertEqual(closed,scan.witness._iso(SLOT))
            self.assertIn(state,("EVALUATED","NOT_EVALUABLE"))
            self.assertTrue(count is None or count >= 0)
            self.assertEqual(mac,lineage._mac(
                KEY,lineage._document_sha(docs[symbol])))
        stored="\n".join(self.db.iterdump())
        self.assertNotIn(SECRET,stored)
        self.assertNotIn(KEY.decode(),stored)
        self.assertNotIn('"o":',stored)
        public=json.dumps(out)
        self.assertNotIn(SECRET,public)
        self.assertNotIn("EURUSD",public)

    def test_missing_original_observed_as_unknown_not_zero(self):
        rows,docs=inputs(pilot=("EURUSD",))
        out=self.run_adapter(rows,docs)
        self.assertEqual(out["scanAttemptsRecorded"],2)
        missing=next(r for r in self.records() if r[0]=="XAUUSD")
        self.assertEqual(missing[2],"NOT_EVALUABLE")
        self.assertIsNone(missing[3])
        self.assertIsNone(missing[4])
        self.assertGreaterEqual(out["unknownAttempts"],1)

    def test_sha_changed_and_cross_market_document_are_rejected(self):
        rows,docs=inputs()
        docs["EURUSD"]["providerSymbol"]="REPLACEMENT_AFTER_SCAN"
        with self.assertRaisesRegex(ValueError,"source_digest"):
            self.run_adapter(rows,docs)
        self.assertEqual(self.records(),[])
        rows,docs=inputs()
        docs["XAUUSD"]["symbol"]="EURUSD"
        with self.assertRaises(ValueError):
            self.run_adapter(rows,docs)
        self.assertEqual(self.records(),[])

    def test_missing_volume_or_late_source_is_not_negative(self):
        rows,docs=inputs()
        with self.assertRaisesRegex(ValueError,"incomplete_tick_volume"):
            self.run_adapter(update_row(rows,"EURUSD",14,0),docs)
        self.assertEqual(self.records(),[])
        with patch.object(adapter,"_utc_now",return_value=AT+timedelta(minutes=3)):
            with self.assertRaises(ValueError):
                self.run_adapter(rows,docs)
        self.assertEqual(self.records(),[])

    def test_duplicate_is_not_overwritten(self):
        self.run_adapter()
        original=self.records()
        with self.assertRaisesRegex(ValueError,"duplicate_or_retroactive"):
            self.run_adapter()
        self.assertEqual(self.records(),original)

    def test_a_later_slot_already_present_forbids_backdating(self):
        later=SLOT+timedelta(minutes=15)
        self.db.execute(
            "INSERT INTO "+scan.TABLE+
            " (symbol,closed_at,attempted_at,state,source_hmac,"
            "session_prefix_hmac,new_confirmations,reason,schema_version)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("EURUSD",stamp(later),stamp(later+timedelta(minutes=1)),
             "NOT_EVALUABLE",None,None,None,"SOURCE_ABSENT",scan.SCHEMA))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"duplicate_or_retroactive"):
            self.run_adapter()
        self.assertEqual(len(self.records()),1)

    def test_second_insert_sqlite_failure_rolls_back_both(self):
        self.db.execute(
            "CREATE TRIGGER fake_disk_full BEFORE INSERT ON "+scan.TABLE+
            " WHEN NEW.symbol='XAUUSD' "
            "BEGIN SELECT RAISE(ABORT,'synthetic_disk_full'); END")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                     "synthetic_disk_full"):
            self.run_adapter()
        self.assertEqual(self.records(),[])

    def test_interrupted_commit_rolls_back_both(self):
        self.db.close()
        self.db=sqlite3.connect(":memory:",factory=InterruptedCommit)
        scan.ensure_schema(self.db)
        self.db.fail_next=True
        with self.assertRaises(SystemExit):
            self.run_adapter()
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.records(),[])

    def test_database_lock_cannot_leave_partial_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"only_research.sqlite3")
            one=sqlite3.connect(path,timeout=2)
            two=sqlite3.connect(path,timeout=2)
            try:
                scan.ensure_schema(one)
                two.execute("BEGIN IMMEDIATE")
                with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                    self.run_adapter(db=one)
                two.rollback()
                self.assertEqual(self.records(db=one),[])
            finally:
                two.close()
                one.close()

    def test_bounded_input_and_clock_drift(self):
        rows,docs=inputs()
        docs["EURUSD"]["timeframes"]["M15"] *= 28
        with self.assertRaises(ValueError):
            self.run_adapter(rows,docs)
        self.assertEqual(self.records(),[])
        rows,docs=inputs()
        with patch.object(adapter,"_utc_now",side_effect=[
                AT, AT+timedelta(seconds=31)]):
            with self.assertRaisesRegex(ValueError,"processing_delay"):
                self.run_adapter(rows,docs)
        self.assertEqual(self.records(),[])

    def test_never_connected_to_live_paths(self):
        root=Path(__file__).resolve().parents[1]
        for file in ("scripts/private_server.py","scripts/signals_monitor.py"):
            self.assertNotIn("shark_cvd_same_source_adapter",
                             (root/file).read_text())
        self.assertEqual(tuple(scan.PILOT),adapter.PILOT)


if __name__=="__main__":
    unittest.main()
