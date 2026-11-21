# REMURA Contributors v0.91 LAB — ONLY NEW bounded probe tests, no real HTTP.
from datetime import date,timedelta
from unittest.mock import patch
import contextlib,io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cloudflare_d1_diagnostic_v091_lab as m

DAY=date(2026,11,21)
def payload(day=DAY,rows=100,writes=1,groups=None):
    if groups is None:
        groups=[{"dimensions":{"date":day.isoformat(),"databaseId":"a-private-test-id"},
                 "sum":{"rowsRead":rows,"rowsWritten":writes}}]
    return {"data":{"viewer":{"accounts":[{"d1AnalyticsAdaptiveGroups":groups}]}}}
def empty(day=DAY):return payload(day,groups=[])
def mock_transport(items):
    calls=[]
    def send(q,day):
        calls.append(day)
        assert len(calls)<=len(items),"unexpected extra call"
        x=items[len(calls)-1]
        if isinstance(x,Exception):raise x
        return x
    return send,calls

class ProbeTests(unittest.TestCase):
    def safe(self,r):
        self.assertEqual(r["decision"],"NO_GO")
        self.assertFalse(r["staging_allowed"])
        self.assertFalse(r["deploy_allowed"])
        self.assertFalse(r["access_seats_verified"])
        self.assertFalse(r["free_plan_verified"])
        self.assertFalse(r["automatic_retry"])
        self.assertFalse(r["secrets_logged"])
        self.assertFalse(r["db_identifiers_logged"])
        self.assertLessEqual(r["provider_post_count"],2)
        self.assertEqual(r["d1_sql_calls"],0)
    def test_01_offline_plan(self):
        r=m.offline_plan(DAY);self.safe(r)
        self.assertEqual(r["provider_post_count"],0)
    def test_02_pinned_query(self):
        q,d=m.pinned_query()
        from readonly_probe_plan_v086_lab import EXPECTED_QUERY_SHA256
        self.assertEqual(d,EXPECTED_QUERY_SHA256)
        self.assertIn("d1AnalyticsAdaptiveGroups",q)
    def test_03_today_one_call(self):
        t,c=mock_transport([payload()])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(r["status"],"TODAY_ADAPTIVE_ESTIMATE_PRESENT")
        self.assertEqual(c,[DAY.isoformat()])
    def test_04_today_empty_prior_present(self):
        y=DAY-timedelta(days=1)
        t,c=mock_transport([empty(),payload(y)])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(c,[DAY.isoformat(),y.isoformat()])
        self.assertEqual(r["status"],"TODAY_EMPTY_PREVIOUS_PRESENT")
        self.assertIsNone(r["daily_read_band"])
    def test_05_both_empty_not_zero(self):
        t,c=mock_transport([empty(),empty(DAY-timedelta(days=1))])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(r["status"],"BOTH_DAYS_EMPTY_NOT_ZERO")
        self.assertEqual(len(c),2)
        self.assertIsNone(r["daily_write_band"])
    def test_06_first_failure_no_retry(self):
        t,c=mock_transport([TimeoutError("secret-private")])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(len(c),1)
        self.assertEqual(r["status"],"ERROR_UNATTESTED")
        self.assertNotIn("secret-private",str(r))
    def test_07_second_failure_no_retry(self):
        t,c=mock_transport([empty(),TimeoutError("private")])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(len(c),2)
        self.assertEqual(r["provider_post_count"],2)
    def test_08_group_zero_explicit(self):
        t,c=mock_transport([payload(rows=0,writes=0)])
        r=m.diagnostic(DAY,t);self.safe(r)
        self.assertEqual(r["status"],"TODAY_ADAPTIVE_ESTIMATE_PRESENT")
    def test_09_duplicate_groups(self):
        g=payload()["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(groups=[g,g]),DAY)
    def test_10_bad_date(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(DAY-timedelta(days=1)),DAY)
    def test_11_over_ten_groups(self):
        groups=[{"dimensions":{"date":DAY.isoformat(),"databaseId":str(i)},"sum":{"rowsRead":0,"rowsWritten":0}} for i in range(11)]
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(groups=groups),DAY)
    def test_12_negative_read(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(rows=-1),DAY)
    def test_13_fractional_read(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(rows=1.7),DAY)
    def test_14_string_count(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(writes="1"),DAY)
    def test_15_bool_count(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily(payload(rows=True),DAY)
    def test_16_multiple_accounts(self):
        v=payload()
        v["data"]["viewer"]["accounts"].append({"d1AnalyticsAdaptiveGroups":[]})
        with self.assertRaises(m.DiagnosticError):m.parse_daily(v,DAY)
    def test_17_no_viewer(self):
        with self.assertRaises(m.DiagnosticError):m.parse_daily({"data":{}},DAY)
    def test_18_graphql_errors(self):
        v=payload();v["errors"]=[{"message":"account secret"}]
        with self.assertRaises(m.DiagnosticError):m.parse_daily(v,DAY)
    def test_19_read_limit(self):
        t,c=mock_transport([payload(rows=5_000_000)])
        self.assertEqual(m.diagnostic(DAY,t)["daily_read_band"],"AT_OR_ABOVE_NOMINAL_LIMIT")
    def test_20_70pct_threshold(self):
        t,c=mock_transport([payload(rows=3_500_000,writes=70_000)])
        r=m.diagnostic(DAY,t)
        self.assertEqual(r["daily_read_band"],"70_TO_90_PERCENT")
        self.assertEqual(r["daily_write_band"],"70_TO_90_PERCENT")
    def test_21_no_raw_identifiers(self):
        t,c=mock_transport([payload()])
        r=m.diagnostic(DAY,t)
        self.assertNotIn("a-private-test-id",str(r))
        self.assertNotIn("rowsRead",str(r))
    def test_22_unapproved_mode(self):
        with patch.dict(m.os.environ,{},clear=True),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(["--execute-one-time"]),3)
        self.assertIn("NOT_AUTHORIZED_NO_NETWORK",out.getvalue())
    def test_23_one_gate_is_not_enough(self):
        with patch.dict(m.os.environ,{"REMURA_CF_PROBE_ACK":m.ACK},clear=True),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(["--execute-one-time"]),3)
    def test_24_approved_but_no_secret(self):
        env={"REMURA_CF_PROBE_ACK":m.ACK,"REMURA_V091_ACTIVATE":m.ACTIVATION}
        with patch.dict(m.os.environ,env,clear=True),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(["--execute-one-time"]),4)
        self.assertIn("MISSING_OR_INVALID",out.getvalue())
    def test_25_offline_mode_works_with_no_secrets(self):
        with patch.dict(m.os.environ,{},clear=True),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(["--offline-plan"]),0)
        self.assertIn("OFFLINE_NOT_AUTHORIZED",out.getvalue())
if __name__=="__main__":unittest.main()
