"""Offline real-first-seen archive capsule regression, disposable SQLite.

The original Squalincome history is deleted ONLY inside a synthetic test DB
AFTER an independently verified private local capsule was created. No provider
or Oracle access, real backups, cloud artifacts, CLI or LIVE collector.
"""
from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from scripts import shark_retail_evidence_capsule as capsule
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_original_decision_atomic_gate as atomic
from test_shark_original_decision_atomic_gate import new_history
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ,RECORDED
from test_shark_signal_ingest_decision_link import setup_case,OBS,NOW


class RetailOriginalCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.out=Path(self.tmp.name)/"evidence.zip"
        self.db,_,self.doc=setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)
        retail.capture_pair(self.db,original_snapshot=original_pair(),
                            file_read_at=READ,clock=RECORDED,
                            research_numeric_features=True)
        atomic.record_new(self.db,insert_history=new_history,
                          original_document=self.doc,clock=NOW,
                          research_retail_inbox=True)
        self.id=self.db.execute("SELECT id FROM squalincome_history").fetchone()[0]

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def export(self):
        self.db.execute("PRAGMA query_only=ON")
        try:
            return capsule.export_archive(self.db,self.out,history_ids=(self.id,))
        finally:
            self.db.execute("PRAGMA query_only=OFF")

    def test_complete_capsule_survives_native_30_day_purge(self):
        changes=self.db.total_changes
        result=self.export()
        self.assertEqual(self.db.total_changes,changes)
        self.assertEqual(result["completeLocalNumericLinks"],1)
        self.assertEqual(result["retailUnknownPreserved"],0)
        self.assertEqual(self.out.stat().st_mode & 0o077,0)
        with self.db:
            self.db.execute("DELETE FROM squalincome_history WHERE observed_at < ?",
                            ((OBS+timedelta(days=31)-timedelta(days=30))
                             .isoformat(),))
        self.assertEqual(numeric.read_linked(
            self.db,history_id=self.id)["status"],"UNKNOWN_NO_ORIGINAL_RETAIL_LINK")
        restored=capsule.verify_archive(self.out)
        self.assertEqual(restored["completeLocalNumericLinks"],1)
        self.assertEqual(restored["originalDecisionsPreserved"],1)
        self.assertFalse(restored["offHostRecoveryVerified"])
        self.assertFalse(restored["liveAuthorized"])

    def test_corrupted_capsule_hash_is_rejected_and_never_executes_sql(self):
        self.export()
        altered=Path(self.tmp.name)/"altered.zip"
        with zipfile.ZipFile(self.out) as reader:
            payload=reader.read(capsule.CAPSULES)
            manifest=reader.read(capsule.MANIFEST)
        altered.write_bytes(b"")
        os.chmod(altered,0o600)
        with zipfile.ZipFile(altered,"w",zipfile.ZIP_DEFLATED) as writer:
            writer.writestr(capsule.CAPSULES,payload.replace(
                b'"EURUSD"',b'"GBPUSD"',1))
            writer.writestr(capsule.MANIFEST,manifest)
        with self.assertRaisesRegex(ValueError,"digest_mismatch"):
            capsule.verify_archive(altered)

    def test_absent_original_row_refuses_backfill(self):
        self.db.execute("PRAGMA query_only=ON")
        try:
            with self.assertRaisesRegex(ValueError,"not_available_before_prune"):
                capsule.export_archive(self.db,self.out,history_ids=(self.id+100,))
        finally:
            self.db.execute("PRAGMA query_only=OFF")
        self.assertFalse(self.out.exists())

    def test_explicit_ids_and_readonly_required_no_research_writes(self):
        with self.assertRaisesRegex(ValueError,"read_only_clean"):
            capsule.export_archive(self.db,self.out,history_ids=(self.id,))
        self.db.execute("PRAGMA query_only=ON")
        try:
            for ids in ((self.id,self.id),(),(True,),("EURUSD",)):
                with self.subTest(ids=ids):
                    with self.assertRaises(ValueError):
                        capsule.export_archive(self.db,self.out,history_ids=ids)
        finally:
            self.db.execute("PRAGMA query_only=OFF")
        self.assertFalse(self.out.exists())

    def test_no_overwrite_and_public_destination_rejected(self):
        self.export()
        original=self.out.read_bytes()
        self.db.execute("PRAGMA query_only=ON")
        try:
            with self.assertRaises(FileExistsError):
                capsule.export_archive(self.db,self.out,history_ids=(self.id,))
        finally:
            self.db.execute("PRAGMA query_only=OFF")
        self.assertEqual(self.out.read_bytes(),original)
        public=Path(self.tmp.name)/"public"
        public.mkdir(mode=0o755)
        self.db.execute("PRAGMA query_only=ON")
        try:
            with self.assertRaisesRegex(ValueError,"parent_must_be_0700"):
                capsule.export_archive(
                    self.db,public/"evidence.zip",history_ids=(self.id,))
        finally:
            self.db.execute("PRAGMA query_only=OFF")

    def test_unknown_without_receipt_remains_unknown_not_zero(self):
        # A new original Squalincome observation without a retail link
        # must stay UNKNOWN in the capsule, not a synthetic sentiment.
        with self.db:
            self.db.execute(
                "INSERT INTO squalincome_history(symbol,observed_at) VALUES(?,?)",
                ("XAUUSD",NOW.isoformat()))
            other=self.db.execute("SELECT max(id) FROM squalincome_history").fetchone()[0]
        self.db.execute("PRAGMA query_only=ON")
        try:
            result=capsule.export_archive(
                self.db,self.out,history_ids=(self.id,other))
        finally:
            self.db.execute("PRAGMA query_only=OFF")
        self.assertEqual(result["completeLocalNumericLinks"],1)
        self.assertEqual(result["retailUnknownPreserved"],1)
        self.assertEqual(capsule.verify_archive(self.out)["originalDecisionsPreserved"],2)


if __name__=="__main__":
    unittest.main()
