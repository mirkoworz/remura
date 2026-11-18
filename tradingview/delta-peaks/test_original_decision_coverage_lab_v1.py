# REMURA v0.8.171 LAB — 18/11/2026, sessione delle 17:48 CET
import unittest
import json
from original_decision_coverage_lab_v1 import coverage
from test_research_dossier_preview_v1 import pair,T0
from test_fx_asof_handoff_v1 import good
from test_cvd_squalincome_asof_preview_v1 import coherent
from test_volume_features_v1 import changed

class OriginalCoverageTests(unittest.TestCase):
    def audit(self,legacy,cvd,pairs=None):
        return coverage([pair()] if pairs is None else pairs,legacy,cvd,
                        as_of_ms=T0+8000,synthetic=True)
    def test_joint_coverage_not_equivalence(self):
        r=self.audit([good()],[coherent()])
        self.assertEqual(r["counts"],{"FXCM_PRESENT|FX_PRESENT":1})
        self.assertEqual(r["both_descriptive_present"],1)
        self.assertFalse(r["source_price_equivalence"])
        self.assertFalse(r["outcomes_evaluated"])
        self.assertNotIn("raw_json",json.dumps(r))
    def test_late_cvd_does_not_fill_original_decision(self):
        r=self.audit([good()],[dict(coherent(),received_at_ms=T0+7000)])
        self.assertEqual(r["counts"],{"FXCM_PRESENT|FX_UNKNOWN":1})
    def test_config_mismatch_not_present(self):
        r=self.audit([changed(good(),lambda p:p["quality"].update(lower_tf="2"))],[coherent()])
        self.assertEqual(r["counts"],{"FXCM_UNKNOWN|FX_PRESENT":1})
    def test_empty_and_duplicate(self):
        self.assertEqual(self.audit([],[],pairs=[])["population"],0)
        self.assertEqual(self.audit([],[])["counts"],{"FXCM_UNKNOWN|FX_UNKNOWN":1})
        with self.assertRaises(ValueError):self.audit([],[],pairs=[pair(),pair()])
    def test_explicit_and_separate_feed(self):
        with self.assertRaises(ValueError):coverage([],[],[],as_of_ms=T0)
        with self.assertRaises(ValueError):self.audit([coherent()],[])
        with self.assertRaises(ValueError):self.audit([],[good()])
if __name__=="__main__":unittest.main()
