#!/usr/bin/env python3
# REMURA v0.8.59 LAB — 14/11/2026 12:45 CET — synthetic only
import unittest
from pathlib import Path
from test_telemetry_v1 import sample,T0
from cvd_telemetry_preview_v1 import validate,SCHEMA,SNAPSHOT_SCHEMA,VERSION,SYMBOL,CONFIG,M5

def fixture():
    p=sample()
    p.update(schema=SNAPSHOT_SCHEMA,version=VERSION,symbol=SYMBOL,feed="FX")
    c={"model":"D08_SEGMENT_PORT_V091","intrabar_count":5,"complete":True,
       "continuous":True,"day_valid":True,"segment_id":1,"segment_bars":12,
       "day_key_ms":T0-12*M5,"raw_delta":2400,"trusted_delta":2400,
       "daily_cvd":3000,"segment_cvd":2800,"eligible":True,
       "price_bull":True,"price_bear":False,"cvd_bull":True,"cvd_bear":False,
       "pivot_close_ms":T0-2*M5}
    return {"schema":SCHEMA,"snapshot":p,"configuration":dict(CONFIG),"cvd":c}
def run(p):
    return validate(p,received_ms=T0+5000)

class CVDPreviewTests(unittest.TestCase):
    def test_distinct_cohort(self):
        r=run(fixture())
        self.assertEqual(r["delta_difference"],0)
        self.assertIn(VERSION,r["event_key"])
        self.assertIn(SYMBOL,r["event_key"])
        self.assertFalse(r["predictive_admissible"])
    def test_legacy_and_feed_rejected(self):
        with self.assertRaises(ValueError):
            run(sample())
        p=fixture();p["snapshot"].update(symbol="FXCM:EURUSD",feed="FXCM")
        with self.assertRaises(ValueError):
            run(p)
    def test_config_mutation_rejected(self):
        p=fixture();p["configuration"]["cvd_right"]=3
        with self.assertRaises(ValueError):
            run(p)
    def test_gap_incomplete_unknown(self):
        p=fixture();p["cvd"].update(intrabar_count=4,complete=False,
            continuous=None,day_valid=False,segment_bars=0,raw_delta=None,
            trusted_delta=None,daily_cvd=None,segment_cvd=None,eligible=False,
            price_bull=False,cvd_bull=False,pivot_close_ms=None)
        self.assertIsNone(run(p)["delta_difference"])
    def test_first_complete_after_gap(self):
        p=fixture();p["cvd"].update(continuous=False,day_valid=False,
            segment_bars=1,trusted_delta=None,daily_cvd=None,segment_cvd=None,
            eligible=False,price_bull=False,cvd_bull=False,pivot_close_ms=None)
        self.assertIsNone(run(p)["delta_difference"])
        p["cvd"].update(day_valid=True,daily_cvd=2400)
        with self.assertRaises(ValueError):
            run(p)
    def test_subset_and_causality(self):
        for changes in ({"price_bull":False},{"pivot_close_ms":T0},{"eligible":False}):
            p=fixture();p["cvd"].update(changes)
            with self.assertRaises(ValueError):
                run(p)
    def test_late_rejected(self):
        with self.assertRaises(ValueError):
            validate(fixture(),received_ms=T0+120001)
    def test_sender_static(self):
        s=Path(__file__).with_name("REMURA-ALL-IN-ONE-Premium-v0.9.1-CVD-TELEMETRY-PREVIEW.pine").read_text()
        self.assertIn('input.bool(false, "CVD LAB: payload preview',s)
        self.assertIn('syminfo.tickerid == "FX:EURUSD" and syminfo.prefix == "FX"',s)
        self.assertIn("if not cvd_newDay\n            cvd_validDay := false",s)
        self.assertEqual(s.count("alert(envelope, alert.freq_once_per_bar_close)"),1)
        self.assertIn(SNAPSHOT_SCHEMA,s)
        self.assertIn(SCHEMA,s)
        self.assertNotIn("workers.dev",s)
        self.assertNotIn("alert(payload,",s)

if __name__=="__main__":
    unittest.main()
