#!/usr/bin/env python3
# REMURA v0.8.69 LAB — 14/11/2026 CET — synthetic only.
import json,sqlite3,sys,types,unittest
from unittest.mock import patch
from test_cvd_pilot_analytic_reader_v1 import row
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,stamp,mock_audit
from cvd_squalincome_asof_preview_v1 import index_rows,at_decision,join_local_pairs
from research_dossier_preview_v1 import dossier
from research_dashboard_preview_v1 import render,notification_preview

def coherent():
    r=row();e=json.loads(r["raw_json"]);p=e["snapshot"]
    p["signed_result_atr"]=(p["ohlc"]["close"]-p["ohlc"]["open"])/p["ohlc"]["atr14"]
    p["efficiency"]=p["signed_result_atr"]/p["effort"]
    p["footprint"]["delta_pct"]=100*250/3550
    r["raw_json"]=json.dumps(e)
    return r

class CVDJoinTests(unittest.TestCase):
    def test_match_and_direction(self):
        j=join_local_pairs([pair()],[coherent()],as_of_ms=T0+8000)
        self.assertEqual(j["pair_counts"],{"DESCRIPTIVE_MATCH":1})
        self.assertEqual(j["cot_vs_cvd_selected"],{"ALIGNED":1})
        self.assertFalse(j["ct_cvd_same_decision_proven"])
        self.assertFalse(j["orders_enabled"])
    def test_late_no_fallback(self):
        self.assertEqual(at_decision(index_rows([coherent()]),close_ms=T0,decision_ms=T0+4999)[0],"NOT_KNOWN_AT_DECISION")
        self.assertEqual(at_decision(index_rows([coherent()]),close_ms=T0+900000,decision_ms=T0+906000)[0],"NO_EXACT_CLOSE")
    def test_old_feed_rejected(self):
        with self.assertRaises(ValueError):
            index_rows([dict(coherent(),symbol="FXCM:EURUSD")])
    def test_conflict_and_duplicates_asof(self):
        r=coherent(); later=dict(r,received_at_ms=T0+7000)
        self.assertEqual(at_decision(index_rows([r,r,later]),close_ms=T0,decision_ms=T0+6000)[0],"DESCRIPTIVE_MATCH")
        self.assertEqual(at_decision(index_rows([r,later]),close_ms=T0,decision_ms=T0+8000)[0],"BLOCKED_CONFLICT")
    def test_quality_and_identity(self):
        for r,state in ((row(),"BLOCKED_DIAGNOSTIC_REVIEW"),(dict(coherent(),event_key="bad"),"BLOCKED_INVALID"),
                        (dict(coherent(),is_timely=1),"BLOCKED_INVALID")):
            self.assertEqual(at_decision(index_rows([r]),close_ms=T0,decision_ms=T0+6000)[0],state)
    def test_dossier_dashboard_and_preview(self):
        db=sqlite3.connect(":memory:")
        try:
            db.execute("PRAGMA query_only=ON")
            packages=types.ModuleType("scripts")
            packages.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
            with patch.dict(sys.modules,{"scripts":packages}):
                r=dossier(db,[],as_of_utc=stamp(T0+8000),origin="SYNTHETIC",cvd_rows=[coherent()])
            self.assertEqual(r["pair_counts"],{"NO_CURRENT_ASOF_OBSERVATION":1})
            self.assertEqual(r["tv_cvd_join"]["pair_counts"],{"DESCRIPTIVE_MATCH":1})
            self.assertEqual(r["sentiment_status"],"UNKNOWN_NOT_JOINED")
            a=notification_preview(r)
            self.assertEqual(a["tv_cvd_match_count"],1)
            self.assertFalse(a["sent"])
            self.assertIn("FX:EURUSD",render(r))
            self.assertNotIn("raw_json",render(r))
            r["tv_cvd_join"]["orders_enabled"]=True
            with self.assertRaises(ValueError):
                render(r)
        finally:
            db.close()
    def test_before_deployment(self):
        t=1793786400000
        t-=t%900000
        self.assertEqual(at_decision({},close_ms=t,decision_ms=t+6000)[0],"BEFORE_CVD_DEPLOYMENT")
    def test_no_selected_direction_is_not_opposition(self):
        r=coherent();e=json.loads(r["raw_json"])
        e["cvd"]["cvd_bull"]=False
        r["raw_json"]=json.dumps(e)
        j=join_local_pairs([pair()],[r],as_of_ms=T0+8000)
        self.assertEqual(j["cot_vs_cvd_selected"],{"NO_SELECTED_DIRECTION":1})
if __name__=="__main__":
    unittest.main()
