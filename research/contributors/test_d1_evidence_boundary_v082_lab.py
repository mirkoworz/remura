# REMURA v0.82 LAB — NEW offline transport boundary tests (no historical suite)
import unittest
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1_evidence_boundary_v082_lab as m
NOW = datetime(2026, 11, 21, 17, 0, tzinfo=timezone.utc)

class D1NewBoundaryTests(unittest.TestCase):
    def good(self):
        return m._demo()
    def assert_blocked(self, value, status=None):
        out = m.audit(value, now_utc=NOW)
        self.assertEqual(out["decision"], "NO_GO")
        self.assertFalse(out["automatic_deploy_allowed"])
        self.assertFalse(out["d1_daily_usage_attested"])
        self.assertFalse(out["exact_billing_attested"])
        if status:
            self.assertEqual(out["status"], status)
    def test_01_today_empty_not_zero(self):
        self.assert_blocked(self.good(), "TODAY_EMPTY_PRIOR_PRESENT_UNKNOWN_NOT_ZERO")
    def test_02_both_empty_still_unknown(self):
        a=self.good()
        a["prior"]["graphql"]["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"]=[]
        self.assert_blocked(a,"BOTH_DAYS_EMPTY_UNKNOWN_NOT_ZERO")
    def test_03_present_adaptive_never_billing(self):
        a=self.good()
        a["today"]["graphql"]["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"]=[
            {"dimensions":{"date":"2026-11-21","databaseId":a["inventory"][0]["uuid"]},
             "sum":{"rowsRead":0,"rowsWritten":0}}
        ]
        self.assert_blocked(a,"TODAY_ADAPTIVE_ESTIMATE_ONLY")
    def test_04_timeout_no_response(self):
        a=self.good()
        a["today"].update(transport="TIMEOUT",http_status=None,content_type=None,body_bytes=0,graphql=None)
        self.assert_blocked(a,"TRANSPORT_OR_HTTP_UNAVAILABLE")
    def test_05_network_error_no_response(self):
        a=self.good()
        a["today"].update(transport="NETWORK_ERROR",http_status=None,content_type=None,body_bytes=0,graphql=None)
        self.assert_blocked(a,"TRANSPORT_OR_HTTP_UNAVAILABLE")
    def test_06_timeout_with_stale_body_rejected(self):
        a=self.good()
        a["today"]["transport"]="TIMEOUT"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_07_auth_denied(self):
        a=self.good()
        a["today"]["http_status"]=403
        self.assert_blocked(a,"TRANSPORT_OR_HTTP_UNAVAILABLE")
        self.assertEqual(m.audit(a,now_utc=NOW)["today"],"AUTH_DENIED")
    def test_08_rate_limit(self):
        a=self.good()
        a["today"]["http_status"]=429
        self.assert_blocked(a,"TRANSPORT_OR_HTTP_UNAVAILABLE")
        self.assertEqual(m.audit(a,now_utc=NOW)["today"],"RATE_LIMITED")
    def test_09_provider_server_error(self):
        a=self.good();a["prior"]["http_status"]=503
        self.assert_blocked(a,"TRANSPORT_OR_HTTP_UNAVAILABLE")
    def test_10_wrong_mime(self):
        a=self.good();a["today"]["content_type"]="text/html"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_11_excess_response_size(self):
        a=self.good();a["today"]["body_bytes"]=m.MAX_BODY_BYTES+1
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_12_future_observation(self):
        a=self.good();a["today"]["observed_utc"]="2026-11-21T17:10:00Z"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_13_stale_observation(self):
        a=self.good();a["prior"]["observed_utc"]="2026-11-20T13:00:00Z"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_14_wrong_day(self):
        a=self.good();a["today"]["day"]="2026-11-20"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_15_wrong_uuid_in_today(self):
        a=self.good();a["today"]["graphql"]["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"]=[
            {"dimensions":{"date":"2026-11-21","databaseId":"22222222-2222-4222-8222-222222222222"},
             "sum":{"rowsRead":1,"rowsWritten":0}}
        ]
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_16_graphql_error_no_spill(self):
        a=self.good();a["today"]["graphql"]["errors"]=[{"message":"SECRET_EMAIL@example.invalid"}]
        result=m.audit(a,now_utc=NOW)
        self.assertEqual(result["status"],"INVALID_OR_UNVERIFIABLE")
        self.assertNotIn("SECRET_EMAIL",str(result))
    def test_17_invalid_run_id(self):
        a=self.good();a["run_id"]=True
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_18_bad_fingerprint(self):
        a=self.good();a["query_digest"]="not-a-sha"
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_19_payload_pii_not_exposed(self):
        a=self.good();a["today"]["graphql"]["extra_pii"]="redacted@private.invalid"
        self.assertNotIn("private.invalid",str(m.audit(a,now_utc=NOW)))
    def test_20_invalid_timezone(self):
        self.assert_blocked(self.good() , "TODAY_EMPTY_PRIOR_PRESENT_UNKNOWN_NOT_ZERO")
        a=m.audit(self.good(),now_utc=datetime(2026,11,21,17,0))
        self.assertEqual(a["status"],"INVALID_OR_UNVERIFIABLE")
    def test_21_bad_args(self):
        self.assertEqual(m.main([]),2)
    def test_22_self_check(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
    def test_23_missing_inventory(self):
        a=self.good();del a["inventory"]
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
    def test_24_duplicate_account(self):
        a=self.good();a["prior"]["graphql"]["data"]["viewer"]["accounts"].append({"d1AnalyticsAdaptiveGroups":[]})
        self.assert_blocked(a,"INVALID_OR_UNVERIFIABLE")
