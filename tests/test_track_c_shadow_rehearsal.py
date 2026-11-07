"""Track C in-memory synthetic shadow rehearsal; no network or real market data."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import track_c_shadow_rehearsal as c


NOW = "2026-11-09T12:30:00Z"


def pair():
    return [
        {"symbol": sym, "observedAtUtc": NOW,
         "sources": {
             name: {"readAtUtc": NOW, "document": {"synthetic": sym + name}}
             for name in c.SOURCES}}
        for sym in c.PILOT
    ]


class TrackCRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.assertEqual(c.prepare(self.db), c.SCHEMA)

    def tearDown(self):
        self.db.close()

    def count(self):
        return self.db.execute(f"SELECT count(*) FROM {c.TABLE}").fetchone()[0]

    def test_dual_market_atomic_and_no_raw_document_persisted(self):
        out = c.rehearse(self.db, now_utc=NOW, pair=pair(), mode=c.MODE)
        self.assertEqual((out["receipts"], out["pilotMarkets"]), (6, 2))
        self.assertEqual(out["cvd"], "UNKNOWN")
        self.assertFalse(out["trackBOriginalSourceVerified"])
        self.assertFalse(out["outcomesObserved"])
        self.assertEqual(self.count(), 6)
        material = json.dumps(self.db.execute(
            f"SELECT * FROM {c.TABLE}").fetchall())
        self.assertNotIn("synthetic", material)
        self.assertNotIn("token", material)

    def test_retail_missing_is_unknown_not_negative(self):
        data = pair()
        del data[0]["sources"]["retail"]
        data[1]["sources"]["retail"] = None
        out = c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual((self.count(), out["missingRetail"]), (4, 2))

    def test_no_implicit_activation_or_schema(self):
        with self.assertRaisesRegex(ValueError, "explicit_offline_mode"):
            c.rehearse(self.db, now_utc=NOW, pair=pair())
        raw = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(ValueError, "explicit_rehearsal_schema"):
                c.rehearse(raw, now_utc=NOW, pair=pair(), mode=c.MODE)
        finally:
            raw.close()

    def test_never_touch_file_sqlite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "live-mimic.sqlite3"
            disk = sqlite3.connect(path)
            try:
                with self.assertRaisesRegex(ValueError, "only_single_in_memory"):
                    c.prepare(disk)
                with self.assertRaisesRegex(ValueError, "only_single_in_memory"):
                    c.rehearse(disk, now_utc=NOW, pair=pair(), mode=c.MODE)
            finally:
                disk.close()
            self.assertEqual(path.stat().st_size, 0)

    def test_future_and_retroactive_observations_rejected(self):
        for bad in ("2026-11-09T12:31:00Z", "2026-11-09T12:29:00Z"):
            data = pair()
            data[0]["observedAtUtc"] = bad
            with self.assertRaisesRegex(ValueError, "observation"):
                c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 0)

    def test_future_or_stale_source_is_rejected(self):
        for name, bad in (
            ("price", "2026-11-09T12:31:00Z"),
            ("price", "2026-11-09T10:00:00Z"),
            ("retail", "2026-11-09T11:00:00Z"),
            ("cot", "2026-10-20T00:00:00Z"),
        ):
            data = pair()
            data[1]["sources"][name]["readAtUtc"] = bad
            with self.assertRaisesRegex(ValueError, "future_or_stale_source"):
                c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 0)

    def test_missing_cot_or_price_and_wrong_market(self):
        for key in ("cot", "price"):
            data = pair()
            del data[0]["sources"][key]
            with self.assertRaises(ValueError):
                c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        data = pair()
        data[1]["symbol"] = "GBPUSD"
        with self.assertRaises(ValueError):
            c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 0)

    def test_second_market_failure_rolls_back_first(self):
        data = pair()
        # First market writes, second market hits an earlier receipt key.
        c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 6)
        with self.assertRaises(sqlite3.IntegrityError):
            c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 6)
        self.assertFalse(self.db.in_transaction)

    def test_trigger_protection(self):
        c.rehearse(self.db, now_utc=NOW, pair=pair(), mode=c.MODE)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(f"UPDATE {c.TABLE} SET source='price' WHERE id=1")
        self.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(f"DELETE FROM {c.TABLE} WHERE id=1")
        self.db.rollback()
        self.assertEqual(self.count(), 6)

    def test_cap_cannot_partially_commit_pair(self):
        self.db.executemany(
            f"INSERT INTO {c.TABLE}(symbol,observed_at,source,read_at,local_sha256)"
            " VALUES(?,?,?,?,?)",
            [("EURUSD", f"2026-11-07T00:{i:02d}:00Z", "price", NOW, "0" * 64)
             for i in range(c.MAX_ROWS - 5)]
        )
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "bounded_rehearsal_capacity"):
            c.rehearse(self.db, now_utc=NOW, pair=pair(), mode=c.MODE)
        self.assertEqual(self.count(), c.MAX_ROWS - 5)

    def test_no_nan_or_oversized_original(self):
        for value in (float("nan"), "X" * 70000):
            data = pair()
            data[1]["sources"]["retail"]["document"]["synthetic"] = value
            with self.assertRaisesRegex(ValueError, "uncanonicalizable|oversized"):
                c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        self.assertEqual(self.count(), 0)

    def test_reject_non_utc_and_extra_source(self):
        data = pair()
        data[0]["sources"]["extra"] = {"readAtUtc": NOW, "document": {"n": 1}}
        with self.assertRaisesRegex(ValueError, "unapproved_source"):
            c.rehearse(self.db, now_utc=NOW, pair=data, mode=c.MODE)
        with self.assertRaisesRegex(ValueError, "strict_utc"):
            c.rehearse(self.db, now_utc=NOW.replace("Z", "+00:00"),
                       pair=pair(), mode=c.MODE)
        self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main()
