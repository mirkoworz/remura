# REMURA v0.8.156 LAB — 18/11/2026, sessione successiva alle 12:26 CET
# Offline regression with actual public aggregate evidence, no raw candles.
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"gateway-lab"))
from cvd_receipt_window_audit_v1 import aggregate_receipts,AuditError
class FirstReceiptEvidence(unittest.TestCase):
    def test_actual_receipt(self):
        r=json.loads((ROOT/"evidence"/"fx_first_receipt_20261116.json").read_text())
        o=aggregate_receipts([r])
        self.assertEqual((o["requested_slots"],o["valid_unique_bars"],o["missing_requested_slots"],o["duplicate_rows"]),(4,4,0,0))
        self.assertEqual((o["max_lag_ms"],o["collection_rows_read"],o["collection_rows_written"]),(7092,9,0))
        self.assertFalse(o["scientific_admission"])
        with self.assertRaises(AuditError):aggregate_receipts([r,r])
    def test_candidate_workflow_boundary(self):
        old=(ROOT/"evidence"/"cvd_main_v3_workflow.yml.txt").read_text()
        new=(ROOT/"evidence"/"cvd_main_v4_candidate.yml.txt").read_text()
        self.assertEqual(new,old.replace(old.splitlines()[0],"# REMURA v0.8.89 LAB — candidate workflow, 16/11/2026 10:55 CET",1).replace(old.splitlines()[1],"# Rollback: restore reviewed V3 workflow before any later promotion.",1).replace("batch V3 (max 576 slot)","batch V4 (max 576 slot)").replace("ref: 4f1f9cb250241007bc5f9a97527972d3a47b9d2a","ref: 08f5cdb48d430739ce3688480d95ac78aea3640b").replace("cvd_test_batch_reader_v3.py","cvd_test_batch_reader_v4.py"))
        self.assertIn("github.triggering_actor == 'mirkoworz'",new)
        self.assertIn("github.ref == 'refs/heads/main'",new)
        self.assertIn("workflow_dispatch:",new)
        self.assertNotIn("schedule:",new)
        self.assertIn("default: receipt-only",new)
        self.assertIn("persist-credentials: false",new)

    def test_two_actual_disjoint_receipts(self):
        first=json.loads((ROOT/"evidence"/"fx_first_receipt_20261116.json").read_text())
        second=json.loads((ROOT/"evidence"/"fx_second_receipt_20261116.json").read_text())
        o=aggregate_receipts([first,second])
        self.assertEqual((o["windows"],o["requested_slots"],o["valid_unique_bars"],o["missing_requested_slots"],o["duplicate_rows"]),(2,16,16,0,0))
        self.assertEqual((o["max_lag_ms"],o["collection_rows_read"],o["collection_rows_written"]),(21660,34,0))
        self.assertFalse(o["scientific_admission"])
        with self.assertRaises(AuditError):aggregate_receipts([first,second,second])

    def test_three_actual_disjoint_receipts_through_nov18(self):
        names=("fx_first_receipt_20261116.json","fx_second_receipt_20261116.json","fx_third_receipt_20261118.json")
        records=[json.loads((ROOT/"evidence"/name).read_text()) for name in names]
        latest=records[-1]
        self.assertEqual(latest["run_id"],44294693651)
        one=aggregate_receipts([latest])
        self.assertEqual((one["requested_slots"],one["valid_unique_bars"],one["missing_requested_slots"],one["duplicate_rows"]),(12,12,0,0))
        self.assertEqual((one["max_lag_ms"],one["collection_rows_read"],one["collection_rows_written"]),(16884,25,0))
        o=aggregate_receipts(records)
        self.assertEqual((o["windows"],o["requested_slots"],o["valid_unique_bars"],o["missing_requested_slots"],o["duplicate_rows"]),(3,28,28,0,0))
        self.assertEqual((o["max_lag_ms"],o["collection_rows_read"],o["collection_rows_written"]),(21660,59,0))
        for k in ("scientific_admission","independent_provenance","outcomes_computed","orders_enabled","notifications_enabled"):
            self.assertFalse(o[k])
        self.assertIsNone(o["account_quota_utilization"])
        with self.assertRaises(AuditError):aggregate_receipts(records+[latest])
