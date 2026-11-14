"""Synthetic-only crash recovery and complete private shard backup/restore.

Exercises local files only, no Oracle LIVE, new broker requests, HMAC key
export or GitHub artifact. No source scan attempts are ever pruned.
"""
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_shard_backup as backup
from scripts import shark_cvd_scan_coverage as scan
from test_shark_cvd_scan_coverage import DAY, KEY, make_doc, stamp


class ShardedSnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="remura-shard-restore-")
        self.addCleanup(tmp.cleanup)
        self.parent=Path(tmp.name)
        self.root=self.parent/"shards"
        self.root.mkdir(mode=0o700)
        self.snapshot=self.parent/"snapshot"
        self.restored=self.parent/"restored"
        cap=patch.object(shards,"PER_SHARD",2)
        cap.start()
        self.addCleanup(cap.stop)

    def add(self,i,symbol="EURUSD",document=None,base=None):
        at=(base or (DAY+timedelta(hours=5)))+timedelta(minutes=15*i)
        return shards.record(
            self.root,symbol=symbol,slot_closed_at=stamp(at),
            source_document=document,secret=KEY,
            clock=at+timedelta(minutes=1))

    def build(self):
        for i in range(5):
            self.add(i)
        self.assertEqual(shards.verify(self.root)["segments"],3)

    def test_full_private_backup_restore_preserves_every_shard_and_seal(self):
        self.build()
        before=shards.verify(self.root)
        snap=backup.create_snapshot(self.root,self.snapshot)
        self.assertEqual(snap["segments"],3)
        self.assertEqual(snap["observedAttempts"],5)
        self.assertEqual(snap["storedFiles"],5)
        result=backup.restore_snapshot(self.snapshot,self.restored)
        self.assertEqual(result["status"],"PRIVATE_CVD_SHARD_RESTORED_AND_VERIFIED")
        self.assertEqual(result["observedAttempts"],5)
        self.assertEqual(shards.verify(self.root),before)
        self.assertEqual(shards.verify(self.restored),before)
        for seq in range(1,4):
            name=shards._name(seq)
            with sqlite3.connect(self.root/name) as left, sqlite3.connect(self.restored/name) as right:
                self.assertEqual(left.execute(
                    f"SELECT * FROM {scan.TABLE} ORDER BY symbol,closed_at").fetchall(),
                    right.execute(
                    f"SELECT * FROM {scan.TABLE} ORDER BY symbol,closed_at").fetchall())
                self.assertEqual(right.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                with self.assertRaises(sqlite3.IntegrityError):
                    right.execute(f"DELETE FROM {scan.TABLE}")
            if seq<3:
                self.assertEqual((self.root/shards._seal_name(seq)).read_bytes(),
                                 (self.restored/shards._seal_name(seq)).read_bytes())
        self.assertFalse(result["hmacKeyIncluded"])
        self.assertFalse(result["independentSignature"])
        self.assertFalse(result["readyForVpsDeployment"])
        self.assertFalse(result["missingScansBackfilled"])
        manifest=(self.snapshot/backup.MANIFEST).read_text()
        self.assertNotIn(KEY.decode(),manifest)
        self.assertNotIn("PRIVATE_TEST_BROKER",manifest)

    def test_future_scan_can_append_after_restored_active_segment(self):
        self.build()
        backup.create_snapshot(self.root,self.snapshot)
        backup.restore_snapshot(self.snapshot,self.restored)
        at=DAY+timedelta(hours=6,minutes=15)
        result=shards.record(
            self.restored,symbol="EURUSD",slot_closed_at=stamp(at),
            source_document=None,clock=at+timedelta(minutes=1),secret=KEY)
        self.assertEqual(result["status"],"NOT_EVALUABLE")
        self.assertEqual(shards.verify(self.restored)["totalObservedAttempts"],6)
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],5)

    def test_hmac_v2_full_source_prefix_survives_backup_and_restore(self):
        source=make_doc(count=60)
        at=DAY+timedelta(minutes=900)
        self.add(0,document=source,base=at)
        self.add(1,base=at)
        self.add(2,base=at)  # cross into second shard
        backup.create_snapshot(self.root,self.snapshot)
        backup.restore_snapshot(self.snapshot,self.restored)
        with sqlite3.connect(self.root/shards._name(1)) as left, sqlite3.connect(
                self.restored/shards._name(1)) as right:
            query=f"SELECT session_prefix_hmac,source_hmac,schema_version FROM {scan.TABLE} WHERE state='EVALUATED'"
            original=left.execute(query).fetchone()
            saved=right.execute(query).fetchone()
            self.assertEqual(original,saved)
            self.assertEqual(len(saved[0]),64)
            self.assertEqual(len(saved[1]),64)
            self.assertEqual(saved[2],scan.SCHEMA)

    def test_backup_tampering_rejected_even_if_sqlite_remains_readable(self):
        self.build()
        backup.create_snapshot(self.root,self.snapshot)
        p=self.snapshot/shards._name(3)
        with p.open("ab") as stream:
            stream.write(b"tampered-snapshot")
        with self.assertRaisesRegex(ValueError,"cvd_snapshot_file_hash_mismatch"):
            backup.verify_snapshot(self.snapshot)
        with self.assertRaises(ValueError):
            backup.restore_snapshot(self.snapshot,self.restored)
        self.assertFalse(self.restored.exists())

    def test_no_overwrite_and_incomplete_backup_is_not_published(self):
        self.add(0)
        with patch.object(backup,"_publish_manifest",side_effect=RuntimeError("crash")):
            with self.assertRaisesRegex(RuntimeError,"crash"):
                backup.create_snapshot(self.root,self.snapshot)
        self.assertTrue(self.snapshot.exists())
        with self.assertRaisesRegex(ValueError,"cvd_snapshot_not_finalized"):
            backup.verify_snapshot(self.snapshot)
        with self.assertRaisesRegex(ValueError,"new_backup_directory"):
            backup.create_snapshot(self.root,self.snapshot)
        another=self.parent/"good-snapshot"
        backup.create_snapshot(self.root,another)
        backup.restore_snapshot(another,self.restored)
        with self.assertRaisesRegex(ValueError,"new_backup_directory"):
            backup.restore_snapshot(another,self.restored)

    def test_atomic_shard_creation_failure_does_not_publish_uninitialized_db(self):
        self.add(0)
        self.add(1)
        shards._seal(self.root,1)
        with patch.object(shards.os,"link",side_effect=OSError("synthetic-crash")):
            with self.assertRaisesRegex(OSError,"synthetic-crash"):
                self.add(2)
        self.assertFalse((self.root/shards._name(2)).exists())
        self.assertFalse(list(self.root.glob(".cvd-init-*")))
        self.add(3)
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],3)

    def test_pending_seal_recovery_requires_explicit_consent(self):
        self.add(0)
        self.add(1)
        with patch.object(shards,"_publish",side_effect=SystemExit("crash")):
            with self.assertRaises(SystemExit):
                shards._seal(self.root,1)
        with self.assertRaisesRegex(ValueError,"cvd_shard_seal_missing"):
            shards.verify(self.root)
        with self.assertRaisesRegex(ValueError,"explicit_recovery_acknowledgement"):
            shards.recover_interrupted_rollover(self.root)
        result=shards.recover_interrupted_rollover(self.root,acknowledge=True)
        self.assertEqual(result["status"],"LAST_FULL_SHARD_SEAL_REPAIRED_LOCAL_ONLY")
        self.assertEqual(result["attemptsReconstructed"],0)
        self.assertEqual(shards.verify(self.root)["sealedSegments"],1)
        self.add(2)
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],3)

    def test_unpublished_zero_byte_file_is_retained_not_silently_deleted(self):
        path=self.root/".cvd-init-synthetic.sqlite3"
        path.write_bytes(b"")
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,"unpublished_initialization"):
            shards.verify(self.root)
        result=shards.recover_interrupted_rollover(self.root,acknowledge=True)
        self.assertEqual(result["retainedUnpublishedFiles"],1)
        self.assertEqual(result["sourceRowsDeleted"],0)
        retained=self.root/"unpublished-retained-.cvd-init-synthetic.sqlite3"
        self.assertTrue(retained.is_file())
        self.assertFalse(path.exists())
        self.add(0)
        backup.create_snapshot(self.root,self.snapshot)
        backup.restore_snapshot(self.snapshot,self.restored)
        self.assertTrue((self.restored/retained.name).exists())
        self.assertEqual(shards.verify(self.restored)["totalObservedAttempts"],1)

    def test_unpublished_file_with_a_scan_is_never_quarantined(self):
        staged=self.root/".cvd-init-synthetic.sqlite3"
        with sqlite3.connect(staged) as db:
            scan.ensure_schema(db)
            at=DAY+timedelta(hours=5)
            scan.record(db,symbol="EURUSD",slot_closed_at=stamp(at),
                        clock=at+timedelta(minutes=1),
                        source_document=None,secret=KEY)
        with self.assertRaises(ValueError):
            shards.recover_interrupted_rollover(self.root,acknowledge=True)
        self.assertTrue(staged.is_file())
        with self.assertRaises(ValueError):
            shards.verify(self.root)

    def test_backup_rejects_unexpected_unaccounted_files(self):
        self.add(0)
        (self.root/"untracked-data.sqlite3").write_bytes(b"not-to-be-lost")
        with self.assertRaisesRegex(ValueError,"unexpected_or_missing_cvd_archive_files"):
            backup.create_snapshot(self.root,self.snapshot)
        self.assertFalse(self.snapshot.exists())

    def test_backup_restore_keeps_every_unknown_attempt_unknown(self):
        self.add(0)
        self.add(2)  # missing 05:15 slot stays absent
        backup.create_snapshot(self.root,self.snapshot)
        backup.restore_snapshot(self.snapshot,self.restored)
        with sqlite3.connect(self.restored/shards._name(1)) as db:
            self.assertEqual(db.execute(
                f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0],2)
            self.assertEqual(
                [x[0] for x in db.execute(f"SELECT closed_at FROM {scan.TABLE} ORDER BY closed_at")],
                [stamp(DAY+timedelta(hours=5)),
                 stamp(DAY+timedelta(hours=5,minutes=30))])
        self.assertFalse(backup.verify_snapshot(self.snapshot)["readyForVpsDeployment"])


if __name__=="__main__":
    unittest.main()
