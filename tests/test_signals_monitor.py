"""Offline tests of REMURA v1.33 observation-only monitor."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from price_feed import UTC
import signals_monitor as m
from price_store import connect

NOW=dt.datetime(2026,10,26,12,15,tzinfo=UTC)


class SignalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=Path(self.tmp.name)/"private"/"test.db"
    def tearDown(self):self.tmp.cleanup()

    def test_exactly_supported_markets_with_no_fabricated_cot_proxies(self):
        names=m.monitored_symbols()
        self.assertIn("EURUSD",names)
        self.assertIn("GBPNZD",names)
        self.assertIn("XAUUSD",names)
        self.assertIn("NAS100",names)
        self.assertIn("USOIL",names)
        for name in ("VIX","GER30","DXY","UKOIL"):
            self.assertNotIn(name,names)

    def test_direct_and_synthetic_fx_cot_use_same_report_dates(self):
        db=connect(self.db_path)
        try:
            from cot_monitor import ensure_table
            ensure_table(db)
            for date,eur,jpy in (("2026-10-13",100,60),("2026-10-20",155,45)):
                for code,p in (("099741",eur),("097741",jpy)):
                    db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                        ("tff",code,date,1000,90,40,p,10))
            db.commit()
            eurusd=m.cot_view(m.cot_series(db,"EURUSD"),"EURUSD",NOW)
            usdjpy=m.cot_view(m.cot_series(db,"USDJPY"),"USDJPY",NOW)
            eurjpy=m.cot_view(m.cot_series(db,"EURJPY"),"EURJPY",NOW)
            self.assertEqual(eurusd["side"],1)
            self.assertEqual(usdjpy["side"],1)
            self.assertEqual(eurjpy["side"],1)
            self.assertGreater(eurjpy["weekly"],eurusd["weekly"])
        finally:db.close()

    def test_cot_conflict_stale_or_nonconsecutive_reports_block_events(self):
        series=[("2026-10-13",1.0,1.0),("2026-10-20",-1.0,2.0)]
        self.assertEqual(m.cot_view(series,"XAUUSD",NOW)["side"],-1) # producer hedges are not a conflicting speculator group
        self.assertIsNone(m.cot_view([("2026-10-01",0,0),("2026-10-20",5,5)],"XAUUSD",NOW))
        self.assertIsNone(m.cot_view([("2026-10-13",0,0),("2026-10-20",-5,5)],"EURUSD",NOW))
        self.assertIsNone(m.cot_view([("2026-09-01",0,0),("2026-09-08",5,5)],"US30",NOW))

    def test_only_new_confirmed_source_changes_create_events(self):
        start={"state":"divergent","side":1,"report_date":"2026-10-20",
               "price_time":"2026-10-26T10:00:00+00:00","price_state":"watch"}
        same={**start,"state":"aligned","price_state":"confirmed"}
        self.assertIsNone(m.transition(start,same))
        newer={**same,"price_time":"2026-10-26T10:15:00+00:00"}
        self.assertEqual(m.transition(start,newer),"new_convergence")
        self.assertIsNone(m.transition(start,{**newer,"price_time":"2026-10-26T09:45:00+00:00"}))
        self.assertEqual(m.transition({**start,"state":"aligned"},{
            **newer,"state":"divergent"}),"new_divergence")
        self.assertEqual(m.transition({**start,"state":"aligned"},newer),"confirmation_strengthened")

    def test_empty_or_weekend_only_scan_writes_no_false_events(self):
        # Empty CFTC and price data => no baseline or event.
        result=m.scan_once(self.db_path,NOW)
        self.assertEqual(result,{"examined":0,"baselines":0,"newEvents":0})
        state=m.status(self.db_path,True,NOW)
        self.assertTrue(state["enabled"])
        self.assertEqual(state["mode"],"observation_only")
        self.assertFalse(state["notificationsEnabled"])
        self.assertEqual(state["baselines"],0)
        self.assertEqual(state["lastEvents"],[])
        import json
        self.assertNotIn("access_token",json.dumps(state))
        self.assertNotIn("password",json.dumps(state))


    def test_database_event_flow_baseline_change_and_dedup_without_network(self):
        from unittest.mock import patch
        from cot_monitor import ensure_table
        from price_store import connect
        db=connect(self.db_path)
        try:
            ensure_table(db)
            db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                       ("tff","099741","2026-10-13",1000,100,50,120,30))
            db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                       ("tff","099741","2026-10-20",1000,110,50,160,30))
            db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",
                       ("EURUSD","ctrader","EURUSD",NOW.isoformat(),'{"symbol":"EURUSD"}'))
            db.commit()
        finally:db.close()
        prior={"side":-1,"state":"watch","last_m15":"2026-10-26T11:00:00+00:00"}
        recent={"side":1,"state":"confirmed","last_m15":"2026-10-26T11:15:00+00:00"}
        with patch.object(m,"price_view",return_value=prior):
            first=m.scan_once(self.db_path,NOW)
        self.assertEqual(first["newEvents"],0)
        self.assertEqual(first["baselines"],1)
        with patch.object(m,"price_view",return_value=recent):
            second=m.scan_once(self.db_path,NOW+dt.timedelta(minutes=5))
            repeat=m.scan_once(self.db_path,NOW+dt.timedelta(minutes=6))
        self.assertEqual(second["newEvents"],1)
        self.assertEqual(repeat["newEvents"],0)
        found=m.status(self.db_path,True,NOW)
        self.assertEqual(found["lastEvents"][0]["eventType"],"new_convergence")
        self.assertFalse(found["notificationsEnabled"])
        self.assertEqual(found["lastEvents"][0]["symbol"],"EURUSD")

    def test_rollup_quality_gate_rejects_missing_or_weekend_prices(self):
        self.assertIsNone(m.price_view(None,NOW))
        from unittest.mock import patch
        with patch.object(m,"audit_market",return_value={"integrity":"verified",
                "freshness":"weekend","ready":True}):
            self.assertIsNone(m.price_view({"timeframes":{}},NOW))
        with patch.object(m,"audit_market",return_value={"integrity":"partial",
                "freshness":"recent","ready":True}):
            self.assertIsNone(m.price_view({"timeframes":{}},NOW))


    def test_prolonged_monitor_outage_restarts_baseline_without_event(self):
        from unittest.mock import patch
        from cot_monitor import ensure_table
        db=connect(self.db_path)
        try:
            ensure_table(db)
            for date,net in (("2026-10-13",100),("2026-10-20",155)):
                db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                    ("tff","099741",date,1000,100,50,net,30))
            db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",
                ("EURUSD","ctrader","EURUSD",NOW.isoformat(),'{"symbol":"EURUSD"}'))
            m.ensure_tables(db)
            with db:
                db.execute("INSERT INTO squalincome_observations VALUES(?,?,?,?,?,?,?)",
                  ("EURUSD","divergent",1,"2026-10-13","2026-10-26T10:00:00+00:00",
                   "watch",(NOW-dt.timedelta(days=20)).isoformat()))
        finally:db.close()
        p={"side":1,"state":"confirmed","last_m15":"2026-10-26T11:15:00+00:00"}
        with patch.object(m,"price_view",return_value=p):
            result=m.scan_once(self.db_path,NOW)
        self.assertEqual(result["newEvents"],0)
        self.assertEqual(result["baselines"],1)

    def test_duplicate_snapshot_upsert_and_event_key_is_idempotent(self):
        db=connect(self.db_path)
        try:
            m.ensure_tables(db)
            row=("GBPJPY","new_convergence",1,"2026-10-20","2026-10-26T10:00:00+00:00",
                 NOW.isoformat(),"tested")
            with db:
                db.execute("INSERT OR IGNORE INTO squalincome_events"
                           "(symbol,event_type,side,report_date,price_time,observed_at,detail) "
                           "VALUES(?,?,?,?,?,?,?)",row)
                db.execute("INSERT OR IGNORE INTO squalincome_events"
                           "(symbol,event_type,side,report_date,price_time,observed_at,detail) "
                           "VALUES(?,?,?,?,?,?,?)",row)
            self.assertEqual(db.execute("SELECT count(*) FROM squalincome_events").fetchone()[0],1)
        finally:db.close()

if __name__=="__main__":unittest.main()
