"""REMURA v1.49: watch individual official COT contract/week acquisition."""
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
import cot_week_watch
import private_server
from price_feed import UTC
from price_store import connect,set_status

NOW=dt.datetime(2026,10,29,9,0,tzinfo=UTC)
LATER=NOW+dt.timedelta(hours=5)
LATEST="2026-10-27"
PREVIOUS="2026-10-20"
RECENT=dt.datetime(2026,10,28,20,0,tzinfo=UTC)


def row_feed(kind,week):
    cfg=cot_monitor.DATASETS[kind]
    return [{"report_date_as_yyyy_mm_dd":week+"T00:00:00",
             "cftc_contract_market_code":code,
             "open_interest_all":"1000",
             **{field:"50" for field in cfg["keys"]}}
            for code in cfg["codes"]]


class TestCotWeekWatch(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dbfile=Path(self.temp.name)/"private"/"remura-prices.sqlite3"
        db=connect(self.dbfile)
        cot_monitor.ensure_table(db)
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def archive(self,kind,week,missing=(),seen=None):
        db=connect(self.dbfile)
        with db:
            for code in cot_monitor.DATASETS[kind]["codes"]:
                if code in missing:
                    continue
                db.execute(
                    "INSERT OR IGNORE INTO cot_reports VALUES (?,?,?,?,?,?,?,?)",
                    (kind,code,week,1000,50,50,40,40))
                if seen is not None:
                    db.execute(
                        "INSERT OR IGNORE INTO cot_first_seen VALUES(?,?,?,?)",
                        (kind,code,week,seen.isoformat()))
        db.close()

    def sync(self,now=RECENT,missing=()):
        def fetch(kind,_):
            data=row_feed(kind,LATEST)+row_feed(kind,PREVIOUS)
            if kind=="disagg":
                data=[r for r in data
                      if not (r["report_date_as_yyyy_mm_dd"].startswith(LATEST)
                              and r["cftc_contract_market_code"] in missing)]
            return data
        return cot_monitor.collect_once(self.dbfile,now,fetch)

    def result(self,enabled=True,now=NOW):
        return cot_week_watch.cot_week_watch_status(
            self.dbfile,enabled,now)

    def test_real_collector_creates_new_capture_and_does_not_fake_legacy(self):
        for kind in ("tff","disagg"):
            self.archive(kind,PREVIOUS)
        self.sync()
        report=self.result()
        self.assertEqual(report["schema"],"remura-cot-week-watch-v1")
        self.assertEqual(report["status"],"ready")
        self.assertEqual(report["expectedContracts"],14)
        self.assertEqual(report["latestCommonCompleteWeek"],LATEST)
        self.assertEqual(report["previousCommonCompleteWeek"],PREVIOUS)
        self.assertTrue(report["hasTwoCompleteReferenceWeeks"])
        self.assertTrue(report["latestWeekLocallyCapturedIn48h"])
        self.assertEqual(report["datasets"]["tff"]["firstSeenKnown"],11)
        self.assertEqual(report["datasets"]["disagg"]["firstSeenKnown"],3)
        self.assertEqual(report["weeks"][1]["datasets"]["tff"]["firstSeenUnknown"],11)
        self.assertEqual(report["weeks"][1]["datasets"]["disagg"]["firstSeenUnknown"],3)
        self.assertFalse(report["officialReleaseTimeVerified"])
        # Only newly seen 2026-10-27 keys are stamped; repetition changes nothing.
        self.sync(now=LATER)
        db=connect(self.dbfile)
        try:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM cot_first_seen").fetchone()[0],14)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM cot_reports").fetchone()[0],28)
            self.assertEqual(db.execute(
                "SELECT DISTINCT first_seen_at FROM cot_first_seen"
            ).fetchall(),[(RECENT.isoformat(),)])
        finally:
            db.close()
        # A price-only cycle must not manufacture a new COT week.
        db=connect(self.dbfile)
        set_status(db,prices_last_attempt=LATER.isoformat())
        db.close()
        self.assertEqual(self.result()["latestCommonCompleteWeek"],LATEST)

    def test_partial_latest_week_remains_visible_and_warns_exact_missing(self):
        for kind in ("tff","disagg"):
            self.archive(kind,PREVIOUS)
        self.sync(missing=("067651",))
        r=self.result()
        self.assertEqual(r["status"],"attention")
        self.assertEqual(r["latestCommonCompleteWeek"],PREVIOUS)
        self.assertIsNone(r["previousCommonCompleteWeek"])
        self.assertFalse(r["latestWeekLocallyCapturedIn48h"])
        self.assertEqual(r["datasets"]["disagg"]["state"],"incomplete")
        self.assertEqual(r["datasets"]["disagg"]["missingCodes"],["067651"])
        self.assertEqual(r["datasets"]["tff"]["state"],"ok")
        self.assertEqual(r["weeks"][0]["datasets"]["disagg"]["present"],2)
        self.assertEqual(r["weeks"][0]["datasets"]["disagg"]["expected"],3)
        self.assertEqual(r["weeks"][0]["complete"],False)

    def test_successful_archive_with_failed_source_is_not_ready(self):
        for kind in ("tff","disagg"):
            self.archive(kind,PREVIOUS)
        self.sync()
        def broken(kind,now):
            if kind=="tff":
                raise RuntimeError("source unavailable")
            return row_feed(kind,LATEST)
        cot_monitor.collect_once(self.dbfile,LATER,broken)
        # Evaluate after the simulated collection, not before its timestamp.
        r=self.result(now=LATER+dt.timedelta(minutes=1))
        self.assertEqual(r["datasets"]["tff"]["state"],"source_error")
        self.assertEqual(r["datasets"]["disagg"]["state"],"ok")
        self.assertEqual(r["status"],"attention")
        self.assertEqual(r["latestCommonCompleteWeek"],LATEST)

    def test_stale_report_is_review_not_claim_of_data_loss(self):
        for kind in ("tff","disagg"):
            self.archive(kind,PREVIOUS)
        r=self.result(now=dt.datetime(2026,11,11,10,tzinfo=UTC))
        self.assertEqual(r["datasets"]["tff"]["state"],"age_review")
        self.assertEqual(r["datasets"]["disagg"]["state"],"age_review")
        self.assertEqual(r["status"],"attention")
        self.assertEqual(r["datasets"]["tff"]["reportAgeDays"],22)
        self.assertFalse(r["latestWeekLocallyCapturedIn48h"])

    def test_disable_unknown_and_future_firstseen_not_accepted(self):
        for kind in ("tff","disagg"):
            self.archive(kind,LATEST)
            self.archive(kind,PREVIOUS)
        disabled=self.result(False)
        self.assertEqual(disabled["status"],"disabled")
        self.assertFalse(disabled["latestWeekLocallyCapturedIn48h"])
        db=connect(self.dbfile)
        set_status(db,cot_tff_state="ok",cot_disagg_state="ok",
                   cot_tff_last_success=RECENT.isoformat(),
                   cot_disagg_last_success=RECENT.isoformat())
        db.execute(
            "INSERT INTO cot_first_seen VALUES(?,?,?,?)",
            ("tff","099741",LATEST,(NOW+dt.timedelta(hours=2)).isoformat()))
        db.commit()
        db.close()
        live=self.result()
        self.assertEqual(live["datasets"]["tff"]["invalidFirstSeen"],1)
        self.assertEqual(live["datasets"]["tff"]["state"],"timestamp_review")
        self.assertEqual(live["datasets"]["tff"]["recentlyCapturedRows48h"],0)
        self.assertFalse(live["latestWeekLocallyCapturedIn48h"])

    def test_unmatched_datasets_do_not_claim_complete_week(self):
        self.archive("tff",LATEST)
        self.archive("disagg",PREVIOUS)
        r=self.result()
        self.assertIsNone(r["latestCommonCompleteWeek"])
        self.assertFalse(r["hasTwoCompleteReferenceWeeks"])
        self.assertEqual(len(r["weeks"]),2)
        self.assertEqual(r["datasets"]["disagg"]["latestCotWeek"],PREVIOUS)

    def test_private_api_no_store_and_missing_database_never_created(self):
        for kind in ("tff","disagg"):
            self.archive(kind,PREVIOUS)
        server=ThreadingHTTPServer(
            ("127.0.0.1",0),private_server.http_handler(self.dbfile))
        task=Thread(target=server.serve_forever,daemon=True)
        task.start()
        try:
            with patch.object(private_server,"cot_sync_enabled",return_value=True),\
                 patch.object(cot_week_watch,"utcnow",return_value=NOW):
                with urlopen(
                    "http://127.0.0.1:"+str(server.server_port)+
                    "/private-api/cot/week-watch",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),
                                     "no-store, max-age=0")
                    status=json.load(response)
            self.assertEqual(status["schema"],"remura-cot-week-watch-v1")
            self.assertEqual(status["expectedContracts"],14)
            self.assertNotIn("password",json.dumps(status).lower())
            self.assertNotIn("token",json.dumps(status).lower())
        finally:
            server.shutdown()
            server.server_close()
            task.join(timeout=2)
        with tempfile.TemporaryDirectory() as d:
            missing=Path(d)/"missing.sqlite3"
            with self.assertRaises(FileNotFoundError):
                cot_week_watch.cot_week_watch_status(missing,True,NOW)
            self.assertFalse(missing.exists())


if __name__=="__main__":
    unittest.main()
