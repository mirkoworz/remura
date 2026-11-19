"""Synthetic-only tests for private read-only REMURA research census."""
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_research_census as census

UTC = timezone.utc
BASE = datetime(2026, 11, 2, 0, 0, tzinfo=UTC)
ASOF = "2026-11-04T10:00:00Z"


def _time(at):
    return at.isoformat().replace("+00:00", "Z")


def create_schema(db):
    db.executescript("""
        CREATE TABLE prices(symbol TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE cot_first_seen(dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT);
        CREATE TABLE squalincome_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          symbol TEXT,report_date TEXT,price_time TEXT,observed_at TEXT,
          cot_side INTEGER,h1_side INTEGER);
        CREATE TABLE squalincome_validation_cohorts(
          symbol TEXT,report_date TEXT,stage TEXT,observed_at TEXT,
          price_time TEXT,cot_side INTEGER,relationship TEXT,
          broker_symbol TEXT,entry_at TEXT,entry_open REAL);
        CREATE TABLE squalincome_validation_outcomes(
          symbol TEXT,report_date TEXT,stage TEXT,horizon_hours INTEGER,
          evaluated_at TEXT,directional_bps REAL,long_benchmark_bps REAL);
    """)


def create_sample(db):
    for sym, ds, code in (
            ("EURUSD", "tff", "099741"), ("XAUUSD", "disagg", "088691")):
        rows = []
        for idx in range(80):
            rows.append({
                "t": _time(BASE+timedelta(minutes=15*idx)),
                "o": 1.1, "h": 1.2, "l": 1.0, "c": 1.15,
                **({"v": 22} if sym == "EURUSD" else {})
            })
        doc = {"symbol": sym, "provider": "ctrader",
               "providerSymbol": "PRIVATE_FAKE_BROKER_X",
               "timeframes": {"M15": rows, "H1": [], "H4": []}}
        db.execute("INSERT INTO prices VALUES(?,?)", (sym, json.dumps(doc)))
        db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
                   (ds, code, "2026-10-20", "2026-10-25T20:00:00+00:00"))
        db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
                   (ds, code, "2026-10-27", "2026-10-30T20:00:00+00:00"))
    db.execute(
        "INSERT INTO squalincome_history(symbol,report_date,price_time,observed_at,cot_side,h1_side) "
        "VALUES(?,?,?,?,?,?)",
        ("EURUSD", "2026-10-27", "2026-11-02T09:00:00+00:00",
         "2026-11-02T09:01:00+00:00", 1, 1))
    db.execute(
        "INSERT INTO squalincome_validation_cohorts VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("EURUSD", "2026-10-27", "observation",
         "2026-11-02T09:01:00+00:00", "2026-11-02T09:00:00+00:00",
         1, "aligned", "PRIVATE_FAKE_BROKER_X",
         "2026-11-02T09:15:00+00:00", 1.1))
    db.execute(
        "INSERT INTO squalincome_validation_outcomes VALUES(?,?,?,?,?,?,?)",
        ("EURUSD", "2026-10-27", "observation", 4,
         "2026-11-03T20:00:00+00:00", 8.0, 8.0))
    db.commit()


class ResearchCensusTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        create_schema(self.db)
        create_sample(self.db)

    def tearDown(self):
        self.db.close()

    def test_asof_cohort_census_is_aggregate_and_not_trade_claim(self):
        result = census.audit_connection(self.db, as_of=ASOF)
        eur = result["markets"]["EURUSD"]
        self.assertEqual(eur["initialCohortsPersisted"], 1)
        self.assertEqual(eur["authenticFirstObservations"], 1)
        self.assertEqual(eur["contextCohortsPossiblyUsable"], 1)
        self.assertEqual(eur["archivedM15"]["withVolume"], 80)
        self.assertEqual(result["markets"]["XAUUSD"]["archivedM15"]["withoutVolume"], 80)
        h4 = next(x for x in eur["historicalOutcomes"] if x["hours"] == 4)
        self.assertEqual(h4["recordedOutcomeRows"], 1)
        self.assertEqual(h4["pointInTimeEligible"], 1)
        self.assertEqual(h4["cotWeeksEligible"], 1)
        self.assertEqual(h4["sampleGate"], "INSUFFICIENT")
        self.assertEqual(result["outcomeRowsExamined"], 1)
        self.assertEqual(result["outcomeLineageExclusions"]["paired_valid"], 1)
        self.assertFalse(result["actualTradingEdgeEstablished"])
        self.assertFalse(result["cvdHistoryAvailable"])
        self.assertFalse(result["notificationsEnabled"])
        self.assertEqual(result["brokerCalls"], 0)
        sanitized = json.dumps(result)
        self.assertNotIn("PRIVATE_FAKE_BROKER_X", sanitized)
        self.assertNotIn("2026-11-02T09:01", sanitized)
        self.assertNotIn("1.15", sanitized)
        self.assertNotIn("8.0", sanitized)

    def test_missing_previous_cot_excludes_both_context_and_outcome(self):
        self.db.execute(
            "UPDATE cot_first_seen SET first_seen_at=? WHERE report_date=?",
            ("2026-11-04T12:00:00+00:00", "2026-10-20"))
        result = census.audit_connection(self.db, as_of=ASOF)
        eur = result["markets"]["EURUSD"]
        self.assertEqual(eur["contextCohortsPossiblyUsable"], 0)
        self.assertEqual(eur["contextExclusionCounts"]["cot_previous_week_not_known"], 1)
        self.assertEqual(eur["historicalOutcomes"][1]["pointInTimeEligible"], 0)
        self.assertEqual(result["outcomeLineageExclusions"]["cot_previous_week_not_known"], 1)

    def test_not_yet_evaluated_event_does_not_count_as_eligible(self):
        self.db.execute(
            "UPDATE squalincome_validation_outcomes SET evaluated_at=?",
            ("2026-11-06T20:00:00+00:00",))
        result = census.audit_connection(self.db, as_of=ASOF)
        self.assertEqual(result["markets"]["EURUSD"]["historicalOutcomes"][1]["recordedOutcomeRows"], 1)
        self.assertEqual(result["markets"]["EURUSD"]["historicalOutcomes"][1]["pointInTimeEligible"], 0)

    def test_unavailable_tables_are_explicit_and_not_fake_zero_edge(self):
        with sqlite3.connect(":memory:") as empty:
            report = census.audit_connection(empty, as_of=ASOF)
            self.assertEqual(len(report["missingValidationTables"]), 3)
            self.assertEqual(report["markets"]["EURUSD"]["historicalOutcomes"][1]["pointInTimeEligible"], 0)
            self.assertFalse(report["actualTradingEdgeEstablished"])

    def test_read_only_db_file_does_not_modify_bytes_or_create_wal(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"sensitive-PRIVATE-DB.sqlite"
            with sqlite3.connect(path) as conn:
                create_schema(conn)
                create_sample(conn)
            before = path.read_bytes()
            out = census.audit_path(path, as_of=ASOF)
            self.assertEqual(out["markets"]["EURUSD"]["initialCohortsPersisted"], 1)
            self.assertEqual(before, path.read_bytes())
            self.assertFalse(path.with_name(path.name+"-wal").exists())
            self.assertNotIn(str(path), json.dumps(out))

    def test_cli_fail_closed_does_not_print_private_path(self):
        secret = "/do/not/print/PRIVATE_SENSITIVE/sqlite.db"
        buf = io.StringIO()
        with patch.dict("os.environ", {"REMURA_RESEARCH_DB_PATH": secret}):
            with contextlib.redirect_stdout(buf):
                self.assertEqual(census.main(), 1)
        self.assertIn("NON_COMPLETATO", buf.getvalue())
        self.assertNotIn(secret, buf.getvalue())

    def test_future_utc_and_invalid_timezone_disallowed(self):
        with self.assertRaises(ValueError):
            census.audit_connection(self.db, as_of="2026-11-04T10:00:00")
        with self.assertRaises(ValueError):
            census.audit_connection(self.db, as_of="2026-11-04T11:00:00+01:00")

    def test_memory_bound_blocks_abnormally_large_archives(self):
        with patch.object(census, "MAX_ROWS", 0):
            with self.assertRaises(ValueError):
                census.audit_connection(self.db, as_of=ASOF)


if __name__ == "__main__":
    unittest.main()
