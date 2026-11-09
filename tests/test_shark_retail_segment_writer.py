"""Real offline two-week SQLite rollover, concurrency and crash regression."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import sqlite3
import statistics
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import shark_retail_segment_writer as writer
from scripts import shark_retail_numeric_features as numeric
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

    def test_second_numeric_insert_disk_full_simulation_rolls_back_both(self):
        """The genuine insert transaction must roll back at the second feature.

        This is injected SQLITE_FULL, not a real filled filesystem or
        provider outage. The empty shard is not a counted observation.
        """
        real=numeric.append_inside_original_pair
        calls=[0]

        def fail_on_second(*args,**kwargs):
            calls[0]+=1
            if calls[0]==2:
                raise sqlite3.OperationalError(
                    "database or disk is full (injected test only)")
            return real(*args,**kwargs)

        stamp=self.begin+timedelta(minutes=5)
        with patch.object(numeric,"append_inside_original_pair",
                          side_effect=fail_on_second):
            with self.assertRaisesRegex(sqlite3.OperationalError,"disk is full"):
                self.write(stamp)
        self.assertEqual(calls[0],2)
        empty=self.verify()
        self.assertEqual(empty["publishedSegments"],1)
        self.assertEqual(empty["sourcePairs"],0)
        self.assertEqual(empty["numericRows"],0)
        with sqlite3.connect(str(self.root/"retail-000001.sqlite3")) as db:
            for table in (retail.TABLE,numeric.TABLE):
                self.assertEqual(
                    db.execute(f"SELECT count(*) FROM {table}").fetchone()[0],0)
        self.assertEqual(self.write(stamp)["pairReceiptsWritten"],2)
        restored=self.verify()
        self.assertEqual(restored["sourcePairs"],1)
        self.assertEqual(restored["numericRows"],2)

    def test_24h_actual_writer_disk_profile_and_no_network(self):
        """72 authentic local writer calls; source values are 100% synthetic.

        No hard performance threshold and no inference about OCI billing,
        shared broker data, future partitions or physical disk failure.
        """
        first=self.begin+timedelta(minutes=10)
        durations=[]
        measured={}
        for i in range(72):
            stamp=first+timedelta(minutes=20*i)
            t0=time.perf_counter()
            report=self.write(stamp)
            durations.append(time.perf_counter()-t0)
            self.assertEqual(report["segmentNumber"],1)
            self.assertEqual(report["newApiCalls"],0)
            if i in (0,35,71):
                measured[str(i+1)]=(
                    self.root/"retail-000001.sqlite3").stat().st_size
        file=self.root/"retail-000001.sqlite3"
        with sqlite3.connect(str(file)) as db:
            page_count=db.execute("PRAGMA page_count").fetchone()[0]
            page_bytes=db.execute("PRAGMA page_size").fetchone()[0]
            receipts=db.execute(
                f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0]
            numeric_rows=db.execute(
                f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0]
        result=self.verify()
        self.assertEqual(result["sourcePairs"],72)
        self.assertEqual(result["numericRows"],144)
        self.assertEqual(receipts,144)
        self.assertEqual(numeric_rows,144)
        self.assertEqual(file.stat().st_size,page_count*page_bytes)
        self.assertEqual(result["publishedSegments"],1)
        self.assertFalse(result["liveAuthorized"])
        self.assertLess(file.stat().st_size,writer.MAX_BYTES)
        self.assertEqual(len(list(self.root.glob("*.sqlite3-journal"))),0)
        self.assertEqual(len(list(self.root.glob("*.sqlite3-wal"))),0)
        ordered=sorted(durations)
        profile={
            "schema":"remura-track-b-synthetic-retail-disk-profile-v1",
            "status":"GITHUB_RUNNER_SYNTHETIC_24H_ONLY_NOT_OCI_CAPACITY",
            "source":"fake_in_memory_Myfxbook_pairs_only",
            "recordedPairs":72,
            "recordedReceiptsAndNumericRows":144,
            "bytesAfter1Pair":measured["1"],
            "bytesAfter36Pairs":measured["36"],
            "bytesAfter72Pairs":measured["72"],
            "pageCount":page_count,
            "pageBytes":page_bytes,
            "writerWallSeconds72Calls":round(sum(durations),3),
            "writerP95WallMilliseconds":round(
                1000*ordered[68],3),
            "budgetDiskBytesPerShard":writer.MAX_BYTES,
            "completeFourteenDaysMeasured":False,
            "complete196DaysMeasured":False,
            "realOCIStorageOrCostVerified":False,
            "physicalDiskFullTested":False,
            "crossDBSqualincomeAtomicityVerified":False,
            "liveAuthorized":False,
            "newApiCalls":0,
        }
        print("REMURA_B_RETAIL_SEGMENT_SYNTHETIC_PROFILE="
              +json.dumps(profile,sort_keys=True))

    def test_source_validation_before_creating_any_shard(self):
        now=self.begin+timedelta(minutes=5)
        stale=make_pair(now-timedelta(hours=2))
        with self.assertRaisesRegex(ValueError,"source_unavailable_or_stale"):
            self.write(now,snapshot=stale)
        self.assertEqual(list(self.root.glob("retail-*.sqlite3")),[])


if __name__=="__main__":
    unittest.main()
