"""REMURA v1.46: regression tests for paired market research, no live broker."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import market_validation
import dual24_validation
import statistical_validation
import private_server
from price_store import connect

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,4,15,0,tzinfo=UTC)


def when(week):
    return dt.datetime.fromisoformat(week).replace(tzinfo=UTC)+dt.timedelta(days=1,hours=10)


class MarketAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"private"/"remura-prices.sqlite3"
        db=connect(self.path)
        statistical_validation.ensure_tables(db)
        dual24_validation.ensure_tables(db)
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def add(self, symbol, week, relation, results=("calendar24","trading96"), stage="observation",
            direction=12., evaluated=None, exit_offset=25, entry=None):
        start=entry or when(week)
        finish=start+dt.timedelta(hours=exit_offset)
        assessed=evaluated or finish+dt.timedelta(minutes=15)
        side=1 if relation=="aligned" else -1
        db=connect(self.path)
        with db:
            db.execute(
                "INSERT OR IGNORE INTO squalincome_validation_cohorts "
                "(symbol,report_date,observed_at,price_time,cot_side,relationship,"
                "stage,broker_symbol,entry_at,entry_open) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (symbol,week,(start-dt.timedelta(minutes=5)).isoformat(),
                 (start-dt.timedelta(minutes=15)).isoformat(),side,relation,stage,
                 "HIDDEN-BROKER-ID",start.isoformat(),1.2))
            for metric in results:
                db.execute(
                    "INSERT OR IGNORE INTO squalincome_dual24_outcomes "
                    "(symbol,report_date,stage,metric,entry_at,exit_at,evaluated_at,"
                    "entry_open,exit_open,calendar_minutes,closed_m15,verified_pauses,"
                    "exit_delay_minutes,directional_bps,long_benchmark_bps,"
                    "favorable_bps,adverse_bps) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (symbol,week,stage,metric,start.isoformat(),finish.isoformat(),
                     assessed.isoformat(),1.2,1.21,1500,96,1,0,direction,
                     direction*.7,40.,-15.))
        db.close()

    def fixture(self):
        self.add("XAUUSD","2026-10-20","aligned",direction=20)
        self.add("EURUSD","2026-10-20","divergent",direction=-10)
        self.add("XAUUSD","2026-10-27","aligned",direction=30)
        self.add("GBPUSD","2026-10-20","divergent",results=("calendar24",))
        self.add("USDJPY","2026-10-20","aligned",stage="technical_confirmation",direction=1000)

    def test_pairs_only_and_two_distinct_weeks(self):
        self.fixture()
        result=market_validation.market_audit_status(self.path,NOW)
        self.assertEqual(result["mode"],"research_only")
        self.assertEqual(result["total"]["cohortsMatured"],4)
        self.assertEqual(result["total"]["pairedSamples"],3)
        self.assertEqual(result["total"]["unpairedMatured"],1)
        self.assertEqual(result["total"]["reportWeeksPaired"],2)
        self.assertEqual(result["total"]["calendar24"]["samples"],3)
        self.assertEqual(result["total"]["trading96"]["samples"],3)
        market={r["symbol"]:r for r in result["markets"]}
        self.assertEqual(market["XAUUSD"]["pairedSamples"],2)
        self.assertEqual(market["XAUUSD"]["reportWeeksPaired"],2)
        self.assertEqual(market["EURUSD"]["pairedSamples"],1)
        self.assertEqual(market["GBPUSD"]["pairedSamples"],0)
        self.assertEqual(market["GBPUSD"]["unpairedMatured"],1)
        self.assertNotIn("USDJPY",market)
        relation={r["relationship"]:r for r in result["relationships"]}
        self.assertEqual(relation["aligned"]["pairedSamples"],2)
        self.assertEqual(relation["divergent"]["pairedSamples"],1)
        self.assertEqual(result["total"]["deltaTradingMinusCalendarBps"],0)
        self.assertEqual(result["total"]["calendar24"]["verdict"],"Campione insufficiente")
        self.assertNotIn("HIDDEN-BROKER-ID",json.dumps(result))
        self.assertNotIn("entry_open",json.dumps(result))
        self.assertNotIn("exit_open",json.dumps(result))
        self.assertNotIn("2026-10-21T",json.dumps(result))

    def test_only_a_pair_not_single_horizon_changes_aggregates(self):
        self.add("XAGUSD","2026-10-20","aligned",results=("calendar24",),direction=5000)
        result=market_validation.market_audit_status(self.path,NOW)
        self.assertEqual(result["total"]["pairedSamples"],0)
        self.assertEqual(result["total"]["unpairedMatured"],1)
        self.assertEqual(result["total"]["calendar24"]["samples"],0)
        self.assertIsNone(result["total"]["deltaTradingMinusCalendarBps"])

    def test_as_of_never_exposes_future_evaluation_or_exit(self):
        self.add("XAUUSD","2026-10-27","aligned")
        early=when("2026-10-27")+dt.timedelta(hours=25)
        status=market_validation.market_audit_status(self.path,early)
        self.assertEqual(status["total"]["pairedSamples"],0)
        self.assertEqual(status["total"]["cohortsMatured"],1)
        self.assertEqual(market_validation.market_audit_status(self.path,NOW)["total"]["pairedSamples"],1)
        # Even an artificially early evaluated_at must not reveal an unclosed exit M15.
        db=connect(self.path)
        with db:
            db.execute("UPDATE squalincome_dual24_outcomes SET evaluated_at=?",
                       ((when("2026-10-27")+dt.timedelta(hours=25)).isoformat(),))
        db.close()
        late=market_validation.market_audit_status(self.path,NOW)
        self.assertEqual(late["total"]["pairedSamples"],0)

    def test_stage_overlap_not_independent(self):
        self.add("XAUUSD","2026-10-20","aligned")
        self.add("XAUUSD","2026-10-20","aligned",stage="qualified_event",direction=9000)
        value=market_validation.market_audit_status(self.path,NOW)
        self.assertEqual(value["total"]["pairedSamples"],1)

    def test_http_private_endpoint_no_cache_or_secrets(self):
        self.fixture()
        server=ThreadingHTTPServer(("127.0.0.1",0),private_server.http_handler(self.path))
        thread=Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.object(market_validation,"utcnow",return_value=NOW):
                with urlopen("http://127.0.0.1:"+str(server.server_port)+
                             "/private-api/signals/dual24/markets",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                    body=json.load(response)
            self.assertEqual(body["schema"],"remura-market-audit-v1")
            self.assertEqual(body["total"]["pairedSamples"],3)
            self.assertNotIn("HIDDEN-BROKER-ID",json.dumps(body))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_read_only_db_missing_does_not_create_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"missing.sqlite3"
            with self.assertRaises(FileNotFoundError):
                market_validation.market_audit_status(p,NOW)
            self.assertFalse(p.exists())


if __name__=="__main__":
    unittest.main()
