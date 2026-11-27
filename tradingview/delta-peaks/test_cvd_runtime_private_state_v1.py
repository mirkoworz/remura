#!/usr/bin/env python3
# REMURA v0.8.83 LAB — 14/11/2026 20:31 CET — synthetic only
import sys,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_runtime_private_state_v1 as s
import cvd_runtime_one_shot_v2 as o
from cvd_runtime_singleflight_v1 import NAME as LOCK
from test_cvd_runtime_resource_gate_v1 import fixture
from cvd_private_runtime_preview_v1 import MIN_CLOSE_MS
NOW=s.bucket(MIN_CLOSE_MS+900000)
def result(cutoff,origin="SYNTHETIC"):
    return {"schema":"remura.tv.private.runtime.preview.v1","status":"LOCAL_PREVIEW_ONLY","origin":origin,
        "raw_export_returned":False,"notifications_enabled":False,"orders_enabled":False,"edge":"NOT_ESTABLISHED",
        "html":"<!doctype html><title>REMURA LAB — 0.8.75</title><small>v0.8.75 LAB | 14/11/2026 CET | Anteprima offline</small>",
        "notice":{"schema":"remura.tv.diagnostic.notice.preview.v1","notice_id":str(cutoff),"state":"NO_DESCRIPTIVE_PAIR","text":"LAB","candidate_count":0,"tv_cvd_match_count":0,"tv_cvd_reasons":{},"auxiliary_summary":None,"would_send":False,"sent":False,"orders_enabled":False},
        "coverage":{"requested_slots":1,"valid_unique_bars":0,"missing_requested_slots":1,"first_requested_close_ms":cutoff-s.DELAY,"last_requested_close_ms":cutoff-s.DELAY,"basis":"MATURE_REQUESTED_SLOTS_NOT_MARKET_CALENDAR","latest_immature_bars_not_queried":True,"legacy_fxcm_export_supplied":False,"scientific_benchmarks_computed":False}}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/LOCK).touch(mode=0o600)
    @contextmanager
    def store(self,origin="SYNTHETIC"):
        with s.open_state(self.root,origin=origin,guard=lambda:None,explicit=True) as store:yield store
    def test_bucket_and_durable_claim(self):
        self.assertEqual(s.bucket(NOW+899999),NOW)
        with self.store() as x:self.assertTrue(x.claim(NOW))
        with self.store() as x:
            self.assertFalse(x.claim(NOW))
            with self.assertRaises(ValueError):x.claim(NOW-s.PERIOD)
            self.assertIsNone(x.read()["last_success"])
    def test_last_success_retained_after_next_claim(self):
        with self.store() as x:
            x.claim(NOW);flags=x.complete(NOW,result(NOW),now=NOW+1)
            self.assertFalse(flags["diagnostic_aggregate_unchanged"])
            x.claim(NOW+s.PERIOD)
            self.assertEqual(x.read()["last_success"]["cutoff_ms"],NOW)
        with self.store() as x:
            flags=x.complete(NOW+s.PERIOD,result(NOW+s.PERIOD),now=NOW+s.PERIOD+1)
            self.assertTrue(flags["diagnostic_aggregate_unchanged"])
            self.assertFalse(flags["notice_sent"])
            self.assertIn("0.8.83",x.read()["last_success"]["html"])
            self.assertEqual((self.root/s.NAME).stat().st_mode&0o777,0o600)
    def test_scope_and_corruption_fail_closed(self):
        with self.store() as x:x.claim(NOW)
        with self.store("LOCAL_SNAPSHOT") as x:
            with self.assertRaises(ValueError):x.read()
        (self.root/s.NAME).write_text("{}")
        with self.store() as x:
            with self.assertRaises(ValueError):x.claim(NOW+s.PERIOD)
    def test_rejected_preview_never_replaces_last(self):
        with self.store() as x:
            x.claim(NOW);x.complete(NOW,result(NOW),now=NOW)
            x.claim(NOW+s.PERIOD)
            bad=result(NOW+s.PERIOD);bad["notice"]["sent"]=True
            with self.assertRaises(ValueError):x.complete(NOW+s.PERIOD,bad,now=NOW+s.PERIOD)
            self.assertEqual(x.read()["last_success"]["cutoff_ms"],NOW)
    def test_size_failure_preserves_claim(self):
        with self.store() as x:
            x.claim(NOW)
            with patch.object(s,"MAX_BYTES",1024):
                bad=result(NOW);bad["html"]+="a"*3000
                with self.assertRaises(ValueError):x.complete(NOW,bad,now=NOW)
            self.assertEqual(x.read()["claim_ms"],NOW)
            self.assertIsNone(x.read()["last_success"])
    @contextmanager
    def prep(self,*args,**kwargs):
        yield None,None,{}
    def call(self,collector,now=NOW):
        host,budget=fixture();host["observed_ms"]=budget["observed_ms"]=now
        with patch.object(o.time,"time_ns",return_value=now*1000000),patch.object(o.time,"monotonic_ns",return_value=0),patch.object(o,"sample_host",return_value=host),patch.object(o,"prepared",side_effect=self.prep) as prep,patch.object(o,"collect_guarded",side_effect=collector) as collect:
            try:return o.run_once(self.root,{},self.root,"","",budget=budget,explicit=True,origin="SYNTHETIC")
            finally:self.calls=(prep.call_count,collect.call_count)
    def test_sequential_duplicate_zero_collection(self):
        a=self.call(lambda *a,**kw:result(kw["now"]))
        self.assertEqual(a["status"],"LOCAL_PREVIEW_SAVED")
        b=self.call(lambda *a,**kw: self.fail("duplicate collection"),NOW+1000)
        self.assertEqual(b["status"],"ALREADY_CLAIMED_NO_COLLECTION")
        self.assertEqual(self.calls,(0,0))
    def test_failed_collection_no_retry_in_same_bucket(self):
        def fail(*a,**kw):raise RuntimeError("synthetic")
        with self.assertRaises(RuntimeError):self.call(fail)
        self.assertFalse(self.call(lambda *a,**kw:self.fail("retry"))["collection_attempted"])
        self.assertEqual(self.calls,(0,0))
        self.assertEqual(self.call(lambda *a,**kw:result(kw["now"]),NOW+s.PERIOD)["status"],"LOCAL_PREVIEW_SAVED")
    def test_symlink_rejected(self):
        (self.root/s.NAME).symlink_to(self.root/LOCK)
        with self.store() as x:
            with self.assertRaises(OSError):x.read()
if __name__=="__main__":unittest.main()
