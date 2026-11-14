#!/usr/bin/env python3
# REMURA v0.8.71 LAB — 14/11/2026 16:56 CET — synthetic only.
import unittest
from unittest.mock import patch
from cvd_oos_protocol_preview_v1 import clock,digest,evaluate_folds,covered,FOLDS
from cvd_telemetry_preview_v1 import M5
from cvd_archive_preview_v1 import assemble

S=clock(FOLDS[1][1]); E=clock(FOLDS[1][2])
def triple(t,receipt):
    return ({"bar_close_ms":t,"received_at_ms":receipt},{},{})
class FoldTests(unittest.TestCase):
    def test_fixed_digest(self):
        self.assertEqual(len(digest()),64)
        self.assertEqual(digest(),digest())
    def test_no_interim_results(self):
        with patch("cvd_oos_protocol_preview_v1.compare") as cmp:
            r=evaluate_folds([triple(S,S+5000)],[(S,E-M5)],as_of_ms=E-1)
            self.assertEqual(r["folds"]["HOLDOUT_1"]["status"],"PENDING_FIXED_END")
            cmp.assert_not_called()
    def test_incomplete_scope(self):
        with patch("cvd_oos_protocol_preview_v1.compare") as cmp:
            r=evaluate_folds([triple(S,S+5000)],[(S,E-2*M5)],as_of_ms=E)
            self.assertEqual(r["folds"]["HOLDOUT_1"]["status"],"INCOMPLETE_REQUEST_SCOPE")
            cmp.assert_not_called()
    def test_purge_cross_boundary(self):
        good=triple(S,S+5000)
        with patch("cvd_oos_protocol_preview_v1.compare",return_value={"status":"SYNTHETIC"}) as cmp:
            r=evaluate_folds([good,triple(S-M5,S-2000),triple(E,E+5000),triple(E-M5,E+2)],[(S,E-M5)],as_of_ms=E)
            cmp.assert_called_once_with([good],as_of_ms=E-1)
            self.assertEqual(r["folds"]["HOLDOUT_1"]["status"],"DESCRIPTIVE_FOLD_ONLY")
            self.assertFalse(r["independent_blinding_attested"])
    def test_no_observations_not_edge(self):
        r=evaluate_folds([],[(S,E-M5)],as_of_ms=E)
        self.assertEqual(r["folds"]["HOLDOUT_1"]["status"],"NO_OBSERVATIONS")
        self.assertEqual(r["edge"],"NOT_ESTABLISHED")
    def test_gap_and_contiguous_windows(self):
        self.assertTrue(covered([(S,S+M5),(S+2*M5,E-M5)],S,E))
        self.assertFalse(covered([(S,S+M5),(S+3*M5,E-M5)],S,E))
    def test_archive_report_includes_protocol(self):
        r=assemble([],as_of_ms=S)
        self.assertEqual(r["prospective_folds"]["protocol_sha256"],digest())
        self.assertFalse(r["prospective_folds"]["scientific_admission"])
if __name__=="__main__":
    unittest.main()
