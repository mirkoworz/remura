# REMURA v0.8.175 LAB — 18/11/2026
import unittest
from unittest.mock import patch
from cvd_fold_coverage_lab_v1 import coverage
from cvd_oos_protocol_preview_v2 import FOLDS,clock,digest
from cvd_telemetry_preview_v1 import M5
S=clock(FOLDS[0][1])
E=clock(FOLDS[0][2])

def window(a,b):
    return {"start_ms":a,"end_ms":b,"rows":[]}

class CoverageTests(unittest.TestCase):
    def test_empty_elapsed_and_future_distinction(self):
        r=coverage([],as_of_ms=S+M5+120000,synthetic=True)
        a=r["folds"]["DEVELOPMENT"]
        self.assertEqual(a["elapsed_calendar_slots"],2)
        self.assertEqual(a["unrequested_calendar_slots"],2)
        self.assertFalse(a["requested_elapsed_scope_complete"])
        future=r["folds"]["HOLDOUT_1"]
        self.assertEqual(future["calendar_status"],"NOT_STARTED")
        self.assertIsNone(future["requested_elapsed_scope_complete"])
        self.assertEqual(r["protocol_sha256"],digest())
    def test_gap_and_no_results(self):
        with patch("cvd_archive_preview_v1.summarize",side_effect=AssertionError), \
             patch("cvd_oos_protocol_preview_v2.compare",side_effect=AssertionError):
            r=coverage([window(S,S),window(S+2*M5,S+2*M5)],
                       as_of_ms=S+2*M5+120000,synthetic=True)
        a=r["folds"]["DEVELOPMENT"]
        self.assertEqual((a["requested_slots"],a["missing_requested_slots"],a["unrequested_calendar_slots"]),(2,2,1))
        self.assertFalse(r["outcomes_evaluated"])
        self.assertFalse(r["market_coverage_attested"])
    def test_boundary_and_late_receipt_accounting(self):
        # Isolated accounting test: injected already-validated triples only.
        rows=[({"bar_close_ms":E-M5,"received_at_ms":E+1},{},{}),
              ({"bar_close_ms":E,"received_at_ms":E+5000},{},{})]
        with patch("cvd_fold_coverage_lab_v1.validate_windows",
                   return_value=(rows,{"valid_unique_bars":2})):
            r=coverage([window(E-M5,E)],as_of_ms=E+120000,synthetic=True)
        a,b=r["folds"]["DEVELOPMENT"],r["folds"]["HOLDOUT_1"]
        self.assertEqual(a["receipts_after_fold_end"],1)
        self.assertEqual(a["usable_receipt_clocks_within_fold"],0)
        self.assertEqual(b["usable_receipt_clocks_within_fold"],1)
        self.assertEqual(r["outside_fold_unique_bars"],0)
    def test_scope_and_explicit_flag(self):
        with self.assertRaises(ValueError):coverage([],as_of_ms=S)
        with self.assertRaises(ValueError):coverage([window(S,S+M5)],as_of_ms=S,synthetic=True)
        r=coverage([window(S,S)],as_of_ms=S+120000,synthetic=True)
        self.assertTrue(r["folds"]["DEVELOPMENT"]["requested_elapsed_scope_complete"])
        self.assertEqual(r["folds"]["DEVELOPMENT"]["missing_requested_slots"],1)
if __name__=="__main__":unittest.main()
