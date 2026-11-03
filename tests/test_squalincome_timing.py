"""Offline timing audit; no real broker requests, VPS or personal data."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import squalincome_timing as timing
import private_server as server

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,3,0,30,tzinfo=UTC)


class TimingTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"private.sqlite3"
        with sqlite3.connect(self.db) as con:
            con.execute("CREATE TABLE status(key TEXT PRIMARY KEY,value TEXT)")
            con.execute("INSERT INTO status VALUES ('secrets','DO_NOT_PRINT_PRIVATE')")
    def put(self, kind="post_ingest", seconds=4, events=0, ok=True):
        start=NOW+dt.timedelta(seconds=seconds)
        timing.record(self.db,kind=kind,started=start,
                      completed=start+dt.timedelta(seconds=1),
                      duration_ms=1000,examined=1,new_events=events,ok=ok,
                      saved_count=1 if kind=="post_ingest" else 0,
                      batch_completed=start if kind=="post_ingest" else None)
    def test_empty_read_does_not_create_timing_table(self):
        value=timing.summary(self.db)
        self.assertEqual(value["state"],"not_collected")
        with sqlite3.connect(self.db) as con:
            self.assertFalse(con.execute("SELECT 1 FROM sqlite_master WHERE name='squalincome_scan_timing'").fetchone())
    def test_measures_both_sources_without_fake_signal_lead(self):
        self.put("periodic")
        self.put("post_ingest",events=1)
        self.put("post_ingest",seconds=9)
        doc=timing.summary(self.db)
        self.assertEqual(doc["postIngest"]["samples"],2)
        self.assertEqual(doc["postIngest"]["newEvents"],1)
        self.assertEqual(doc["postIngest"]["medianBatchToScanMs"],1000)
        self.assertEqual(doc["periodic"]["samples"],1)
        self.assertIsNone(doc["periodic"]["medianBatchToScanMs"])
        self.assertIn("not_candle_or_signal_lead",doc["meaning"])
        self.assertNotIn("DO_NOT_PRINT_PRIVATE",json.dumps(doc))
        self.assertEqual(doc["postIngest"]["medianDurationMs"],1000)
    def test_bad_inputs_rejected_before_writes(self):
        with self.assertRaises(ValueError):
            timing.record(self.db,kind="broker",started=NOW,completed=NOW,
                          duration_ms=2)
        with self.assertRaises(ValueError):
            timing.record(self.db,kind="post_ingest",started=NOW,completed=NOW,
                          duration_ms=2,saved_count=3,batch_completed=None)
        with self.assertRaises(ValueError):
            timing.record(self.db,kind="periodic",started=NOW,
                          completed=NOW-dt.timedelta(seconds=1),duration_ms=2)
        with self.assertRaises(ValueError):
            timing.record(self.db,kind="post_ingest",started=NOW,completed=NOW,
                          duration_ms=2,saved_count=1,examined=2,
                          batch_completed=NOW)
        self.assertEqual(timing.summary(self.db)["state"],"not_collected")
    def test_retention_bounded_to_256_records(self):
        for i in range(270):
            self.put("periodic",seconds=i)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM squalincome_scan_timing").fetchone()[0],256)
        self.assertEqual(timing.summary(self.db)["periodic"]["samples"],256)
    def test_error_count_and_failure_do_not_fabricate_latency(self):
        self.put("post_ingest",ok=False)
        state=timing.summary(self.db)["postIngest"]
        self.assertEqual(state["failures"],1)
        self.assertEqual(state["successes"],0)
        self.assertIsNone(state["medianBatchToScanMs"])
    def test_real_post_ingest_hook_records_and_no_extra_broker_calls(self):
        env={"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED":"1",
             "REMURA_SQUALINCOME_MONITOR_ENABLED":"1",
             "REMURA_COLLECTOR_ENABLED":"1","REMURA_COT_SYNC_ENABLED":"1"}
        with patch.object(server,"squalincome_monitored_symbols",
                          return_value=("EURUSD",)), \
             patch.object(server,"observe_squalincome",
                          return_value={"examined":1,"newEvents":0}) as observe:
            result=server.observe_updated_batch(self.db,("EURUSD",),env=env,
                        batch_completed=dt.datetime.now(UTC)-dt.timedelta(seconds=1))
        self.assertEqual(result["examined"],1)
        observe.assert_called_once_with(self.db,targets=("EURUSD",))
        self.assertEqual(timing.summary(self.db)["postIngest"]["samples"],1)
    def test_telemetry_error_does_not_suppress_signal(self):
        env={"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED":"1",
             "REMURA_SQUALINCOME_MONITOR_ENABLED":"1",
             "REMURA_COLLECTOR_ENABLED":"1","REMURA_COT_SYNC_ENABLED":"1"}
        with patch.object(server,"squalincome_monitored_symbols",
                          return_value=("EURUSD",)), \
             patch.object(server,"observe_squalincome",
                          return_value={"examined":1,"newEvents":1}), \
             patch.object(server,"record_scan_timing",
                          side_effect=sqlite3.OperationalError("private error")):
            result=server.observe_updated_batch(self.db,("EURUSD",),env=env,
                         batch_completed=dt.datetime.now(UTC))
        self.assertEqual(result["newEvents"],1)

if __name__=="__main__":
    unittest.main()
