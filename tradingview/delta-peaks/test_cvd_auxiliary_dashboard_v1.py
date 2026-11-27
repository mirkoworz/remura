#!/usr/bin/env python3
# REMURA v0.8.75 LAB — 14/11/2026 17:07 CET — synthetic only
import sqlite3,types,sys,unittest,copy
from unittest.mock import patch
from test_research_dossier_preview_v1 import pair,stamp,mock_audit
from test_cvd_telemetry_preview_v1 import T0
from test_cvd_squalincome_asof_preview_v1 import coherent
from research_dossier_preview_v1 import dossier
from research_dashboard_preview_v1 import render,notification_preview
class AuxDashboardTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.db.execute("PRAGMA query_only=ON")
        self.ct=sqlite3.connect(":memory:");self.ct.execute("PRAGMA query_only=ON")
    def tearDown(self):
        self.db.close();self.ct.close()
    def make(self,**kw):
        s=types.ModuleType("scripts")
        s.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
        with patch.dict(sys.modules,{"scripts":s}):
            return dossier(self.db,[],as_of_utc=stamp(T0+8000),origin="SYNTHETIC",cvd_rows=[coherent()],**kw)
    def full(self):
        with (patch("cvd_auxiliary_same_decision_preview_v1.exact_events",return_value=[]),
              patch("cvd_auxiliary_same_decision_preview_v1.exact_direction",return_value="ALIGNED"),
              patch("cvd_auxiliary_same_decision_preview_v1.retail_pin",return_value="LOCAL_ORIGINAL_PIN_VERIFIED")):
            return self.make(auxiliary=True,private_cvd_db=self.ct,cvd_secret=b"synthetic-only-secret",retail_root="lab",retail_authorized_at="synthetic")
    def test_default_and_opt_in_unknown(self):
        self.assertIsNone(notification_preview(self.make())["auxiliary_summary"])
        s=notification_preview(self.make(auxiliary=True))["auxiliary_summary"]
        self.assertEqual(s["direction_categories"],{"DIRECTION_UNKNOWN_OR_NOT_SELECTED":1})
        self.assertEqual(s["all_local_proof_types"],0)
    def test_full_synthetic(self):
        r=self.full();n=notification_preview(r);s=n["auxiliary_summary"]
        self.assertEqual(s["all_local_proof_types"],1)
        self.assertEqual(s["direction_categories"],{"BOTH_ALIGNED_WITH_COT":1})
        self.assertFalse(n["sent"])
        page=render(r);self.assertIn("BOTH_ALIGNED_WITH_COT",page)
        self.assertNotIn("synthetic-only-secret",page);self.assertNotIn("<script",page)
        self.assertEqual(n["notice_id"],notification_preview(r)["notice_id"])
    def test_tamper_rejected(self):
        for key,val in (("orders_enabled",True),("eurusd_pairs",2),("retail_direction_used",True),
                        ("matrix",{"<script>":1}),("counts",{"TV_DESCRIPTIVE_MATCH":2})):
            r=self.full();r["auxiliary_same_decision"][key]=val
            with self.assertRaises(ValueError):render(r)
    def test_marginal_and_intersection(self):
        r=self.full();r["auxiliary_same_decision"]["counts"]["CT_EXACT_ALIGNED"]=0
        r["auxiliary_same_decision"]["counts"]["CT_EXACT_OPPOSED"]=1
        with self.assertRaises(ValueError):notification_preview(r)
        r=self.full();r["auxiliary_same_decision"]["counts"]["ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION"]=0
        with self.assertRaises(ValueError):notification_preview(r)
    def test_explicit_and_secret_pair(self):
        for kw in ({"private_cvd_db":self.ct},{"auxiliary":True,"private_cvd_db":self.ct},{"auxiliary":True,"retail_root":"lab"}):
            with self.assertRaises(ValueError):self.make(**kw)
    def test_notice_changes_with_aux(self):
        self.assertNotEqual(notification_preview(self.make())["notice_id"],notification_preview(self.full())["notice_id"])
if __name__=="__main__":unittest.main()
