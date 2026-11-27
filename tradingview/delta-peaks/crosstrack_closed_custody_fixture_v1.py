# REMURA v0.8.129 LAB — 17/11/2026 CET
import unittest
import test_level_receipt_custody_lab_v1 as d
import test_closed_source_custody_lab_v1 as e
from level_receipt_witness_lab_v1 import genesis
from closed_de_custody_coverage_lab_v1 import coverage
FLAGS=dict(synthetic=True,ingress_closed=True)
KEY=b"q"*32;GEN="3"*32
class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.d=d.ReceiptCustodyTests("test_exact_sqlite_backup_and_closed_flags")
        self.d.setUp();self.addCleanup(self.d.doCleanups)
        self.d.reserve(d.T+301500);self.d.finish(2,d.T+301500,n=1)
        self.db=self.d.copy();_,p=self.d.seal(self.db)
        self.record,self.anchor=genesis(p,GEN,KEY,**FLAGS)
        self.e=e.SourceCustodyTests("test_repeat_and_bound_candidate")
        self.e.setUp();self.addCleanup(self.e.doCleanups)
        b,bp,m,c=self.e.make()
        self.args=dict(d_witness=self.record,d_key=KEY,d_latest=dict(latest_anchor=self.anchor,latest_generation=GEN,latest_sequence=1),
            e_binding=b,e_binding_pin=bp,e_manifest=m,e_candidate=c,e_source_pin=self.e.source,e_journal_pin=self.e.pin,
            e_old_generation=e.f.G,e_new_generation=e.f.N,cutoff_ms=d.T+1600,audit_ms=d.T+400000,**FLAGS)
    def run_case(self,**kw):return coverage(self.db,**dict(self.args,**kw))
    def test_verified_actual_d_and_e_no_comparison(self):
        r=self.run_case()
        self.assertEqual((r["d_eligible_fixture_snapshots"],r["d_future_archive_snapshots"]),(1,1))
        self.assertEqual(r["d_latest_slot_counts"],{"MISSING":2,"PRESENT_UNATTESTED":4})
        self.assertEqual(r["e_retained_quarantine_only"],1)
        self.assertEqual(r["e_asof_review_diagnostics"],{"NOT_AVAILABLE_ASOF":1})
        for k in ("price_comparison_performed","receipt_authenticated","source_equivalence_attested","scientific_admission","operational_signal","historical_population_unbiased","orders_enabled"):self.assertFalse(r[k])
        for raw in ("1.085301","friend-b", "private-note"):self.assertNotIn(raw,str(r))
    def test_millisecond_completion_boundary(self):
        r=self.run_case(cutoff_ms=d.T+1599)
        self.assertEqual((r["d_eligible_fixture_snapshots"],r["d_late_archive_snapshots"]),(0,1))
        self.assertEqual(self.run_case(cutoff_ms=d.T+1600)["d_eligible_fixture_snapshots"],1)
    def test_late_second_does_not_replace_first(self):
        r=self.run_case(cutoff_ms=d.T+301599)
        self.assertEqual((r["d_eligible_fixture_snapshots"],r["d_late_archive_snapshots"]),(1,1))
        self.assertEqual(self.run_case(cutoff_ms=d.T+301600)["d_eligible_fixture_snapshots"],2)
    def test_e_review_timing_never_unquarantines(self):
        t=1794900000000
        r=self.run_case(cutoff_ms=t,audit_ms=t)
        self.assertEqual(r["e_asof_review_diagnostics"],{"REVIEW_APPROVED":1})
        self.assertIn("E_QUARANTINE",r["blocked_reasons"])
        self.assertFalse(r["price_comparison_performed"])
    def test_wrong_anchors_and_tamper(self):
        for kw in (dict(e_source_pin="0"*64),dict(e_candidate={**self.args["e_candidate"],"entries":[]}),
                   dict(d_latest={**self.args["d_latest"],"latest_anchor":"0"*64}),dict(d_key=b"x"*32)):
            with self.assertRaises(ValueError):self.run_case(**kw)
    def test_wrong_scope_and_clock(self):
        for kw in (dict(synthetic=False),dict(ingress_closed=False),dict(cutoff_ms=self.args["audit_ms"]+1)):
            with self.assertRaises(ValueError):self.run_case(**kw)
if __name__=="__main__":
    unittest.main()
