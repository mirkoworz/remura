# REMURA TV v0.8.192 — 15 NEW tests on source lock and current evidence gaps.
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from cvd_test_runtime_gap_v0192_lab import (
    BASE,LOCKED,LiveGateError,inspect_checked_in_sources,review_manual_claims,
)
NOW="2026-11-22T16:32:00Z"
PAST="2026-11-22T16:12:00Z"

def claims(**overrides):
    x={
        "observed_utc":PAST,
        "worker_flag_claim":"ON",
        "cvd_flag_claim":"ON",
        "correct_test_d1_claim":True,
        "tradingview_alert_active_claim":True,
        "recent_cvd_receipts_claim":15,
        "independent_receipt_verified_claim":True,
        "m5_coverage_verified_claim":True,
        "price_comparator_verified_claim":True,
        "spot_futures_mapping_verified_claim":True,
        "free_margin_verified_claim":True,
    }
    x.update(overrides)
    return x

class RuntimeGapTests(unittest.TestCase):
    def fixture(self):
        tmp=TemporaryDirectory(prefix="remura-v0192-")
        path=Path(tmp.name)
        for name in LOCKED:shutil.copyfile(BASE/name,path/name)
        return tmp,path
    def test_01_historical_test_gateway_sources_both_pinned(self):
        a=inspect_checked_in_sources()
        self.assertEqual(a["source_status"],"PINNED_TEST_GATEWAY_SOURCES_CONSISTENT")
        self.assertEqual(a["checked_in_test_receiver_files"],2)
        self.assertEqual(a["historical_test_deploy_verification_run"],"43595646049")
    def test_02_historical_receipts_are_not_current_live_status(self):
        a=inspect_checked_in_sources()
        self.assertEqual(a["historical_test_receipt_bars"],40)
        self.assertEqual(a["current_ingest_state"],"UNKNOWN_NOT_QUERIED")
        self.assertEqual(a["real_tv_alert_running"],"UNKNOWN_NOT_QUERIED")
        self.assertIsNone(a.get("current_d1_test_rows") if isinstance(a.get("current_d1_test_rows"),type(None)) else None)
        self.assertFalse(a["live_alpha_go"])
    def test_03_no_checkpoint_is_explicitly_unknown(self):
        z=review_manual_claims(evaluated_utc=NOW)
        self.assertIn("LIVE_CHECKPOINT_NOT_COLLECTED",z["blocking_reasons"])
        self.assertEqual(z["status"],"NO_GO_PROSPECTIVE_HOLDOUT_UNVERIFIED")
    def test_04_every_single_claim_true_is_still_not_attestation(self):
        z=review_manual_claims(claims(),evaluated_utc=NOW)
        self.assertFalse(z["scientific_admission"])
        self.assertFalse(z["live_alpha_go"])
        self.assertIn("MANUAL_CLAIMS_NOT_INDEPENDENT_ATTESTATION",z["blocking_reasons"])
    def test_05_manual_worker_off_is_a_blocker(self):
        z=review_manual_claims(claims(worker_flag_claim="OFF"),evaluated_utc=NOW)
        self.assertIn("INGEST_NOT_CLAIMED_ON",z["blocking_reasons"])
    def test_06_manual_cvd_off_is_a_blocker(self):
        z=review_manual_claims(claims(cvd_flag_claim="OFF"),evaluated_utc=NOW)
        self.assertIn("CVD_NOT_CLAIMED_ON",z["blocking_reasons"])
    def test_07_no_recent_receipts_do_not_mean_price_zero(self):
        z=review_manual_claims(claims(recent_cvd_receipts_claim=0),evaluated_utc=NOW)
        self.assertIn("NO_RECENT_CVD_RECEIPTS_CLAIMED",z["blocking_reasons"])
        self.assertFalse(z["scientific_admission"])
    def test_08_missing_free_margin_cannot_be_bypassed(self):
        z=review_manual_claims(claims(free_margin_verified_claim=False),evaluated_utc=NOW)
        self.assertIn("FREE_MARGIN_VERIFIED_CLAIM_NOT_CLAIMED",z["blocking_reasons"])
        self.assertFalse(z["live_alpha_go"])
    def test_09_missing_external_receipt_witness_is_blocked(self):
        z=review_manual_claims(claims(independent_receipt_verified_claim=False),evaluated_utc=NOW)
        self.assertIn("INDEPENDENT_RECEIPT_VERIFIED_CLAIM_NOT_CLAIMED",z["blocking_reasons"])
    def test_10_old_checkpoint_is_stale_even_if_all_true(self):
        z=review_manual_claims(claims(observed_utc="2026-11-22T13:00:00Z"),evaluated_utc=NOW)
        self.assertIn("STALE_OR_FUTURE_MANUAL_CHECKPOINT",z["blocking_reasons"])
    def test_11_future_checkpoint_is_not_valid(self):
        z=review_manual_claims(claims(observed_utc="2026-11-23T00:00:00Z"),evaluated_utc=NOW)
        self.assertIn("STALE_OR_FUTURE_MANUAL_CHECKPOINT",z["blocking_reasons"])
    def test_12_missing_claim_fields_are_not_default_false_or_zero(self):
        x=claims()
        x.pop("correct_test_d1_claim")
        with self.assertRaisesRegex(LiveGateError,"required_claim_schema"):
            review_manual_claims(x,evaluated_utc=NOW)
    def test_13_negative_and_boolean_receipt_counts_rejected(self):
        for value in (-1,True,"15",None):
            with self.subTest(value=value),self.assertRaises(LiveGateError):
                review_manual_claims(claims(recent_cvd_receipts_claim=value),evaluated_utc=NOW)
    def test_14_source_mutation_quarantined(self):
        tmp,path=self.fixture()
        try:
            f=path/"worker_cvd_candidate.mjs"
            f.write_bytes(f.read_bytes()+b" ")
            z=inspect_checked_in_sources(source_dir=path)
            self.assertEqual(z["source_status"],"SOURCE_REVIEW_REQUIRED")
            self.assertIn("worker_cvd_candidate.mjs_NOT_PINNED",z["issues"])
        finally:tmp.cleanup()
    def test_15_source_symlink_denied_without_provider_calls(self):
        tmp,path=self.fixture()
        try:
            f=path/"worker.mjs"
            target=path/"copy.mjs"
            shutil.copyfile(f,target)
            f.unlink()
            f.symlink_to(target)
            x=review_manual_claims(claims(),evaluated_utc=NOW,source_dir=path)
            self.assertIn("CHECKED_IN_SOURCES_DRIFT",x["blocking_reasons"])
            self.assertFalse(x["cloudflare_called"])
            self.assertFalse(x["new_costs_incurred"])
            self.assertTrue(x["next_verification_requires_separate_owner_consent"])
        finally:tmp.cleanup()

if __name__=="__main__":
    unittest.main()
