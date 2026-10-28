"""REMURA v1.45: offline true-M15 dual-horizon contract tests."""
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
import dual24_validation as dual
import statistical_validation as legacy
import private_server
from price_store import connect

UTC=dt.timezone.utc
START=dt.datetime(2026,10,26,10,0,tzinfo=UTC)
NOW=dt.datetime(2026,10,29,16,0,tzinfo=UTC)


def sample(start=START,closed_days=(),skip=None,extra_days=3):
    skip=skip or set()
    bars=[]
    earliest=start-dt.timedelta(hours=2)
    for n in range(100*4*extra_days):
        when=earliest+dt.timedelta(minutes=15*n)
        if when.weekday() in closed_days or when in skip:
            continue
        if when.hour==21:  # fixed metal break confirmed in cTrader
            continue
        close=1.0+n*.00001
        bars.append({"t":when.isoformat(),"o":close,"h":close+.00002,
                     "l":close-.000005,"c":close+.000006})
    return bars


class Dual24Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"private"/"remura-prices.sqlite3"
        db=connect(self.path)
        legacy.ensure_tables(db)
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def seed(self,symbol="XAUUSD",gap=True,stage="observation",side=1,
             start=START, missing=None,broker=None):
        broker=broker or symbol
        timeline=sample(start=start,skip=missing)
        if not gap:
            timeline=[dict(row) for row in timeline]
            # Include genuine M15 during 21 UTC to simulate a continuously quoted FX market.
            all_timestamps={dt.datetime.fromisoformat(x["t"]) for x in timeline}
            earliest=start-dt.timedelta(hours=2)
            for n in range(100*4*3):
                stamp=earliest+dt.timedelta(minutes=15*n)
                if stamp not in all_timestamps and stamp not in (missing or set()):
                    price=1.0+n*.00001
                    timeline.append({"t":stamp.isoformat(),"o":price,
                                     "h":price+.00002,"l":price-.000005,
                                     "c":price+.000006})
            timeline.sort(key=lambda x:x["t"])
        entry=next(x["o"] for x in timeline if x["t"]==start.isoformat())
        payload={"provider":"ctrader","providerSymbol":broker,
                 "timeframes":{"M15":timeline}}
        db=connect(self.path)
        with db:
            db.execute("INSERT OR REPLACE INTO prices"
                       "(symbol,source,broker_symbol,updated_at,payload) "
                       "VALUES(?,?,?,?,?)",
                       (symbol,"ctrader",broker,NOW.isoformat(),json.dumps(payload)))
            db.execute(
                "INSERT OR IGNORE INTO squalincome_validation_cohorts"
                "(symbol,report_date,observed_at,price_time,cot_side,relationship,"
                "stage,broker_symbol,entry_at,entry_open)"
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (symbol,"2026-10-20",(start-dt.timedelta(minutes=1)).isoformat(),
                 (start-dt.timedelta(minutes=15)).isoformat(),side,
                 "aligned" if side==1 else "divergent",stage,broker,start.isoformat(),entry))
        db.close()
        return payload,entry

    def test_genuine_metal_pauses_produce_distinct_outcomes(self):
        self.seed()
        self.assertEqual(dual.update_dual24(self.path,NOW)["outcomesAdded"],2)
        self.assertEqual(dual.update_dual24(self.path,NOW)["outcomesAdded"],0)
        db=connect(self.path)
        rows=db.execute(
            "SELECT metric,calendar_minutes,closed_m15,verified_pauses,"
            "exit_delay_minutes FROM squalincome_dual24_outcomes ORDER BY metric"
        ).fetchall()
        self.assertEqual(rows,[
            ("calendar24",1440,92,1,0),
            ("trading96",1500,96,1,0)
        ])
        self.assertEqual(db.execute("SELECT count(*) FROM squalincome_validation_outcomes").fetchone()[0],0)
        db.close()

    def test_calendar_and_trading_cannot_interpolate_missing_bar(self):
        missing={START+dt.timedelta(hours=3,minutes=15)}
        self.seed(missing=missing)
        self.assertEqual(dual.update_dual24(self.path,NOW)["outcomesAdded"],0)
        report=dual.dual24_status(self.path,NOW)
        self.assertEqual(report["outcomes"],0)
        for row in report["segments"]:
            if row["segment"]=="all":
                self.assertEqual(row["samples"],0)
                self.assertEqual(row["unmeasuredCandidates"],1)

    def test_24_calendar_uses_open_at_exact_time_not_future_close(self):
        self.seed()
        dual.update_dual24(self.path,NOW)
        db=connect(self.path)
        row=db.execute("SELECT exit_at,exit_open,entry_open,directional_bps FROM "
                       "squalincome_dual24_outcomes WHERE metric='calendar24'").fetchone()
        payload=json.loads(db.execute("SELECT payload FROM prices").fetchone()[0])
        bytime={x["t"]:x for x in payload["timeframes"]["M15"]}
        self.assertEqual(row[0],(START+dt.timedelta(hours=24)).isoformat())
        self.assertEqual(row[1],bytime[row[0]]["o"])
        self.assertAlmostEqual(row[3],(row[1]-row[2])/row[2]*10000,places=6)
        db.close()

    def test_96_closed_bars_require_closed_exit_bar(self):
        self.seed()
        # 96 trading candles after 10:00 with a 1h gap => 11:00 next day
        cutoff=START+dt.timedelta(hours=25,minutes=10)
        self.assertEqual(dual.update_dual24(self.path,cutoff)["outcomesAdded"],1)
        self.assertEqual(dual.dual24_status(self.path,cutoff)["outcomes"],1)
        self.assertEqual(dual.update_dual24(self.path,NOW)["outcomesAdded"],1)

    def test_real_exit_open_is_counted_in_excursion_without_future_high(self):
        payload,entry=self.seed()
        target=(START+dt.timedelta(hours=24)).isoformat()
        for row in payload["timeframes"]["M15"]:
            if row["t"]==target:
                row["o"]=entry*1.07
                row["h"]=entry*1.09  # future high MUST NOT be used
                row["l"]=entry*1.06
                row["c"]=entry*1.08
        result=dual._measurement(payload,"XAUUSD",START,entry,1,"calendar24",NOW)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["directional_bps"],700,places=3)
        self.assertAlmostEqual(result["favorable_bps"],700,places=3)
        self.assertLess(result["favorable_bps"],900)

    def test_broker_switch_never_mix_old_entry_with_new_quote(self):
        self.seed(broker="FP-ONLY-SECRET")
        db=connect(self.path)
        doc=json.loads(db.execute("SELECT payload FROM prices").fetchone()[0])
        doc["providerSymbol"]="DIFFERENT"
        with db:
            db.execute("UPDATE prices SET broker_symbol=?,payload=?",("DIFFERENT",json.dumps(doc)))
        db.close()
        self.assertEqual(dual.update_dual24(self.path,NOW)["outcomesAdded"],0)

    def test_unchanged_legacy_24h_result_is_untouched(self):
        self.seed()
        db=connect(self.path)
        with db:
            db.execute(
                "INSERT INTO squalincome_validation_outcomes"
                "(symbol,report_date,stage,horizon_hours,evaluated_at,directional_bps,"
                "long_benchmark_bps,favorable_bps,adverse_bps) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                ("XAUUSD","2026-10-20","observation",24,NOW.isoformat(),
                 123.45,123.45,130,-5))
        before=db.execute("SELECT directional_bps FROM squalincome_validation_outcomes").fetchall()
        db.close()
        dual.update_dual24(self.path,NOW)
        db=connect(self.path)
        self.assertEqual(db.execute("SELECT directional_bps FROM "
                                    "squalincome_validation_outcomes").fetchall(),before)
        db.close()

    def test_unsupported_weekend_gap_is_not_approved_automatically(self):
        # Create a weekend: no Fri night / Sat / Sun / Monday morning quotes.
        start=dt.datetime(2026,10,23,10,tzinfo=UTC)
        timeline=[]
        for i in range(96*5):
            t=start+dt.timedelta(minutes=15*i)
            if t.weekday() in (5,6):
                continue
            timeline.append((t,(1.0,1.001,.999,1.0002)))
        # Future weekday Monday is present; weekend gap remains unsupported.
        bars=dict(timeline)
        self.assertIsNone(dual._measurement(
            {"provider":"ctrader","providerSymbol":"EURUSD",
             "timeframes":{"M15":[{"t":t.isoformat(),"o":a,"h":b,"l":c,"c":d}
                                  for t,(a,b,c,d) in sorted(bars.items())]}},
            "EURUSD",start,1.0,1,"trading96",
            dt.datetime(2026,10,29,tzinfo=UTC)))

    def test_no_future_candle_influence_and_entry_validation(self):
        doc,entry=self.seed()
        self.assertIsNone(dual._measurement(doc,"XAUUSD",START,entry,1,
                                            "calendar24",START+dt.timedelta(hours=24)))
        self.assertIsNone(dual._measurement(doc,"XAUUSD",START,entry*2,1,
                                            "calendar24",NOW))
        self.assertIsNone(dual._measurement(doc,"XAUUSD",START,entry,1,
                                            "trading96",START+dt.timedelta(hours=24)))

    def test_aggregation_exposes_no_trade_or_broker_fields(self):
        self.seed(broker="SECRET-FP-ACCOUNT")
        dual.update_dual24(self.path,NOW)
        payload=dual.dual24_status(self.path,NOW)
        self.assertEqual(payload["schema"],"remura-dual24-validation-v1")
        self.assertEqual(payload["outcomes"],2)
        self.assertEqual(len(payload["segments"]),12)
        primary={r["metric"]:r for r in payload["segments"] if r["segment"]=="all"}
        self.assertEqual(primary["calendar24"]["meanElapsedHours"],24)
        self.assertEqual(primary["trading96"]["meanElapsedHours"],25)
        self.assertEqual(primary["trading96"]["reportWeeks"],1)
        self.assertEqual(primary["trading96"]["verdict"],"Campione insufficiente")
        text=json.dumps(payload)
        for forbidden in ("SECRET-FP-ACCOUNT","entry_open","exit_open","XAUUSD","CTRADER_CLIENT_SECRET"):
            self.assertNotIn(forbidden,text)

    def test_as_of_snapshot_cannot_use_future_outcomes(self):
        self.seed()
        dual.update_dual24(self.path,NOW)
        past=START+dt.timedelta(hours=1)
        report=dual.dual24_status(self.path,past)
        self.assertEqual(report["outcomes"],0)
        self.assertEqual(report["cohorts"],1)
        for group in report["segments"]:
            self.assertEqual(group["samples"],0)

    def test_http_readonly_endpoint_returns_aggregate_and_no_cache(self):
        self.seed()
        dual.update_dual24(self.path,NOW)
        server=ThreadingHTTPServer(("127.0.0.1",0),private_server.http_handler(self.path))
        worker=Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            with patch.object(dual,"utcnow",return_value=NOW):
                with urlopen("http://127.0.0.1:"+str(server.server_port)+
                             "/private-api/signals/dual24",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                    data=json.load(response)
            self.assertEqual(data["schema"],"remura-dual24-validation-v1")
            self.assertEqual(data["outcomes"],2)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__=="__main__":
    unittest.main()
