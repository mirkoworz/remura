# REMURA TradingView v0.8.188 — new scientific abstention checks only.
# No provider data, PnL, trading orders, or old suite reruns.
import unittest
from scientific_admission_firewall_v0188_lab import review_decision,audit_batch,AdmissionError

T0="2026-11-23T00:00:00Z"
T1="2026-11-23T00:01:30Z"
T2="2026-11-23T00:02:00Z"
SHA="b"*64

def sample(*,did="TV_SYN_01",close=T0,receipt=T1):
    return {"decision_id":did,"bar_close_utc":close,
            "receipt_utc":receipt,"source":"TRADINGVIEW_CVD",
            "timeframe":"M5","source_sha256":SHA,
            "price_only_comparator_id":"PRICE_SYN_01",
            "external_witness_reference":"synthetic-local-claim"}

def review(**override):
    values=dict(decision_id="TV_SYN_01",decision_utc=T2,cvd_candidate=sample(),
        retail_evidence={"status":"REPOSITORY_REPLAY_UNATTESTED"},
        cot_evidence={"status":"LOCAL_VERSION_UNATTESTED"},
        mapping_claim="EURUSD/CFTC-CONTRACT-NOT-VERIFIED",
        required_m5_bars=20,observed_m5_bars=20)
    values.update(override)
    return review_decision(**values)

class ScientificFirewallTests(unittest.TestCase):
    def test_01_all_structurally_present_claims_are_still_abstain(self):
        out=review()
        self.assertEqual(out["status"],"ABSTAIN_NO_PROSPECTIVE_SCIENTIFIC_ADMISSION")
        self.assertFalse(out["external_first_seen_attested"])
        self.assertFalse(out["institutional_edge_proven"])

    def test_02_valid_clock_claim_cannot_bypass_external_cvd_witness(self):
        self.assertIn("M5_CVD_TIME_INDEPENDENTLY_UNVERIFIED",review()["blocking_reasons"])

    def test_03_local_myfxbook_replay_must_remain_unattested(self):
        self.assertIn("RETAIL_SOURCE_RECEIPT_NOT_INDEPENDENTLY_VERIFIED",
                      review()["blocking_reasons"])

    def test_04_local_cot_revision_must_remain_unattested(self):
        self.assertIn("COT_SOURCE_RECEIPT_NOT_INDEPENDENTLY_VERIFIED",
                      review()["blocking_reasons"])

    def test_05_declared_futures_spot_mapping_not_independent_proof(self):
        out=review()
        self.assertIn("SPOT_FUTURES_MAPPING_UNVERIFIED",out["blocking_reasons"])
        self.assertFalse(out["cross_market_mapping_independently_verified"])

    def test_06_missing_mapping_has_distinct_reason(self):
        self.assertIn("SPOT_FUTURES_MAPPING_MISSING",
                      review(mapping_claim=None)["blocking_reasons"])

    def test_07_missing_retail_and_cot_are_unknown_not_market_flat(self):
        out=review(retail_evidence=None,cot_evidence=None)
        self.assertIn("RETAIL_HISTORICAL_VALUE_MISSING",out["blocking_reasons"])
        self.assertIn("COT_HISTORICAL_REVISION_MISSING",out["blocking_reasons"])
        self.assertTrue(out["missingness_is_not_a_market_outcome"])

    def test_08_market_bars_claimed_complete_without_independent_coverage(self):
        out=review()
        self.assertIn("M5_REQUIRED_COVERAGE_UNATTESTED",out["blocking_reasons"])

    def test_09_partial_market_bars_still_missing_and_unattested(self):
        out=review(required_m5_bars=20,observed_m5_bars=15)
        self.assertIn("M5_MISSINGNESS_PRESENT",out["blocking_reasons"])

    def test_10_absent_market_hours_denominator_is_unknown_not_zero(self):
        out=review(required_m5_bars=None,observed_m5_bars=None)
        self.assertIn("M5_REQUIRED_COVERAGE_UNKNOWN",out["blocking_reasons"])

    def test_11_close_after_decision_is_a_future_bar(self):
        out=review(decision_utc=T0,cvd_candidate=sample(receipt=T1))
        self.assertIn("CVD_RECEIPT_NOT_AVAILABLE_BY_DECISION",out["blocking_reasons"])

    def test_12_late_receipt_beyond_120s_rejected(self):
        out=review(decision_utc="2026-11-23T00:05:00Z",
                   cvd_candidate=sample(receipt="2026-11-23T00:02:01Z"))
        self.assertIn("M5_CVD_NOT_ON_TIME_COMPARABLE",out["blocking_reasons"])

    def test_13_missing_decision_identity_link_blocks_pairing(self):
        out=review(cvd_candidate=sample(did="OTHER_SYN_01"))
        self.assertIn("DECISION_LINK_NOT_EXACT",out["blocking_reasons"])

    def test_14_out_of_holdout_decision_never_entered(self):
        out=review(decision_utc="2026-11-22T23:55:00Z")
        self.assertIn("OUTSIDE_PREREGISTERED_HOLDOUT",out["blocking_reasons"])

    def test_15_batch_never_generates_trades_or_pnl(self):
        first=dict(decision_id="TV_SYN_01",decision_utc=T2,
                   cvd_candidate=sample(),retail_evidence=None,cot_evidence=None)
        second=dict(decision_id="TV_SYN_02",decision_utc=T2,
                   cvd_candidate=sample(did="TV_SYN_02"),retail_evidence=None,
                   cot_evidence=None)
        result=audit_batch([first,second])
        self.assertEqual(result["decisions"],2)
        self.assertEqual(result["trade_signals"],0)
        self.assertFalse(result["price_outcomes_calculated"])
        self.assertTrue(result["counts_are_submitted_decisions_not_expected_market_bars"])

    def test_16_duplicate_decision_does_not_backfill_or_repair_fifo(self):
        row=dict(decision_id="TV_SYN_01",decision_utc=T2,cvd_candidate=sample())
        with self.assertRaisesRegex(AdmissionError,"duplicate_decision"):
            audit_batch([row,row])

    def test_17_untrusted_verified_bool_cannot_override_admission(self):
        with self.assertRaises(TypeError):
            review_decision(decision_id="TV_SYN_01",decision_utc=T2,
                            independently_verified=True)

    def test_18_unsupported_evidence_tier_rejected_not_promoted(self):
        out=review(cot_evidence={"status":"EXTERNALLY_TIME_ATTESTED"})
        self.assertIn("COT_EVIDENCE_INVALID_OR_UNSUPPORTED",out["blocking_reasons"])

if __name__=="__main__":
    unittest.main()
