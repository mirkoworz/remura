# REMURA Contributors v0.28 LAB — 16/11/2026 08:22 CET
import unittest,subprocess,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from contributors_budget_candidate import scenario,review_evidence,TARGET
ROOT=Path(__file__).parent
class BundleBudgetTests(unittest.TestCase):
    def test_manifest_reproducible(self):
        cmd=["node",str(ROOT/"contributors_bundle_check.mjs")]
        a=subprocess.check_output(cmd,timeout=20);b=subprocess.check_output(cmd,timeout=20)
        self.assertEqual(a,b);m=json.loads(a)
        self.assertEqual(len(m["files"]),13);self.assertEqual(len(m["manifest_sha256"]),64)
    def test_example_load(self):
        # Two users, three page loads each, ten total submissions and ten owner reviews.
        q=scenario({"cold_page":6,"profile":6,"catalog":6,"intent":20,"submit":10,"review":10,"receipts":6,"queue":6,"history":6})
        self.assertEqual(q["requests"],94);self.assertEqual(q["query_statements"],254)
        self.assertEqual(q["write_statements_upper"],40);self.assertFalse(q["measured_rows"])
    def test_unknown_and_excess(self):
        now=datetime(2026,11,16,7,22,tzinfo=timezone.utc)
        self.assertEqual(review_evidence({},now)["status"],"NO_GO")
        e=dict(observed_at=now.isoformat(),candidate="0.28 LAB",complete=True,account_free_verified=True,aggregate_below_70_percent=True,usage={k:0 for k in TARGET},planned={k:1 for k in TARGET})
        self.assertEqual(review_evidence(e,now)["status"],"EVIDENCE_SHAPE_PASS_ONLY")
        self.assertFalse(review_evidence(e,now)["may_activate"])
        for field,value in [("complete",False),("aggregate_below_70_percent",None),("observed_at",(now-timedelta(hours=2)).isoformat()),("observed_at",(now+timedelta(seconds=1)).isoformat()),("candidate","other"),("usage",{"requests":0})]:
            self.assertEqual(review_evidence({**e,field:value},now)["status"],"NO_GO")
        e["usage"]["requests"]=500
        self.assertIn("requests_target_exceeded",review_evidence(e,now)["reasons"])
    def test_bad_counts(self):
        for c in [{"unknown":1},{"submit":-1},{"submit":True}]:
            with self.assertRaises(ValueError):scenario(c)
        self.assertFalse(scenario({"cold_page":126})["within_request_target"])
