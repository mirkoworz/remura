# REMURA Contributors v0.80 LAB — 31 NEW D1 adaptive GraphQL data tests.
from __future__ import annotations
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import unittest

from d1_two_day_visibility_v080_lab import (
    D1EvidenceError, inspect_day, inspect_window, main,
)

TODAY=date(2026,11,21)
YESTERDAY=TODAY-timedelta(days=1)


def uuid(i):
    return f"{i:08x}-2222-4222-8222-222222222222"


def response(day=TODAY,n=1,read=3,write=1):
    return {"data":{"viewer":{"accounts":[{"d1AnalyticsAdaptiveGroups":[
        {"dimensions":{"date":day.isoformat(),"databaseId":uuid(i)},
         "sum":{"rowsRead":read,"rowsWritten":write}}
        for i in range(n)
    ]}]}}}


def window(today=None,prior=None):
    return inspect_window(
        response(TODAY,1) if today is None else today,
        response(YESTERDAY,1) if prior is None else prior,
        utc_day=TODAY,
    )


class D1TwoDayVisibilityV080Tests(unittest.TestCase):
    def assertUnknown(self,value):
        self.assertEqual(value["status"],"UNKNOWN_OR_INVALID_DATASET")
        self.assertFalse(value["automatic_deploy_allowed"])

    def test_01_today_groups_are_estimate_not_billing(self):
        result=window()
        self.assertEqual(result["status"],"TODAY_GROUPS_PRESENT_STILL_ADAPTIVE")
        self.assertFalse(result["automatic_deploy_allowed"])

    def test_02_today_single_read_count_informative(self):
        self.assertEqual(window()["today_rows_read_estimate"],3)

    def test_03_today_single_write_count_informative(self):
        self.assertEqual(window()["today_rows_written_estimate"],1)

    def test_04_today_empty_prior_present_is_unknown_not_zero(self):
        result=window(response(TODAY,0),response(YESTERDAY,1))
        self.assertEqual(result["status"],"TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO")
        self.assertIsNone(result["today_rows_read_estimate"])
        self.assertIsNone(result["today_rows_written_estimate"])

    def test_05_two_empty_days_are_still_unknown(self):
        result=window(response(TODAY,0),response(YESTERDAY,0))
        self.assertEqual(result["status"],"BOTH_DAYS_EMPTY_NOT_ZERO")
        self.assertIsNone(result["today_rows_read_estimate"])

    def test_06_today_present_prior_empty_does_not_block_data_presence(self):
        result=window(response(TODAY,1),response(YESTERDAY,0))
        self.assertEqual(result["status"],"TODAY_GROUPS_PRESENT_STILL_ADAPTIVE")
        self.assertEqual(result["prior_group_count"],0)

    def test_07_zero_counters_from_actual_group_are_distinct_from_empty(self):
        result=window(response(TODAY,1,0,0))
        self.assertEqual(result["today_rows_read_estimate"],0)
        self.assertEqual(result["today_rows_written_estimate"],0)

    def test_08_two_databases_are_aggregated_without_ids(self):
        result=window(response(TODAY,2,4,3))
        self.assertEqual(result["today_rows_read_estimate"],8)
        self.assertEqual(result["today_rows_written_estimate"],6)
        self.assertNotIn(uuid(0),json.dumps(result))

    def test_09_ten_groups_within_free_reference(self):
        self.assertEqual(window(response(TODAY,10))["today_group_count"],10)

    def test_10_eleven_groups_refused(self):
        self.assertUnknown(window(response(TODAY,11)))

    def test_11_duplicate_db_id_rejected(self):
        src=response(TODAY,2)
        group=src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"]
        group[1]["dimensions"]["databaseId"]=group[0]["dimensions"]["databaseId"]
        self.assertUnknown(window(src))

    def test_12_wrong_date_does_not_convert_to_today(self):
        self.assertUnknown(window(response(YESTERDAY,1)))

    def test_13_prior_wrong_date_denied(self):
        self.assertUnknown(window(prior=response(TODAY,1)))

    def test_14_missing_viewer_denied(self):
        self.assertUnknown(window({"data":{}},response(YESTERDAY,1)))

    def test_15_missing_data_denied(self):
        self.assertUnknown(window({"data":None},response(YESTERDAY,1)))

    def test_16_graphql_errors_denied(self):
        self.assertUnknown(window({"errors":[{"message":"invalid auth"}]},response(YESTERDAY,1)))

    def test_17_multiple_accounts_denied(self):
        src=response()
        src["data"]["viewer"]["accounts"] *= 2
        self.assertUnknown(window(src))

    def test_18_zero_accounts_denied(self):
        src=response()
        src["data"]["viewer"]["accounts"]=[]
        self.assertUnknown(window(src))

    def test_19_missing_groups_denied(self):
        src=response()
        del src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"]
        self.assertUnknown(window(src))

    def test_20_missing_dimensions_denied(self):
        src=response()
        del src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]["dimensions"]
        self.assertUnknown(window(src))

    def test_21_missing_sum_denied(self):
        src=response()
        del src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]["sum"]
        self.assertUnknown(window(src))

    def test_22_boolean_read_count_denied(self):
        self.assertUnknown(window(response(TODAY,1,True,0)))

    def test_23_negative_write_count_denied(self):
        self.assertUnknown(window(response(TODAY,1,1,-1)))

    def test_24_fractional_read_count_denied(self):
        self.assertUnknown(window(response(TODAY,1,1.7,0)))

    def test_25_integral_float_count_accepted_only_as_estimate(self):
        self.assertEqual(window(response(TODAY,1,4.0,2.0))["today_rows_read_estimate"],4)

    def test_26_absurdly_large_counter_denied(self):
        self.assertUnknown(window(response(TODAY,1,1000000000001,0)))

    def test_27_missing_database_id_denied(self):
        src=response()
        del src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]["dimensions"]["databaseId"]
        self.assertUnknown(window(src))

    def test_28_bad_database_id_denied(self):
        src=response()
        src["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]["dimensions"]["databaseId"]="DB-SECRET"
        self.assertUnknown(window(src))

    def test_29_no_raw_account_ids_in_summary(self):
        src=response()
        src["data"]["viewer"]["accounts"][0]["raw-account-id"]="private-account"
        self.assertNotIn("private-account",json.dumps(window(src)))

    def test_30_no_network_or_secrets_in_code(self):
        source=(Path(__file__).parent/"d1_two_day_visibility_v080_lab.py").read_text()
        for item in ("urllib", "requests.", "os.environ","Authorization: Bearer","api.cloudflare.com"):
            self.assertNotIn(item,source)

    def test_31_cli_rejects_any_live_args(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(main(["--access-token","hidden"]),2)
        self.assertIn("NO_GO",out.getvalue())

    def test_32_cli_synthetic_verification(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(main(["--synthetic-self-check"]),0)
        result=json.loads(out.getvalue())
        self.assertEqual(result["status"],"TODAY_EMPTY_PRIOR_ACTIVITY_NOT_ZERO")
        self.assertFalse(result["automatic_deploy_allowed"])


if __name__=="__main__":
    unittest.main()
