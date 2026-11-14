#!/usr/bin/env python3
# REMURA v0.8.73 LAB — 14/11/2026 17:04 CET — synthetic mocked unit tests
import sqlite3,types,sys,unittest
from unittest.mock import patch
from test_research_dossier_preview_v1 import pair,stamp,mock_audit
from test_cvd_telemetry_preview_v1 import T0
from test_cvd_squalincome_asof_preview_v1 import coherent
from cvd_auxiliary_same_decision_preview_v1 import audit
class AuxiliaryTests(unittest.TestCase):
    def setUp(self):
        self.core=sqlite3.connect(":memory:");self.core.execute("PRAGMA query_only=ON")
        self.private=sqlite3.connect(":memory:");self.private.execute("PRAGMA query_only=ON")
    def tearDown(self):
        self.core.close();self.private.close()
    def run_audit(self,pairs=None,rows=None,**kwargs):
        s=types.ModuleType("scripts")
        s.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()] if pairs is None else pairs))
        with patch.dict(sys.modules,{"scripts":s}):
            return audit(self.core,kwargs.pop("private",None),[coherent()] if rows is None else rows,
                         as_of_utc=stamp(T0+8000),**kwargs)
    def test_missing_is_unknown(self):
        r=self.run_audit()
        self.assertEqual(r["counts"]["TV_DESCRIPTIVE_MATCH"],1)
        self.assertEqual(r["counts"]["CT_EXACT_UNKNOWN"],1)
        self.assertEqual(r["counts"]["RETAIL_UNKNOWN"],1)
        self.assertFalse(r["missing_is_negative"])
    def test_same_decision_counts_once(self):
        with (patch("cvd_auxiliary_same_decision_preview_v1.exact_events",return_value=[]),
              patch("cvd_auxiliary_same_decision_preview_v1.exact_direction",return_value="ALIGNED"),
              patch("cvd_auxiliary_same_decision_preview_v1.retail_pin",return_value="LOCAL_ORIGINAL_PIN_VERIFIED")):
            r=self.run_audit(private=self.private,retail_root="synthetic",authorized_at="synthetic")
        self.assertEqual(r["counts"]["ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION"],1)
        self.assertEqual(sum(r["matrix"].values()),1)
        self.assertFalse(r["scientific_admission"])
    def test_no_tv_no_four_way_match(self):
        with (patch("cvd_auxiliary_same_decision_preview_v1.exact_events",return_value=[]),
              patch("cvd_auxiliary_same_decision_preview_v1.exact_direction",return_value="ALIGNED"),
              patch("cvd_auxiliary_same_decision_preview_v1.retail_pin",return_value="LOCAL_ORIGINAL_PIN_VERIFIED")):
            r=self.run_audit(rows=[],private=self.private,retail_root="synthetic",authorized_at="synthetic")
        self.assertNotIn("ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION",r["counts"])
    def test_cap_before_aux_reads(self):
        with patch("cvd_auxiliary_same_decision_preview_v1.exact_events") as e:
            with self.assertRaises(ValueError):
                self.run_audit(pairs=[pair()]*21,private=self.private)
            e.assert_not_called()
    def test_read_only_required(self):
        self.core.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):self.run_audit()
if __name__=="__main__":
    unittest.main()
