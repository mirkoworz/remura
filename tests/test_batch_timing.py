"""Offline-only tests: bounded aggregate batch timing, zero broker requests."""
import datetime as dt
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import batch_timing as timing
import private_server as server

UTC=dt.timezone.utc
T0=dt.datetime(2026,11,3,11,30,0,tzinfo=UTC)


class PrivateBatchTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"private.sqlite3"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE prices (dummy INTEGER)")
    def tearDown(self):
        self.tmp.cleanup()

    def add(self,*,start=T0,seconds=110,slot=1,scheduled=5,saved=5,
            state="ok",post_delta=0.2):
        ingest=start+dt.timedelta(seconds=seconds)
        end=ingest+dt.timedelta(seconds=1)
        return timing.record(self.db,
            started=start,ingest_returned=ingest,finished=end,
            scheduled_markets=scheduled,saved_markets=saved,slot=slot,
            post_scan_state=state,
            post_scan_finished=(ingest+dt.timedelta(seconds=post_delta)
                                if state!="not_run" else None))

    def test_default_disabled_flag_and_empty_database_are_fail_closed(self):
        self.assertFalse(server.batch_timing_enabled({}))
        self.assertFalse(server.batch_timing_enabled(
            {"REMURA_BATCH_TIMING_ENABLED":"true"}))
        self.assertTrue(server.batch_timing_enabled(
            {"REMURA_BATCH_TIMING_ENABLED":"1"}))
        self.assertEqual(timing.summary(self.db)["state"],"not_collected")
        self.assertEqual(timing.summary(self.db)["samples"],None)
        self.assertEqual(timing.summary(self.db.parent/"missing.db")["state"],
                         "not_collected")

    def test_summary_uses_only_aggregates_and_true_post_ingest_lag(self):
        self.add()
        self.add(start=T0+dt.timedelta(minutes=15),seconds=70,
                 slot=2,scheduled=4,saved=2,state="not_run")
        self.add(start=T0+dt.timedelta(minutes=30),seconds=90,
                 slot=3,scheduled=5,saved=0,state="failed",post_delta=0.4)
        doc=timing.summary(self.db)
        self.assertEqual(doc["schema"],timing.SCHEMA)
        self.assertEqual(doc["state"],"ready")
        self.assertEqual(doc["samples"],3)
        self.assertEqual(doc["scheduledMarkets"],14)
        self.assertEqual(doc["savedMarkets"],7)
        self.assertEqual(doc["zeroSavedBatches"],1)
        self.assertEqual(doc["medianCollectorToIngestReturnMs"],90000)
        self.assertEqual(doc["maxCollectorToIngestReturnMs"],110000)
        self.assertEqual(doc["postScanSuccesses"],1)
        self.assertEqual(doc["postScanFailures"],1)
        self.assertEqual(doc["postScanNotRun"],1)
        self.assertEqual(doc["medianIngestReturnToPostScanMs"],200)
        self.assertEqual(doc["lastIngestReturnedUtc"],
                         "2026-11-03T12:01:30+00:00")
        self.assertNotIn("EURUSD",str(doc))
        self.assertNotIn("token",str(doc).lower())
        self.assertNotIn("prices",str(doc))

    def test_invalid_counts_clocks_and_scan_states_write_nothing(self):
        normal=dict(started=T0,ingest_returned=T0+dt.timedelta(seconds=3),
                    finished=T0+dt.timedelta(seconds=7),
                    scheduled_markets=5,saved_markets=2,slot=1,
                    post_scan_state="not_run",post_scan_finished=None)
        invalid=[
            {"started":T0.replace(tzinfo=None)},
            {"ingest_returned":T0-dt.timedelta(seconds=1)},
            {"finished":T0+dt.timedelta(days=1)},
            {"scheduled_markets":True},
            {"scheduled_markets":9},
            {"saved_markets":6},
            {"saved_markets":-1},
            {"slot":0},
            {"slot":9},
            {"slot":True},
            {"post_scan_state":"SECRET"},
            {"post_scan_state":"ok"},
            {"post_scan_finished":T0},
            {"post_scan_state":"failed","post_scan_finished":T0},
            {"post_scan_state":"ok",
             "post_scan_finished":T0+dt.timedelta(hours=2)},
        ]
        for changed in invalid:
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                timing.record(self.db,**dict(normal,**changed))
        self.assertEqual(timing.summary(self.db)["state"],"not_collected")

    def test_retention_bounded_and_representative_batch_slots(self):
        for i in range(261):
            self.add(start=T0+dt.timedelta(minutes=i*15),seconds=1,
                     slot=i%8+1,scheduled=5,saved=5,state="not_run")
        with sqlite3.connect(self.db) as conn:
            count=conn.execute("SELECT COUNT(*) FROM remura_batch_timing").fetchone()[0]
            cols=[row[1] for row in conn.execute("PRAGMA table_info(remura_batch_timing)")]
        self.assertEqual(count,timing.MAX_ROWS)
        self.assertEqual(timing.summary(self.db)["samples"],timing.MAX_ROWS)
        for banned in ("symbol","provider","token","price","account","secret","oauth"):
            self.assertTrue(all(banned not in name.lower() for name in cols))

    def test_corrupted_rows_return_nothing_instead_of_false_ready(self):
        self.add()
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE remura_batch_timing SET post_scan_state='SECRET'")
        state=timing.summary(self.db)
        self.assertEqual(state["state"],"invalid_data")
        self.assertIsNone(state["samples"])
        self.assertNotIn("SECRET",str(state))

    def test_no_network_or_collector_call_during_summary(self):
        self.add()
        with patch("urllib.request.urlopen",side_effect=AssertionError("NO NETWORK")):
            self.assertEqual(timing.summary(self.db)["state"],"ready")

    def test_import_is_disconnected_from_trading_and_default_server_is_off(self):
        with patch.dict("os.environ",{},clear=True):
            self.assertFalse(server.batch_timing_enabled())
        body=(Path(__file__).resolve().parents[1]/"scripts"/"private_server.py").read_text("utf-8")
        self.assertIn('result["collectorTiming"]=(batch_timing_summary(db_path)',body)
        self.assertIn("if batch_timing_enabled(env):",body)
        self.assertIn("saved_markets=len(saved_this_batch)",body)
        self.assertIn("ingest_returned=utcnow()",body)


if __name__=="__main__":
    unittest.main()
