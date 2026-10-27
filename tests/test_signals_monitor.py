"""Offline tests of REMURA v1.37 observation-only monitor."""
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

    def test_diagnostics_empty_scan_is_data_insufficient_not_no_event(self):
        result=m.scan_once(self.db_path,NOW)
        self.assertEqual(result["examined"],0)
        info=m.status(self.db_path,True,NOW)["diagnostics"]
        self.assertEqual(info["lastScanAt"],NOW.isoformat())
        self.assertEqual(info["analyzed"],0)
        self.assertEqual(info["excluded"],len(m.monitored_symbols()))
        self.assertEqual(info["trackedMarkets"],info["analyzed"]+info["excluded"])
        self.assertEqual(info["exclusionReasons"]["cot_missing"],info["excluded"])
        self.assertEqual(info["exclusionReasons"]["prices_missing"],info["excluded"])
        self.assertEqual(info["outcome"],"data_insufficient")
        self.assertEqual(m.status(self.db_path,True,NOW)["eventsTotal"],0)
        import json
        self.assertNotIn("access_token",json.dumps(info))
        self.assertNotIn("providerSymbol",json.dumps(info))
        self.assertNotIn('"o":',json.dumps(info))
        self.assertEqual(len(info["markets"]),len(m.monitored_symbols()))

    def test_usable_data_with_zero_events_is_not_data_insufficient(self):
        from unittest.mock import patch
        p={"side":1,"state":"confirmed","last_m15":"2026-10-26T11:15:00+00:00"}
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=p):
            first=m.scan_once(self.db_path,NOW)
            second=m.scan_once(self.db_path,NOW+dt.timedelta(minutes=15))
        self.assertEqual(first["examined"],len(m.monitored_symbols()))
        self.assertEqual(first["baselines"],len(m.monitored_symbols()))
        self.assertEqual(second["newEvents"],0)
        info=m.status(self.db_path,True,NOW)["diagnostics"]
        self.assertEqual(info["analyzed"],len(m.monitored_symbols()))
        self.assertEqual(info["excluded"],0)
        self.assertEqual(info["outcome"],"no_significant_event")
        self.assertEqual(info["newBaselines"],0)

    def test_weekend_is_explicit_and_never_fabricates_live_analysis(self):
        from unittest.mock import patch
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        weekend_quality={"integrity":"verified","freshness":"weekend","ready":True,
                         "h1":{"mismatched":0},"h4":{"mismatched":0}}
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"audit_market",return_value=weekend_quality):
            m.scan_once(self.db_path,NOW)
        info=m.status(self.db_path,True,NOW)["diagnostics"]
        self.assertEqual(info["outcome"],"data_insufficient")
        self.assertEqual(info["exclusionReasons"]["market_closed"],len(m.monitored_symbols()))
        self.assertNotIn("new_convergence",str(info))
        self.assertEqual(m.status(self.db_path,True,NOW)["baselines"],0)

    def test_non_directional_cot_is_not_labeled_missing(self):
        from unittest.mock import patch
        rows=[("2026-10-13",0,0),("2026-10-20",0.01,0.02)]
        p={"side":1,"state":"watch","last_m15":"2026-10-26T11:15:00+00:00"}
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=p):
            m.scan_once(self.db_path,NOW)
        info=m.status(self.db_path,True,NOW)["diagnostics"]
        self.assertEqual(info["outcome"],"no_qualifying_setup")
        self.assertEqual(info["exclusionReasons"]["cot_no_direction"],len(m.monitored_symbols()))
        self.assertNotIn("cot_missing",info["exclusionReasons"])

    def test_diagnostic_reason_taxonomy_distinguishes_timeframes(self):
        from unittest.mock import patch
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        self.assertEqual(m.cot_exclusion(rows,"EURUSD",NOW),"cot_no_direction")
        self.assertEqual(m.cot_exclusion([], "EURUSD",NOW),"cot_missing")
        self.assertEqual(m.cot_exclusion([("2026-10-13",0,0),
                              ("2026-10-20",-2,2)],"EURUSD",NOW),"cot_group_conflict")
        self.assertEqual(m.cot_exclusion([("2026-09-01",0,0),("2026-09-08",1,1)],
                                         "EURUSD",NOW),"cot_stale")
        quality={"integrity":"invalid","freshness":"recent","ready":True,
                 "h1":{"mismatched":1},"h4":{"mismatched":0}}
        with patch.object(m,"audit_market",return_value=quality):
            self.assertEqual(m.price_exclusion({"timeframes":{}},NOW),"ohlc_mismatch")
        quality["integrity"]="insufficient"
        quality["h1"]["mismatched"]=0
        quality["ready"]=False
        with patch.object(m,"audit_market",return_value=quality):
            self.assertEqual(m.price_exclusion({"timeframes":{}},NOW),"candles_insufficient")

    def test_real_closed_candle_ages_without_exposing_ohlc(self):
        now=dt.datetime(2026,10,26,12,15,tzinfo=UTC)
        doc={"timeframes":{
            "M15":[{"t":"2026-10-26T11:45:00+00:00","o":1.42,"c":1.56}],
            "H1":[{"t":"2026-10-26T10:00:00+00:00","o":1.3,"h":2}],
            "H4":[{"t":"2026-10-26T04:00:00+00:00","l":1.1}]}}
        frames=m.safe_frame_diagnostics(doc,now)
        self.assertEqual(frames["M15"]["lastClosedAt"],"2026-10-26T12:00:00+00:00")
        self.assertEqual(frames["M15"]["ageMinutes"],15)
        self.assertEqual(frames["H1"]["ageMinutes"],75)
        self.assertEqual(frames["H4"]["ageMinutes"],255)
        self.assertEqual(frames["M15"]["bars"],1)
        import json
        flat=json.dumps(frames)
        for secret in ('"o"', '"h"', '"l"', '"c"', "1.42", "refresh_token"):
            self.assertNotIn(secret,flat)
        self.assertIsNone(m.safe_frame_diagnostics(None,now)["H4"]["lastClosedAt"])

    def test_scan_reports_timeframe_ages_even_for_excluded_markets(self):
        from unittest.mock import patch
        doc={"timeframes":{
            "M15":[{"t":"2026-10-26T11:45:00+00:00"}],
            "H1":[{"t":"2026-10-26T10:00:00+00:00"}],
            "H4":[{"t":"2026-10-26T04:00:00+00:00"}]}}
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value=doc), \
             patch.object(m,"price_view",return_value=None), \
             patch.object(m,"price_exclusion",return_value="prices_stale"):
            m.scan_once(self.db_path,NOW)
        d=m.status(self.db_path,True,NOW)["diagnostics"]
        self.assertEqual(d["trackedMarkets"],34)
        self.assertEqual(d["excluded"],34)
        self.assertEqual(len(d["markets"]),34)
        self.assertEqual(d["markets"][0]["timeframes"]["H4"]["ageMinutes"],255)
        self.assertFalse(d["markets"][0]["analyzed"])
        self.assertEqual(d["exclusionReasons"]["prices_stale"],34)
        self.assertEqual(d["updatedObservations"],0)

    def test_distinguishes_opposing_trends_from_corrupted_rollups(self):
        from unittest.mock import patch
        verified={"integrity":"verified","freshness":"recent","ready":True,
                  "h1":{"mismatched":0},"h4":{"mismatched":0}}
        def direction(bars,seconds,now):
            return {"side":1 if seconds==14400 else -1,
                    "close_time":NOW.isoformat(),"breakout":0}
        doc={"timeframes":{key:[{}]*55 for key in m.DURATIONS}}
        with patch.object(m,"audit_market",return_value=verified), \
             patch.object(m,"frame_direction",side_effect=direction):
            self.assertEqual(m.price_exclusion(doc,NOW),"trend_disagreement")
            self.assertIsNone(m.price_view(doc,NOW))
        verified["h4"]["mismatched"]=1
        verified["integrity"]="invalid"
        with patch.object(m,"audit_market",return_value=verified):
            self.assertEqual(m.price_exclusion(doc,NOW),"ohlc_mismatch")

    def test_existing_observations_list_is_read_only_and_preserved(self):
        from unittest.mock import patch
        p={"side":1,"state":"watch","last_m15":"2026-10-26T11:15:00+00:00"}
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=p):
            m.scan_once(self.db_path,NOW)
        baseline=m.status(self.db_path,True,NOW)
        self.assertEqual(len(baseline["observations"]),34)
        self.assertEqual(baseline["observations"][0]["priceState"],"watch")
        self.assertEqual(baseline["diagnostics"]["newBaselines"],34)
        nextp={**p,"last_m15":"2026-10-26T11:30:00+00:00"}
        with patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=nextp):
            m.scan_once(self.db_path,NOW+dt.timedelta(minutes=15))
        after=m.status(self.db_path,True,NOW)
        self.assertEqual(after["baselines"],34)
        self.assertEqual(after["diagnostics"]["newBaselines"],0)
        self.assertEqual(after["diagnostics"]["updatedObservations"],34)
        self.assertEqual(after["eventsTotal"],0)

    def test_v137_preserves_old_baselines_and_collects_real_history_only(self):
        from unittest.mock import patch
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        db=connect(self.db_path)
        m.ensure_tables(db)
        with db:
            db.execute("INSERT INTO squalincome_observations VALUES(?,?,?,?,?,?,?)",
                ("EURUSD","divergent",1,"2026-10-20",
                 "2026-10-26T11:00:00+00:00","watch",
                 (NOW-dt.timedelta(minutes=30)).isoformat()))
        db.close()
        p={"side":-1,"state":"watch","last_m15":"2026-10-26T11:15:00+00:00",
           "h4_side":-1,"h1_side":-1,"m15_side":-1}
        with patch.object(m,"monitored_symbols",return_value=("EURUSD",)), \
             patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=p):
            m.scan_once(self.db_path,NOW)
            first=m.status(self.db_path,True,NOW)
            self.assertEqual(first["baselines"],1)
            self.assertEqual(first["historyTotal"],1)
            self.assertEqual(first["history"][0]["origin"],"first_after_upgrade")
            self.assertEqual(first["history"][0]["cotSide"],1)
            self.assertEqual(first["history"][0]["priceSide"],-1)
            self.assertEqual(first["history"][0]["h4Side"],-1)
            self.assertEqual(first["history"][0]["state"],"divergent")
            self.assertEqual(first["history"][0]["cotWeekly"],2)
            repeat=m.scan_once(self.db_path,NOW+dt.timedelta(minutes=1))
            self.assertEqual(repeat["newEvents"],0)
            self.assertEqual(m.status(self.db_path,True,NOW)["historyTotal"],1)
            p.update(side=1,state="confirmed",h4_side=1,h1_side=1,
                     m15_side=1,last_m15="2026-10-26T11:30:00+00:00")
            second=m.scan_once(self.db_path,NOW+dt.timedelta(minutes=15))
            after=m.status(self.db_path,True,NOW)
        self.assertEqual(second["newEvents"],1)
        self.assertEqual(after["historyTotal"],2)
        self.assertEqual([h["state"] for h in after["history"]],
                         ["divergent","aligned"])
        self.assertEqual(after["history"][-1]["eventType"],"new_convergence")
        self.assertEqual(after["history"][-1]["origin"],"update")
        self.assertEqual(after["eventsTotal"],1)
        self.assertEqual(after["baselines"],1)

    def test_v137_history_is_bounded_and_no_false_events_after_outage(self):
        from unittest.mock import patch
        rows=[("2026-10-13",0,0),("2026-10-20",2,2)]
        p={"side":1,"state":"watch","last_m15":"2026-10-26T11:15:00+00:00",
           "h4_side":1,"h1_side":1,"m15_side":0}
        with patch.object(m,"monitored_symbols",return_value=("EURUSD",)), \
             patch.object(m,"cot_series",return_value=rows), \
             patch.object(m,"latest",return_value={"timeframes":{}}), \
             patch.object(m,"price_view",return_value=p), \
             patch.object(m,"HISTORY_MAX_PER_SYMBOL",3):
            for i in range(6):
                p["last_m15"]=(NOW+dt.timedelta(minutes=i*15)).isoformat()
                m.scan_once(self.db_path,NOW+dt.timedelta(minutes=i*15+15))
            state=m.status(self.db_path,True,NOW)
        self.assertEqual(state["historyTotal"],3)
        self.assertEqual(len(state["history"]),3)
        self.assertEqual(state["eventsTotal"],0)
        self.assertEqual(state["baselines"],1)
        self.assertEqual(state["history"][-1]["priceTime"],
                         (NOW+dt.timedelta(minutes=75)).isoformat())
        import json
        serialized=json.dumps(state["history"])
        for secret in ('"o":','"h":','"l":','"c":','CTRADER_ACCESS_TOKEN',
                       'refresh_token','client_secret'):
            self.assertNotIn(secret,serialized)

    def test_v137_empty_scan_does_not_create_synthetic_timeline(self):
        m.scan_once(self.db_path,NOW)
        data=m.status(self.db_path,True,NOW)
        self.assertEqual(data["baselines"],0)
        self.assertEqual(data["historyTotal"],0)
        self.assertEqual(data["history"],[])

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
