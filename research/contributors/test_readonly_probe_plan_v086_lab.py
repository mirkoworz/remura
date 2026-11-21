# REMURA Contributors v0.86 LAB — 18 NEW tests, no real Cloudflare requests.
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import readonly_probe_plan_v086_lab as m

class ProbePlanTests(unittest.TestCase):
    def setUp(self):
        self.day=date(2026,11,21)
    def check(self,day=None):
        r=m.plan(self.day if day is None else day)
        self.assertEqual(r["decision"],"NO_GO")
        self.assertFalse(r["approved_to_execute"])
        self.assertFalse(r["deployment_allowed"])
        self.assertFalse(r["auto_retry_allowed"])
        self.assertFalse(r["provider_secrets_accessed"])
        self.assertFalse(r["workflow_dispatch_triggered"])
        self.assertEqual(r["http_calls_performed"],0)
        self.assertEqual(r["access_users_api_calls"],0)
        self.assertEqual(r["d1_sql_calls"],0)
        return r
    def test_01_original_guard_pinned(self):
        self.assertEqual(m.sha256(m.QUERY_FIXTURE.read_text(encoding="utf-8").removesuffix("\n").encode()).hexdigest(),m.EXPECTED_QUERY_SHA256)
    def test_02_query_retrieved(self):
        q,d=m.pinned_query()
        self.assertIn("d1AnalyticsAdaptiveGroups",q)
        self.assertEqual(len(d),64)
    def test_03_plan_today_prior(self):
        r=self.check()
        self.assertEqual(r["day_scopes_utc"],["2026-11-21","2026-11-20"])
    def test_04_capped_two_calls(self):
        self.assertEqual(self.check()["additional_graphql_calls_max_after_separate_approval"],2)
    def test_05_no_seat_api(self):
        self.assertEqual(self.check()["access_seats"],"MANUAL_DASHBOARD_CHECK_REQUIRED")
    def test_06_no_billing_attestation(self):
        self.assertFalse(self.check()["same_day_billing_attested"])
        self.assertFalse(self.check()["d1_rows_today_attested"])
    def test_07_invalid_date_string(self):
        self.assertEqual(self.check("2026-11-21")["status"],"INVALID_OR_UNVERIFIED")
    def test_08_invalid_datetime_type(self):
        from datetime import datetime,timezone
        self.assertEqual(self.check(datetime(2026,11,21,tzinfo=timezone.utc))["status"],"INVALID_OR_UNVERIFIED")
    def test_09_outside_month(self):
        self.assertEqual(self.check(date(2027,1,1))["status"],"INVALID_OR_UNVERIFIED")
    def test_10_previous_period_rejected(self):
        self.assertEqual(self.check(date(2026,10,31))["status"],"INVALID_OR_UNVERIFIED")
    def test_11_drifted_guard_rejected(self):
        with TemporaryDirectory() as p:
            file=Path(p)/"guard.py"
            file.write_text("QUERY='mutation { deleteAll }'")
            with patch.object(m,"QUERY_FIXTURE",file):
                self.assertEqual(self.check()["status"],"INVALID_OR_UNVERIFIED")
    def test_12_missing_guard_rejected(self):
        with patch.object(m,"QUERY_FIXTURE",Path("/tmp/this-path-should-not-exist-remura")):
            self.assertEqual(self.check()["status"],"INVALID_OR_UNVERIFIED")
    def test_13_guard_symlink_rejected(self):
        with TemporaryDirectory() as p:
            symlink=Path(p)/"guard.py";symlink.symlink_to(m.QUERY_FIXTURE)
            with patch.object(m,"QUERY_FIXTURE",symlink):
                self.assertEqual(self.check()["status"],"INVALID_OR_UNVERIFIED")
    def test_14_bad_blob_hash_rejected(self):
        with patch.object(m,"EXPECTED_QUERY_SHA256","0"*64):
            self.assertEqual(self.check()["status"],"INVALID_OR_UNVERIFIED")
    def test_15_output_identifier_free(self):
        result=str(self.check())
        for text in ("Bearer","accountTag","email","private.invalid"):
            self.assertNotIn(text,result)
    def test_16_restrict_endpoint(self):
        self.assertEqual(m.GRAPHQL_ENDPOINT,"https://api.cloudflare.com/client/v4/graphql")
    def test_17_cli_rejects_execution(self):
        self.assertEqual(m.main(["--execute"]),2)
    def test_18_cli_self_check(self):
        self.assertEqual(m.main(["--review-synthetic-plan"]),0)
if __name__=="__main__":unittest.main()
