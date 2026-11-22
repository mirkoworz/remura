# REMURA new TV v0.8.187 evidence inventory checks only; synthetic metadata.
import unittest

from holdout_evidence_ledger_v0187_lab import AdmissionError, classify, review

H1="2026-11-23T00:00:00Z"
H2="2026-11-30T00:00:00Z"
LAST="2026-12-07T00:00:00Z"
VALID_SHA="a"*64

def row(*, decision="TV_SYN_001", close=H1,
        receipt="2026-11-23T00:01:30Z", source="TRADINGVIEW_CVD",
        timeframe="M5", digest=VALID_SHA, price="PRICE_SYN_001",
        witness="synthetic-assertion-not-verified"):
    return dict(decision_id=decision,bar_close_utc=close,receipt_utc=receipt,
                source=source,timeframe=timeframe,source_sha256=digest,
                price_only_comparator_id=price,
                external_witness_reference=witness)

class TVEvidenceLedgerTests(unittest.TestCase):
    def label(self, sample):
        result=review([sample])
        self.assertEqual(result["submitted_records"],1)
        return next(iter(result["record_classes"]))

    def test_01_empty_window_does_not_invent_coverage(self):
        r=review([])
        self.assertEqual(r["submitted_records"],0)
        self.assertEqual(r["record_classes"],{})
        self.assertFalse(r["m5_market_coverage_verified"])

    def test_02_ontime_claim_still_does_not_admit_real_holdout(self):
        r=review([row()])
        self.assertIn("ON_TIME_CLAIM_NOT_INDEPENDENTLY_VERIFIED",r["record_classes"])
        self.assertFalse(r["scientific_admission"])
        self.assertEqual(r["status"],"NO_GO_REAL_HOLDOUT_ADMISSION")

    def test_03_holdout_one_exact_start_included(self):
        r=review([row()])
        self.assertEqual(r["record_fold_counts"],{"HOLDOUT_1":1})

    def test_04_holdout_two_exact_start_included(self):
        r=review([row(decision="TV_SYN_002",close=H2,receipt="2026-11-30T00:01:00Z")])
        self.assertEqual(r["record_fold_counts"],{"HOLDOUT_2":1})

    def test_05_holdout_two_end_excluded(self):
        self.assertEqual(self.label(row(close=LAST,receipt="2026-12-07T00:01:00Z")),"OUTSIDE_HOLDOUT")

    def test_06_development_cannot_be_relabelled_holdout(self):
        self.assertEqual(self.label(row(close="2026-11-22T23:55:00Z",receipt="2026-11-22T23:56:00Z")),"OUTSIDE_HOLDOUT")

    def test_07_late_more_than_120_seconds_fails(self):
        self.assertEqual(self.label(row(receipt="2026-11-23T00:02:01Z")),"LATE_UNADMITTED")

    def test_08_exact_120_second_boundary_allowed_as_claim_not_proof(self):
        self.assertEqual(self.label(row(receipt="2026-11-23T00:02:00Z")),"ON_TIME_CLAIM_NOT_INDEPENDENTLY_VERIFIED")

    def test_09_receipt_before_close_detected_clock_conflict(self):
        self.assertEqual(self.label(row(receipt="2026-11-22T23:59:59Z")),"CLOCK_CONFLICT")

    def test_10_absent_receipt_is_unknown_not_zero(self):
        self.assertEqual(self.label(row(receipt=None)),"UNKNOWN_RECEIPT")

    def test_11_missing_content_digest_cannot_pass(self):
        self.assertEqual(self.label(row(digest=None)),"NO_CONTENT_IDENTITY")

    def test_12_missing_witness_reference_is_separate_label(self):
        self.assertEqual(self.label(row(witness=None)),"NO_INDEPENDENT_WITNESS")

    def test_13_synthetic_witness_reference_is_never_verified(self):
        r=review([row(witness="https://example.invalid/not-a-real-witness")])
        self.assertFalse(r["independent_time_anchor_verified"])

    def test_14_ctrader_tick_proxy_not_aggressor_cvd(self):
        self.assertEqual(self.label(row(source="CTRADER_TICK_PROXY",timeframe="M15")),"INCOMPARABLE_SOURCE_OR_BAR")

    def test_15_wrong_m5_grid_denied(self):
        self.assertEqual(self.label(row(close="2026-11-23T00:01:00Z")),"INCOMPARABLE_SOURCE_OR_BAR")

    def test_16_missing_price_comparator_cannot_match(self):
        self.assertEqual(self.label(row(price=None)),"MISSING_PRICE_ONLY_COMPARATOR")

    def test_17_duplicate_decision_identifiers_quarantined_without_replacement(self):
        r=review([row(),row(receipt="2026-11-23T00:02:01Z")])
        self.assertEqual(r["record_classes"],{"DUPLICATE_DECISION_QUARANTINE":2})

    def test_18_multiple_distinct_entries_preserve_denominator(self):
        r=review([row(),row(decision="TV_SYN_002",receipt=None)])
        self.assertEqual(r["submitted_records"],2)
        self.assertEqual(sum(r["record_classes"].values()),2)
        self.assertTrue(r["submitted_records_are_not_required_market_hours"])

    def test_19_timestamp_iso_offset_not_accepted(self):
        self.assertEqual(self.label(row(receipt="2026-11-23T01:01:30+01:00")),"INVALID_RECORD")

    def test_20_no_outcomes_or_pnl_ever_reported(self):
        r=review([row()])
        self.assertFalse(r["holdout_outcomes_measured"])
        self.assertFalse(r["statistical_alpha_proven"])
        self.assertFalse(r["live_deployment"])
        self.assertEqual(r["provider_calls"],0)

if __name__=="__main__":
    unittest.main()
