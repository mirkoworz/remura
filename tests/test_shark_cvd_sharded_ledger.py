"""Synthetic-only private CVD scan sharding and interruption/retention tests.

No network, broker, LIVE SQLite, new daemon, raw OHLC in GitHub outputs,
or archive upload. All temporary files are disposable and mode 0700.
"""
from datetime import timedelta
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_scan_coverage as scan
from test_shark_cvd_scan_coverage import DAY, KEY, make_doc, stamp


class SegmentedCvdTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-shard-synthetic-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"private"
        self.root.mkdir(mode=0o700)
        limit=patch.object(shards,"PER_SHARD",2)
        limit.start()
        self.addCleanup(limit.stop)

    def add(self,i,symbol="EURUSD",doc=None):
        at=DAY+timedelta(hours=5,minutes=15*i)
        return shards.record(
            self.root,symbol=symbol,slot_closed_at=stamp(at),
            clock=at+timedelta(minutes=1),source_document=doc,secret=KEY)

    def test_empty_is_unknown_and_no_unjustified_zero_negative(self):
        report=shards.verify(self.root)
        self.assertEqual(report["status"],"NO_SHARD_YET")
        self.assertEqual(report["totalObservedAttempts"],0)
        self.assertTrue(report["missingCalendarSlotsRemainUnknown"])
        self.assertFalse(report["readyForVpsDeployment"])
        self.assertFalse(report["tradingEdgeEstablished"])

    def test_crosses_limit_and_keeps_older_immutable_shards(self):
        for i in range(5):
            self.assertEqual(self.add(i)["status"],"NOT_EVALUABLE")
        report=shards.verify(self.root)
        self.assertEqual(report["segments"],3)
        self.assertEqual(report["sealedSegments"],2)
        self.assertEqual(report["totalObservedAttempts"],5)
        self.assertEqual(report["activeSegmentRows"],1)
        self.assertEqual(report["sourceRowsDeleted"],0)
        self.assertEqual(report["remainingTotalRows"],64*2-5)
        with sqlite3.connect(self.root/"scan-000001.sqlite3") as db:
            rows=db.execute(f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0]
            self.assertEqual(rows,2)
            self.assertTrue(db.execute(
                "SELECT 1 FROM sqlite_master WHERE name=?",
                (shards.SEAL_TRIGGER,)).fetchone())
            with self.assertRaisesRegex(sqlite3.IntegrityError,"sealed_shard"):
                db.execute(
                    f"INSERT INTO {scan.TABLE} SELECT * FROM {scan.TABLE} LIMIT 1")
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(f"DELETE FROM {scan.TABLE}")
        for seq in (1,2):
            self.assertTrue((self.root/shards._seal_name(seq)).is_file())
        # No text contains source key, OHLC or broker symbol.
        safe=json.dumps(report)
        self.assertNotIn(KEY.decode(),safe)
        self.assertNotIn("providerSymbol",safe)
        self.assertNotIn("PRIVATE_TEST_BROKER",safe)

    def test_recording_two_markets_and_monotonicity_across_shards(self):
        self.add(0,"EURUSD")
        self.add(0,"XAUUSD")
        self.add(1,"XAUUSD")  # rollover to second segment
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],3)
        with self.assertRaisesRegex(ValueError,"duplicate_or_backfilled"):
            self.add(0,"EURUSD")
        with self.assertRaisesRegex(ValueError,"duplicate_or_backfilled"):
            self.add(0,"XAUUSD")
        self.add(1,"EURUSD")
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],4)

    def test_hmac_session_prefix_survives_shard_transition_and_backup(self):
        doc=make_doc(count=60)
        closed=DAY+timedelta(minutes=60*15)
        out=shards.record(
            self.root,symbol="EURUSD",slot_closed_at=stamp(closed),
            clock=closed+timedelta(minutes=1),source_document=doc,secret=KEY)
        self.assertEqual(out["status"],"EVALUATED")
        with sqlite3.connect(self.root/"scan-000001.sqlite3") as source:
            original=source.execute(
                f"SELECT session_prefix_hmac,schema_version FROM {scan.TABLE}").fetchone()
            self.assertEqual(len(original[0]),64)
            self.assertEqual(original[1],scan.SCHEMA)
            destination=sqlite3.connect(self.root/"test-restore.sqlite3")
            try:
                source.backup(destination)
                self.assertEqual(
                    destination.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertEqual(
                    destination.execute(
                        f"SELECT session_prefix_hmac,schema_version FROM {scan.TABLE}"
                    ).fetchone(),original)
            finally:
                destination.close()
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],1)

    def test_hash_chain_detects_changed_sealed_db_and_marker(self):
        self.add(0)
        self.add(1)
        self.add(2)
        marker=self.root/"scan-000001.seal.json"
        payload=json.loads(marker.read_text())
        self.assertEqual(payload["rows"],2)
        self.assertEqual(len(payload["sha256"]),64)
        old=marker.read_bytes()
        marker.write_bytes(old.replace(payload["sha256"].encode(),b"0"*64))
        with self.assertRaisesRegex(ValueError,"cvd_shard_sealed_bytes_changed"):
            shards.verify(self.root)
        marker.write_bytes(old)
        with (self.root/"scan-000001.sqlite3").open("ab") as db:
            db.write(b"synthetic-tamper")
        with self.assertRaises(ValueError):
            shards.verify(self.root)

    def test_missing_seal_or_sequence_gap_fails_closed(self):
        self.add(0)
        self.add(1)
        self.add(2)
        seal=self.root/"scan-000001.seal.json"
        seal.unlink()
        with self.assertRaisesRegex(ValueError,"cvd_shard_seal_missing"):
            shards.verify(self.root)
        (self.root/"scan-000001.sqlite3").unlink()
        with self.assertRaisesRegex(ValueError,"cvd_shard_sequence_gap"):
            shards.verify(self.root)

    def test_interrupted_rollover_leaves_empty_new_file_not_fabricated_scan(self):
        self.add(0)
        self.add(1)
        with patch.object(shards.scan,"record",side_effect=RuntimeError("synthetic-crash")):
            with self.assertRaisesRegex(RuntimeError,"synthetic-crash"):
                self.add(2)
        report=shards.verify(self.root)
        self.assertEqual(report["segments"],2)
        self.assertEqual(report["sealedSegments"],1)
        self.assertEqual(report["totalObservedAttempts"],2)
        self.assertTrue(report["missingCalendarSlotsRemainUnknown"])
        self.add(3)
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],3)
        self.assertEqual(shards.verify(self.root)["activeSegmentRows"],1)

    def test_global_limit_stops_instead_of_pruning(self):
        with patch.object(shards,"MAX_SHARDS",2):
            for i in range(4):
                self.add(i)
            before=shards.verify(self.root)
            self.assertEqual(before["status"],"AT_GLOBAL_SHARD_LIMIT")
            with self.assertRaisesRegex(ValueError,"sequence_capacity_reached"):
                self.add(4)
            self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],4)
            self.assertTrue((self.root/"scan-000001.sqlite3").exists())

    def test_private_directory_and_busy_lock_required(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError,"private_0700"):
            shards.verify(self.root)
        self.root.chmod(0o700)
        shards.verify(self.root)
        lockfd=os.open(self.root/".cvd-shards.lock",os.O_RDWR)
        try:
            fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,"cvd_shard_writer_busy"):
                self.add(0)
        finally:
            fcntl.flock(lockfd,fcntl.LOCK_UN)
            os.close(lockfd)

    def test_no_automatic_restore_or_deletion_of_broken_shard(self):
        self.add(0)
        # A broken local file must not be silently discarded/replaced.
        path=self.root/"scan-000001.sqlite3"
        path.write_bytes(b"not-sqlite")
        with self.assertRaises(sqlite3.DatabaseError):
            self.add(1)
        self.assertEqual(path.read_bytes(),b"not-sqlite")


if __name__=="__main__":
    unittest.main()
