"""Offline tests for the v1.62 opt-in private H1 pairing/store integration."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import h1_paired_store as store
import private_server as server
from h1_batch_comparison import compare_paired_h1

UTC = dt.timezone.utc
POST = dt.datetime(2026, 11, 3, 16, 20, tzinfo=UTC)
INGEST = dt.datetime(2026, 11, 3, 16, 19, tzinfo=UTC)


def frame(iso):
    return {"H1": {"bars": 60, "lastClosedAt": iso, "ageMinutes": 0}}


def full_snapshot():
    markets = [
        {"symbol": f"C{i:02}", "timeframes": frame("2026-11-03T15:00:00Z")}
        for i in range(32)
    ]
    markets += [
        {"symbol": "EURUSD", "timeframes": frame("2026-11-03T14:00:00Z")},
        {"symbol": "XAUUSD", "timeframes": frame("2026-11-03T15:00:00Z")},
    ]
    return {"lastScanAt": "2026-11-03T16:10:00Z", "markets": markets}


def newer():
    return {
        "EURUSD": frame("2026-11-03T15:00:00Z"),
        "XAUUSD": frame("2026-11-03T15:00:00Z"),
    }


def enabled():
    return {
        "REMURA_H1_PAIRED_ENABLED": "1",
        "REMURA_SQUALINCOME_AFTER_INGEST_ENABLED": "1",
        "REMURA_SQUALINCOME_MONITOR_ENABLED": "1",
        "REMURA_COT_SYNC_ENABLED": "1",
        "REMURA_COLLECTOR_ENABLED": "1",
    }


class H1PairedStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "private.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE squalincome_last_scan (
                id INTEGER PRIMARY KEY, summary TEXT NOT NULL)""")
            db.execute("INSERT INTO squalincome_last_scan VALUES (1,?)",
                       (json.dumps(full_snapshot()),))

    def tearDown(self):
        self.temp.cleanup()

    def measure(self, doc=None):
        return compare_paired_h1(
            full_snapshot() if doc is None else doc, newer(),
            post_scan_utc=POST.isoformat(), ingest_returned_utc=INGEST.isoformat())

    def test_read_only_snapshot_and_same_utc_paired_counts(self):
        self.assertEqual(store.load_full_scan(self.path), full_snapshot())
        result = self.measure()
        self.assertEqual(result["state"], "COMPARABLE")
        self.assertEqual(result["staleToReady"], 1)
        store.record(self.path, result, post_scan_utc=POST,
                     ingest_returned_utc=INGEST)
        value = store.summary(self.path)
        self.assertEqual((value["samples"], value["comparableSamples"]), (1, 1))
        self.assertEqual((value["marketsCompared"], value["readyBefore"],
                          value["readyAfter"], value["staleToReady"],
                          value["h1Advanced"], value["h1Unchanged"]),
                         (2, 1, 2, 1, 1, 1))
        dumped = json.dumps(value)
        for disallowed in ("EURUSD", "XAUUSD", "providerSymbol", "CTRADER_", '"o":'):
            self.assertNotIn(disallowed, dumped)
        with sqlite3.connect(self.path) as db:
            columns = [row[1] for row in db.execute("PRAGMA table_info(remura_h1_paired)")]
            self.assertNotIn("symbol", columns)
            self.assertNotIn("price", columns)

    def test_missing_full_scan_is_nd_not_a_false_zero(self):
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM squalincome_last_scan")
        self.assertIsNone(store.load_full_scan(self.path))
        result = compare_paired_h1(
            store.load_full_scan(self.path), newer(),
            post_scan_utc=POST.isoformat(), ingest_returned_utc=INGEST.isoformat())
        self.assertNotEqual(result["state"], "COMPARABLE")
        self.assertIsNone(result["staleToReady"])
        store.record(self.path, result, post_scan_utc=POST,
                     ingest_returned_utc=INGEST)
        value = store.summary(self.path)
        self.assertEqual(value["unverifiableSamples"], 1)
        self.assertIsNone(value["staleToReady"])
        self.assertIsNone(value["readyBefore"])

    def test_invalid_metrics_fail_closed_and_leave_db_unchanged(self):
        good = self.measure()
        invalid = [
            {"schema": good["schema"], "state": "COMPARABLE",
             **{key: None for key in store.COUNTS}},
            {**good, "staleToReady": 9},
            {**good, "freshestH1Advanced": 0},
            {**good, "state": "INVALID_CLOCKS"},
            {**good, "schema": "untrusted"},
        ]
        for value in invalid:
            with self.subTest(value=value["state"]):
                with self.assertRaises(ValueError):
                    store.record(self.path, value, post_scan_utc=POST,
                                 ingest_returned_utc=INGEST)
        self.assertEqual(store.summary(self.path)["state"], "not_collected")
        with self.assertRaises(ValueError):
            store.record(self.path, good, post_scan_utc=POST.replace(tzinfo=None),
                         ingest_returned_utc=INGEST)

    def test_max_256_and_read_only_summary_without_mutation(self):
        value = self.measure()
        for _ in range(270):
            store.record(self.path, value, post_scan_utc=POST,
                         ingest_returned_utc=INGEST)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM remura_h1_paired").fetchone()[0], 256)
        self.assertEqual(store.summary(self.path)["samples"], 256)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE remura_h1_paired SET stale_to_ready=99 WHERE id=("
                       "SELECT MAX(id) FROM remura_h1_paired)")
        self.assertEqual(store.summary(self.path)["state"], "invalid_data")

    def test_malformed_full_snapshot_and_missing_db_fail_closed(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE squalincome_last_scan SET summary=? WHERE id=1",
                       ("{" + "X" * 70000,))
        self.assertIsNone(store.load_full_scan(self.path))
        unknown = self.path.with_name("absent.sqlite3")
        self.assertIsNone(store.load_full_scan(unknown))
        self.assertEqual(store.summary(unknown)["state"], "not_collected")
        self.assertFalse(unknown.exists())

    def test_default_off_and_requires_post_ingest_flag(self):
        self.assertFalse(server.h1_paired_enabled({}))
        partial = enabled()
        partial["REMURA_SQUALINCOME_AFTER_INGEST_ENABLED"] = "0"
        self.assertFalse(server.h1_paired_enabled(partial))
        self.assertTrue(server.h1_paired_enabled(enabled()))
        with patch.object(server, "observe_squalincome", return_value={
            "examined": 1, "baselines": 0, "newEvents": 0}) as scan:
            result = server.observe_updated_batch(
                self.path, {"EURUSD"}, env={**enabled(),
                    "REMURA_H1_PAIRED_ENABLED": "0"}, batch_completed=INGEST)
            self.assertEqual(result["examined"], 1)
            scan.assert_called_once_with(self.path, targets=("EURUSD",))
        self.assertEqual(store.summary(self.path)["state"], "not_collected")

    def test_post_ingest_reuses_one_scan_and_no_broker_calls(self):
        def captured(db_path, *, now, targets):
            self.assertEqual(now, POST)
            self.assertEqual(targets, ("EURUSD", "XAUUSD"))
            self.assertTrue(server._SQUALINCOME_SCAN_LOCK.locked())
            return {"examined": 2, "baselines": 0, "newEvents": 0,
                    "h1Frames": newer()}
        with patch.object(server, "utcnow", return_value=POST), \
             patch.object(server, "observe_squalincome_with_frames", side_effect=captured) as scan, \
             patch.object(server, "collect_once") as broker:
            result = server.observe_updated_batch(
                self.path, {"XAUUSD", "EURUSD"}, env=enabled(),
                batch_completed=INGEST)
        self.assertEqual(scan.call_count, 1)
        broker.assert_not_called()
        self.assertEqual(result["examined"], 2)
        self.assertNotIn("h1Frames", result)
        self.assertEqual(store.summary(self.path)["staleToReady"], 1)

    def test_comparison_error_never_breaks_observer(self):
        with patch.object(server, "utcnow", return_value=POST), \
             patch.object(server, "observe_squalincome_with_frames", return_value={
                 "examined": 1, "baselines": 0, "newEvents": 0,
                 "h1Frames": {"EURUSD": frame("2026-11-03T15:00:00Z")}}), \
             patch.object(server, "record_h1_pair", side_effect=sqlite3.OperationalError):
            result = server.observe_updated_batch(self.path, {"EURUSD"},
                 env=enabled(), batch_completed=INGEST)
        self.assertEqual(result["examined"], 1)
        self.assertNotIn("h1Frames", result)


if __name__ == "__main__":
    unittest.main()
