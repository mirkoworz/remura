# REMURA Contributors v0.79 LAB — FRESH synthetic cases ONLY; no Cloudflare calls.
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import contextlib
import io
import json
import tempfile
import unittest

import free_quota_evidence_v079_lab as guard

TODAY = datetime(2026, 11, 21, 17, 15, 0, tzinfo=timezone.utc)


def logs(day="2026-11-21"):
    return {
        "d1": (
            "REMURA_CF_ACCOUNT_QUOTA=OK\n"
            "UTC_DAY="+day+"; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
            "D1_ACCOUNT_ROWS_READ_ESTIMATE=196\n"
            "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784\n"
            "D1_FREE_READ_LIMIT=5000000\n"
            "D1_FREE_WRITE_LIMIT=100000\n"
        ),
        "workers": (
            "REMURA_CF_WORKERS_USAGE=OK\n"
            "WORKERS_UTC_DAY="+day+"; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
            "WORKERS_ACCOUNT_REQUESTS_ESTIMATE=199\n"
            "WORKERS_ACCOUNT_ERRORS_ESTIMATE=0\n"
            "WORKERS_FREE_DAILY_REQUEST_LIMIT=100000\n"
        ),
        "test_storage": (
            "REMURA_D1_TEST_STORAGE=OK\n"
            "REMURA_D1_TEST_STORAGE_BYTES=6266880\n"
            "REMURA_D1_TEST_STORAGE_LIMIT_BYTES=500000000\n"
        ),
        "account_storage": (
            "REMURA_D1_ACCOUNT_STORAGE=OK\n"
            "D1_ACCOUNT_DATABASE_COUNT=4\n"
            "D1_ACCOUNT_STORAGE_BYTES=6557696\n"
            "D1_ACCOUNT_LARGEST_DB_BYTES=6266880\n"
            "D1_ACCOUNT_FREE_STORAGE_LIMIT_BYTES=5000000000\n"
            "D1_ACCOUNT_FREE_SINGLE_DB_LIMIT_BYTES=500000000\n"
            "D1_ACCOUNT_FREE_DB_COUNT_LIMIT=10\n"
        ),
    }


def replace(key, before, after, d=None):
    result = dict(logs() if d is None else d)
    assert before in result[key], "fixture must contain the target"
    result[key] = result[key].replace(before, after)
    return result


def assess(d=None, **kwargs):
    return guard.classify(logs() if d is None else d, now_utc=TODAY, **kwargs)


def graphql(n=0):
    return {"data": {"viewer": {"accounts": [{"d1AnalyticsAdaptiveGroups": [
        {"dimensions": {"date": "2026-11-21", "databaseId": str(i)},
         "sum": {"rowsRead": 1, "rowsWritten": 1}}
        for i in range(n)
    ]}]}}}


class FreeEvidenceCases(unittest.TestCase):
    def test_01_complete_without_access_is_no_go(self):
        self.assertEqual(assess().decision, "NO_GO")

    def test_02_no_access_evidence_reason(self):
        self.assertIn("ACCESS_FREE_SEATS_NOT_ATTESTED", assess().reason_codes)

    def test_03_perfect_synthetic_report_is_only_review(self):
        self.assertEqual(assess(access_seats_attested=True).decision, "LAB_REVIEW_ONLY")

    def test_04_review_never_authorizes_deployment(self):
        self.assertIs(assess(access_seats_attested=True).public_dict()["automatic_deploy_allowed"], False)

    def test_05_report_has_only_safe_aggregates(self):
        value = json.dumps(assess().public_dict())
        self.assertNotIn("6266880", value)
        self.assertNotIn("remura-collector", value)
        self.assertNotIn("@", value)
        self.assertIn('"version": "0.79"', value)

    def test_06_missing_d1_graphql_groups_are_unknown_not_zero(self):
        d = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA")
        result = assess(d, access_seats_attested=True)
        self.assertEqual(result.decision, "NO_GO")
        self.assertIn("D1_DAILY_UNKNOWN_NOT_ZERO", result.reason_codes)

    def test_07_d1_error_is_no_go(self):
        d = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=ERROR:graphql")
        self.assertEqual(assess(d, access_seats_attested=True).decision, "NO_GO")

    def test_08_yesterdays_d1_metrics_not_accepted_for_today(self):
        d = replace("d1", "UTC_DAY=2026-11-21", "UTC_DAY=2026-11-20")
        self.assertIn("D1_DAILY_NOT_FRESH", assess(d).reason_codes)

    def test_09_workers_yesterday_cannot_prove_today(self):
        d = replace("workers", "WORKERS_UTC_DAY=2026-11-21", "WORKERS_UTC_DAY=2026-11-20")
        self.assertIn("WORKERS_DAILY_NOT_FRESH", assess(d).reason_codes)

    def test_10_d1_source_must_be_adaptive_estimate_and_not_billing(self):
        d = replace("d1", "SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE", "SOURCE=BILLING_EXACT")
        self.assertIn("D1_DAILY_NOT_FRESH", assess(d).reason_codes)

    def test_11_workers_source_must_be_attested_type(self):
        d = replace("workers", "NOT_EXACT_BILLING", "EXACT_BILL")
        self.assertIn("WORKERS_DAILY_NOT_FRESH", assess(d).reason_codes)

    def test_12_missing_d1_rows_read_cannot_be_inferred(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_READ_ESTIMATE=196\n", "")
        self.assertIn("D1_DAILY_INVALID_COUNTERS", assess(d).reason_codes)

    def test_13_missing_d1_rows_write_cannot_be_inferred(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784\n", "")
        self.assertIn("D1_DAILY_INVALID_COUNTERS", assess(d).reason_codes)

    def test_14_ambiguous_zero_and_missing_are_different(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_READ_ESTIMATE=196", "D1_ACCOUNT_ROWS_READ_ESTIMATE=0")
        d = replace("d1", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0", d)
        self.assertEqual(assess(d, access_seats_attested=True).decision, "LAB_REVIEW_ONLY")
        empty = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA", d)
        self.assertEqual(assess(empty, access_seats_attested=True).decision, "NO_GO")

    def test_15_false_free_read_limit_must_not_go(self):
        d = replace("d1", "D1_FREE_READ_LIMIT=5000000", "D1_FREE_READ_LIMIT=500000000")
        self.assertIn("D1_REFERENCE_LIMIT_CHANGED", assess(d).reason_codes)

    def test_16_changed_daily_write_limit_must_not_go(self):
        d = replace("d1", "D1_FREE_WRITE_LIMIT=100000", "D1_FREE_WRITE_LIMIT=500000")
        self.assertIn("D1_REFERENCE_LIMIT_CHANGED", assess(d).reason_codes)

    def test_17_writes_at_70_percent_block(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=70000")
        self.assertIn("D1_DAILY_TOO_CLOSE_TO_FREE_CAP", assess(d).reason_codes)

    def test_18_reads_at_70_percent_block(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_READ_ESTIMATE=196", "D1_ACCOUNT_ROWS_READ_ESTIMATE=3500000")
        self.assertIn("D1_DAILY_TOO_CLOSE_TO_FREE_CAP", assess(d).reason_codes)

    def test_19_warning_must_not_become_ok(self):
        d = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=WARNING")
        self.assertEqual(assess(d, access_seats_attested=True).decision, "NO_GO")

    def test_20_critical_must_not_become_ok(self):
        d = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=CRITICAL")
        self.assertEqual(assess(d, access_seats_attested=True).decision, "NO_GO")

    def test_21_worker_requests_70_percent_block(self):
        d = replace("workers", "WORKERS_ACCOUNT_REQUESTS_ESTIMATE=199", "WORKERS_ACCOUNT_REQUESTS_ESTIMATE=70000")
        self.assertIn("WORKERS_DAILY_INVALID_OR_NEAR_CAP", assess(d).reason_codes)

    def test_22_worker_errors_cannot_exceed_requests(self):
        d = replace("workers", "WORKERS_ACCOUNT_ERRORS_ESTIMATE=0", "WORKERS_ACCOUNT_ERRORS_ESTIMATE=200")
        self.assertIn("WORKERS_DAILY_INVALID_OR_NEAR_CAP", assess(d).reason_codes)

    def test_23_workers_warning_blocks(self):
        d = replace("workers", "REMURA_CF_WORKERS_USAGE=OK", "REMURA_CF_WORKERS_USAGE=WARNING")
        self.assertEqual(assess(d, access_seats_attested=True).decision, "NO_GO")

    def test_24_missing_workers_graphql_blocks(self):
        d = replace("workers", "REMURA_CF_WORKERS_USAGE=OK", "REMURA_CF_WORKERS_USAGE=UNKNOWN_NO_DATA")
        self.assertIn("WORKERS_DAILY_UNKNOWN", assess(d).reason_codes)

    def test_25_no_account_storage_metadata_blocks(self):
        d = replace("account_storage", "REMURA_D1_ACCOUNT_STORAGE=OK", "REMURA_D1_ACCOUNT_STORAGE=UNKNOWN")
        self.assertIn("D1_STORAGE_METADATA_UNKNOWN", assess(d).reason_codes)

    def test_26_no_test_storage_metadata_blocks(self):
        d = replace("test_storage", "REMURA_D1_TEST_STORAGE=OK", "REMURA_D1_TEST_STORAGE=UNKNOWN")
        self.assertIn("D1_STORAGE_METADATA_UNKNOWN", assess(d).reason_codes)

    def test_27_count_at_free_limit_blocks(self):
        d = replace("account_storage", "D1_ACCOUNT_DATABASE_COUNT=4", "D1_ACCOUNT_DATABASE_COUNT=10")
        self.assertIn("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP", assess(d).reason_codes)

    def test_28_count_near_free_limit_blocks(self):
        d = replace("account_storage", "D1_ACCOUNT_DATABASE_COUNT=4", "D1_ACCOUNT_DATABASE_COUNT=7")
        self.assertIn("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP", assess(d).reason_codes)

    def test_29_total_storage_seventy_percent_blocks(self):
        d = replace("account_storage", "D1_ACCOUNT_STORAGE_BYTES=6557696", "D1_ACCOUNT_STORAGE_BYTES=3500000000")
        self.assertIn("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP", assess(d).reason_codes)

    def test_30_single_database_storage_near_cap_blocks(self):
        d = replace("account_storage", "D1_ACCOUNT_LARGEST_DB_BYTES=6266880", "D1_ACCOUNT_LARGEST_DB_BYTES=350000000")
        self.assertIn("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP", assess(d).reason_codes)

    def test_31_test_db_cannot_exceed_biggest_db(self):
        d = replace("test_storage", "REMURA_D1_TEST_STORAGE_BYTES=6266880", "REMURA_D1_TEST_STORAGE_BYTES=9000000")
        self.assertIn("D1_STORAGE_INCONSISTENT_OR_NEAR_CAP", assess(d).reason_codes)

    def test_32_storage_reference_limit_change_denied(self):
        d = replace("account_storage", "D1_ACCOUNT_FREE_DB_COUNT_LIMIT=10", "D1_ACCOUNT_FREE_DB_COUNT_LIMIT=100")
        self.assertIn("D1_STORAGE_REFERENCE_LIMIT_CHANGED", assess(d).reason_codes)

    def test_33_negative_storage_is_not_silently_zero(self):
        d = replace("account_storage", "D1_ACCOUNT_STORAGE_BYTES=6557696", "D1_ACCOUNT_STORAGE_BYTES=-1")
        self.assertIn("D1_STORAGE_INVALID_COUNTERS", assess(d).reason_codes)

    def test_34_false_integer_counter_is_not_accepted(self):
        d = replace("d1", "D1_ACCOUNT_ROWS_READ_ESTIMATE=196", "D1_ACCOUNT_ROWS_READ_ESTIMATE=1.5")
        self.assertIn("D1_DAILY_INVALID_COUNTERS", assess(d).reason_codes)

    def test_35_duplicate_status_key_fails_closed(self):
        d = replace("d1", "REMURA_CF_ACCOUNT_QUOTA=OK", "REMURA_CF_ACCOUNT_QUOTA=OK\nREMURA_CF_ACCOUNT_QUOTA=OK")
        with self.assertRaises(guard.EvidenceError):
            assess(d)

    def test_36_oversized_log_denied(self):
        d = dict(logs())
        d["d1"] += "X"*guard.MAX_BYTES_PER_LOG
        with self.assertRaises(guard.EvidenceError):
            assess(d)

    def test_37_malformed_json_is_not_used_as_evidence(self):
        with self.assertRaises(guard.EvidenceError):
            guard.diagnostic({"not_data": []}, None)

    def test_38_empty_today_with_no_prior_is_unknown(self):
        self.assertEqual(guard.diagnostic(graphql(0), None), "UNKNOWN_EMPTY_TODAY_WITHOUT_CONTROL")

    def test_39_empty_today_plus_prior_activity_is_still_unknown(self):
        self.assertEqual(guard.diagnostic(graphql(0), graphql(1)), "UNKNOWN_EMPTY_TODAY_PRIOR_HAS_ACTIVITY")

    def test_40_empty_both_days_does_not_mean_zero(self):
        self.assertEqual(guard.diagnostic(graphql(0), graphql(0)), "UNKNOWN_EMPTY_BOTH_DAYS")

    def test_41_any_present_group_still_needs_numeric_validation(self):
        self.assertEqual(guard.diagnostic(graphql(1), graphql(0)), "GROUPS_PRESENT_VALUES_STILL_NEED_VALIDATION")

    def test_42_graphql_errors_fail_closed(self):
        with self.assertRaises(guard.EvidenceError):
            guard.diagnostic({"errors": [{"message": "invalid token"}]}, None)

    def test_43_missing_account_results_fail_closed(self):
        with self.assertRaises(guard.EvidenceError):
            guard.diagnostic({"data": {"viewer": {"accounts": []}}}, None)

    def test_44_invalid_time_zone_no_go(self):
        with self.assertRaises(guard.EvidenceError):
            guard.classify(logs(), now_utc=datetime(2026,11,21,17,15))

    def test_45_non_utc_clock_denied(self):
        from datetime import timedelta
        with self.assertRaises(guard.EvidenceError):
            guard.classify(logs(), now_utc=datetime(2026,11,21,17,15,tzinfo=timezone(timedelta(hours=1))))

    def test_46_access_attestation_must_be_bool(self):
        with self.assertRaises(guard.EvidenceError):
            assess(access_seats_attested="YES")

    def test_47_unexpected_category_keys_refused(self):
        d=logs()
        d["owner_email"]="hidden"
        with self.assertRaises(guard.EvidenceError):
            assess(d)

    def test_48_unknown_lines_and_tokens_are_never_printed(self):
        d=logs()
        d["d1"] += "REMURA_CF_API_TOKEN=very-secret-123456\n"
        out = json.dumps(assess(d).public_dict())
        self.assertNotIn("very-secret-123456", out)

    def test_49_account_daily_report_from_2026_11_21_remains_no_go(self):
        d=logs()
        d["d1"]="REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\nREAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED\n"
        verdict=assess(d, access_seats_attested=False)
        self.assertEqual(verdict.decision,"NO_GO")
        self.assertEqual(verdict.d1_daily,"UNKNOWN")
        self.assertEqual(verdict.workers_daily,"ADAPTIVE_ESTIMATE_PRESENT")
        self.assertEqual(verdict.d1_storage,"METADATA_SNAPSHOT_PRESENT")

    def test_50_no_automatic_go_or_live_action_in_any_output(self):
        for seats in (False,True):
            s=assess(access_seats_attested=seats).public_dict()
            self.assertIs(s["automatic_deploy_allowed"],False)
            self.assertNotIn("DEPLOY",s["decision"])

    def test_51_cli_offline_missing_input_is_no_go(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc=guard.main(["script","--offline-logs","/missing1","/missing2","/missing3","/missing4"])
        self.assertEqual(rc,3)
        self.assertIn("NO_GO",out.getvalue())

    def test_52_cli_invalid_arguments_are_rejected(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc=guard.main(["script","--deploy"])
        self.assertEqual(rc,2)
        self.assertIn("NO_GO",out.getvalue())

    def test_53_cli_complete_synthetic_evidence_is_still_no_go_due_to_access(self):
        with tempfile.TemporaryDirectory() as temp:
            d=logs()
            paths=[]
            for category,text in d.items():
                p=Path(temp)/(category+".log")
                p.write_text(text,encoding="utf-8")
                paths.append(str(p))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=guard.main(["script","--offline-logs",*paths])
            self.assertEqual(rc,3)
            body=json.loads(out.getvalue())
            self.assertEqual(body["decision"],"NO_GO")
            self.assertEqual(body["access"],"NOT_MEASURED")
            self.assertFalse(body["automatic_deploy_allowed"])


if __name__=="__main__":
    unittest.main()
