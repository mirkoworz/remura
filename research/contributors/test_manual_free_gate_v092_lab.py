"""REMURA Contributors v0.92 — NEW manual aggregate budget gate cases only."""
from __future__ import annotations
from copy import deepcopy
import unittest
from manual_free_gate_v092_lab import review, SOURCE, SCHEMA

NOW = "2026-11-21T22:00:00Z"
EXAMPLE = {
    "source": SOURCE,
    "observed_utc": "2026-11-21T21:55:00Z",
    "daily_utc": "2026-11-21",
    "free_workers_confirmed": True,
    "free_d1_confirmed": True,
    "access_free_confirmed": True,
    "coverage_all_workers": True,
    "coverage_all_d1_databases": True,
    "requests_today": 1000,
    "rows_read_today": 30000,
    "rows_written_today": 500,
    "d1_storage_bytes": 8_000_000,
    "d1_database_count": 4,
    "access_seats_in_use": 1,
    "access_seats_limit": 50,
}
PROPOSED = {
    "pilot_users": 2,
    "extra_requests": 200,
    "extra_rows_read": 5000,
    "extra_rows_written": 200,
    "extra_storage_bytes": 5_000_000,
    "extra_databases": 1,
}


def run(snapshot=None, planned=None, now=NOW):
    return review(deepcopy(EXAMPLE if snapshot is None else snapshot),
                  deepcopy(PROPOSED if planned is None else planned), now_utc=now)


class ManualFreeGateTests(unittest.TestCase):
    def test_01_nominal_headroom_never_stages_or_bills(self):
        r = run()
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["status"], "MANUAL_SHAPE_AND_PLANNING_HEADROOM_ONLY_NO_GO")
        for k in ("staging_allowed", "deploy_allowed", "pilot_allowed",
                  "additional_spending_allowed", "provider_account_verified_by_tool"):
            self.assertFalse(r[k])
        self.assertEqual(r["cloudflare_api_calls"], 0)
        self.assertEqual(r["d1_sql_calls"], 0)

    def test_02_missing_counter_is_unknown_not_zero(self):
        s = deepcopy(EXAMPLE);del s["rows_read_today"]
        self.assertEqual(run(s)["status"], "UNKNOWN_OR_INCOMPLETE")

    def test_03_explicit_null_counter_is_not_zero(self):
        s = deepcopy(EXAMPLE);s["rows_written_today"] = None
        self.assertIn("rows_written_today_unknown",run(s)["reasons"])

    def test_04_a_valid_explict_zero_counter_is_distinct_from_unknown(self):
        s = deepcopy(EXAMPLE);s["rows_written_today"] = 0
        self.assertEqual(run(s)["status"], "MANUAL_SHAPE_AND_PLANNING_HEADROOM_ONLY_NO_GO")

    def test_05_untrusted_source_cannot_be_treated_as_dashboard_evidence(self):
        s = deepcopy(EXAMPLE);s["source"] = "API_RESULT_EMPTY"
        self.assertEqual(run(s)["status"], "UNKNOWN_OR_INCOMPLETE")

    def test_06_snapshot_older_than_one_hour_blocks(self):
        s = deepcopy(EXAMPLE);s["observed_utc"] = "2026-11-21T20:00:00Z"
        self.assertIn("stale_or_future_snapshot",run(s)["reasons"])

    def test_07_cross_utc_day_snapshot_rejected(self):
        s = deepcopy(EXAMPLE);s["daily_utc"] = "2026-11-20"
        self.assertIn("wrong_utc_day",run(s)["reasons"])

    def test_08_false_plan_declaration_blocks(self):
        s = deepcopy(EXAMPLE);s["free_d1_confirmed"] = False
        self.assertEqual(run(s)["status"],"UNKNOWN_OR_INCOMPLETE")

    def test_09_missing_account_wide_d1_coverage_blocks(self):
        s = deepcopy(EXAMPLE);s["coverage_all_d1_databases"] = False
        self.assertEqual(run(s)["status"],"UNKNOWN_OR_INCOMPLETE")

    def test_10_internal_d1_read_budget_crossed(self):
        s = deepcopy(EXAMPLE);s["rows_read_today"] = 3_499_999
        self.assertIn("rows_read_today_internal_70_percent_ceiling",run(s)["reasons"])

    def test_11_internal_worker_request_budget crossed(self):
        s = deepcopy(EXAMPLE);s["requests_today"] = 70_000
        self.assertIn("requests_today_internal_70_percent_ceiling",run(s)["reasons"])

    def test_12_database_count_above_nominal_limit_rejected(self):
        s = deepcopy(EXAMPLE);s["d1_database_count"] = 10
        self.assertIn("d1_database_count_nominal_limit",run(s)["reasons"])

    def test_13_access_seats_must_cover_all_future_friends(self):
        s = deepcopy(EXAMPLE);s["access_seats_in_use"] = 49
        self.assertIn("insufficient_access_seats",run(s)["reasons"])

    def test_14_boolean_counter_is_not_a_valid_integer(self):
        s = deepcopy(EXAMPLE);s["rows_read_today"] = True
        self.assertIn("rows_read_today_unknown",run(s)["reasons"])

    def test_15_more_than_two_friends_requires_replanning(self):
        p = deepcopy(PROPOSED);p["pilot_users"] = 3
        self.assertIn("pilot_size_not_1_or_2",run(planned=p)["reasons"])

    def test_16_future_usage_unknown_cannot_be_declared_zero(self):
        p = deepcopy(PROPOSED);p["extra_requests"] = 0
        self.assertIn("future_usage_not_planned",run(planned=p)["reasons"])

    def test_17_prohibited_secret_identifiers_cannot_be_added_to_aggregates(self):
        s = deepcopy(EXAMPLE);s["private_access_token"] = "secret-should-not-be-logged"
        r = run(s)
        self.assertEqual(r["status"],"UNKNOWN_OR_INCOMPLETE")
        self.assertNotIn("secret-should-not-be-logged",str(r))

    def test_18_invalid_utc_audit_clock_fails_closed(self):
        self.assertIn("invalid_audit_clock",run(now="yesterday")["reasons"])


if __name__ == "__main__":
    unittest.main()
