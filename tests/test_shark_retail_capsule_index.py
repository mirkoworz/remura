"""Offline 0700 synthetic multi-pack index regression, no real VPS data."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_retail_capsule_index as index
from scripts import shark_retail_evidence_capsule as capsule
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from test_shark_original_decision_atomic_gate import new_history
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ, RECORDED
from test_shark_signal_ingest_decision_link import setup_case, NOW


class PrivateCapsuleIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.db,_,self.doc=setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)
        retail.capture_pair(self.db,original_snapshot=original_pair(),
                            file_read_at=READ,clock=RECORDED,
                            research_numeric_features=True)
        atomic.record_new(self.db,insert_history=new_history,
                          original_document=self.doc,clock=NOW,
                          research_retail_inbox=True)
        self.real_id=self.db.execute(
            "SELECT id FROM squalincome_history").fetchone()[0]
        with self.db:
            self.db.execute(
                "INSERT INTO squalincome_history(symbol,observed_at) VALUES(?,?)",
                ("XAUUSD",NOW.isoformat()))
            self.unknown_id=self.db.execute(
                "SELECT max(id) FROM squalincome_history").fetchone()[0]

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def pack(self,name,ids):
        self.db.execute("PRAGMA query_only=ON")
        try:
            return capsule.export_archive(self.db,self.folder/name,history_ids=ids)
        finally:
            self.db.execute("PRAGMA query_only=OFF")

    def test_two_generations_preserve_causality_after_prune(self):
        self.pack("a.zip",(self.real_id,))
        a=index.publish_next(self.folder)
        self.assertEqual(a["generation"],1)
        first=(self.folder/"retail-index-000001.json").read_bytes()
        self.pack("b.zip",(self.unknown_id,))
        with self.assertRaisesRegex(ValueError,"new_capsule_not_in_published_index"):
            index.verify_latest(self.folder)
        b=index.publish_next(self.folder)
        self.assertEqual(b["generation"],2)
        self.assertEqual(b["originalDecisions"],2)
        self.assertEqual(b["completeRetail"],1)
        self.assertEqual(b["unknownRetail"],1)
        self.assertEqual((self.folder/"retail-index-000001.json").read_bytes(),first)
        with self.db:
            self.db.execute("DELETE FROM squalincome_history")
        self.assertEqual(index.verify_latest(self.folder)["originalDecisions"],2)
        self.assertFalse(b["offHostRestoreVerified"])
        self.assertFalse(b["automaticPruningAuthorized"])

    def test_duplicate_history_across_packs_fails_closed(self):
        self.pack("a.zip",(self.real_id,))
        self.pack("b.zip",(self.real_id,))
        with self.assertRaisesRegex(ValueError,"duplicate_original_history"):
            index.publish_next(self.folder)
        self.assertEqual(list(self.folder.glob("retail-index-*.json")),[])

    def test_tampered_and_deleted_pack_detected(self):
        self.pack("a.zip",(self.real_id,))
        index.publish_next(self.folder)
        path=self.folder/"a.zip"
        original=path.read_bytes()
        path.write_bytes(original[:-3]+b"bad")
        # This torn ZIP previously leaked a low-level OSError on zipfile
        # seek. The index must expose a controlled corruption NO-GO.
        with self.assertRaisesRegex(
                ValueError,"private_capsule_unreadable_or_corrupt"):
            index.verify_latest(self.folder)
        path.write_bytes(original)
        self.assertEqual(index.verify_latest(self.folder)["generation"],1)
        path.unlink()
        with self.assertRaises(ValueError):
            index.verify_latest(self.folder)

    def test_modified_ancestor_index_detected(self):
        self.pack("a.zip",(self.real_id,))
        index.publish_next(self.folder)
        self.pack("b.zip",(self.unknown_id,))
        index.publish_next(self.folder)
        old=self.folder/"retail-index-000001.json"
        old.write_bytes(old.read_bytes().replace(
            b'"generation":1',b'"generation":2'))
        with self.assertRaises(ValueError):
            index.verify_latest(self.folder)

    def test_crash_staging_is_not_discarded(self):
        self.pack("a.zip",(self.real_id,))
        stage=self.folder/".remura-retail-aborted.tmp"
        stage.write_bytes(b"partial private payload")
        with self.assertRaisesRegex(ValueError,"incomplete_private_capsule_staging"):
            index.publish_next(self.folder)
        self.assertTrue(stage.exists())
        stage.unlink()  # Synthetic fixture cleanup, NOT production behavior
        self.assertEqual(index.publish_next(self.folder)["generation"],1)

    def test_atomic_link_failure_does_not_publish_or_erase_zip(self):
        self.pack("a.zip",(self.real_id,))
        with patch.object(index.os,"link",side_effect=OSError("forced")):
            with self.assertRaisesRegex(OSError,"forced"):
                index.publish_next(self.folder)
        self.assertTrue((self.folder/"a.zip").is_file())
        self.assertFalse(list(self.folder.glob("retail-index-*.json")))
        self.assertFalse(list(self.folder.glob(".remura-retail-index-*.tmp")))
        self.assertEqual(index.publish_next(self.folder)["generation"],1)

    def test_duplicate_index_generation_requires_new_pack(self):
        self.pack("a.zip",(self.real_id,))
        index.publish_next(self.folder)
        with self.assertRaisesRegex(ValueError,"no_new_capsule"):
            index.publish_next(self.folder)

    def test_public_directory_rejected(self):
        target=self.folder/"shared"
        target.mkdir(mode=0o755)
        with self.assertRaisesRegex(ValueError,"private_0700"):
            index.publish_next(target)


if __name__=="__main__":
    unittest.main()
