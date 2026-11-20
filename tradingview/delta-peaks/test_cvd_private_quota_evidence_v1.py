#!/usr/bin/env python3
# REMURA v0.8.85 LAB — 14/11/2026 20:39 CET — synthetic only
import sys,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_private_quota_evidence_v1 as q
from cvd_runtime_resource_gate_v1 import assess
from test_cvd_runtime_resource_gate_v1 import NOW,fixture

A="a"*32;T="a"*40;D="b"*40
N=q.EXPECTED_NAME
MAIN=q.storage.MAIN_DB_NAME
class Tests(unittest.TestCase):
    def run_mock(self,*,usage=(100,288),workers={"requests_estimate":300},count=2,size=10000,times=None,explicit=True,tokens=(T,D)):
        inv=[(MAIN,"main","eu"),(N,"test","eu")]+[(str(i),str(i),None) for i in range(count-2)]
        with ExitStack() as s:
            s.enter_context(patch.object(q,"require_account_id",return_value=A))
            s.enter_context(patch.object(q,"require_account_token",side_effect=lambda t:t))
            s.enter_context(patch.object(q.time,"time_ns",**({"side_effect":[t*1000000 for t in times]} if times is not None else {"return_value":NOW*1000000})))
            s.enter_context(patch.object(q.time,"monotonic_ns",return_value=0))
            d=s.enter_context(patch.object(q.d1,"query_account_analytics",return_value=usage))
            w=s.enter_context(patch.object(q.workers,"fetch_workers_analytics",return_value=workers))
            api=s.enter_context(patch.object(q,"api_request",return_value={}))
            s.enter_context(patch.object(q,"verify_account_token"))
            s.enter_context(patch.object(q.storage,"parse_inventory",return_value=inv))
            s.enter_context(patch.object(q.storage,"read_db_size",return_value=size))
            try:return q.acquire(A,*tokens,explicit=explicit)
            finally:
                self.calls=(d.call_count,w.call_count,api.call_count)
                self.methods=[x.args[0] for x in api.call_args_list]
                self.analytics_args=d.call_args
    def test_gate_compatible_and_only_get_metadata(self):
        r=self.run_mock()
        self.assertEqual(self.calls,(1,1,4))
        self.assertEqual(self.methods,["GET"]*4)
        self.assertEqual(r["observed_ms"],NOW)
        self.assertEqual(assess(now=NOW,host=fixture()[0],budget=r)["status"],"ONE_SHOT_TEST_PREVIEW_PLAUSIBLE")
        self.assertNotIn(T,str(r));self.assertNotIn(D,str(r))
    def test_requires_optin_and_distinct_tokens(self):
        for kw in ({"explicit":False},{"tokens":(T,T)}):
            with self.assertRaises(ValueError):self.run_mock(**kw)
            self.assertEqual(self.calls,(0,0,0))
    def test_unknown_and_warning_stop_early(self):
        for val,expected in ((None,(1,0,0)),((3500000,0),(1,0,0))):
            with self.assertRaises(q.AuditError):self.run_mock(usage=val)
            self.assertEqual(self.calls,expected)
        with self.assertRaises(q.AuditError):self.run_mock(workers=None)
        self.assertEqual(self.calls,(1,1,0))
    def test_inventory_limit_before_db_metadata(self):
        with self.assertRaises(q.AuditError):self.run_mock(count=7)
        self.assertEqual(self.calls,(1,1,2))
        self.run_mock(count=6);self.assertEqual(self.calls,(1,1,8))
    def test_storage_warning_stops(self):
        with self.assertRaises(q.AuditError):self.run_mock(size=350000000)
        self.assertEqual(self.calls,(1,1,3))
    def test_clock_jump_stops(self):
        with self.assertRaises(q.AuditError):self.run_mock(times=[NOW,NOW+10000])
        self.assertEqual(self.calls,(0,0,0))
    def test_old_evidence_not_relabelled(self):
        r=self.run_mock()
        host=fixture()[0];host["observed_ms"]=NOW+1800001
        self.assertEqual(assess(now=NOW+1800001,host=host,budget=r)["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
