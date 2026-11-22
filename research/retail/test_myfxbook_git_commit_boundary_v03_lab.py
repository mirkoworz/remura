# REMURA Retail real Git object verification - NEW tests only.
# Existing pinned-file v0.2 tests and 34-series audit are not rerun.
import copy
import unittest
from myfxbook_git_commit_boundary_v03_lab import (
    CHECKPOINTS,ReplayError,audit,review_claims,
)

class GitProvenanceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real=audit() # One bounded read of four local Git objects.

    def test_01_four_distinct_real_commit_snapshots_reconciled(self):
        self.assertEqual(self.real["summary"]["total_pinned_commits"],4)
        self.assertEqual(self.real["summary"]["status"],
                         "FOUR_COMMIT_CONTENT_RECONCILED_TIME_UNATTESTED")

    def test_02_all_expected_git_commit_identifiers_are_used(self):
        self.assertEqual([x["commit_sha"] for x in self.real["samples"]],
                         [x[0] for x in CHECKPOINTS])

    def test_03_all_expected_git_blob_identifiers_are_used(self):
        self.assertEqual([x["latest_blob_sha1"] for x in self.real["samples"]],
                         [x[1] for x in CHECKPOINTS])

    def test_04_all_historical_utc_snapshots_match_archived_history(self):
        self.assertEqual([x["archived_record_at"] for x in self.real["samples"]],
                         [x[2] for x in CHECKPOINTS])

    def test_05_commit_date_claim_matches_source_clock_but_not_a_witness(self):
        self.assertTrue(self.real["summary"]["timestamp_claims_match"])
        for record in self.real["samples"]:
            self.assertEqual(record["commit_committer_clock_claim"],
                             record["sampled_at"])
        self.assertFalse(self.real["summary"]["independent_github_receive_time_verified"])

    def test_06_no_external_provider_first_seen_from_git_commit_metadata(self):
        self.assertFalse(self.real["summary"]["external_provider_first_seen_verified"])
        self.assertFalse(self.real["summary"]["holdout_decision_admission"])

    def test_07_no_institutional_alpha_from_four_retail_snapshots(self):
        self.assertFalse(self.real["summary"]["institutional_edge_established"])
        self.assertEqual(self.real["summary"]["provider_or_cloudflare_calls"],0)

    def test_08_retained_retail_positions_change_without_predictive_claim(self):
        positions=[s["retail_long_pct"] for s in self.real["samples"]]
        self.assertTrue(all(type(x) in (float,int) and 0<=x<=100 for x in positions))
        self.assertEqual(len(positions),4)
        self.assertFalse(self.real["summary"]["holdout_decision_admission"])

    def test_09_mutated_synthetic_archive_reference_clock_rejected(self):
        forged=copy.deepcopy(self.real["samples"])
        forged[0]["archived_record_at"]="2026-11-18T00:00:00Z"
        with self.assertRaisesRegex(ReplayError,"archived_sample_clock_mismatch"):
            review_claims(forged)

    def test_10_non_utc_claim_rejected(self):
        forged=copy.deepcopy(self.real["samples"])
        forged[1]["sampled_at"]="2026-11-21T09:12:01+01:00"
        forged[1]["archived_record_at"]=forged[1]["sampled_at"]
        with self.assertRaises(ReplayError):
            review_claims(forged)

    def test_11_wrong_number_of_witness_claims_rejected(self):
        with self.assertRaisesRegex(ReplayError,"invalid_pinned_sample_count"):
            review_claims(self.real["samples"][:-1])

    def test_12_different_commit_date_claim_cannot_upgrade_provenance(self):
        forged=copy.deepcopy(self.real["samples"])
        forged[0]["commit_metadata_equals_sample_clock"]=False
        state=review_claims(forged)
        self.assertFalse(state["timestamp_claims_match"])
        self.assertFalse(state["independent_github_receive_time_verified"])
        self.assertFalse(state["holdout_decision_admission"])

if __name__=="__main__":
    unittest.main()
