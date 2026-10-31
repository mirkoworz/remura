"""Offline tests for REMURA's strict read-only SQLite research adapter."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shark_sqlite_lab as lab

UTC = dt.timezone.utc
START = dt.datetime(2026, 10, 26, 8, 0, tzinfo=UTC)


def sample(n=120):
    result = []
    for i in range(n):
        start = START + dt.timedelta(minutes=15 * i)
        op = 1.10 + i * 0.0001
        result.append({"t": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "o": op, "h": op + 0.0002,
                       "l": op - 0.0001, "c": op + 0.0001})
    return result


def as_of(rows):
    return (dt.datetime.fromisoformat(rows[-1]["t"].replace("Z", "+00:00"))
            + dt.timedelta(minutes=15)).isoformat()


class SharkSQLiteLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbpath = Path(self.tmp.name) / "private.sqlite3"
        self.rows = sample()
        self._init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def _init_db(self, *, source="ctrader", broker="EURUSD",
                 document_symbol="EURUSD", provider="ctrader", rows=None):
        rows = self.rows if rows is None else rows
        doc = {"symbol": document_symbol, "provider": provider,
               "providerSymbol": broker, "lastComplete": rows[-1]["t"],
               "timeframes": {"M15": rows}}
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE IF NOT EXISTS prices "
                       "(symbol TEXT PRIMARY KEY,source TEXT,broker_symbol TEXT,payload TEXT)")
            db.execute("INSERT OR REPLACE INTO prices VALUES(?,?,?,?)",
                       ("EURUSD", source, broker, json.dumps(doc)))

    def _analyze(self, **opts):
        return lab.analyze_database(self.dbpath, "EURUSD", as_of=as_of(self.rows),
                                    round_trip_cost_bps=1.8, **opts)

    def test_existing_archive_no_db_mutation_or_raw_leakage(self):
        before = hashlib.sha256(self.dbpath.read_bytes()).digest()
        result = self._analyze()
        after = hashlib.sha256(self.dbpath.read_bytes()).digest()
        self.assertEqual(before, after)
        self.assertEqual(result["source"], "private_sqlite_readonly")
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["observedBars"], len(self.rows))
        self.assertEqual(result["archiveQuality"]["gapsDetected"], 0)
        self.assertEqual(result["archiveQuality"]["longestContiguousM15"], len(self.rows))
        self.assertEqual(result["archiveQuality"]["historyCoverage"], "limited")
        self.assertGreater(result["all"]["trades"], 0)
        self.assertEqual(result["all"]["evidence"], "insufficient")
        self.assertNotIn("providerSymbol", result)
        self.assertNotIn("timeframes", result)
        self.assertNotIn(str(self.dbpath), json.dumps(result))

    def test_missing_db_never_created(self):
        missing = Path(self.tmp.name) / "absent.sqlite3"
        with self.assertRaisesRegex(ValueError, "database_unavailable"):
            lab.load_price_document(missing, "EURUSD")
        self.assertFalse(missing.exists())

    def test_unlisted_market_and_missing_market_fails(self):
        with self.assertRaisesRegex(ValueError, "symbol_not_supported"):
            lab.load_price_document(self.dbpath, "EVIL")
        with self.assertRaisesRegex(ValueError, "symbol_not_archived"):
            lab.load_price_document(self.dbpath, "GBPUSD")

    def test_wrong_source_broker_or_document_symbol_rejected(self):
        self._init_db(source="other")
        with self.assertRaisesRegex(ValueError, "unverified_ctrader_payload"):
            self._analyze()
        self._init_db(source="ctrader", broker="BROKER")
        # Broker value and stored document still match: valid verified source.
        self.assertEqual(self._analyze()["symbol"], "EURUSD")
        self._init_db(document_symbol="GBPUSD")
        with self.assertRaisesRegex(ValueError, "source_or_broker_mismatch"):
            self._analyze()
        self._init_db(provider="external")
        with self.assertRaisesRegex(ValueError, "source_or_broker_mismatch"):
            self._analyze()

    def test_inconsistent_last_complete_rejected(self):
        with sqlite3.connect(self.dbpath) as db:
            doc = json.loads(db.execute("SELECT payload FROM prices").fetchone()[0])
            doc["lastComplete"] = doc["timeframes"]["M15"][0]["t"]
            db.execute("UPDATE prices SET payload=?", (json.dumps(doc),))
        with self.assertRaisesRegex(ValueError, "last_complete_mismatch"):
            self._analyze()

    def test_stale_market_is_research_only_not_a_live_signal(self):
        result = lab.analyze_database(self.dbpath, "EURUSD",
            as_of="2026-12-01T00:00:00+00:00", round_trip_cost_bps=2.0)
        self.assertEqual(result["verdict"], "research_only_never_live_signal")

    def test_future_incomplete_bar_rejected(self):
        before_last = dt.datetime.fromisoformat(
            self.rows[-1]["t"].replace("Z", "+00:00")) + dt.timedelta(minutes=10)
        with self.assertRaisesRegex(ValueError, "incomplete_or_future_bar"):
            lab.analyze_database(self.dbpath, "EURUSD",
                as_of=before_last.isoformat(), round_trip_cost_bps=2.0)

    def test_broker_payload_with_m15_gap_not_filled(self):
        self.rows = self.rows[:40] + self.rows[41:]
        self._init_db()
        result = self._analyze()
        self.assertLess(result["all"]["trades"], 30)
        self.assertEqual(result["archiveQuality"]["gapsDetected"], 1)
        self.assertEqual(result["archiveQuality"]["largestGapMinutes"], 30)
        self.assertLess(result["archiveQuality"]["longestContiguousM15"], len(self.rows))
        self.assertEqual(result["verdict"], "research_only_never_live_signal")

    def test_no_source_mutations_sqlite_pragma_query_only(self):
        # Even a connect via SQLite read-only URI forbids writes.
        from urllib.parse import quote
        uri = "file:" + quote(str(self.dbpath.absolute()), safe="/") + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.execute("PRAGMA query_only=ON")
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DROP TABLE prices")


if __name__ == "__main__":
    unittest.main()
