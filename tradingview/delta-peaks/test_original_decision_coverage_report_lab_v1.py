# REMURA v0.8.174 LAB — 18/11/2026
import unittest
from original_decision_coverage_report_lab_v1 import render
from original_decision_coverage_lab_v1 import coverage
from test_research_dossier_preview_v1 import pair,T0
from test_fx_asof_handoff_v1 import good
from test_cvd_squalincome_asof_preview_v1 import coherent

class ReportTests(unittest.TestCase):
    def audit(self,a,b,pairs=None):
        return coverage([pair()] if pairs is None else pairs,a,b,as_of_ms=T0+8000,synthetic=True)
    def test_mobile_report_aggregates_only(self):
        r=self.audit([good()],[coherent()])
        page=render(r,synthetic=True)
        for label in ("v0.8.174 LAB","Entrambe disponibili: 1 / 1","FXCM:EURUSD","FX:EURUSD CVD","SOLO DATI SINTETICI"):
            self.assertIn(label,page)
        for forbidden in ("raw_json","1.111","<script"):
            self.assertNotIn(forbidden,page)
    def test_joint_matrix_visible(self):
        r=self.audit([good()],[])
        html=render(r,synthetic=True)
        self.assertIn("Copertura congiunta",html)
        self.assertIn("Solo FXCM completo</td><td>1",html)
        self.assertIn("Nessuna fonte ammessa</td><td>0",html)
        empty=render(self.audit([],[],pairs=[]),synthetic=True)
        self.assertNotIn("Solo FXCM completo",empty)
    def test_empty_and_reject_mismatched_counts(self):
        r=self.audit([],[],pairs=[])
        self.assertIn("Entrambe disponibili: N/D",render(r,synthetic=True))
        r=self.audit([good()],[coherent()])
        with self.assertRaises(ValueError):render(r)
        with self.assertRaises(ValueError):render(dict(r,orders_enabled=True),synthetic=True)
        with self.assertRaises(ValueError):render(dict(r,legacy_reason_counts={"NO_EXACT_CLOSE":1}),synthetic=True)
        with self.assertRaises(ValueError):render(dict(r,cvd_reason_counts={"<script>":1}),synthetic=True)
if __name__=="__main__":unittest.main()
