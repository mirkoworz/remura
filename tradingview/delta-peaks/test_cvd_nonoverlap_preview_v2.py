#!/usr/bin/env python3
# REMURA v0.8.79 LAB — 14/11/2026 18:22 CET — synthetic only.
import copy,unittest
from unittest.mock import patch
from test_cvd_batch_nonoverlap_preview_v1 import triples,T0,M5
from cvd_nonoverlap_preview_v2 import compare
from cvd_nonoverlap_preview_v1 import compare as old_compare
import cvd_oos_protocol_preview_v2 as protocol
import cvd_oos_protocol_preview_v1 as v1

class FrozenPairs(unittest.TestCase):
    def report(self,rows,cutoff=None):
        with patch("cvd_nonoverlap_preview_v2.session_id",return_value=("synthetic",0)):
            return compare(rows,as_of_ms=cutoff if cutoff is not None else T0+60*M5)["horizons"]["60"]
    def cvd(self,rows,cutoff=None):
        return self.report(rows,cutoff)["comparisons"]["CVD"]
    def test_missing_first_control_never_promotes_second(self):
        full=triples(n=44,events=(0,14,28))
        a=self.cvd(full)
        b=self.cvd([x for x in full if x[0]["bar_close_ms"]!=T0+18*M5])
        self.assertEqual(a["assigned_pairs"],1)
        self.assertEqual(a["complete_pairs"],1)
        self.assertEqual(b["assigned_pairs"],1)
        self.assertEqual(b["complete_pairs"],0)
        self.assertEqual(b["incomplete_pairs"],1)
        self.assertEqual(b["unmatched_negative"],1)
        self.assertEqual(a["assignment_sha256"],b["assignment_sha256"])
        self.assertIsNone(b["mean_difference_pips"])
        with patch("cvd_nonoverlap_preview_v1.session_id",return_value=("synthetic",0)):
            old=old_compare([x for x in full if x[0]["bar_close_ms"]!=T0+18*M5],as_of_ms=T0+60*M5)
        self.assertEqual(old["horizons"]["60"]["comparisons"]["CVD"]["matched_pairs"],1)
    def test_missing_positive_keeps_assignment(self):
        rows=triples(n=44,events=(0,14,28))
        a=self.cvd(rows); b=self.cvd([x for x in rows if x[0]["bar_close_ms"]!=T0+4*M5])
        self.assertEqual(a["assignment_sha256"],b["assignment_sha256"])
        self.assertEqual(b["incomplete_pairs"],1)
        self.assertEqual(b["complete_pairs"],0)
    def test_pending_then_mature_no_reassignment(self):
        rows=triples(n=44,events=(0,14,28))
        a=self.cvd(rows,T0+15*M5+120000); b=self.cvd(rows)
        self.assertEqual(a["assigned_pairs"],1)
        self.assertEqual(a["pending_pairs"],1)
        self.assertEqual(a["assignment_sha256"],b["assignment_sha256"])
        self.assertEqual(b["complete_pairs"],1)
    def test_late_outcome_does_not_replace(self):
        rows=triples(n=44,events=(0,14,28))
        changed=copy.deepcopy(rows)
        changed[18][0]["received_at_ms"]+=120001
        a=self.cvd(rows); b=self.cvd(changed)
        self.assertEqual(a["assignment_sha256"],b["assignment_sha256"])
        self.assertEqual(b["complete_pairs"],0)
        self.assertEqual(b["incomplete_reason_pair_counts_nonexclusive"]["QUALITY_OR_CLOCK_BLOCKED"],1)
    def test_late_candidate_not_retroactive(self):
        rows=triples(n=44,events=(0,14,28))
        rows[14][0]["received_at_ms"]+=120001
        a=self.report(rows)
        self.assertEqual(a["counts"]["LATE_CANDIDATE_EXCLUDED"],1)
        self.assertEqual(a["comparisons"]["CVD"]["assigned_pairs"],1)
        self.assertEqual(a["comparisons"]["CVD"]["complete_pairs"],1)
    def test_conflict_fails_closed(self):
        rows=triples()
        clone=copy.deepcopy(rows[4]); clone[0]["event_key"]="other"; clone[2]["event_key"]="other"
        with self.assertRaisesRegex(ValueError,"benchmark_identity"):
            self.report(rows+[clone])
    def test_conservation_all_filters(self):
        for rows in ([],triples(n=44,events=(0,14,28)),triples(n=44,events=(0,14,28),missing=(18,))):
            for h in compare(rows,as_of_ms=T0+60*M5)["horizons"].values():
                for x in h["comparisons"].values():
                    self.assertEqual(x["assigned_pairs"],x["complete_pairs"]+x["incomplete_pairs"])
                    self.assertEqual(x["eligible"]["POSITIVE"],x["assigned_pairs"]+x["unmatched_positive"])
                    self.assertEqual(x["eligible"]["NEGATIVE"],x["assigned_pairs"]+x["unmatched_negative"])
    def test_protocol_locked_and_no_early_fold(self):
        self.assertEqual(protocol.FOLDS,v1.FOLDS)
        for key in ("primary","secondary","entry","cost_scenarios_pips","data","stopping"):
            self.assertEqual(protocol.PROTOCOL[key],v1.PROTOCOL[key])
        self.assertNotEqual(protocol.digest(),v1.digest())
        s=protocol.clock("2026-11-16"); e=protocol.clock("2026-11-23")
        row=({"bar_close_ms":s,"received_at_ms":s+5000},{},{})
        with patch.object(protocol,"compare") as cmp:
            self.assertEqual(protocol.evaluate_folds([row],[(s,e-M5)],as_of_ms=e-1)["folds"]["DEVELOPMENT"]["status"],"PENDING_FIXED_END")
            cmp.assert_not_called()
        with patch.object(protocol,"compare",return_value={}) as cmp:
            protocol.evaluate_folds([row,({"bar_close_ms":e,"received_at_ms":e},{},{})],[(s,e-M5)],as_of_ms=e)
            cmp.assert_called_once_with([row],as_of_ms=e-1)

if __name__=="__main__":
    unittest.main()
