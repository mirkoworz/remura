"""Offline regression tests: no APIs, VPS, credentials, or production data."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import myfxbook_store as store


def row(t, pct=70):
    return {"t": t, "lPct": pct, "sPct": 100-pct,
            "lLots": 12.0, "sLots": 3.0, "lPos": 20, "sPos": 10}


class HistorySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / "private"
        self.public = self.root / "repository"
        self.times = [f"2026-10-30T{hour:02d}:00:00Z" for hour in range(4)]

    def save_history(self, root, rows):
        f = root / "history" / "EURUSD.json"
        store.atomic_json(f, store.history_document("EURUSD", rows))
        return f

    def test_repository_cannot_erase_or_override_private_points(self):
        f = self.save_history(self.private, [
            row(self.times[0]), row(self.times[1], 55), row(self.times[2])])
        self.save_history(self.public, [
            row(self.times[0]), row(self.times[1], 99), row(self.times[3])])
        changed = store.merge_repository(self.private, self.public)
        records = store.read_json(f)["records"]
        self.assertEqual(changed, 1)
        self.assertEqual(len(records), 4)
        self.assertEqual(records[1]["lPct"], 55)
        self.assertEqual(records[-1]["t"], self.times[3])
        self.assertEqual(store.merge_repository(self.private, self.public), 0)

    def test_public_older_does_not_replace_private_latest(self):
        newest = {"status":"ok", "updatedAt":self.times[3],
                  "symbols":{"EURUSD":row(self.times[3])}}
        older = {"status":"ok", "updatedAt":self.times[0],
                 "symbols":{"EURUSD":row(self.times[0])}}
        store.atomic_json(self.private / "latest.json", newest)
        store.atomic_json(self.public / "latest.json", older)
        self.save_history(self.public, [row(self.times[0])])
        store.merge_repository(self.private, self.public)
        self.assertEqual(store.read_json(self.private / "latest.json"), newest)

    def test_missing_latest_can_be_seeded(self):
        latest = {"status":"ok", "updatedAt":self.times[0],
                  "symbols":{"EURUSD":row(self.times[0])}}
        store.atomic_json(self.public / "latest.json", latest)
        self.save_history(self.public, [row(self.times[0])])
        store.merge_repository(self.private, self.public)
        self.assertEqual(store.read_json(self.private / "latest.json"), latest)

    def test_corrupt_private_blocks_sync_without_overwrite(self):
        f = self.save_history(self.private, [row(self.times[2])])
        f.write_text("{not json")
        other = self.private / "latest.json"
        store.atomic_json(other, {"status":"ok", "updatedAt":self.times[2], "symbols":{}})
        self.save_history(self.public, [row(self.times[0])])
        before = f.read_bytes()
        with self.assertRaises(ValueError):
            store.merge_repository(self.private, self.public)
        self.assertEqual(f.read_bytes(), before)
        self.assertTrue(store.read_json(other))

    def test_collector_appends_and_keeps_private_history(self):
        f = self.save_history(self.private, [row(self.times[0]), row(self.times[1])])
        count = store.update_collection(
            self.private, {"EURUSD":row(self.times[2]), "BTCJPY":row(self.times[2])},
            {"EURUSD"}, cutoff=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc),
            max_points=2250)
        self.assertEqual(count, 1)
        self.assertEqual(len(store.read_json(f)["records"]), 3)
        self.assertFalse((self.private / "history" / "BTCJPY.json").exists())

    def test_bad_existing_history_does_not_silently_reset(self):
        f = self.save_history(self.private, [row(self.times[0])])
        f.write_text("{broken")
        before = f.read_bytes()
        with self.assertRaises(ValueError):
            store.update_collection(
                self.private, {"EURUSD":row(self.times[1])}, {"EURUSD"},
                cutoff=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc),
                max_points=2250)
        self.assertEqual(f.read_bytes(), before)

    def test_atomic_failed_replace_preserves_original_file(self):
        f = self.save_history(self.private, [row(self.times[0])])
        before = f.read_bytes()
        with patch.object(store.os, "replace", side_effect=OSError("injected failure")):
            with self.assertRaises(OSError):
                store.atomic_json(f, store.history_document(
                    "EURUSD", [row(self.times[1])]))
        self.assertEqual(f.read_bytes(), before)
        self.assertEqual(len(list(f.parent.glob(".myfxbook-*.tmp"))), 0)

    def test_latest_saved_last_and_not_regressed(self):
        old = {"status":"ok", "updatedAt":self.times[2],
               "symbols":{"EURUSD":row(self.times[2])}}
        older = {"status":"ok", "updatedAt":self.times[1],
                 "symbols":{"EURUSD":row(self.times[1])}}
        store.atomic_json(self.private / "latest.json", old)
        kw = dict(cutoff=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc),
                  max_points=2250)
        store.update_collection(
            self.private, {"EURUSD":row(self.times[1])}, {"EURUSD"},
            latest=older, **kw)
        self.assertEqual(store.read_json(self.private / "latest.json"), old)
        new = {"status":"ok", "updatedAt":self.times[3],
               "symbols":{"EURUSD":row(self.times[3])}}
        store.update_collection(
            self.private, {"EURUSD":row(self.times[3])}, {"EURUSD"},
            latest=new, **kw)
        self.assertEqual(store.read_json(self.private / "latest.json"), new)

    def test_corrupt_history_aborts_before_latest_overwrite(self):
        doc = {"status":"ok", "updatedAt":self.times[0],
               "symbols":{"EURUSD":row(self.times[0])}}
        store.atomic_json(self.private / "latest.json", doc)
        self.save_history(self.private, [row(self.times[0])]).write_text("{broken")
        new = {"status":"ok", "updatedAt":self.times[1],
               "symbols":{"EURUSD":row(self.times[1])}}
        with self.assertRaises(ValueError):
            store.update_collection(
                self.private, {"EURUSD":row(self.times[1])}, {"EURUSD"},
                cutoff=dt.datetime(2026,10,1,tzinfo=dt.timezone.utc),
                max_points=2250, latest=new)
        self.assertEqual(store.read_json(self.private / "latest.json"), doc)


if __name__ == "__main__":
    unittest.main()
