# REMURA v0.8.168 LAB — 18/11/2026, after 16:21 CET.
import json
import unittest
from unittest.mock import patch
from test_cvd_squalincome_asof_preview_v1 import coherent
from test_cvd_telemetry_preview_v1 import T0,M5
from cvd_source_availability_lab_v1 import availability

class SourceAvailabilityTests(unittest.TestCase):
    def run_rows(self,rows):
        return availability([{"start_ms":T0,"end_ms":T0+M5,"rows":rows}],
                            as_of_ms=T0+M5+120000)
    def test_counts_and_no_outcomes(self):
        with patch("cvd_archive_preview_v1.summarize",side_effect=AssertionError), \
             patch("cvd_archive_preview_v1.compare",side_effect=AssertionError), \
             patch("cvd_archive_preview_v1.evaluate_folds",side_effect=AssertionError):
            r=self.run_rows([coherent(),coherent()])
        self.assertEqual(r["receipt_counts"]["valid_unique_bars"],1)
        self.assertEqual(r["receipt_counts"]["duplicate_rows"],1)
        self.assertEqual(r["receipt_counts"]["missing_requested_slots"],1)
        self.assertEqual(r["availability_counts"]["receipt_clock_usable"],1)
        self.assertFalse(r["outcomes_evaluated"])
        for name in ("raw_json","candidate_cooccurrences","median_direction_adjusted_return_atr"):
            self.assertNotIn(name,json.dumps(r))
    def test_empty_unknown(self):
        r=self.run_rows([])
        self.assertEqual(r["status"],"NO_OBSERVATIONS")
        self.assertEqual(r["receipt_counts"]["missing_requested_slots"],2)
        self.assertFalse(r["scientific_admission"])
    def test_conflicting_rows_fail(self):
        a=coherent();b=dict(a,received_at_ms=a["received_at_ms"]+1)
        with self.assertRaises(ValueError):self.run_rows([a,b])
if __name__=="__main__":unittest.main()
