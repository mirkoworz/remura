#!/usr/bin/env python3
# REMURA v0.8.84 LAB — 14/11/2026 20:34 CET — synthetic only
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_runtime_private_state_v1 as s
import cvd_private_dashboard_reader_v1 as d
from cvd_runtime_capacity_envelope_v1 import envelope
from test_cvd_runtime_private_state_v1 import NOW,result

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def read(self,now=NOW):
        return d.read_dashboard(self.root,now=now,origin="SYNTHETIC",explicit=True)
    def claim(self,cut=NOW):
        with s.open_state(self.root,origin="SYNTHETIC",guard=lambda:None,explicit=True) as x:x.claim(cut)
    def complete(self,cut=NOW,n=0):
        r=result(cut)
        r["html"]="<!doctype html><title>REMURA LAB — 0.8.75</title><main><header>v0.8.75 LAB | 14/11/2026 CET | Anteprima offline</header></main>"
        r["coverage"].update(valid_unique_bars=n,missing_requested_slots=1-n)
        with s.open_state(self.root,origin="SYNTHETIC",guard=lambda:None,explicit=True) as x:x.complete(cut,r,now=cut+1)
    def test_missing_and_incomplete(self):
        self.assertEqual(self.read()["status"],"NO_SAVED_RESULT")
        self.assertEqual(list(self.root.iterdir()),[])
        self.claim();self.assertEqual(self.read()["status"],"INCOMPLETE_NO_RESULT")
    def test_empty_then_old_and_incomplete(self):
        self.claim();self.complete()
        self.assertEqual(self.read(NOW+1)["status"],"CURRENT_EMPTY")
        self.assertEqual(self.read(NOW+s.PERIOD)["status"],"OLDER_RESULT")
        self.claim(NOW+s.PERIOD)
        r=self.read(NOW+s.PERIOD);self.assertEqual(r["status"],"INCOMPLETE_NEWER_CLAIM")
        self.assertEqual(r["age_ms"],s.PERIOD);self.assertFalse(r["orders_enabled"])
        self.assertIn("tentativo successivo incompleto",r["html"])
    def test_complete_is_not_live(self):
        self.claim();self.complete(n=1)
        r=self.read(NOW+1);self.assertEqual(r["status"],"CURRENT_REQUESTED_COMPLETE")
        self.assertFalse(r["market_calendar_verified"]);self.assertFalse(r["live_authorized"])
        self.assertIn("v0.8.84 LAB",r["html"])
    def test_future_clock_and_corruption(self):
        self.claim();self.complete()
        self.assertEqual(self.read(NOW)["status"],"CLOCK_UNVERIFIED")
        self.assertEqual(self.read(NOW-1)["status"],"CLOCK_UNVERIFIED")
        (self.root/s.NAME).write_text("not json")
        self.assertEqual(self.read()["status"],"STATE_UNAVAILABLE")
    def test_no_write_and_origin_scope(self):
        self.claim();self.complete()
        f=self.root/s.NAME;before=f.read_bytes();mtime=f.stat().st_mtime_ns
        self.read(NOW+1)
        self.assertEqual(f.read_bytes(),before);self.assertEqual(f.stat().st_mtime_ns,mtime)
        self.assertEqual(d.read_dashboard(self.root,now=NOW+1,explicit=True)["status"],"STATE_UNAVAILABLE")
        with self.assertRaises(ValueError):d.read_dashboard(self.root,now=NOW+1)
    def test_envelope(self):
        r=envelope();self.assertEqual(r["daily_utc_buckets"],96)
        self.assertEqual(r["max_d1_api_calls"],576)
        self.assertEqual(r["observed_read_threshold_times_buckets"],1920000)
        self.assertFalse(r["read_threshold_is_hard_cap"])
if __name__=="__main__":unittest.main()
