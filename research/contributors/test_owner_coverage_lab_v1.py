# REMURA Contributors v0.46 LAB — 18/11/2026
import json,unittest
# Reuse setup only; avoid importing TestCase at module scope and duplicating tests.
import test_confluence_dashboard_v1 as fixtures
from owner_coverage_lab_v1 import owner_coverage

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.DashboardTests("test_owner_report")
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
    def report(self,automatic=None,rules=None,**kw):
        f=self.f
        return owner_coverage(f.lab,f.owner,[f.auto] if automatic is None else automatic,
                              [fixtures.RULE] if rules is None else rules,synthetic=True,**kw)
    def test_aggregate_no_private_fields(self):
        r=self.report()
        self.assertEqual(r["automatic_status_counts"]["NEAR"],1)
        self.assertEqual(r["manual_status_counts"]["NEAR"],1)
        raw=json.dumps(r)
        for value in ("1.08535","1.08540","PRIVATE NOTE","EURUSD","OANDA","auto-1","friend-a",self.f.friend):
            self.assertNotIn(value,raw)
        self.assertFalse(r["public_export_authorized"])
        self.assertFalse(r["anonymization_attested"])
    def test_missing_rule_and_causal_cutoff(self):
        r=self.report(rules=[])
        self.assertEqual(r["automatic_status_counts"]["NOT_COMPARABLE_NO_RULE"],1)
        self.assertEqual(r["manual_status_counts"]["NOT_COMPARABLE_NO_RULE"],1)
        r=self.report(asof_utc=self.f.receipt)
        self.assertEqual((r["manual_admitted"],r["manual_excluded"]),(0,1))
        self.assertEqual(r["automatic_status_counts"]["NO_COMPARABLE_MANUAL"],1)
    def test_owner_only_and_bounded_inputs(self):
        for token in (self.f.friend,"unknown"):
            with self.assertRaises(PermissionError):
                owner_coverage(self.f.lab,token,[],[],synthetic=True)
        with self.assertRaises(ValueError):self.report(rules=iter([fixtures.RULE]))
        with self.assertRaises(ValueError):self.report(rules=[fixtures.RULE]*201)
        with self.assertRaises(ValueError):self.report(automatic=[self.f.auto]*21)
    def test_no_mutation_and_no_multiple_count(self):
        before=self.f.lab.queue(self.f.owner)
        r=self.report(automatic=[self.f.auto,dict(self.f.auto,id="auto-2")])
        self.assertEqual(r["automatic_status_counts"]["NEAR"],2)
        self.assertEqual(r["manual_status_counts"]["NEAR"],1)
        self.assertEqual(before,self.f.lab.queue(self.f.owner))
if __name__=="__main__":unittest.main()
