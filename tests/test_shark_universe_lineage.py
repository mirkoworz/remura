"""Track B tests: CFTC point-in-time reports for all monitored market types.

Synthetic SQLite only. No cTrader requests, historical reconstruction,
external price data, broker IDs in output, or modifications to live database.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts import shark_universe_lineage as u

ASOF="2026-11-04T10:00:00Z"
COT_WEEK="2026-10-27"
OBSERVED="2026-11-02T09:01:00+00:00"
SEEN="2026-10-30T20:00:00+00:00"
PRIOR="2026-10-25T20:00:00+00:00"
SENSITIVE="SENSITIVE_BROKER_NAME_NOT_TO_LEAK"


def schema(db):
    db.executescript("""
    CREATE TABLE cot_first_seen(dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT);
    CREATE TABLE squalincome_validation_cohorts(
        symbol TEXT,report_date TEXT,stage TEXT,observed_at TEXT,
        price_time TEXT,cot_side INTEGER,relationship TEXT,
        broker_symbol TEXT,entry_at TEXT,entry_open REAL);
    CREATE TABLE squalincome_validation_outcomes(
        symbol TEXT,report_date TEXT,stage TEXT,horizon_hours INTEGER,
        evaluated_at TEXT,directional_bps REAL,long_benchmark_bps REAL);
    """)


def insert(db, symbol, *, add_legs=True, observed=OBSERVED,
           stage="observation", side=1, hours=4, stale_legs=()):
    spec=u.contracts(symbol)
    if spec and add_legs:
        for dataset,code in spec[1]:
            when="2026-11-04T20:00:00+00:00" if code in stale_legs else SEEN
            db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
                       (dataset,code,COT_WEEK,when))
            db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
                       (dataset,code,"2026-10-20",PRIOR))
    db.execute("INSERT INTO squalincome_validation_cohorts VALUES(?,?,?,?,?,?,?,?,?,?)",
               (symbol,COT_WEEK,stage,observed,
                "2026-11-02T09:00:00+00:00",side,
                "aligned",SENSITIVE,
                "2026-11-02T09:15:00+00:00",1.2))
    db.execute("INSERT INTO squalincome_validation_outcomes VALUES(?,?,?,?,?,?,?)",
               (symbol,COT_WEEK,stage,hours,
                "2026-11-03T20:00:00+00:00",float(side*5),5.0))


class MarketUniverseTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        schema(self.db)

    def tearDown(self):
        self.db.close()

    def test_production_catalog_has_direct_and_two_leg_fx(self):
        self.assertEqual(u.contracts("XAUUSD"),("direct_futures",(("disagg","088691"),)))
        self.assertEqual(u.contracts("EURUSD"),("fx_one_leg",(("tff","099741"),)))
        self.assertEqual(u.contracts("USDJPY"),("fx_one_leg",(("tff","097741"),)))
        self.assertEqual(u.contracts("EURJPY"),
                         ("fx_cross_two_legs",(("tff","099741"),("tff","097741"))))
        self.assertEqual(u.contracts("NAS100"),("direct_futures",(("tff","209742"),)))
        self.assertIsNone(u.contracts("GER30"))
        self.assertIsNone(u.contracts("EURABC"))
        self.assertIsNone(u.contracts("EURxxx"))
        self.assertIsNone(u.contracts("USDUSD"))

    def test_all_monitored_families_are_in_scope_and_no_pnl_claimed(self):
        for symbol in ("EURUSD","EURJPY","XAUUSD"):
            insert(self.db,symbol)
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["observationStageOutcomeRowsExamined"],3)
        self.assertEqual(result["reasons"]["eligible_time_provenance_only"],3)
        self.assertEqual(result["eligibleMarketsByFamily"],{
            "fx_one_leg":1,"fx_cross_two_legs":1,"direct_futures":1})
        self.assertEqual(result["eligibleMarkets"]["EURJPY"]["byHorizon"][1]["eligibleOutcomes"],1)
        self.assertEqual(result["eligibleMarkets"]["EURJPY"]["byHorizon"][1]["cotWeeks"],1)
        self.assertEqual(result["eligibleMarkets"]["EURJPY"]["byHorizon"][1]["sampleGate"],"INSUFFICIENT")
        self.assertFalse(result["historicCotValuesVersioned"])
        self.assertFalse(result["outOfSampleVerified"])
        self.assertEqual(result["edge"],"NOT_ESTABLISHED")
        self.assertNotIn(SENSITIVE,json.dumps(result))
        self.assertNotIn(OBSERVED,json.dumps(result))
        self.assertNotIn("1.2",json.dumps(result))

    def test_cross_requires_both_current_reports_acquired_in_time(self):
        insert(self.db,"EURJPY",stale_legs=("097741",))
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["reasons"]["current_report_first_seen_late"],1)
        self.assertFalse(result["eligibleMarkets"])

    def test_cross_requires_both_previous_reports_in_time(self):
        insert(self.db,"EURJPY")
        self.db.execute("UPDATE cot_first_seen SET first_seen_at=? "
                        "WHERE code=? AND report_date=?",
                        ("2026-11-04T20:00:00+00:00","097741","2026-10-20"))
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["reasons"]["previous_report_first_seen_late"],1)
        self.assertFalse(result["eligibleMarkets"])

    def test_missing_first_seen_is_not_backfilled(self):
        insert(self.db,"XAUUSD",add_legs=False)
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["reasons"]["current_report_not_recorded"],1)
        self.assertFalse(result["eligibleMarkets"])

    def test_known_unsupportable_markets_are_not_misclassified(self):
        insert(self.db,"GER30",add_legs=False)
        insert(self.db,"FOOUSD",add_legs=False)
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["reasons"]["not_in_live_cot_contract_catalog"],2)
        self.assertEqual(result["observationStageOutcomeRowsExamined"],2)
        self.assertFalse(result["eligibleMarkets"])

    def test_non_observation_stages_are_never_double_counted(self):
        insert(self.db,"EURUSD")
        insert(self.db,"EURUSD",stage="technical_confirmation")
        result=u.audit_connection(self.db,as_of=ASOF)
        self.assertEqual(result["observationStageOutcomeRowsExamined"],1)
        self.assertEqual(result["allStageOutcomeRows"],2)

    def test_no_future_outcome_or_naive_time(self):
        insert(self.db,"XAUUSD",observed="2026-11-02T09:01:00")
        self.assertEqual(u.audit_connection(self.db,as_of=ASOF)["reasons"]["invalid_cohort_or_outcome"],1)
        with self.assertRaises(ValueError):
            u.audit_connection(self.db,as_of="2026-11-04T10:00:00")

    def test_read_only_sqlite_snapshot_never_modifies_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"private-do-not-disclose.sqlite"
            with sqlite3.connect(path) as db:
                schema(db)
                insert(db,"EURJPY")
                db.commit()
            before=path.read_bytes()
            result=u.audit_path(path,as_of=ASOF)
            self.assertEqual(result["reasons"]["eligible_time_provenance_only"],1)
            self.assertEqual(before,path.read_bytes())
            self.assertFalse(path.with_name(path.name+"-wal").exists())
            self.assertNotIn(str(path),json.dumps(result))

    def test_missing_tables_unavailable(self):
        with sqlite3.connect(":memory:") as db:
            result=u.audit_connection(db,as_of=ASOF)
            self.assertEqual(result["status"],"UNAVAILABLE")
            self.assertEqual(len(result["missingTables"]),3)

    def test_archive_limits_fail_closed(self):
        insert(self.db,"EURUSD")
        from unittest.mock import patch
        with patch.object(u,"MAX_ROWS",0):
            with self.assertRaises(ValueError):
                u.audit_connection(self.db,as_of=ASOF)


if __name__=="__main__":
    unittest.main()
