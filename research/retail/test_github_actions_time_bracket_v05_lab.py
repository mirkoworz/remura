# REMURA v0.5: new offline real-Git clock-bracket cases only.
# Do not rerun earlier v0.2/v0.3/v0.4 retail suites.
import unittest
from github_actions_time_bracket_v05_lab import (
    EVIDENCE, BracketError, inspect_one, audit
)

class TemporalBracketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=audit()

    def test_01_three_real_content_commits_reconciled(self):
        self.assertEqual(self.result["count"],3)
        self.assertEqual(len(self.result["brackets"]),3)

    def test_02_source_github_actions_runs_are_pinned(self):
        self.assertEqual([b["collector_run_id"] for b in self.result["brackets"]],
                         [44726515105,44972218268,45004678062])

    def test_03_existing_pages_run_ids_are_pinned(self):
        self.assertEqual([b["pages_run_id"] for b in self.result["brackets"]],
                         [44726531678,44972231080,45004698324])

    def test_04_run_start_to_pages_start_bracket_seconds(self):
        self.assertEqual([b["bracket_seconds"] for b in self.result["brackets"]],
                         [7,10,15])

    def test_05_source_run_to_sample_clock_gaps_are_not_backfilled(self):
        self.assertEqual([b["collector_to_sample_seconds"] for b in self.result["brackets"]],
                         [5,7,13])

    def test_06_sample_to_pages_run_start_reported_seconds(self):
        self.assertEqual([b["sample_to_pages_seconds"] for b in self.result["brackets"]],
                         [2,3,2])

    def test_07_pages_start_is_not_public_page_availability(self):
        for item in self.result["brackets"]:
            self.assertFalse(item["pages_started_means_page_publicly_available"])

    def test_08_pages_runs_started_before_collector_run_completed(self):
        self.assertEqual([x["pages_started_before_collector_run_completed"]
                          for x in self.result["brackets"]],[True,True,True])

    def test_09_not_independent_market_publication_first_seen(self):
        for item in self.result["brackets"]:
            self.assertFalse(item["original_provider_publication_attested"])
            self.assertFalse(item["market_data_first_seen_independently_attested"])
            self.assertFalse(item["decision_admission_allowed"])

    def test_10_no_external_calls_new_runs_or_market_training(self):
        self.assertEqual(self.result["external_calls"],0)
        self.assertEqual(self.result["new_runs_launched"],0)
        self.assertFalse(self.result["scientific_holdout_admission"])

    def test_11_wrong_parent_run_head_fails_closed(self):
        changed=dict(EVIDENCE[2],collector_run_head="0"*40)
        with self.assertRaisesRegex(BracketError,"source_run_head_not_parent_commit"):
            inspect_one(changed)

    def test_12_wrong_commit_content_blob_fails_closed(self):
        changed=dict(EVIDENCE[0],latest_blob="0"*40)
        with self.assertRaisesRegex(BracketError,"committed_content_hash_mismatch"):
            inspect_one(changed)

    def test_13_pages_before_sample_fails_temporal_boundary(self):
        changed=dict(EVIDENCE[0],pages_created_utc="2026-11-20T11:18:31Z")
        with self.assertRaisesRegex(BracketError,"snapshot_outside"):
            inspect_one(changed)

    def test_14_sample_before_run_started_fails_temporal_boundary(self):
        changed=dict(EVIDENCE[0],collector_created_utc="2026-11-20T11:18:33Z")
        with self.assertRaisesRegex(BracketError,"snapshot_outside"):
            inspect_one(changed)

    def test_15_naive_local_time_not_accepted_as_utc(self):
        changed=dict(EVIDENCE[2],sample_utc="2026-11-22T09:50:44+01:00")
        with self.assertRaises(BracketError):
            inspect_one(changed)

    def test_16_caller_supplied_proof_flag_not_accepted(self):
        changed=dict(EVIDENCE[1],independent_first_seen_verified=True)
        with self.assertRaisesRegex(BracketError,"evidence_schema_invalid"):
            inspect_one(changed)

if __name__=="__main__":
    unittest.main()
