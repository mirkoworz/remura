#!/usr/bin/env python3
# REMURA v0.8.64 LAB — 14/11/2026 CET — mock only
import json,tempfile,unittest
from unittest.mock import patch
from test_cvd_transition_bundle_v1 import config
import cvd_transition_live_bundle_v1 as m

class LiveBundleTests(unittest.TestCase):
    def test_operation_matrix(self):
        for op,state,mode in (("DEPLOY_CVD_TEST",m.ON,"LEGACY"),("ROLLBACK_LEGACY_TEST",m.ON,"CVD_TRUE"),
                              ("STOP_CVD_TEST",m.ON,"CVD_TRUE"),("STOP_CVD_TEST",m.OFF,"LEGACY")):
            m.gate(op,state,mode)
        for op,state,mode in (("DEPLOY_CVD_TEST",m.ON,"CVD_TRUE"),("DEPLOY_CVD_TEST",m.OFF,"LEGACY"),
                              ("ROLLBACK_LEGACY_TEST",m.OFF,"CVD_TRUE"),("STOP_CVD_TEST","UNKNOWN","LEGACY")):
            with self.assertRaises(m.StopUnsafe):
                m.gate(op,state,mode)
    def test_postcheck(self):
        for op,state,mode in (("DEPLOY_CVD_TEST",m.ON,"CVD_TRUE"),("ROLLBACK_LEGACY_TEST",m.ON,"LEGACY"),
                              ("STOP_CVD_TEST",m.OFF,"LEGACY")):
            m.gate(op,state,mode,post=True)
        with self.assertRaises(m.StopUnsafe):
            m.gate("DEPLOY_CVD_TEST",m.ON,"LEGACY",post=True)
    def test_stop_bundle_off_and_legacy(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,"inspect",return_value=(m.ON,"CVD_TRUE",config())):
            (a,b),_=m.prepare("STOP_CVD_TEST","mock","mock","mock",tmp)
            self.assertEqual(json.loads((b/"wrangler.json").read_text())["vars"],{"INGEST_ENABLED":"false"})
    def test_fresh_precheck_binds_exact_manifest_and_code(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,"inspect",return_value=(m.ON,"LEGACY",config())):
            (a,b),cfg=m.prepare("DEPLOY_CVD_TEST","mock","mock","mock",tmp)
            m.verify_target("DEPLOY_CVD_TEST",cfg,tmp,str(a))
            with self.assertRaises(m.StopUnsafe):
                m.verify_target("DEPLOY_CVD_TEST",cfg,tmp,str(b))
            changed=config()
            changed["d1_databases"][0]["database_id"]="00000000-0000-4000-8000-000000000003"
            with self.assertRaises(m.StopUnsafe):
                m.verify_target("DEPLOY_CVD_TEST",changed,tmp,str(a))
            (a/"worker.mjs").write_text("changed")
            with self.assertRaises(m.StopUnsafe):
                m.verify_target("DEPLOY_CVD_TEST",cfg,tmp,str(a))
    def test_bad_state_never_builds(self):
        with patch.object(m,"inspect",return_value=(m.OFF,"LEGACY",config())),patch.object(m,"build_pair") as build:
            with self.assertRaises(m.StopUnsafe):
                m.prepare("DEPLOY_CVD_TEST","mock","mock","mock","mock")
            build.assert_not_called()
if __name__=="__main__":
    unittest.main()
