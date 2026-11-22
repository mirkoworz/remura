# REMURA v0.4: 12 new local GitHub Pages run association tests only.
# Neither prior 4-commit nor Myfxbook historical audit suites are rerun.
import unittest
from github_pages_receipt_association_v04_lab import (
    FIXED,ReplayError,audit,review_association
)

class ServerEventAssociationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=audit()

    def test_01_exact_existing_two_real_run_associations(self):
        self.assertEqual(len(self.result["snapshots"]),2)
        self.assertEqual([s["github_pages_run_id"] for s in self.result["snapshots"]],
                         [44726531678,44972231080])

    def test_02_server_reported_run_created_later_than_sample_clock(self):
        self.assertEqual([s["clock_gap_seconds"] for s in self.result["snapshots"]],[2,3])

    def test_03_a_reported_github_server_time_is_not_cryptographic_notary(self):
        self.assertFalse(self.result["github_run_payload_cryptographically_signed"])
        self.assertFalse(self.result["github_server_receive_time_notarized"])

    def test_04_a_public_pages_run_does_not_attest_provider_market_time(self):
        self.assertFalse(self.result["myfxbook_provider_publication_time_proven"])
        self.assertFalse(self.result["independent_market_first_seen_proven"])

    def test_05_even_matching_run_never_enables_holdout_admission(self):
        self.assertFalse(self.result["holdout_science_admission"])
        self.assertFalse(self.result["decision_time_access_proven"])

    def test_06_existing_run_metadata_only_no_new_execution(self):
        self.assertFalse(self.result["github_api_live_called_by_module"])
        self.assertEqual(self.result["new_workflows_launched"],0)
        self.assertFalse(self.result["secrets_used"])

    def test_07_unrelated_head_sha_not_a_witness(self):
        case=dict(FIXED[0],run_head="0"*40)
        self.assertEqual(review_association(**case)["status"],"UNRELATED_GITHUB_EVENT_CLAIM")

    def test_08_unrelated_workflow_never_as_a_receipt(self):
        case=dict(FIXED[0],run_name="REMURA Myfxbook sentiment")
        self.assertEqual(review_association(**case)["status"],"UNRELATED_GITHUB_EVENT_CLAIM")

    def test_09_failed_pages_run_does_not_promote_provenance(self):
        case=dict(FIXED[0],run_conclusion="failure")
        self.assertEqual(review_association(**case)["status"],"UNFINISHED_OR_FAILED_GITHUB_EVENT")

    def test_10_claim_that_pages_started_before_sample_is_rejected(self):
        case=dict(FIXED[0],run_created="2026-11-20T11:18:31Z")
        self.assertEqual(review_association(**case)["status"],"CLOCK_ORDER_NOT_CREDIBLE")

    def test_11_excessively_late_event_cannot_be_treated_as_near_real_time(self):
        case=dict(FIXED[0],run_created="2026-11-20T15:18:34Z")
        self.assertEqual(review_association(**case)["status"],"CLOCK_ORDER_NOT_CREDIBLE")

    def test_12_self_supplied_perfect_run_still_not_scientifically_admitted(self):
        case=dict(FIXED[1])
        result=review_association(**case)
        self.assertEqual(result["status"],
                         "EXTERNAL_PLATFORM_RUN_ASSOCIATION_UNATTESTED_OFFLINE")
        self.assertFalse(result["can_be_used_for_holdout"])

if __name__=="__main__":
    unittest.main()
