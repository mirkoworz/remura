"""Track B OFFLINE: exact original scanner hook, no LIVE change.

Uses native signals_monitor._scan_once and authentic research modules over
disposable SQLite populated with SYNTHETIC bars/COT/retail receipts only.
No Oracle, real provider data, trades, notifications or network.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

# The real observer is deployed as a top-level module under scripts/.
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import signals_monitor as scanner
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_actual_scan_handoff as hook
from scripts import shark_signal_ingest_decision_link as linked
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ, RECORDED
from test_shark_signal_ingest_decision_link import setup_case, OBS, NOW


class ActualScannerRetailTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"observer.sqlite"
        db,_,self.original_price=setup_case()
        try:
            # The old evidence fixture uses a minimal Squalincome schema;
            # add only columns required by the ORIGINAL production scanner.
            db.execute("ALTER TABLE squalincome_history ADD COLUMN cot_sustained INTEGER")
            db.execute("ALTER TABLE squalincome_history ADD COLUMN event_type TEXT")
            db.commit()
            retail.ensure_schema(db)
            retail.capture_pair(db,original_snapshot=original_pair(),
                                file_read_at=READ,clock=RECORDED)
            target=sqlite3.connect(str(self.path))
            try:
                db.backup(target)
            finally:
                target.close()
        finally:
            db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def query(self,sql):
        db=sqlite3.connect(str(self.path))
        try:
            return db.execute(sql).fetchall()
        finally:
            db.close()

    def test_real_scanner_writes_same_original_retail_link(self):
        # The scan's own classifier and source reads are exercised, not a
        # made-up insert_history callback supplied by the test.
        result=scanner.scan_once_with_retail_inbox_research(
            self.path,OBS,targets=("EURUSD",))
        self.assertEqual(result["retailFirstSeenResearch"]["pilotOriginalLinks"],1)
        self.assertFalse(result["retailFirstSeenResearch"]["productionWired"])
        self.assertEqual(len(self.query("SELECT id FROM squalincome_history")),1)
        self.assertEqual(len(self.query(
            "SELECT history_id FROM research_retail_signal_context")),1)
        self.assertEqual(len(self.query(
            "SELECT history_id FROM research_signal_ingest_source_links")),1)
        self.assertEqual(len(self.query(
            "SELECT symbol FROM research_squalincome_cot_links")),1)

    def test_original_link_precedes_commit_and_no_refetch(self):
        # Capture the real callable BEFORE patching its module attribute,
        # otherwise the spy would recursively call its own MagicMock.
        real_attach=hook.attach_new
        def spy(db,*,history_id,observed_document,clock):
            self.assertTrue(db.in_transaction)
            self.assertEqual(db.execute("SELECT last_insert_rowid()").fetchone()[0],
                             history_id)
            self.assertEqual(observed_document,self.original_price)
            self.assertEqual(clock,OBS)
            return real_attach(
                db,history_id=history_id,
                observed_document=observed_document,clock=clock)
        with patch.object(hook,"attach_new",side_effect=spy):
            result=scanner.scan_once_with_retail_inbox_research(
                self.path,OBS,targets=("EURUSD",))
        self.assertEqual(result["retailFirstSeenResearch"]["pilotOriginalLinks"],1)

    def test_missing_retail_receipt_cannot_commit_research_history(self):
        db=sqlite3.connect(str(self.path))
        try:
            db.execute("DROP TRIGGER research_retail_first_delete")
            db.execute("DELETE FROM research_retail_original_first_seen")
            db.commit()
        finally:
            db.close()
        with self.assertRaises((ValueError,sqlite3.Error)):
            scanner.scan_once_with_retail_inbox_research(
                self.path,OBS,targets=("EURUSD",))
        self.assertEqual(self.query("SELECT count(*) FROM squalincome_history")[0][0],0)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_signal_ingest_source_links")[0][0],0)

    def test_shadow_missing_receipt_is_unknown_without_dropping_original(self):
        """Research failure rolls back proofs, NOT genuine Squalincome history."""
        db=sqlite3.connect(str(self.path))
        try:
            db.execute("DROP TRIGGER research_retail_first_delete")
            db.execute("DELETE FROM research_retail_original_first_seen")
            db.commit()
        finally:
            db.close()
        result=scanner.scan_once_with_retail_inbox_research(
            self.path,OBS,targets=("EURUSD",),
            research_missing_is_unknown=True)
        summary=result["retailFirstSeenResearch"]
        self.assertEqual(summary["pilotOriginalLinks"],0)
        self.assertEqual(summary["pilotRetailUnknown"],1)
        self.assertTrue(summary["missingRetailPreservesOriginalHistory"])
        self.assertEqual(self.query(
            "SELECT count(*) FROM squalincome_history")[0][0],1)
        self.assertEqual(self.query(
            "SELECT count(*) FROM squalincome_observations")[0][0],1)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_signal_ingest_source_links")[0][0],0)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_squalincome_cot_links")[0][0],0)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_retail_signal_context")[0][0],0)

    def test_shadow_with_receipt_links_original_and_no_unknown(self):
        result=scanner.scan_once_with_retail_inbox_research(
            self.path,OBS,targets=("EURUSD",),
            research_missing_is_unknown=True)
        summary=result["retailFirstSeenResearch"]
        self.assertEqual(summary["pilotOriginalLinks"],1)
        self.assertEqual(summary["pilotRetailUnknown"],0)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_retail_signal_context")[0][0],1)

    def test_wrong_scope_unsupported_and_default_scan_remains_unchanged(self):
        for targets in (None,(),("GBPUSD",),("EURUSD","EURUSD")):
            with self.subTest(targets=targets):
                with self.assertRaises(ValueError):
                    scanner.scan_once_with_retail_inbox_research(
                        self.path,OBS,targets=targets)
        # Default scanner does not import or run this research hook.
        with patch.object(hook,"attach_new",side_effect=AssertionError(
                "RESEARCH_HOOK_MUST_STAY_OFF")):
            result=scanner.scan_once(self.path,OBS,targets=("EURUSD",))
        self.assertNotIn("retailFirstSeenResearch",result)
        self.assertEqual(self.query(
            "SELECT count(*) FROM research_retail_signal_context")[0][0],0)


if __name__=="__main__":
    unittest.main()
