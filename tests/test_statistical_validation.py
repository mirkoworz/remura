"""Offline tests for v1.40 forward-only validation. No network or credentials."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import statistical_validation as v
import signals_monitor as s
from price_store import connect

UTC = dt.timezone.utc
OBS = dt.datetime(2026, 10, 26, 9, 1, tzinfo=UTC)
NOW = dt.datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
ISO = lambda value: value.isoformat()


class ForwardValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name)/"private"/"prices.sqlite"
        db = connect(self.db_path)
        s.ensure_tables(db)
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def seed(self, side=1, gap=False, broker="EURUSD",
             event=None, relation="aligned", stage="watch"):
        start = dt.datetime(2026, 10, 26, 8, 0, tzinfo=UTC)
        rows = []
        for i in range(113):
            t = start + dt.timedelta(minutes=15*i)
            if gap and t == dt.datetime(2026, 10, 26, 9, 45, tzinfo=UTC):
                continue
            base = 1.0+i*.0001
            rows.append({"t":ISO(t),"o":base,"h":base+.00015,
                         "l":base-.00005,"c":base+.0001})
        doc = {"provider":"ctrader","providerSymbol":broker,
               "timeframes":{"M15":rows}}
        db = connect(self.db_path)
        with db:
            db.execute("INSERT OR REPLACE INTO prices"
                       "(symbol,source,broker_symbol,updated_at,payload) VALUES(?,?,?,?,?)",
                       ("EURUSD","ctrader",broker,ISO(NOW),json.dumps(doc)))
            db.execute("INSERT OR IGNORE INTO squalincome_history"
                       "(symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
                       "price_state,report_date,price_time,observed_at,cot_weekly,"
                       "cot_sustained,origin,event_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       ("EURUSD",relation,side,(-side if relation == "divergent" else side),side,side,side,stage,
                        "2026-10-20",ISO(dt.datetime(2026,10,26,9,0,tzinfo=UTC)),
                        ISO(OBS),.7,1,"update",event))
        db.close()
        return doc

    def run_update(self, now=NOW):
        with patch.object(v,"monitored_symbols",return_value=("EURUSD",)):
            return v.update_validation(self.db_path,now)

    def test_closed_m15_forward_1_4_24h_and_idempotency(self):
        self.seed()
        first = self.run_update()
        self.assertEqual(first,{"cohortsAdded":1,"outcomesAdded":3})
        self.assertEqual(self.run_update(),{"cohortsAdded":0,"outcomesAdded":0})
        status = v.validation_status(self.db_path)
        self.assertEqual(status["cohorts"],1)
        self.assertEqual(status["outcomes"],3)
        self.assertFalse(status["costsIncluded"])
        one = next(x for x in status["segments"]
                   if x["segment"]=="all" and x["horizonHours"]==1)
        self.assertEqual(one["verdict"],"Campione insufficiente")
        self.assertEqual(one["directionHitPct"],100)
        self.assertEqual(one["maturedCohorts"],1)
        self.assertEqual(one["unevaluatedMatured"],0)
        self.assertEqual(one["coveragePct"],100)
        self.assertLess(one["wilson95Pct"][0],50)
        self.assertNotIn("1.00",json.dumps(status))

    def test_does_not_count_later_weekly_repeat_or_fabricate_old_release(self):
        self.seed()
        db = connect(self.db_path)
        with db:
            db.execute("INSERT INTO squalincome_history"
                       "(symbol,state,cot_side,price_side,price_state,report_date,"
                       "price_time,observed_at,origin) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("EURUSD","divergent",-1,1,"confirmed","2026-10-20",
                        ISO(dt.datetime(2026,10,26,9,15,tzinfo=UTC)),
                        ISO(OBS+dt.timedelta(minutes=20)),"update"))
        db.close()
        self.run_update()
        db=connect(self.db_path)
        row=db.execute("SELECT cot_side,relationship,observed_at FROM "
                       "squalincome_validation_cohorts").fetchone()
        db.close()
        self.assertEqual(row,(1,"aligned",ISO(OBS)))

    def test_gap_and_weekend_are_not_turned_into_fake_forward_bars(self):
        self.seed(gap=True)
        self.assertEqual(self.run_update()["outcomesAdded"],0)
        self.assertEqual(v.validation_status(self.db_path)["outcomes"],0)
        gap_stats=v.validation_status(self.db_path)["segments"]
        gap_one=next(x for x in gap_stats if x["segment"]=="all" and x["horizonHours"]==1)
        self.assertEqual(gap_one["maturedCohorts"],1)
        self.assertEqual(gap_one["coveragePct"],0)

    def test_only_matured_horizons_are_evaluated(self):
        self.seed()
        now=dt.datetime(2026,10,26,11,0,tzinfo=UTC)
        self.assertEqual(self.run_update(now)["outcomesAdded"],1)
        self.assertEqual(self.run_update(NOW)["outcomesAdded"],2)

    def test_short_side_and_divergence_are_separate(self):
        self.seed(side=-1, relation="divergent",stage="confirmed")
        self.run_update()
        status=v.validation_status(self.db_path)
        x=next(x for x in status["segments"]
               if x["horizonHours"]==4 and x["segment"]=="divergent")
        self.assertEqual(x["samples"],1)
        self.assertEqual(x["directionHitPct"],0)
        y=next(x for x in status["segments"]
               if x["horizonHours"]==4 and x["segment"]=="technical_confirmation")
        self.assertEqual(y["samples"],1)
        self.assertEqual(x["meanDirectionalBps"],-x["meanLongBenchmarkBps"])

    def test_broker_change_cannot_combine_foreign_price_history(self):
        self.seed()
        self.run_update(dt.datetime(2026,10,26,11,0,tzinfo=UTC))
        db=connect(self.db_path)
        original=json.loads(db.execute("SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0])
        original["providerSymbol"]="other-broker"
        with db:
            db.execute("UPDATE prices SET broker_symbol=?,payload=? WHERE symbol='EURUSD'",
                       ("other-broker",json.dumps(original)))
        db.close()
        self.assertEqual(self.run_update(NOW)["outcomesAdded"],0)

    def test_no_entry_before_observation_and_future_observation_rejected(self):
        self.seed()
        db=connect(self.db_path)
        with db:
            db.execute("UPDATE squalincome_history SET observed_at=?",
                       (ISO(NOW+dt.timedelta(hours=1)),))
        db.close()
        self.assertEqual(self.run_update()["cohortsAdded"],0)

    def test_no_private_ohlc_or_broker_in_status(self):
        self.seed(broker="private-broker-symbol")
        self.run_update()
        serial=json.dumps(v.validation_status(self.db_path))
        self.assertNotIn("private-broker-symbol",serial)
        self.assertNotIn("entry_open",serial)
        self.assertNotIn("refresh_token",serial)



    def test_three_nested_study_arms_are_not_pooled_as_independent(self):
        self.seed(stage="watch")
        db = connect(self.db_path)
        with db:
            for minute, candle_minute, price_state, event in (
                (20, 15, "confirmed", None),
                (40, 30, "confirmed", "new_convergence"),
            ):
                db.execute(
                    "INSERT INTO squalincome_history"
                    "(symbol,state,cot_side,price_side,price_state,report_date,"
                    "price_time,observed_at,origin,event_type)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?)",
                    ("EURUSD","aligned",1,1,price_state,"2026-10-20",
                     ISO(dt.datetime(2026,10,26,9,candle_minute,tzinfo=UTC)),
                     ISO(OBS+dt.timedelta(minutes=minute)),"update",event))
        db.close()
        result = self.run_update()
        self.assertEqual(result,{"cohortsAdded":3,"outcomesAdded":9})
        stats = v.validation_status(self.db_path)["segments"]
        for arm in ("all","observation","technical_confirmation","qualified_event"):
            self.assertEqual(next(r["samples"] for r in stats if
                                 r["horizonHours"]==1 and r["segment"]==arm),1)
        self.assertEqual(self.run_update(),
                         {"cohortsAdded":0,"outcomesAdded":0})

    def test_private_http_endpoint_aggregates_without_exposing_prices(self):
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        import threading
        import private_server
        self.seed(broker="do-not-expose-private-name")
        self.run_update()
        site = ThreadingHTTPServer(("127.0.0.1", 0),
                                   private_server.http_handler(self.db_path))
        worker = threading.Thread(target=site.serve_forever, daemon=True)
        worker.start()
        try:
            with urlopen("http://127.0.0.1:" + str(site.server_port) +
                         "/private-api/signals/validation", timeout=5) as response:
                self.assertEqual(response.headers.get("Cache-Control"),
                                 "no-store, max-age=0")
                payload = json.load(response)
            self.assertEqual(payload["schema"], "remura-forward-validation-v1")
            self.assertEqual(payload["outcomes"], 3)
            exposed = json.dumps(payload)
            for secret in ("do-not-expose-private-name","entry_open",
                           '"o":','"h":','"l":','"c":',"CTRADER_ACCESS_TOKEN"):
                self.assertNotIn(secret, exposed)
        finally:
            site.shutdown()
            site.server_close()
            worker.join(timeout=2)



if __name__ == "__main__":
    unittest.main()
