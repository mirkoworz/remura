# REMURA v0.8.178 LAB — 18/11/2026
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"gateway-lab"))
from cvd_receipt_fold_attribution_lab_v1 import summarize
from cvd_receipt_window_audit_v1 import AuditError
from cvd_oos_protocol_preview_v2 import FOLDS,clock
from cvd_telemetry_preview_v1 import M5

def evidence():
    return [json.loads((ROOT/"evidence"/name).read_text()) for name in
            ("fx_first_receipt_20261116.json","fx_second_receipt_20261116.json","fx_third_receipt_20261118.json")]

class AttributionTests(unittest.TestCase):
    def test_existing_real_receipts_calendared(self):
        rows=evidence()
        r=summarize(rows,audit_ms=rows[-1]["observed_ms"])
        d=r["folds"]["DEVELOPMENT"]
        self.assertEqual((d["windows"],d["requested_slots"],d["valid_unique_bars"],d["collection_rows_read"]),(3,28,28,59))
        self.assertEqual(d["max_lag_ms"],21660)
        self.assertEqual(r["folds"]["HOLDOUT_1"]["receipt_evidence_status"],"NO_RECEIPT_EVIDENCE")
        self.assertEqual(r["folds"]["HOLDOUT_1"]["calendar_status"],"NOT_STARTED")
        self.assertFalse(d["per_bar_fold_receipt_clock_attested"])
        self.assertFalse(r["outcomes_computed"])
        self.assertEqual(r["new_network_reads"],0)
        self.assertNotIn("radar",json.dumps(r))
        self.assertNotIn("run_id",json.dumps(r))
    def test_four_actual_disjoint_receipts(self):
        fourth=json.loads((ROOT/"evidence"/"fx_fourth_receipt_20261118.json").read_text())
        self.assertEqual(fourth["run_id"],44362438343)
        self.assertNotIn("radar",fourth["report"])
        self.assertEqual(fourth["report"]["max_lag_ms"],17876)
        rows=evidence()+[fourth]
        r=summarize(rows,audit_ms=fourth["observed_ms"])
        d=r["folds"]["DEVELOPMENT"]
        self.assertEqual((d["windows"],d["requested_slots"],d["valid_unique_bars"],
                          d["missing_requested_slots"],d["duplicate_rows"],
                          d["collection_rows_read"],d["collection_rows_written"]),
                         (4,40,40,0,0,84,0))
        self.assertEqual(d["max_lag_ms"],21660)
        self.assertFalse(d["market_coverage_attested"])
        self.assertFalse(d["per_bar_fold_receipt_clock_attested"])
        self.assertFalse(r["scientific_admission"])
        self.assertFalse(r["outcomes_computed"])
        self.assertEqual(r["new_network_reads"],0)
        with self.assertRaises(AuditError):summarize(rows+[fourth],audit_ms=fourth["observed_ms"])
    def test_future_audit_or_duplicate_denied(self):
        rows=evidence()
        with self.assertRaises(AuditError):summarize(rows,audit_ms=rows[-1]["observed_ms"]-1)
        with self.assertRaises(AuditError):summarize(rows+[rows[-1]],audit_ms=rows[-1]["observed_ms"])
    def test_cross_fold_not_split(self):
        # Synthetic shifted aggregate only, no genuine receipt inference.
        row=copy.deepcopy(evidence()[1])
        boundary=clock(FOLDS[0][2])
        a,b=boundary-M5,boundary+10*M5
        now=b+120000
        row.update(start_ms=a,end_ms=b,observed_ms=now)
        row["report"]["window"]=dict(start_close_ms=a,end_close_ms=b,as_of_ms=now)
        r=summarize([row],audit_ms=now)
        self.assertEqual(r["unallocated_outside_or_crossing_fold"]["valid_unique_bars"],12)
        self.assertEqual(r["folds"]["DEVELOPMENT"]["requested_slots"],0)
        self.assertEqual(r["folds"]["HOLDOUT_1"]["requested_slots"],0)
    def test_empty_unknown_not_zero_market_coverage(self):
        r=summarize([],audit_ms=clock(FOLDS[0][1]))
        self.assertEqual(r["folds"]["DEVELOPMENT"]["receipt_evidence_status"],"NO_RECEIPT_EVIDENCE")
        self.assertIsNone(r["folds"]["DEVELOPMENT"]["max_lag_ms"])
        self.assertFalse(r["scientific_admission"])
if __name__=="__main__":unittest.main()
