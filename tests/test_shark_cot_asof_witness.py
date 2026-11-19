"""Synthetic-only tests for the prospective, non-live COT witness research."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from scripts import shark_cot_asof_witness as w

T0=datetime(2026,11,4,11,45,tzinfo=timezone.utc)
OLD=(2026,10,20)
NEW=(2026,10,27)
REPORTS=(
    ("tff","099741"),  # EUR
    ("tff","097741"),  # JPY
    ("disagg","088691"), # XAU
)


def fixture():
    db=sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE cot_reports(
            dataset TEXT NOT NULL,code TEXT NOT NULL,
            report_date TEXT NOT NULL,oi REAL NOT NULL,
            first_long REAL NOT NULL,first_short REAL NOT NULL,
            second_long REAL NOT NULL,second_short REAL NOT NULL,
            PRIMARY KEY(dataset,code,report_date));
        CREATE TABLE cot_first_seen(
            dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT,
            PRIMARY KEY(dataset,code,report_date));
    """)
    for kind,code in REPORTS:
        for y,m,d in (OLD,NEW):
            week=f"{y:04d}-{m:02d}-{d:02d}"
            db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                       (kind,code,week,1000.0,100.0,90.0,120.0,110.0))
    db.commit()
    w.ensure_schema(db)
    return db


def available(db,time=None):
    at=T0+timedelta(minutes=1) if time is None else time
    return w.readiness(db,as_of=at.isoformat().replace("+00:00","Z"))


class CotWitnessTests(unittest.TestCase):
    def setUp(self):
        self.db=fixture()

    def tearDown(self):
        self.db.close()

    def test_catalog_matches_34_live_markets_not_all_possible_crosses(self):
        self.assertEqual(len(w.CATALOG),34)
        self.assertIn("EURJPY",w.CATALOG)
        self.assertIn("NAS100",w.CATALOG)
        self.assertNotIn("GER30",w.CATALOG)
        self.assertNotIn("USDEUR",w.CATALOG)

    def test_local_existing_legacy_reports_are_witnessed_only_from_now(self):
        before=self.db.execute("SELECT count(*) FROM cot_first_seen").fetchone()[0]
        self.assertEqual(before,0)
        self.assertEqual(available(self.db)["marketsWithTwoWeeksAttested"],0)
        status=w.witness(self.db,clock=T0)
        self.assertEqual(status["sourceValuesPresent"],6)
        self.assertEqual(status["newWitnessRows"],6)
        self.assertFalse(status["historicalFirstSeenModified"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM cot_first_seen").fetchone()[0],0)
        past=T0-timedelta(seconds=1)
        self.assertEqual(available(self.db,time=past)["marketsWithTwoWeeksAttested"],0)
        prospect=available(self.db)
        self.assertGreaterEqual(prospect["marketsWithTwoWeeksAttested"],3)
        self.assertEqual(prospect["status"],"PROSPECTIVE_SOURCE_ONLY")
        self.assertFalse(prospect["historicalEventsRetroactivelyQualified"])
        self.assertFalse(prospect["originalSignalValueDigestRecorded"])
        self.assertEqual(prospect["edge"],"NOT_ESTABLISHED")
        self.assertEqual(prospect["newBrokerCalls"],0)
        self.assertFalse(prospect["ordersEnabled"])
        self.assertNotIn("1000.0",json.dumps(prospect))

    def test_unmodified_values_are_idempotent_without_fake_freshness(self):
        w.witness(self.db,clock=T0)
        second=w.witness(self.db,clock=T0+timedelta(minutes=30))
        self.assertEqual(second["newWitnessRows"],0)
        self.assertEqual(second["estimatedTotalRows"],6)
        historical=self.db.execute(
            "SELECT count(*) FROM research_cot_asof_attestations "
            "WHERE witnessed_at LIKE ?",("2026-11-04T11:45%",)
        ).fetchone()[0]
        self.assertEqual(historical,6)

    def test_source_revision_blocks_until_new_current_value_witnessed(self):
        w.witness(self.db,clock=T0)
        self.db.execute(
            "UPDATE cot_reports SET first_long=123 WHERE code=? AND report_date=?",
            ("099741","2026-10-27"))
        not_ready=available(self.db)
        self.assertGreater(not_ready["blockerCounts"]["source_values_not_yet_witnessed"],0)
        self.assertGreaterEqual(not_ready["marketsWithTwoWeeksAttested"],1) # gold
        update_time=T0+timedelta(minutes=2)
        self.assertEqual(w.witness(self.db,clock=update_time)["newWitnessRows"],1)
        old_time=available(self.db,time=T0+timedelta(minutes=1))
        self.assertGreater(old_time["blockerCounts"]["source_values_not_yet_witnessed"],0)
        good=available(self.db,time=update_time+timedelta(seconds=1))
        self.assertGreater(good["marketsWithTwoWeeksAttested"],
                           not_ready["marketsWithTwoWeeksAttested"])

    def test_no_evidence_for_only_one_week_or_only_one_currency_leg(self):
        self.db.execute("DELETE FROM cot_reports WHERE report_date=?",("2026-10-20",))
        w.witness(self.db,clock=T0)
        self.assertEqual(available(self.db)["marketsWithTwoWeeksAttested"],0)
        self.assertGreater(available(self.db)["blockerCounts"]["no_two_consecutive_weeks"],0)

    def test_append_only_evidence_cannot_be_updated_or_deleted(self):
        w.witness(self.db,clock=T0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE research_cot_asof_attestations "
                            "SET witnessed_at='1999-01-01T00:00:00Z'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM research_cot_asof_attestations")
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM research_cot_asof_attestations").fetchone()[0],6)

    def test_bad_volume_or_future_report_fails_closed_and_rolls_back(self):
        self.db.execute(
            "UPDATE cot_reports SET oi=-1 WHERE code=? AND report_date=?",
            ("099741","2026-10-27"))
        with self.assertRaises(ValueError):
            w.witness(self.db,clock=T0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM research_cot_asof_attestations").fetchone()[0],0)

    def test_bad_utc_or_nonexistent_source_rejected(self):
        with self.assertRaises(ValueError):
            w.witness(self.db,clock=datetime(2026,11,4,11,45))
        with self.assertRaises(ValueError):
            w.readiness(self.db,as_of="2026-11-04T11:46:00")
        self.db.execute("DROP TABLE cot_reports")
        with self.assertRaises(ValueError):
            w.witness(self.db,clock=T0)

    def test_missing_evidence_table_fails_closed(self):
        self.db.execute("DROP TABLE research_cot_asof_attestations")
        with self.assertRaises(ValueError):
            w.readiness(self.db,as_of="2026-11-04T11:46:00Z")

    def test_strict_row_limits_prevent_unbounded_archive(self):
        from unittest.mock import patch
        with patch.object(w,"MAX_SOURCE_ROWS",1):
            with self.assertRaises(ValueError):
                w.witness(self.db,clock=T0)
        with patch.object(w,"MAX_EVIDENCE_ROWS",1):
            with self.assertRaises(ValueError):
                w.witness(self.db,clock=T0)


if __name__=="__main__":
    unittest.main()
