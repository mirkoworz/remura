# REMURA v0.8.177 LAB — 18/11/2026
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"gateway-lab"))
from cvd_receipt_request_preview_lab_v1 import preview
from cvd_receipt_window_audit_v1 import AuditError
from test_cvd_receipt_fold_attribution_lab_v1 import evidence
from cvd_oos_protocol_preview_v2 import FOLDS,clock
from cvd_telemetry_preview_v1 import M5

class RequestPreviewTests(unittest.TestCase):
    def test_disjoint_explicit_window(self):
        rows=evidence()
        t=clock("2026-11-18")+16*3600000
        r=preview(rows,start_ms=t,end_ms=t+11*M5,audit_ms=t+11*M5+120000)
        self.assertEqual(r["inputs"]["start_utc"],"2026-11-18T16:00Z")
        self.assertEqual(r["inputs"]["end_utc"],"2026-11-18T16:55Z")
        self.assertEqual(r["requested_slots"],12)
        self.assertTrue(r["owner_dispatch_required"])
        self.assertFalse(r["dispatch_authorized"])
        self.assertEqual(r["network_requests"],0)
        self.assertIsNone(r["actual_rows_read"])
    def test_existing_overlap_denied(self):
        rows=evidence();t=rows[-1]["end_ms"]
        with self.assertRaises(AuditError):preview(rows,start_ms=t,end_ms=t+M5,audit_ms=rows[-1]["observed_ms"])
    def test_cross_fold_future_and_oversize(self):
        end=clock(FOLDS[0][2])
        for a,b,at in ((end-M5,end,end+120000),(end,end,end+119999),
                       (end,end+12*M5,end+12*M5+120000)):
            with self.assertRaises(AuditError):preview([],start_ms=a,end_ms=b,audit_ms=at)
    def test_audit_clock_never_accepts_future_evidence(self):
        rows=evidence();t=rows[0]["start_ms"]-M5
        with self.assertRaises(AuditError):preview(rows,start_ms=t,end_ms=t,audit_ms=rows[-1]["observed_ms"]-1)
if __name__=="__main__":unittest.main()
