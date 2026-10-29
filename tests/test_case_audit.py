"""REMURA v1.47: individual evidence facts, shared old cohort rules and privacy."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import case_audit
import market_validation
import statistical_validation
import dual24_validation
import private_server
from price_store import connect

UTC=dt.timezone.utc
NOW=dt.datetime(2026,12,15,15,0,tzinfo=UTC)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"private"/"remura-prices.sqlite3"
        db=connect(self.path)
        statistical_validation.ensure_tables(db)
        dual24_validation.ensure_tables(db)
        db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def add(self,symbol,week,relation,side,calendar,negotiated=None,
            stage="observation",evaluated=None):
        start=dt.datetime.fromisoformat(week).replace(tzinfo=UTC)+dt.timedelta(days=1,hours=10)
        finish=start+dt.timedelta(hours=25)
        assessed=evaluated if evaluated is not None else finish+dt.timedelta(minutes=15)
        db=connect(self.path)
        with db:
            db.execute(
                "INSERT OR IGNORE INTO squalincome_validation_cohorts "
                "(symbol,report_date,observed_at,price_time,cot_side,relationship,"
                "stage,broker_symbol,entry_at,entry_open) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (symbol,week,(start-dt.timedelta(minutes=5)).isoformat(),
                 (start-dt.timedelta(minutes=15)).isoformat(),side,relation,stage,
                 "SECRET_BROKER_ID",start.isoformat(),1.2))
            for metric,direction in (("calendar24",calendar),("trading96",negotiated)):
                if direction is None:
                    continue
                db.execute(
                    "INSERT OR IGNORE INTO squalincome_dual24_outcomes "
                    "(symbol,report_date,stage,metric,entry_at,exit_at,evaluated_at,"
                    "entry_open,exit_open,calendar_minutes,closed_m15,verified_pauses,"
                    "exit_delay_minutes,directional_bps,long_benchmark_bps,"
                    "favorable_bps,adverse_bps) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (symbol,week,stage,metric,start.isoformat(),finish.isoformat(),
                     assessed.isoformat(),1.2,1.21,1500,96,1,0,direction,
                     -direction if side==-1 else direction,200.,-200.))
        db.close()

    def test_fact_register_explains_short_cot_long_price_without_calling_it_a_trade(self):
        self.add("XAUUSD","2026-10-20","aligned",-1,-126.18,-136.57)
        result=case_audit.case_audit_status(self.path,NOW)
        self.assertEqual(result["pairedCasesShown"],1)
        record=result["cases"][0]
        self.assertEqual(record["symbol"],"XAUUSD")
        self.assertEqual(record["cotSide"],"short")
        self.assertEqual(record["initialRelationship"],"aligned")
        self.assertEqual(record["cotWeek"],"2026-10-20")
        self.assertEqual(record["calendar24"]["directionalBps"],-126.18)
        self.assertEqual(record["calendar24"]["benchmarkLongBps"],126.18)
        self.assertFalse(record["calendar24"]["directionHit"])
        self.assertEqual(record["deltaTradingMinusCalendarBps"],-10.39)
        self.assertEqual(result["weekly"][0]["pairedSamples"],1)
        self.assertEqual(result["weekly"][0]["aligned"]["negativeOrFlatCalendar"],1)
        text=json.dumps(result)
        for token in ["SECRET_BROKER_ID","entry_open","exit_open","entry_at","evaluated_at"]:
            self.assertNotIn(token,text)

    def test_same_paired_universe_as_v146_and_no_stage_overlap(self):
        self.add("EURUSD","2026-10-20","divergent",1,25,30)
        self.add("XAUUSD","2026-10-20","aligned",-1,-20,-30)
        self.add("XAGUSD","2026-10-20","divergent",1,55,None)
        self.add("USDJPY","2026-10-20","divergent",1,999,999,stage="technical_confirmation")
        snapshot=case_audit.case_audit_status(self.path,NOW)
        original=market_validation.market_audit_status(self.path,NOW)
        self.assertEqual(snapshot["pairedCasesShown"],original["total"]["pairedSamples"])
        self.assertEqual(snapshot["pairedCasesShown"],2)
        self.assertEqual(snapshot["caseCountByRelationship"],{"aligned":1,"divergent":1})
        self.assertEqual(snapshot["weekly"][0]["pairedSamples"],2)
        self.assertEqual(snapshot["weekly"][0]["maturedCohorts"],3)
        self.assertEqual(snapshot["weekly"][0]["divergent"]["positiveCalendar"],1)
        self.assertEqual(snapshot["weekly"][0]["divergent"]["meanCalendarBps"],25)

    def test_future_outcomes_never_included_as_of(self):
        self.add("XAUUSD","2026-10-20","divergent",1,20,21)
        start=dt.datetime(2026,10,21,10,tzinfo=UTC)
        too_early=start+dt.timedelta(hours=25)
        result=case_audit.case_audit_status(self.path,too_early)
        self.assertEqual(result["pairedCasesShown"],0)
        self.assertEqual(result["weekly"][0]["pairedSamples"],0)
        self.assertEqual(case_audit.case_audit_status(self.path,NOW)["pairedCasesShown"],1)

    def test_last_12_reference_weeks_not_performance_selected(self):
        first=dt.date(2026,6,2)
        for i in range(14):
            day=(first+dt.timedelta(weeks=i)).isoformat()
            self.add("EURUSD",day,"divergent",1,1 if i%2 else -1,3)
        result=case_audit.case_audit_status(self.path,NOW)
        self.assertEqual(result["totalEligibleWeeks"],14)
        self.assertEqual(result["weeksShown"],12)
        self.assertEqual(result["pairedCasesShown"],12)
        self.assertEqual(result["weekly"][0]["cotWeek"],(first+dt.timedelta(weeks=13)).isoformat())
        self.assertNotIn(first.isoformat(),{x["cotWeek"] for x in result["cases"]})
        self.assertEqual(len({x["cotWeek"] for x in result["cases"]}),12)

    def test_private_endpoint_and_query_only_no_price_or_broker(self):
        self.add("XAUUSD","2026-10-20","divergent",-1,20,21)
        server=ThreadingHTTPServer(("127.0.0.1",0),private_server.http_handler(self.path))
        worker=Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            with patch.object(case_audit,"utcnow",return_value=NOW):
                with urlopen("http://127.0.0.1:"+str(server.server_port)+
                             "/private-api/signals/dual24/cases",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                    payload=json.load(response)
            self.assertEqual(payload["schema"],"remura-case-audit-v1")
            self.assertEqual(payload["pairedCasesShown"],1)
            self.assertNotIn("SECRET_BROKER_ID",json.dumps(payload))
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_missing_db_not_created_by_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"nonexistent.db"
            with self.assertRaises(FileNotFoundError):
                case_audit.case_audit_status(p,NOW)
            self.assertFalse(p.exists())


if __name__=="__main__":
    unittest.main()
