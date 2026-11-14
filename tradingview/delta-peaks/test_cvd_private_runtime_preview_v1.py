#!/usr/bin/env python3
# REMURA v0.8.76 LAB — 14/11/2026 17:10 CET — synthetic only
import json,sqlite3,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_private_runtime_preview_v1 as m
from test_cvd_squalincome_asof_preview_v1 import coherent
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,mock_audit
from test_cvd_batch_nonoverlap_preview_v1 import response
NOW=T0+120000
def windows(now=NOW):
    return [{"start_ms":a,"end_ms":b,"rows":[]} for a,b in m.plan(now)]
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.core=sqlite3.connect(":memory:");self.core.execute("PRAGMA query_only=ON")
        s=types.ModuleType("scripts")
        s.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
        self.p=patch.dict(sys.modules,{"scripts":s});self.p.start()
    def tearDown(self):
        self.p.stop();self.core.close()
    def test_plan_max_and_maturity(self):
        pages=m.plan(NOW+10*m.DAY)
        self.assertLessEqual(len(pages),5)
        self.assertEqual(pages[-1][1],T0+10*m.DAY)
        self.assertTrue(all(a==p+m.M5 for (_,p),(a,_) in zip(pages,pages[1:])))
        with self.assertRaises(m.AuditError):m.plan(m.MIN_CLOSE_MS)
    def test_end_to_end(self):
        w=windows()
        w[-1]["rows"]=[coherent()]
        r=m.preview(self.core,w,now=NOW,origin="SYNTHETIC")
        self.assertEqual(r["coverage"]["valid_unique_bars"],1)
        self.assertEqual(r["notice"]["tv_cvd_match_count"],1)
        self.assertIn("DATI SINTETICI",r["html"])
        self.assertFalse(r["notice"]["sent"]);self.assertFalse(r["orders_enabled"])
        self.assertNotIn("raw_json",json.dumps(r))
    def test_empty_and_invalid_window(self):
        r=m.preview(self.core,windows(),now=NOW)
        self.assertEqual(r["coverage"]["valid_unique_bars"],0)
        self.assertEqual(r["notice"]["tv_cvd_match_count"],0)
        with self.assertRaises(ValueError):m.preview(self.core,[],now=NOW)
    def test_conflict_fails_closed(self):
        w=windows();w[-1]["rows"]=[coherent(),dict(coherent(),received_at_ms=T0+6000)]
        with self.assertRaises(ValueError):m.preview(self.core,w,now=NOW)
    def test_explicit_and_db_before_network(self):
        with patch.object(m,"api_request") as api:
            with self.assertRaises(m.AuditError):m.collect_test_preview(self.core,"","",now=NOW)
            self.core.execute("PRAGMA query_only=OFF")
            with self.assertRaises(ValueError):m.collect_test_preview(self.core,"","",now=NOW,explicit=True)
            api.assert_not_called()
    def call_mock(self,reply):
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="token"),
              patch.object(m,"inspect_verified_inventory",return_value={m.MAIN_DB:"main",m.TEST_DB:"test"}),
              patch.object(m,"api_request",return_value={}) as api,
              patch.object(m,"fetch_page",return_value=reply) as page):
            r=m.collect_test_preview(self.core,"","",now=NOW,explicit=True)
            self.assertEqual(api.call_count,1)
            self.assertEqual(page.call_count,len(m.plan(NOW)))
            self.assertTrue(all(c.args[1]=="test" for c in page.call_args_list))
            return r
    def test_usage_metadata(self):
        r=self.call_mock(response([],{"rows_read":1,"rows_written":0}))
        self.assertEqual(r["collection"]["rows_read"],len(m.plan(NOW)))
        self.assertIsNone(r["collection"]["account_quota_utilization"])
        for bad in (response([]),response([],{"rows_read":20001,"rows_written":0})):
            with self.assertRaises(m.AuditError):self.call_mock(bad)
if __name__=="__main__":unittest.main()
