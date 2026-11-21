# REMURA v0.84 LAB — NEW sanitized offline evidence tests only
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import public_evidence_v084_lab as m

class PublicEvidenceNewTests(unittest.TestCase):
    def setUp(self):
        self.sample,self.now=m.demo()
    def call(self):
        r=m.review(self.sample,now_utc=self.now)
        self.assertEqual(r["decision"],"NO_GO")
        self.assertFalse(r["automatic_deploy_allowed"])
        self.assertFalse(r["billing_attested"])
        self.assertFalse(r["real_provider_attested"])
        self.assertEqual(r["access_seats"],"UNKNOWN_NOT_ATTESTED")
        return r
    def test_01_unknown_d1_is_not_zero(self):
        self.assertEqual(self.call()["d1_daily"],"UNKNOWN_NOT_ZERO")
    def test_02_workers_estimate_caution(self):
        self.assertEqual(self.call()["workers_daily"],"ESTIMATE_BELOW_CAUTION_NOT_BILLING")
    def test_03_storage_metadata(self):
        self.assertEqual(self.call()["d1_storage"],"METADATA_BELOW_CAUTION_NOT_BILLING")
    def test_04_real_zero_is_adaptive_only(self):
        self.sample["d1_rows_read_estimate"]=0
        self.sample["d1_rows_written_estimate"]=0
        self.assertEqual(self.call()["d1_daily"],"ADAPTIVE_ESTIMATE_BELOW_CAUTION_NOT_BILLING")
    def test_05_d1_read_at_70_percent(self):
        self.sample["d1_rows_read_estimate"]=3500000
        self.sample["d1_rows_written_estimate"]=0
        self.assertEqual(self.call()["d1_daily"],"NEAR_REFERENCE_LIMIT")
    def test_06_d1_write_at_limit(self):
        self.sample["d1_rows_read_estimate"]=0
        self.sample["d1_rows_written_estimate"]=100000
        self.assertEqual(self.call()["d1_daily"],"AT_OR_OVER_REFERENCE_LIMIT")
    def test_07_workers_at_limit(self):
        self.sample["workers_requests_estimate"]=100000
        self.assertEqual(self.call()["workers_daily"],"AT_OR_OVER_REFERENCE_LIMIT")
    def test_08_storage_at_db_count_limit(self):
        self.sample["d1_database_count"]=10
        self.assertEqual(self.call()["d1_storage"],"AT_OR_OVER_REFERENCE_LIMIT")
    def test_09_unknown_storage(self):
        self.sample["d1_database_count"]=None
        self.sample["d1_account_storage_bytes"]=None
        self.assertEqual(self.call()["d1_storage"],"UNKNOWN")
    def test_10_partial_d1_denied(self):
        self.sample["d1_rows_read_estimate"]=0
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_11_partial_storage_denied(self):
        self.sample["d1_account_storage_bytes"]=None
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_12_bool_as_count_denied(self):
        self.sample["workers_requests_estimate"]=True
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_13_negative_count_denied(self):
        self.sample["workers_requests_estimate"]=-1
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_14_extra_sensitive_key_denied_silent(self):
        self.sample["private_email"]="private@example.invalid"
        r=self.call()
        self.assertEqual(r["status"],"INVALID_OR_UNKNOWN")
        self.assertNotIn("private@example.invalid",str(r))
    def test_15_non_allowlisted_source_denied(self):
        self.sample["source"]="LIVE_PROVIDER"
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_16_yesterday_data_denied(self):
        self.sample["utc_day"]="2026-11-20"
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_17_stale_day_observation_denied(self):
        self.sample["observed_utc"]="2026-11-21T10:00:00Z"
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_18_future_timestamp_denied(self):
        self.sample["observed_utc"]="2026-11-21T17:40:00Z"
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_19_access_counts_not_certification(self):
        self.sample["access_plan"]="FREE_MANUAL_UNVERIFIED"
        self.sample["access_seats_used"]=2
        self.sample["access_seats_total"]=50
        self.assertEqual(self.call()["access_seats"],"UNKNOWN_NOT_ATTESTED")
    def test_20_access_overfull_denied(self):
        self.sample["access_seats_used"]=51
        self.sample["access_seats_total"]=50
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
    def test_21_no_utc_clock_denied(self):
        r=m.review(self.sample,now_utc=datetime(2026,11,21,17,30))
        self.assertEqual(r["status"],"INVALID_OR_UNKNOWN")
    def test_22_raw_input_never_reflected(self):
        self.sample["access_plan"]="PRIVATE_USER@EXAMPLE.INVALID"
        r=self.call()
        self.assertNotIn("@",str(r))
    def test_23_cli_bad_arguments(self):
        self.assertEqual(m.main([]),2)
    def test_24_cli_synthetic(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
    def test_25_oversized_number_denied(self):
        self.sample["d1_rows_read_estimate"]=10**15
        self.sample["d1_rows_written_estimate"]=0
        self.assertEqual(self.call()["status"],"INVALID_OR_UNKNOWN")
if __name__ == "__main__": unittest.main()
