# REMURA Contributors v0.83 LAB — ONLY new provenance tests.
from datetime import datetime,timedelta,timezone
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import monitor_provenance_v083_lab as m

class NewProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.meta,self.log,self.now=m.synthetic()
    def check(self,status=None):
        r=m.assess(self.meta,self.log,now_utc=self.now)
        self.assertEqual(r["decision"],"NO_GO")
        self.assertFalse(r["automatic_deploy_allowed"])
        self.assertFalse(r["d1_usage_attested"])
        self.assertFalse(r["billing_attested"])
        self.assertEqual(r["access_free_seats"],"UNKNOWN")
        if status:self.assertEqual(r["d1_daily"],status)
        return r
    def test_01_failed_run(self):
        self.assertEqual(self.check("UNKNOWN_NOT_ZERO")["monitor"],"WORKFLOW_INCOMPLETE")
    def test_02_success_metadata_not_provider_proof(self):
        self.meta["conclusion"]="success"
        self.assertEqual(self.check()["monitor"],"WORKFLOW_SUCCESS_METADATA_ONLY")
    def test_03_today_empty_not_zero(self):
        self.log="REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA"
        self.check("UNKNOWN_NOT_ZERO")
    def test_04_yesterday_cannot_be_today(self):
        self.log="\n".join(["REMURA_CF_ACCOUNT_QUOTA=OK","UTC_DAY=2026-11-20; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING","D1_ACCOUNT_ROWS_READ_ESTIMATE=0","D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0","D1_FREE_READ_LIMIT=5000000","D1_FREE_WRITE_LIMIT=100000"])
        self.check("DAY_OR_SOURCE_UNVERIFIED")
    def test_05_today_valid_estimate_still_no_go(self):
        self.log="\n".join(["REMURA_CF_ACCOUNT_QUOTA=OK","UTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING","D1_ACCOUNT_ROWS_READ_ESTIMATE=0","D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0","D1_FREE_READ_LIMIT=5000000","D1_FREE_WRITE_LIMIT=100000"])
        self.check("ADAPTIVE_ESTIMATE_PRESENT_NOT_BILLING")
    def test_06_duplicate_status_denied(self):
        self.log="REMURA_CF_ACCOUNT_QUOTA=OK\nREMURA_CF_ACCOUNT_QUOTA=OK"
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_07_duplicate_counter_denied(self):
        self.log="D1_ACCOUNT_ROWS_READ_ESTIMATE=5\nD1_ACCOUNT_ROWS_READ_ESTIMATE=6"
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_08_counter_bool_invalid(self):
        self.log="REMURA_CF_ACCOUNT_QUOTA=OK\nUTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\nD1_ACCOUNT_ROWS_READ_ESTIMATE=True"
        self.check("COUNTERS_INVALID")
    def test_09_token_never_echoed(self):
        self.log += "\nTOKEN_SECRET=abcd-password-private"
        self.assertNotIn("abcd-password-private",str(self.check()))
    def test_10_unknown_status(self):
        self.log="REMURA_CF_ACCOUNT_QUOTA=GREEN"
        self.check("UNKNOWN_NOT_ZERO")
    def test_11_bad_branch(self):
        self.meta["branch"]="feature"
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_12_bad_run_id(self):
        self.meta["run_id"]=True
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_13_wrong_workflow(self):
        self.meta["workflow"]="deploy"
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_14_bad_sha(self):
        self.meta["head_sha"]="xyz"
        self.assertEqual(self.check()["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_15_stale_run(self):
        self.meta["started_utc"]="2026-11-20T15:32:05Z"
        self.assertEqual(self.check()["monitor"],"STALE_OR_OTHER_DAY")
    def test_16_future_run(self):
        self.meta["started_utc"]="2026-11-21T19:32:05Z"
        self.assertEqual(self.check()["monitor"],"STALE_OR_OTHER_DAY")
    def test_17_missing_log(self):
        self.assertEqual(m.assess(self.meta,None,now_utc=self.now)["d1_daily"],"UNKNOWN_NOT_ZERO")
    def test_18_bad_timezone(self):
        self.assertEqual(m.assess(self.meta,self.log,now_utc=datetime(2026,11,21))["monitor"],"INVALID_OR_UNVERIFIABLE")
    def test_19_bad_cli(self):
        self.assertEqual(m.main([]),2)
    def test_20_self_check(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)

if __name__=="__main__":unittest.main()
