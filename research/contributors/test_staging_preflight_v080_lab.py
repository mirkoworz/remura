# REMURA Contributors v0.80 LAB — 19 NEW combined NO-GO preflight tests.
from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
import json
import unittest

from staging_preflight_v080_lab import build_preflight,REQUIRED_MANUAL_GATES

NOW=datetime(2026,11,21,17,22,tzinfo=timezone.utc)


def logs():
    return {
        "d1": (
            "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA\n"
            "REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED\n"
        ),
        "workers": (
            "REMURA_CF_WORKERS_USAGE=OK\n"
            "WORKERS_UTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
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


def group(day,n=1):
    return {"data":{"viewer":{"accounts":[{"d1AnalyticsAdaptiveGroups":[{
        "dimensions":{"date":day.isoformat(),
                      "databaseId":"11111111-1111-4111-8111-111111111111"},
        "sum":{"rowsRead":12,"rowsWritten":1},
    }] if n else []}]}}}


def users(n=1):
    return [{"success":True,"errors":[],"result":[{
        "id":f"{i:08x}-1111-4111-8111-111111111111",
        "access_seat":True,"email":f"fictional{i}@example.invalid"} for i in range(n)],
        "result_info":{"page":1,"per_page":100,"count":n,"total_count":n,"total_pages":1}}]


def preflight(*, monitor=None, access=None, today=None, prior=None, when=NOW):
    return build_preflight(
        existing_monitor_logs=logs() if monitor is None else monitor,
        access_users_pages=users() if access is None else access,
        d1_today=group(when.date(),0) if today is None else today,
        d1_yesterday=group(when.date()-timedelta(days=1),1) if prior is None else prior,
        now_utc=when,
    )


class StagingPreflightV080(unittest.TestCase):
    def test_01_real_21_nov_2026_status_is_no_go(self):
        self.assertEqual(preflight()["decision"],"NO_GO")

    def test_02_no_automatic_deploy_flag(self):
        self.assertIs(preflight()["automatic_deploy_allowed"],False)

    def test_03_d1_daily_stays_unknown(self):
        self.assertEqual(preflight()["d1_daily"],"UNKNOWN")

    def test_04_d1_two_day_today_empty_does_not_mean_zero(self):
        self.assertEqual(preflight()["d1_window_status"],"TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO")

    def test_05_worker_estimate_can_be_present_while_d1_unknown(self):
        self.assertEqual(preflight()["workers_daily"],"ADAPTIVE_ESTIMATE_PRESENT")

    def test_06_account_storage_metadata_is_separate(self):
        self.assertEqual(preflight()["d1_storage"],"METADATA_SNAPSHOT_PRESENT")

    def test_07_access_user_count_does_not_attest_billing(self):
        s=preflight()
        self.assertEqual(s["access_authenticated_flags"],1)
        self.assertIsNone(s["access_billing_seats_available"])

    def test_08_access_plan_must_be_confirmed_manually(self):
        self.assertIn("CONFIRM_ACCESS_FREE_PLAN_AND_BILLABLE_SEATS",preflight()["pending_gates"])

    def test_09_new_staging_requires_independent_authorization(self):
        self.assertIn("AUTHORIZE_STAGING_DEPLOY_SEPARATELY",preflight()["pending_gates"])

    def test_10_safari_login_logout_remains_unverified(self):
        self.assertIn("VERIFY_SAFARI_LOGIN_LOGOUT_REVOKE",preflight()["pending_gates"])

    def test_11_access_context_remains_unverified(self):
        self.assertFalse(preflight()["cloudflare_access_real_session_attested"])

    def test_12_all_required_manual_gates_remain_pending(self):
        self.assertTrue(set(REQUIRED_MANUAL_GATES).issubset(set(preflight()["pending_gates"])))

    def test_13_with_d1_today_groups_still_no_go(self):
        s=preflight(today=group(NOW.date(),1))
        self.assertEqual(s["d1_window_status"],"TODAY_GROUPS_PRESENT_STILL_ADAPTIVE")
        self.assertEqual(s["decision"],"NO_GO")

    def test_14_with_both_days_empty_still_no_go(self):
        s=preflight(prior=group(NOW.date()-timedelta(days=1),0))
        self.assertIn("D1_TWO_DAY_ADAPTIVE_DATASET_INCOMPLETE",s["pending_gates"])

    def test_15_invalid_access_api_pagination_blocks(self):
        s=preflight(access=[{"secret":"error"}])
        self.assertIn("ACCESS_USERS_INVENTORY_UNKNOWN_OR_EMPTY",s["pending_gates"])

    def test_16_empty_access_inventory_blocks(self):
        s=preflight(access=users(0))
        self.assertIn("ACCESS_USERS_INVENTORY_UNKNOWN_OR_EMPTY",s["pending_gates"])

    def test_17_no_email_or_cloudflare_id_leaks_into_report(self):
        s=json.dumps(preflight(),sort_keys=True)
        self.assertNotIn("@example.invalid",s)
        self.assertNotIn("11111111-1111",s)

    def test_18_max_potential_status_is_still_no_go(self):
        d=logs()
        d["d1"]=(
            "REMURA_CF_ACCOUNT_QUOTA=OK\n"
            "UTC_DAY=2026-11-21; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING\n"
            "D1_ACCOUNT_ROWS_READ_ESTIMATE=196\n"
            "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=784\n"
            "D1_FREE_READ_LIMIT=5000000\n"
            "D1_FREE_WRITE_LIMIT=100000\n"
        )
        s=preflight(monitor=d,today=group(NOW.date(),1),access=users(1))
        self.assertEqual(s["decision"],"NO_GO")
        self.assertFalse(s["production_budget_attested"])

    def test_19_invalid_or_duplicate_monitor_evidence_fails_closed(self):
        d=logs()
        d["workers"] += "REMURA_CF_WORKERS_USAGE=OK\n"
        with self.assertRaises(ValueError):
            preflight(monitor=d)


if __name__=="__main__":
    unittest.main()
