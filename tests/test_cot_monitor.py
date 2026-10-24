"""Offline safety tests for private official CFTC snapshots."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from price_feed import UTC
from price_store import connect
import cot_monitor as cot

NOW=dt.datetime(2026,10,24,18,0,tzinfo=UTC)

def rows(dataset, date="2026-10-20",value=50):
    spec=cot.DATASETS[dataset]
    return [{"report_date_as_yyyy_mm_dd":date+"T00:00:00",
             "cftc_contract_market_code":code,
             "open_interest_all":"1000",
             **{field:str(value) for field in spec["keys"]}}
            for code in spec["codes"]]

class TestCftcMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"private"/"prices.sqlite3"
    def tearDown(self):self.tmp.cleanup()

    def test_official_tff_disagg_urls_only_with_bounded_codes_and_columns(self):
        for name,spec in cot.DATASETS.items():
            url=cot.build_url(name,NOW)
            parts=urlparse(url)
            self.assertIn(parts.hostname,("publicreporting.cftc.gov","publicreportinghub.cftc.gov"))
            self.assertEqual(parts.path,"/resource/"+spec["id"]+".json")
            p=parse_qs(parts.query)
            self.assertEqual(p["$limit"],["3000"])
            self.assertIn("cftc_contract_market_code IN",p["$where"][0])
            self.assertNotIn("password",url.lower())
        with self.assertRaises(ValueError):
            cot.build_url("tff",NOW,"https://example.com")

    def test_validates_tracked_report_and_rejects_future_or_bad_numbers(self):
        self.assertEqual(len(cot.normalize("tff",rows("tff"),NOW)),11)
        self.assertEqual(len(cot.normalize("disagg",rows("disagg"),NOW)),3)
        invalid=rows("tff")
        invalid[0]["asset_mgr_positions_long"]="NaN"
        invalid[1]["report_date_as_yyyy_mm_dd"]="2030-01-01T00:00:00"
        invalid[2]["cftc_contract_market_code"]="UNKNOWN"
        self.assertEqual(len(cot.normalize("tff",invalid,NOW)),8)
        with self.assertRaises(ValueError):cot.normalize("tff",[],NOW)
        conflict=rows("tff")
        extra=dict(conflict[0]);extra["asset_mgr_positions_long"]="42";conflict.append(extra)
        with self.assertRaises(ValueError):cot.normalize("tff",conflict,NOW)

    def test_maintains_sqlite_history_and_never_invents_weekend_report(self):
        feed=lambda ds,now:rows(ds)
        r=cot.collect_once(self.path,NOW,feed)
        self.assertEqual(r["errors"],{})
        self.assertEqual(r["saved"],{"tff":11,"disagg":3})
        s=cot.public_status(self.path,True,NOW)
        self.assertEqual(s["state"],"ready")
        self.assertEqual(s["datasets"]["tff"]["lastReportDate"],"2026-10-20")
        self.assertEqual(s["datasets"]["disagg"]["contracts"],3)
        self.assertNotIn("first_long",json.dumps(s))
        self.assertNotIn("token",json.dumps(s).lower())
        again=cot.collect_once(self.path,NOW,feed)
        self.assertEqual(again["saved"],r["saved"])
        db=connect(self.path)
        try:self.assertEqual(db.execute("SELECT count(*) FROM cot_reports").fetchone()[0],14)
        finally:db.close()
        saturday=dt.datetime(2026,10,24,20,0,tzinfo=UTC)
        self.assertEqual(cot.public_status(self.path,True,saturday)["state"],"ready")
        old=dt.datetime(2026,11,15,10,0,tzinfo=UTC)
        self.assertEqual(cot.public_status(self.path,True,old)["state"],"waiting")

    def test_source_failure_preserves_prior_good_data_and_is_not_ready(self):
        cot.collect_once(self.path,NOW,lambda ds,now:rows(ds))
        def broken(ds,now):
            if ds=="tff":raise RuntimeError("no connection")
            return rows(ds)
        report=cot.collect_once(self.path,NOW,broken)
        self.assertEqual(report["errors"],{"tff":"unavailable"})
        self.assertEqual(cot.public_status(self.path,True,NOW)["state"],"waiting")
        db=connect(self.path)
        try:self.assertEqual(db.execute("SELECT count(*) FROM cot_reports").fetchone()[0],14)
        finally:db.close()

    def test_disabled_reports_do_not_claim_monitoring_active(self):
        status=cot.public_status(self.path,False,NOW)
        self.assertEqual(status["state"],"disabled")
        self.assertEqual(status["datasets"]["tff"]["status"],"disabled")
        self.assertIsNone(status["datasets"]["tff"]["lastReportDate"])

if __name__=="__main__":unittest.main()
