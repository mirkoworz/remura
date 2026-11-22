# REMURA Contributors v0.93 — new offline Free-budget evidence cases.
# Uses sanitized historical GitHub log statuses, no CF GraphQL or Secrets.
import unittest
from contributors_free_proof_gate_v093_lab import (
    REDACTED_RUN_STATUS, EvidenceError, sanitize_status_lines, evaluate
)

RUN=44919682812
DATE="2026-11-21T15:32:05Z"
NOW="2026-11-22T11:38:00Z"

def check(text=REDACTED_RUN_STATUS,**override):
    inputs={"sanitized_status_text":text,"observed_run_id":RUN,
            "observed_run_created_utc":DATE,"reviewed_at_utc":NOW}
    inputs.update(override)
    return evaluate(**inputs)

class ContributorsFreeProofTests(unittest.TestCase):
    def test_01_real_21_nov_d1_graphql_unknown_keeps_no_go(self):
        r=check()
        self.assertEqual(r["status"],"NO_GO_REAL_CONTRIBUTOR_PILOT")
        self.assertIn("REMURA_CF_ACCOUNT_QUOTA:UNKNOWN_NO_GRAPHQL_DATA",r["blocking_reasons"])

    def test_02_existing_three_ok_checks_preserved_without_false_green(self):
        r=check()
        self.assertEqual(r["budget_checks"]["REMURA_CF_WORKERS_USAGE"],"OK")
        self.assertEqual(r["budget_checks"]["REMURA_D1_TEST_STORAGE"],"OK")
        self.assertEqual(r["budget_checks"]["REMURA_D1_ACCOUNT_STORAGE"],"OK")
        self.assertFalse(r["confirmed_billable_headroom"])

    def test_03_incomplete_daily_budget_is_not_silent_success(self):
        r=check()
        self.assertEqual(r["daily_report"],"INCOMPLETE_OR_CRITICAL")
        self.assertIn("DAILY_REPORT_INCOMPLETE",r["blocking_reasons"])

    def test_04_old_log_cannot_prove_todays_account_headroom(self):
        r=check()
        self.assertIn("OBSERVATION_OVER_12H_OLD",r["blocking_reasons"])

    def test_05_github_actions_remaining_allowance_unknown(self):
        self.assertIn("GITHUB_ACTIONS_FREE_HEADROOM_NOT_INDEPENDENTLY_PROVEN",
                      check()["blocking_reasons"])

    def test_06_access_identity_and_free_seat_headroom_unknown(self):
        self.assertIn("CURRENT_ACCESS_SEAT_HEADROOM_NOT_INDEPENDENTLY_PROVEN",
                      check()["blocking_reasons"])

    def test_07_current_cloudflare_billing_plan_unverified(self):
        self.assertIn("CURRENT_CF_PLAN_NOT_INDEPENDENTLY_PROVEN",
                      check()["blocking_reasons"])

    def test_08_never_invites_real_users_or_enables_staging(self):
        r=check()
        self.assertFalse(r["user_invitation_or_staging_enabled"])
        self.assertFalse(r["payment_authorized"])
        self.assertFalse(r["cloudflare_live_query_performed"])

    def test_09_a_all_ok_sanitized_report_still_isnt_independent_provider_proof(self):
        good=("REMURA_CF_ACCOUNT_QUOTA=OK\n"
              "REMURA_CF_WORKERS_USAGE=OK\n"
              "REMURA_D1_TEST_STORAGE=OK\n"
              "REMURA_D1_ACCOUNT_STORAGE=OK\n"
              "REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE\n")
        r=check(good,reviewed_at_utc="2026-11-21T15:33:00Z",
                plan_verified=True,access_seat_headroom_verified=True,
                github_actions_headroom_verified=True,
                independent_provider_receipt_verified=True)
        self.assertIn("SELF_REPORTED_GATES_NOT_A_PROVIDER_AUTHORIZATION",r["blocking_reasons"])
        self.assertEqual(r["status"],"NO_GO_REAL_CONTRIBUTOR_PILOT")

    def test_10_summary_looks_green_but_d1_unknown_is_conflict(self):
        bad=REDACTED_RUN_STATUS.replace(
            "REMURA_DAILY_BUDGET=INCOMPLETE_OR_CRITICAL",
            "REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE")
        self.assertIn("DAILY_SUMMARY_CONFLICT",check(bad)["blocking_reasons"])

    def test_11_bad_or_unknown_key_rejected_without_echo(self):
        with self.assertRaises(EvidenceError):
            sanitize_status_lines(REDACTED_RUN_STATUS+"CLOUDFLARE_TOKEN=private\n")

    def test_12_duplicate_metric_fails_closed(self):
        with self.assertRaises(EvidenceError):
            sanitize_status_lines(REDACTED_RUN_STATUS+"REMURA_CF_WORKERS_USAGE=OK\n")

    def test_13_incomplete_log_is_not_zero_or_green(self):
        with self.assertRaises(EvidenceError):
            sanitize_status_lines("REMURA_CF_WORKERS_USAGE=OK\n")

    def test_14_other_run_id_does_not_inherit_old_status(self):
        with self.assertRaises(EvidenceError):
            check(observed_run_id=RUN+1)

    def test_15_review_date_cannot_be_before_existing_run(self):
        with self.assertRaises(EvidenceError):
            check(reviewed_at_utc="2026-11-20T15:32:05Z")

    def test_16_non_bool_proof_flag_rejected(self):
        with self.assertRaises(EvidenceError):
            check(plan_verified="true")

if __name__=="__main__":
    unittest.main()
