#!/usr/bin/env python3
# REMURA v0.8.78 LAB — 14/11/2026 18:00 CET — synthetic only
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_runtime_resource_gate_v1 as m
from cvd_oos_protocol_preview_v1 import clock
NOW=clock("2026-11-14")+12*3600000
def fixture():
    h={"observed_ms":NOW,"available_bytes":512*1024*1024,"load1":0.2,"visible_cpus":1}
    b={"observed_ms":NOW,"complete":True,"reports":{
        "d1":"REMURA_CF_ACCOUNT_QUOTA=OK\nUTC_DAY=2026-11-14; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\nD1_ACCOUNT_ROWS_READ_ESTIMATE=100\nD1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=288",
        "workers":"REMURA_CF_WORKERS_USAGE=OK\nWORKERS_UTC_DAY=2026-11-14; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\nWORKERS_ACCOUNT_REQUESTS_ESTIMATE=300",
        "storage":"REMURA_D1_TEST_STORAGE=OK\nREMURA_D1_TEST_STORAGE_BYTES=10000",
        "account_storage":"REMURA_D1_ACCOUNT_STORAGE=OK\nD1_ACCOUNT_DATABASE_COUNT=2\nD1_ACCOUNT_STORAGE_BYTES=20000\nD1_ACCOUNT_LARGEST_DB_BYTES=10000"}}
    return h,b
class GateTests(unittest.TestCase):
    def check(self,h,b):return m.assess(now=NOW,host=h,budget=b)
    def test_ok_not_live(self):
        r=self.check(*fixture())
        self.assertEqual(r["status"],"ONE_SHOT_TEST_PREVIEW_PLAUSIBLE")
        self.assertFalse(r["live_authorized"]);self.assertFalse(r["cost_verified_zero"])
    def test_host_limits(self):
        for k,v in (("available_bytes",255*1024*1024),("load1",0.8),("observed_ms",NOW-60001),("visible_cpus",0),("load1",float("nan"))):
            h,b=fixture();h[k]=v
            self.assertEqual(self.check(h,b)["status"],"BLOCKED")
    def test_budget_scope_and_freshness(self):
        for k,v in (("observed_ms",NOW-1800001),("observed_ms",NOW+1),("complete",False)):
            h,b=fixture();b[k]=v
            self.assertEqual(self.check(h,b)["status"],"BLOCKED")
        h,b=fixture();b["reports"]["d1"]=b["reports"]["d1"].replace("2026-11-14","2026-11-13")
        self.assertEqual(self.check(h,b)["status"],"BLOCKED")
    def test_numeric_limits_despite_ok(self):
        h,b=fixture();b["reports"]["d1"]=b["reports"]["d1"].replace("ESTIMATE=100","ESTIMATE=3480000")
        self.assertIn("HEADROOM_D1_ACCOUNT_ROWS_READ_ESTIMATE",self.check(h,b)["reasons"])
        h,b=fixture();b["reports"]["workers"]=b["reports"]["workers"].replace("=OK","=WARNING")
        self.assertEqual(self.check(h,b)["status"],"BLOCKED")
    def test_missing_and_duplicate(self):
        h,b=fixture();b["reports"]["storage"]+="\nREMURA_D1_TEST_STORAGE_BYTES=10000"
        self.assertEqual(self.check(h,b)["status"],"BLOCKED")
        h,b=fixture();del b["reports"]["storage"]
        self.assertEqual(self.check(h,b)["status"],"BLOCKED")
    def test_storage_consistency(self):
        h,b=fixture();b["reports"]["account_storage"]=b["reports"]["account_storage"].replace("DB_BYTES=10000","DB_BYTES=9000")
        self.assertIn("STORAGE_INCOHERENT",self.check(h,b)["reasons"])
    def test_block_before_collection(self):
        h,b=fixture();h["available_bytes"]=0
        with patch.object(m,"collect_test_preview") as call:
            r=m.guarded_collect(None,"","",now=NOW,host=h,budget=b,explicit=True)
            self.assertFalse(r["collection_attempted"]);call.assert_not_called()
            with self.assertRaises(ValueError):m.guarded_collect(None,"","",now=NOW,host=h,budget=b)
            call.assert_not_called()
        h,b=fixture()
        with patch.object(m,"collect_test_preview",return_value={"orders_enabled":False}) as call:
            r=m.guarded_collect(None,"","",now=NOW,host=h,budget=b,explicit=True)
            self.assertTrue(r["collection_attempted"]);call.assert_called_once()
if __name__=="__main__":unittest.main()
