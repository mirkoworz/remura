#!/usr/bin/env python3
# REMURA v0.8.82 LAB — 14/11/2026 20:28 CET — synthetic only
import os,sys,tempfile,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_runtime_singleflight_v1 as lock
import cvd_guarded_collection_v2 as c
import cvd_runtime_one_shot_v1 as o
from test_cvd_telemetry_preview_v1 import T0
from test_cvd_batch_nonoverlap_preview_v1 import response
from test_cvd_runtime_resource_gate_v1 import fixture
NOW=T0+120000

class LockTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.f=self.root/lock.NAME
        self.f.touch(mode=0o600)
    def test_busy_and_release_on_failure(self):
        with self.assertRaisesRegex(RuntimeError,"synthetic"):
            with lock.single_flight(self.root) as check:
                check()
                with self.assertRaisesRegex(ValueError,"runtime_already_running"):
                    with lock.single_flight(self.root):pass
                raise RuntimeError("synthetic")
        with lock.single_flight(self.root) as check:check()
        self.assertEqual(self.f.read_bytes(),b"")
    def test_permissions_symlink_and_replaced(self):
        self.f.chmod(0o644)
        with self.assertRaises(ValueError):
            with lock.single_flight(self.root):pass
        self.f.chmod(0o600)
        with lock.single_flight(self.root) as check:
            self.f.rename(self.root/"old");self.f.touch(mode=0o600)
            with self.assertRaisesRegex(ValueError,"runtime_lock_replaced"):check()
        self.f.unlink();self.f.symlink_to(self.root/"old")
        with self.assertRaises(OSError):
            with lock.single_flight(self.root):pass

class CollectTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
    def run_mock(self,guard):
        with patch.object(c,"require_account_id",return_value="account"),patch.object(c,"require_account_token",return_value="token"),patch.object(c,"inspect_verified_inventory",return_value={c.MAIN_DB:"main",c.TEST_DB:"test"}),patch.object(c,"api_request",return_value={}) as api,patch.object(c,"fetch_page",return_value=response([],{"rows_read":1,"rows_written":0})) as page,patch.object(c,"preview",return_value={"status":"LOCAL_PREVIEW_ONLY"}) as render:
            try:r=c.collect_guarded(self.db,"","",now=NOW,explicit=True,guard=guard)
            finally:self.calls=(api.call_count,page.call_count,render.call_count)
        return r
    def test_guard_at_all_boundaries(self):
        calls=[]
        r=self.run_mock(lambda:calls.append(1))
        self.assertEqual(self.calls,(1,len(c.plan(NOW)),1))
        self.assertEqual(len(calls),len(c.plan(NOW))+3)
        self.assertEqual(r["collection"]["rows_written"],0)
    def test_guard_blocks_before_inventory_and_before_page(self):
        for fail,expected in ((1,(0,0,0)),(2,(1,0,0)),(len(c.plan(NOW))+2,(1,len(c.plan(NOW)),0)),(len(c.plan(NOW))+3,(1,len(c.plan(NOW)),1))):
            calls=[]
            def stop():
                calls.append(1)
                if len(calls)==fail:raise ValueError("blocked")
            with self.assertRaisesRegex(ValueError,"blocked"):self.run_mock(stop)
            self.assertEqual(self.calls,expected)
    def test_explicit_required_and_no_guard(self):
        with patch.object(c,"api_request") as api:
            with self.assertRaises(c.AuditError):c.collect_guarded(self.db,"","",now=NOW,explicit=True)
            api.assert_not_called()

class OneShotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/lock.NAME).touch(mode=0o600)
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
    @contextmanager
    def prepared(self,*args,**kwargs):
        yield self.db,None,{}
    def test_clock_gate_and_frozen_cutoff(self):
        host,budget=fixture();now=host["observed_ms"]
        with patch.object(o.time,"time_ns",return_value=now*1000000),patch.object(o.time,"monotonic_ns",return_value=10*1000000),patch.object(o,"sample_host",return_value=host),patch.object(o,"prepared",side_effect=self.prepared),patch.object(o,"collect_guarded",return_value={"status":"LOCAL_PREVIEW_ONLY"}) as collect:
            r=o.run_once(self.root,{},self.root,"","",budget=budget,explicit=True)
            self.assertEqual(r["cutoff_ms"],now)
            self.assertEqual(collect.call_args.kwargs["now"],now)
            self.assertFalse(r["live_authorized"]);self.assertFalse(r["notifications_enabled"])
        with lock.single_flight(self.root):pass
    def test_stale_budget_and_clock_jump_block_before_prepare(self):
        host,budget=fixture();now=host["observed_ms"]
        for sample,wall in ((dict(host,available_bytes=0),[now,now]),(host,[now,now+10000])):
            with patch.object(o.time,"time_ns",side_effect=[x*1000000 for x in wall]),patch.object(o.time,"monotonic_ns",return_value=0),patch.object(o,"sample_host",return_value=sample),patch.object(o,"prepared") as prep,patch.object(o,"collect_guarded") as collect:
                with self.assertRaises(ValueError):o.run_once(self.root,{},self.root,"","",budget=budget,explicit=True)
                prep.assert_not_called();collect.assert_not_called()
    def test_explicit_and_busy_never_collect(self):
        host,budget=fixture()
        with patch.object(o,"collect_guarded") as collect:
            with self.assertRaises(ValueError):o.run_once(self.root,{},self.root,"","",budget=budget)
            with lock.single_flight(self.root):
                with self.assertRaisesRegex(ValueError,"runtime_already_running"):o.run_once(self.root,{},self.root,"","",budget=budget,explicit=True)
            collect.assert_not_called()
if __name__=="__main__":unittest.main()
