# REMURA v0.8.172 LAB — 18/11/2026, sessione successiva alle 17:48 CET
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
    def test_late_vs_absent_and_audit_ceiling(self):
        late=self.audit([dict(good(),received_at_ms=T0+7000)],
                        [dict(coherent(),received_at_ms=T0+7000)])
        self.assertEqual(late["legacy_reason_counts"],{"NOT_KNOWN_AT_DECISION":1})
        self.assertEqual(late["cvd_reason_counts"],{"NOT_KNOWN_AT_DECISION":1})
        absent=self.audit([],[])
        after=self.audit([dict(good(),received_at_ms=T0+9000)],
                         [dict(coherent(),received_at_ms=T0+9000)])
        self.assertEqual(absent,after)
        self.assertEqual(absent["legacy_reason_counts"],{"NO_EXACT_CLOSE":1})
        self.assertEqual(absent["cvd_reason_counts"],{"NO_EXACT_CLOSE":1})
    def test_conflict_and_nonretroactive_receipts(self):
        legacy,cvd=good(),coherent()
        r=self.audit([legacy,dict(legacy,received_at_ms=T0+4000)],
                     [cvd,dict(cvd,received_at_ms=T0+4000)])
        self.assertEqual(r["legacy_reason_counts"],{"BLOCKED_INVALID_OR_CONFLICT":1})
        self.assertEqual(r["cvd_reason_counts"],{"BLOCKED_CONFLICT":1})
        self.assertEqual(self.audit([legacy],[cvd]),self.audit(
            [legacy,dict(legacy,received_at_ms=T0+7000)],
            [cvd,dict(cvd,received_at_ms=T0+7000)]))
    def test_reason_population_and_configuration(self):
        other=list(pair());other[0]="GBPUSD"
        r=self.audit([changed(good(),lambda p:p["quality"].update(lower_tf="2"))],
                     [coherent()],pairs=[pair(),tuple(other)])
        self.assertEqual(r["population"],2)
        self.assertEqual(r["eligible_clock_population"],1)
        self.assertEqual(r["legacy_reason_counts"],{"BLOCKED_CONFIG_METADATA_MISMATCH":1})
        self.assertEqual(r["cvd_reason_counts"],{"DESCRIPTIVE_MATCH":1})
    def test_explicit_and_separate_feed(self):
        with self.assertRaises(ValueError):coverage([],[],[],as_of_ms=T0)
        with self.assertRaises(ValueError):self.audit([coherent()],[])
        with self.assertRaises(ValueError):self.audit([],[good()])
if __name__=="__main__":unittest.main()
