#!/usr/bin/env python3
# REMURA v0.8.68 LAB — 14/11/2026 16:46 CET — SYNTHETIC ONLY
import json,unittest
from unittest.mock import patch
from test_cvd_telemetry_preview_v1 import fixture,T0,M5
from test_cvd_pilot_analytic_reader_v1 import row,run
from cvd_radar_preview_v1 import describe
from cvd_archive_preview_v1 import assemble

def report(e):
    return describe(e,received_ms=T0+5000,as_of_ms=T0+120000)

def window(t,end,rows):
    return {"start_ms":t,"end_ms":end,"rows":rows}

class RadarTests(unittest.TestCase):
    def test_observations_no_direction_from_er(self):
        with patch("cvd_radar_preview_v1.diagnose",return_value={}):
            r=report(fixture())
        self.assertEqual(r["candidate"],"BULL")
        self.assertEqual(r["observed"]["er"],"POSITIVE_EFFORT")
        self.assertEqual(r["observed"]["delta_footprint_relation"],"ALIGNED")
        self.assertIn("POSSIBLE_BUYING_EFFORT_ABSORPTION",r["hypotheses"])
        self.assertFalse(r["orders_enabled"])
        day=next(x for x in r["observed"]["levels"] if x["name"]=="day1")
        self.assertIsNone(day["range_touch"])
        self.assertIsNone(day["distance_close_atr"])
    def test_missing_and_review(self):
        e=fixture()
        p=e["snapshot"]
        p["footprint"]={k:False if k=="available" else None for k in p["footprint"]}
        p["quality"]["has_footprint"]=False
        with patch("cvd_radar_preview_v1.diagnose",return_value={"test":"REVIEW"}):
            r=report(e)
        self.assertEqual(r["observed"]["delta_footprint_relation"],"UNKNOWN")
        self.assertEqual(r["hypotheses"],[])
        self.assertEqual(r["status"],"BLOCKED_REVIEW")
    def test_dual_and_asof(self):
        e=fixture();e["cvd"]["price_bear"]=True
        with patch("cvd_radar_preview_v1.diagnose",return_value={}):
            self.assertEqual(report(e)["candidate"],"AMBIGUOUS")
        with self.assertRaises(ValueError):
            describe(e,received_ms=T0+5000,as_of_ms=T0+4999)
    def test_reader_aggregated_only(self):
        r=run([row()])
        self.assertIn("radar",r)
        self.assertNotIn("raw_json",r["radar"])
        self.assertFalse(r["radar"]["orders_enabled"])
    def test_archive_recomputes_24h(self):
        from cvd_telemetry_preview_v1 import validate
        rows=[]
        for i in range(290):
            t=T0+i*M5
            e=fixture();p=e["snapshot"];c=e["cvd"]
            p.update(bar_close_ms=t,bar_open_ms=t-M5,sent_clock_ms=t+1000)
            for k,x in p["level_origin_ms"].items():
                if x is not None: p["level_origin_ms"][k]=x+i*M5
            c.update(price_bull=i in (0,1),cvd_bull=i==0,pivot_close_ms=t-2*M5 if i in (0,1) else None)
            v=validate(e,received_ms=t+5000)
            rows.append(dict(row(),bar_close_ms=t,received_at_ms=t+5000,event_key=v["event_key"],raw_json=json.dumps(e)))
        windows=[window(chunk[0]["bar_close_ms"],chunk[-1]["bar_close_ms"],chunk) for i in range(0,len(rows),72) for chunk in [rows[i:i+72]]]
        with patch("cvd_outcome_readiness_v1.diagnose",return_value={}),patch("cvd_radar_preview_v1.diagnose",return_value={}):
            r=assemble(windows,as_of_ms=T0+289*M5+120000)
        self.assertEqual(r["valid_unique_bars"],290)
        self.assertEqual(r["outcomes"]["horizons"]["1440"]["matched_selected"],1)
        self.assertFalse(r["provenance_attested"])
    def test_archive_rejects_overlap_and_conflict(self):
        w=window(T0,T0,[row()])
        with self.assertRaises(ValueError):
            assemble([w,w],as_of_ms=T0+120000)
        with self.assertRaises(ValueError):
            assemble([window(T0,T0,[row(),dict(row(),received_at_ms=T0+6000)])],as_of_ms=T0+120000)
    def test_archive_empty_gap_and_duplicate(self):
        r=assemble([window(T0,T0+M5,[row(),row()])],as_of_ms=T0+M5+120000)
        self.assertEqual(r["missing_requested_slots"],1)
        self.assertEqual(r["duplicate_rows"],1)
        self.assertEqual(r["outcomes"]["status"],"DESCRIPTIVE_ONLY")

if __name__=="__main__":
    unittest.main()
