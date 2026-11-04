"""Track B private SQLite readiness: synthetic fixtures, no broker/network."""
import copy
import datetime as dt
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts import shark_data_readiness as r

BASE = dt.datetime(2026, 11, 2, 0, 0, tzinfo=dt.timezone.utc)


def iso(t):
    return t.isoformat()


def market(symbol="EURUSD", count=64, volume=True):
    rows = []
    for idx in range(count):
        row = {"t": iso(BASE+dt.timedelta(minutes=15*idx)),
               "o": 1.1, "h": 1.2, "l": 1.0, "c": 1.13}
        if volume:
            row["v"] = 100
        rows.append(row)
    return {"symbol": symbol, "provider": "ctrader",
            "providerSymbol": "SECRET_BROKER_IDENTIFIER",
            "timeframes": {"M15": rows, "H1": [], "H4": []}}


def setup(db):
    db.executescript("""
    CREATE TABLE prices(symbol TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE squalincome_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT,
        report_date TEXT,price_time TEXT,observed_at TEXT,cot_side INTEGER,
        h1_side INTEGER);
    CREATE TABLE cot_first_seen(dataset TEXT,code TEXT,report_date TEXT,
        first_seen_at TEXT);
    """)
    for sym in r.PILOT:
        db.execute("INSERT INTO prices VALUES (?,?)", (sym, json.dumps(market(sym))))


def observed(db, symbol="EURUSD", date="2026-10-27",
             price="2026-11-02T04:00:00+00:00",
             when="2026-11-02T04:03:00+00:00", cot_side=1, h1=1):
    db.execute("INSERT INTO squalincome_history "
               "(symbol,report_date,price_time,observed_at,cot_side,h1_side) "
               "VALUES (?,?,?,?,?,?)",
               (symbol,date,price,when,cot_side,h1))


def seen(db, symbol="EURUSD", date="2026-10-27",
         when="2026-10-30T20:00:00+00:00"):
    dataset, code = r.PILOT[symbol]
    db.execute("INSERT INTO cot_first_seen VALUES (?,?,?,?)",
               (dataset,code,date,when))


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        setup(self.db)

    def tearDown(self):
        self.db.close()

    def test_genuine_cot_observation_passes_price_context_only(self):
        observed(self.db)
        seen(self.db)
        saved = self.db.execute("SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0]
        out = r.audit_connection(self.db)
        self.assertEqual(out["markets"]["EURUSD"]["priceContextOnly"], 1)
        self.assertEqual(out["markets"]["EURUSD"]["archivedM15"]["withVolume"], 64)
        self.assertFalse(out["cvdDetectionHistoryRecorded"])
        self.assertFalse(out["eligibleForRealCvdWalkForward"])
        self.assertFalse(out["cotValueRevisionSnapshots"])
        self.assertEqual(out["brokerCalls"], 0)
        self.assertEqual(self.db.execute("SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0], saved)
        self.assertNotIn("SECRET_BROKER_IDENTIFIER", json.dumps(out))
        self.assertNotIn("1.13", json.dumps(out))

    def test_cot_first_seen_after_observation_blocks_lookahead(self):
        observed(self.db)
        seen(self.db, when="2026-11-03T20:00:00+00:00")
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["priceContextOnly"], 0)
        self.assertEqual(out["cohortReasons"]["cot_first_seen_after_observation"], 1)

    def test_cot_without_provenance_not_claimed_as_historically_known(self):
        observed(self.db)
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["cohortReasons"]["cot_first_seen_not_recorded"], 1)

    def test_ohlc_is_not_proof_of_volume_or_ingestion_time(self):
        observed(self.db)
        seen(self.db)
        source = market(volume=False)
        self.db.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                        (json.dumps(source),))
        out = r.audit_connection(self.db)
        self.assertEqual(out["markets"]["EURUSD"]["priceContextOnly"], 1)
        self.assertEqual(out["markets"]["EURUSD"]["archivedM15"]["withoutVolume"], 64)
        self.assertFalse(out["m15PerBarCollectionTimestamps"])
        self.assertFalse(out["markets"]["EURUSD"]["cvdAsObservedProof"])

    def test_dedupe_first_observation_per_week(self):
        observed(self.db)
        observed(self.db, when="2026-11-02T04:04:00+00:00")
        seen(self.db)
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["authenticFirstObservations"], 1)
        self.assertEqual(out["cohortReasons"]["same_cot_week_deduplicated"], 1)

    def test_missing_price_and_invalid_h1_excluded_without_fake_cohort(self):
        observed(self.db)
        seen(self.db)
        self.db.execute("DELETE FROM prices WHERE symbol='EURUSD'")
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["cohortReasons"]["observed_m15_not_retained"], 1)
        self.assertEqual(out["archivedM15"]["bars"], 0)
        observed(self.db, symbol="XAUUSD", h1=0)
        seen(self.db, symbol="XAUUSD")
        self.assertEqual(r.audit_connection(self.db)["markets"]["XAUUSD"]["priceContextOnly"],0)

    def test_invalid_price_doc_excludes_and_does_not_leak(self):
        observed(self.db)
        seen(self.db)
        doc = market()
        doc["timeframes"]["M15"][2]["h"] = -9
        self.db.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                        (json.dumps(doc),))
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["archivedM15"]["readable"], False)
        self.assertEqual(out["priceContextOnly"], 0)

    def test_timezone_naive_observation_cannot_pass(self):
        observed(self.db, when="2026-11-02T04:03:00")
        seen(self.db)
        out = r.audit_connection(self.db)["markets"]["EURUSD"]
        self.assertEqual(out["cohortReasons"]["observation_invalid_or_unverified"],1)

    def test_read_only_path_cannot_modify_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"private.sqlite"
            with sqlite3.connect(path) as db:
                setup(db)
                observed(db)
                seen(db)
                db.commit()
            before = path.read_bytes()
            out = r.audit_path(path)
            after = path.read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(out["markets"]["EURUSD"]["priceContextOnly"], 1)
            self.assertFalse(path.with_name(path.name+"-wal").exists())

    def test_missing_tables_returns_explicit_not_available(self):
        with sqlite3.connect(":memory:") as db:
            result = r.audit_connection(db)
            self.assertEqual(sum(result["tablesAvailable"].values()), 0)
            self.assertEqual(result["markets"]["XAUUSD"]["authenticFirstObservations"], 0)


if __name__ == "__main__":
    unittest.main()
