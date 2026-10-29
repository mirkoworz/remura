"""REMURA v1.48: COT first-capture provenance and honest weekly evidence."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import cot_monitor
import dual24_validation
import statistical_validation
import weekly_quality
import private_server
from price_store import connect

UTC=dt.timezone.utc
NOW=dt.datetime(2026,10,29,13,0,tzinfo=UTC)
WEEK="2026-10-20"
PRIOR="2026-10-13"
OBSERVED="2026-10-26T08:00:00+00:00"
CAPTURED="2026-10-24T18:00:00+00:00"
LATER="2026-10-27T18:00:00+00:00"


def make_feed(dataset, date=WEEK):
    spec=cot_monitor.DATASETS[dataset]
    return [{"report_date_as_yyyy_mm_dd":date+"T00:00:00",
             "cftc_contract_market_code":code,
             "open_interest_all":"1000",
             **{field:"50" for field in spec["keys"]}}
            for code in spec["codes"]]


class TestWeeklyQuality(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"private"/"remura-prices.sqlite3"
        db=connect(self.path)
        statistical_validation.ensure_tables(db)
        dual24_validation.ensure_tables(db)
        cot_monitor.ensure_table(db)
        db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def add_case(self,symbol,relationship="divergent",side=1,week=WEEK,direction=25):
        begin=dt.datetime.fromisoformat(week).replace(tzinfo=UTC)+dt.timedelta(days=6,hours=8)
        observation=begin-dt.timedelta(minutes=15)
        finish=begin+dt.timedelta(hours=25)
        assessment=finish+dt.timedelta(minutes=15)
        db=connect(self.path)
        with db:
            db.execute(
                "INSERT INTO squalincome_validation_cohorts "
                "(symbol,report_date,observed_at,price_time,cot_side,relationship,"
                "stage,broker_symbol,entry_at,entry_open) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (symbol,week,observation.isoformat(),
                 (observation-dt.timedelta(minutes=15)).isoformat(),side,
                 relationship,"observation","HIDDEN_BROKER",begin.isoformat(),1.2))
            for metric in ("calendar24","trading96"):
                db.execute(
                    "INSERT INTO squalincome_dual24_outcomes "
                    "(symbol,report_date,stage,metric,entry_at,exit_at,evaluated_at,"
                    "entry_open,exit_open,calendar_minutes,closed_m15,verified_pauses,"
                    "exit_delay_minutes,directional_bps,long_benchmark_bps,"
                    "favorable_bps,adverse_bps) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (symbol,week,"observation",metric,begin.isoformat(),
                     finish.isoformat(),assessment.isoformat(),1.2,1.21,
                     1500,96,0,0,direction,direction*side,40,-10))
        db.close()

    def add_report(self,kind,code,week=WEEK,seen=CAPTURED):
        db=connect(self.path)
        with db:
            db.execute("INSERT OR REPLACE INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                (kind,code,week,1000,50,50,30,30))
            if seen is not None:
                db.execute("INSERT OR REPLACE INTO cot_first_seen VALUES(?,?,?,?)",
                           (kind,code,week,seen))
        db.close()

    def test_first_capture_write_once_repeated_sync_and_legacy_remains_unknown(self):
        # Existing v1.47 historical row must not be stamped as first captured.
        self.add_report("tff","099741",seen=None)
        first=dt.datetime(2026,10,24,18,0,tzinfo=UTC)
        later=dt.datetime(2026,10,26,18,0,tzinfo=UTC)
        feed=lambda dataset,now:make_feed(dataset)
        r=cot_monitor.collect_once(self.path,first,feed)
        self.assertEqual(r["errors"],{})
        cot_monitor.collect_once(self.path,later,feed)
        db=connect(self.path)
        try:
            self.assertIsNone(db.execute(
                "SELECT first_seen_at FROM cot_first_seen WHERE code='099741'"
            ).fetchone())
            self.assertEqual(db.execute(
                "SELECT first_seen_at FROM cot_first_seen WHERE code='084691'"
            ).fetchone()[0],first.isoformat())
            self.assertEqual(db.execute(
                "SELECT count(*) FROM cot_first_seen"
            ).fetchone()[0],13)
            self.assertEqual(db.execute("SELECT count(*) FROM cot_reports").fetchone()[0],14)
        finally:
            db.close()

    def test_weekly_reconciliation_and_exposure_overlap_are_descriptive(self):
        self.add_case("XAUUSD","aligned",-1,direction=-126.18)
        self.add_case("XAGUSD","divergent",1,direction=35)
        self.add_case("EURUSD","divergent",1,direction=10)
        for code in ("088691","084691"):
            for week in (WEEK,PRIOR):
                self.add_report("disagg",code,week)
        for week in (WEEK,PRIOR):
            self.add_report("tff","099741",week)
        report=weekly_quality.weekly_quality_status(self.path,NOW)
        self.assertEqual(report["casesAudited"],3)
        self.assertEqual(report["independentCotWeeksObserved"],1)
        self.assertEqual(report["weeksWithBothRelationships"],1)
        self.assertEqual(report["weeksDivergenceBetter"],1)
        self.assertEqual(report["quality"],"Campione insufficiente")
        self.assertEqual(report["captureCounts"]["recorded_before_observation"],3)
        week=report["weekly"][0]
        self.assertEqual(week["pairedSamples"],3)
        self.assertEqual(week["alignedSamples"],1)
        self.assertEqual(week["divergentSamples"],2)
        self.assertEqual(week["divergentMinusAlignedHitPp"],100)
        factors={x["factor"]:x["markets"] for x in week["sharedFactorWarnings"]}
        self.assertEqual(factors["USD"],3)
        self.assertEqual(factors["precious_metals"],2)
        self.assertNotIn("HIDDEN_BROKER",json.dumps(report))
        self.assertNotIn("first_seen_at",json.dumps(report))

    def test_legacy_unknown_never_invent_publication_or_access_time(self):
        self.add_case("XAUUSD")
        self.add_report("disagg","088691",WEEK,seen=None)
        self.add_report("disagg","088691",PRIOR,seen=None)
        result=weekly_quality.weekly_quality_status(self.path,NOW)
        self.assertEqual(result["captureCounts"]["unknown_legacy"],1)
        self.assertEqual(result["captureCounts"]["recorded_before_observation"],0)
        self.assertNotIn("officialPublishedAt",json.dumps(result))
        self.assertIn("NOT official publication",result["firstSeenMeaning"])

    def test_captured_after_observation_gets_priority_over_unknown(self):
        self.add_case("XAUUSD")
        self.add_report("disagg","088691",WEEK,seen=LATER)
        self.add_report("disagg","088691",PRIOR,seen=None)
        result=weekly_quality.weekly_quality_status(self.path,NOW)
        self.assertEqual(result["captureCounts"]["captured_after_observation"],1)

    def test_pair_requires_two_contracts_and_common_preceding_week(self):
        self.add_case("EURGBP")
        for date in (PRIOR,WEEK):
            self.add_report("tff","099741",date)
        self.add_report("tff","096742",WEEK)
        self.add_report("tff","096742","2026-10-06")
        r=weekly_quality.weekly_quality_status(self.path,NOW)
        self.assertEqual(r["captureCounts"]["missing_cot_reference"],1)
        self.add_report("tff","096742",PRIOR)
        r=weekly_quality.weekly_quality_status(self.path,NOW)
        self.assertEqual(r["captureCounts"]["recorded_before_observation"],1)

    def test_no_lookahead_future_exits_not_counted(self):
        self.add_case("XAUUSD")
        at=dt.datetime(2026,10,27,9,0,tzinfo=UTC)
        r=weekly_quality.weekly_quality_status(self.path,at)
        self.assertEqual(r["casesAudited"],0)
        self.assertEqual(r["independentCotWeeksObserved"],0)

    def test_private_http_and_missing_file_cannot_create_database(self):
        self.add_case("XAUUSD")
        server=ThreadingHTTPServer(("127.0.0.1",0),private_server.http_handler(self.path))
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.object(weekly_quality,"utcnow",return_value=NOW):
                with urlopen(
                    "http://127.0.0.1:"+str(server.server_port)+
                    "/private-api/signals/weekly-quality",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),
                                     "no-store, max-age=0")
                    payload=json.load(response)
            self.assertEqual(payload["schema"],"remura-weekly-quality-v1")
            self.assertEqual(payload["casesAudited"],1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        with tempfile.TemporaryDirectory() as d:
            missing=Path(d)/"missing.db"
            with self.assertRaises(FileNotFoundError):
                weekly_quality.weekly_quality_status(missing,NOW)
            self.assertFalse(missing.exists())


if __name__=="__main__":
    unittest.main()
