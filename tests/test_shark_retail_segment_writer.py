"""Real offline two-week SQLite rollover, concurrency and crash regression."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_retail_segment_writer as writer
from scripts import shark_retail_segment_readiness as layout
from scripts import shark_retail_first_seen as retail
from test_shark_retail_segment_readiness import make_pair, AUTHORIZED

ACK=writer.ACK
UTC=timezone.utc


class RetailSegmentWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-retail-lab-")
        self.root=Path(self.tmp.name)
        self.plan=layout.plan(AUTHORIZED)
        self.begin=layout._time(self.plan["segments"][0]["startUtc"])
        self.next=layout._time(self.plan["segments"][1]["startUtc"])
        self.env=patch.dict(os.environ,{writer.ENV:ACK})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def write(self,stamp,snapshot=None,**kw):
        return writer.record(
            self.root,authorized_at=AUTHORIZED,
            original_snapshot=snapshot or make_pair(stamp),
            file_read_at=stamp-timedelta(seconds=5),
            clock=stamp,**kw)

    def verify(self):
        return writer.verify(self.root,authorized_at=AUTHORIZED)

    def test_two_week_rollover_and_same_shard_pair_atomicity(self):
        first=self.begin+timedelta(minutes=5)
        self.assertEqual(self.write(first)["segmentNumber"],1)
        self.write(first+timedelta(minutes=20))
        self.assertEqual(self.write(self.next)["segmentNumber"],2)
        report=self.verify()
        self.assertEqual(report["publishedSegments"],2)
        self.assertEqual(report["sourcePairs"],3)
        self.assertEqual(report["numericRows"],6)
        self.assertFalse(report["liveAuthorized"])
        self.assertEqual(len(list(self.root.glob("retail-*.sqlite3"))),2)

    def test_duplicate_global_source_after_rollover_rejected(self):
        first=self.next-timedelta(minutes=2)
        self.write(first)
        with self.assertRaisesRegex(ValueError,"duplicate_or_backdated"):
            self.write(self.next,snapshot=make_pair(first))
        self.assertEqual(len(list(self.root.glob("retail-*.sqlite3"))),1)
        self.assertEqual(self.verify()["sourcePairs"],1)

    def test_crash_during_first_write_to_next_shard_retry_has_no_partial_pair(self):
        self.write(self.next-timedelta(minutes=2))
        with patch.object(retail,"capture_pair",
                          side_effect=sqlite3.OperationalError("injected_writer_crash")):
            with self.assertRaisesRegex(sqlite3.OperationalError,"injected_writer"):
                self.write(self.next)
        pending=self.verify()
        self.assertEqual(pending["publishedSegments"],2)
        self.assertEqual(pending["sourcePairs"],1)
        self.assertEqual(self.write(self.next)["pairReceiptsWritten"],2)
        self.assertEqual(self.verify()["sourcePairs"],2)

    def test_initial_gap_or_old_segment_never_backfills(self):
        with self.assertRaisesRegex(ValueError,"initial_segment_must_be_first"):
            self.write(self.next)
        self.assertEqual(self.verify()["publishedSegments"],0)
        self.write(self.begin+timedelta(minutes=5))
        future=layout._time(self.plan["segments"][2]["startUtc"])
        with self.assertRaisesRegex(ValueError,"skipped_or_old"):
            self.write(future)
        self.assertEqual(self.verify()["sourcePairs"],1)

    def test_active_prior_shard_tampered_after_rollover_fails_hash_chain(self):
        self.write(self.next-timedelta(minutes=2))
        self.write(self.next)
        old=self.root/"retail-000001.sqlite3"
        db=sqlite3.connect(str(old))
        try:
            db.execute("CREATE TABLE tamper(x)")
            db.commit()
        finally:
            db.close()
        with self.assertRaisesRegex(ValueError,"hash_chain"):
            self.verify()

    def test_explicit_isolated_permission_gate(self):
        self.env.stop()
        try:
            with self.assertRaisesRegex(ValueError,"explicit_private_tmp"):
                self.write(self.begin+timedelta(minutes=5))
        finally:
            self.env.start()
        public=self.root/"public"
        public.mkdir(mode=0o755)
        with self.assertRaisesRegex(ValueError,"explicit_private_tmp"):
            writer.verify(public,authorized_at=AUTHORIZED)
        self.assertEqual(len(list(self.root.glob("retail-*.sqlite3"))),0)

    def test_unpublished_init_pending_blocks_all_writes_without_deleting(self):
        pending=self.root/".remura-retail-init-aborted.pending"
        pending.write_bytes(b"unpublished synthetic initialization")
        with self.assertRaisesRegex(ValueError,"unpublished_retail_segment"):
            self.write(self.begin+timedelta(minutes=5))
        self.assertTrue(pending.exists())
        with self.assertRaisesRegex(ValueError,"unpublished_retail_segment"):
            self.verify()

    def test_lock_contention_blocks_without_modifying_db(self):
        import fcntl
        self.write(self.begin+timedelta(minutes=5))
        fd=os.open(self.root/writer.LOCK,os.O_RDONLY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,"concurrent_writer_busy"):
                self.write(self.begin+timedelta(minutes=25))
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN)
            os.close(fd)
        self.assertEqual(self.verify()["sourcePairs"],1)

    def test_source_validation_before_creating_any_shard(self):
        now=self.begin+timedelta(minutes=5)
        stale=make_pair(now-timedelta(hours=2))
        with self.assertRaisesRegex(ValueError,"source_unavailable_or_stale"):
            self.write(now,snapshot=stale)
        self.assertEqual(list(self.root.glob("retail-*.sqlite3")),[])


if __name__=="__main__":
    unittest.main()
