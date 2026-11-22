# REMURA TV v0.8.190 — 16 NEW frozen-fold scheduling checks only.
import copy
import unittest
from frozen_fold_maturity_v0190_lab import plan_maturities, AdmissionError

H1="2026-11-23T00:02:00Z"
CLOSE="2026-11-23T00:00:00Z"
RECV="2026-11-23T00:01:00Z"
SPOT=dict(market="FX",provider="TV",ticker="EURUSD",product="SPOT",contract="")
FUT=dict(market="CME",provider="CFTC",ticker="EUR",product="FUTURE",contract="6E")
SHA="a"*64

def sample(when=H1, close=CLOSE, received=RECV, *, did="D1"):
    decision=dict(decision_id=did,decision_utc=when,instrument=dict(SPOT),
                  evidence_ids=dict(CVD_M5="C1",PRICE_ONLY_M5="P1",RETAIL="R1",COT_TFF="T1"))
    rows=[
        dict(evidence_id="C1",decision_id=did,kind="CVD_M5",
             instrument=dict(SPOT),observed_utc=close,received_utc=received,
             published_utc=None,source_sha256=SHA),
        dict(evidence_id="P1",decision_id=did,kind="PRICE_ONLY_M5",
             instrument=dict(SPOT),observed_utc=close,received_utc=received,
             published_utc=None,source_sha256=SHA),
        dict(evidence_id="R1",decision_id=did,kind="RETAIL",
             instrument=dict(SPOT),observed_utc="2026-11-22T23:59:00Z",
             received_utc="2026-11-22T23:59:30Z",published_utc=None,
             source_sha256=SHA),
        dict(evidence_id="T1",decision_id=did,kind="COT_TFF",
             instrument=dict(FUT),observed_utc="2026-11-17T00:00:00Z",
             received_utc="2026-11-20T20:03:00Z",
             published_utc="2026-11-20T20:00:00Z",source_sha256=SHA),
    ]
    return [decision],rows

def check(ds=None,rows=None,now="2026-11-23T00:10:00Z"):
    if ds is None:
        ds,rows=sample()
    return plan_maturities(ds,rows,evaluation_utc=now)

def first(*args,**kwargs):
    return check(*args,**kwargs)["decisions"][0]

class FoldMaturityTests(unittest.TestCase):
    def test_01_fresh_primary_pending_without_market_outcome(self):
        z=first()
        self.assertEqual(z["fold"],"HOLDOUT_1")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],
                         "PENDING_CLAIMED_EVALUATION_CLOCK")
        self.assertIsNone(z["horizons"]["PRIMARY_60M"]["price_outcome"])
    def test_02_elapsed_self_reported_clock_not_proof(self):
        z=first(now="2026-11-23T02:00:00Z")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],
                         "WINDOW_ELAPSED_CLAIM_ONLY_NO_OUTCOME")
        self.assertFalse(z["horizons"]["PRIMARY_60M"]["maturity_clock_independently_verified"])
    def test_03_primary_60m_target_is_exact(self):
        z=first()
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["target_utc"],
                         "2026-11-23T01:02:00Z")
    def test_04_secondary_240_and_1440_targets_are_frozen(self):
        z=first()
        self.assertEqual(z["horizons"]["SECONDARY_240M"]["target_utc"],
                         "2026-11-23T04:02:00Z")
        self.assertEqual(z["horizons"]["SECONDARY_1440M"]["target_utc"],
                         "2026-11-24T00:02:00Z")
    def test_05_last_hour_60m_crossing_end_is_rejected(self):
        ds,rows=sample(when="2026-11-29T23:30:00Z",
                       close="2026-11-29T23:25:00Z",
                       received="2026-11-29T23:26:00Z")
        z=first(ds,rows,now="2026-11-30T03:00:00Z")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],
                         "CROSSES_EXCLUSIVE_FOLD_END_NO_OUTCOME")
        self.assertIn("PRIMARY_60M_CROSSES_FOLD_END",z["blocking_reasons"])
    def test_06_end_exactly_equal_is_within_fold(self):
        ds,rows=sample(when="2026-11-29T23:00:00Z",
                       close="2026-11-29T22:55:00Z",
                       received="2026-11-29T22:56:00Z")
        z=first(ds,rows,now="2026-11-30T00:00:00Z")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["target_utc"],
                         "2026-11-30T00:00:00Z")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],
                         "WINDOW_ELAPSED_CLAIM_ONLY_NO_OUTCOME")
    def test_07_source_bar_from_development_cannot_join_holdout(self):
        ds,rows=sample(close="2026-11-22T23:55:00Z",
                       received="2026-11-22T23:56:00Z")
        a=first(ds,rows)["blocking_reasons"]
        self.assertIn("CVD_M5_BAR_OUTSIDE_DECISION_FOLD",a)
        self.assertIn("PRICE_ONLY_M5_BAR_OUTSIDE_DECISION_FOLD",a)
    def test_08_holdout_1_source_cannot_pair_holdout_2(self):
        ds,rows=sample(when="2026-11-30T00:02:00Z",
                       close="2026-11-29T23:55:00Z",
                       received="2026-11-29T23:56:00Z")
        z=first(ds,rows,now="2026-11-30T00:10:00Z")
        self.assertEqual(z["fold"],"HOLDOUT_2")
        self.assertIn("CVD_M5_BAR_OUTSIDE_DECISION_FOLD",z["blocking_reasons"])
    def test_09_holdout_2_allows_new_fold_local_bar_only_as_claim(self):
        ds,rows=sample(when="2026-11-30T00:02:00Z",
                       close="2026-11-30T00:00:00Z",
                       received="2026-11-30T00:01:00Z")
        z=first(ds,rows,now="2026-11-30T00:10:00Z")
        self.assertNotIn("CVD_M5_BAR_OUTSIDE_DECISION_FOLD",z["blocking_reasons"])
        self.assertEqual(z["status"],"ABSTAIN_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED")
    def test_10_development_decision_no_horizon_admission(self):
        ds,rows=sample(when="2026-11-22T23:58:00Z",
                       close="2026-11-22T23:55:00Z",
                       received="2026-11-22T23:56:00Z")
        z=first(ds,rows)
        self.assertEqual(z["fold"],"DEVELOPMENT_FROZEN")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],"NOT_IN_HOLDOUT")
    def test_11_outside_all_windows_never_matched(self):
        ds,rows=sample(when="2026-12-07T00:00:00Z",
                       close="2026-12-06T23:55:00Z",
                       received="2026-12-06T23:56:00Z")
        z=first(ds,rows,now="2026-12-08T00:00:00Z")
        self.assertEqual(z["horizons"]["PRIMARY_60M"]["state"],"NOT_IN_HOLDOUT")
    def test_12_no_cvd_link_has_explicit_missingness(self):
        ds,rows=sample()
        ds[0]["evidence_ids"]["CVD_M5"]=None
        z=first(ds,rows)
        self.assertIn("CVD_M5_FOLD_SOURCE_UNAVAILABLE",z["blocking_reasons"])
        self.assertIn("CVD_M5_MISSING_NOT_ZERO",z["blocking_reasons"])
    def test_13_wrong_decision_source_is_refused(self):
        ds,rows=sample()
        rows[0]["decision_id"]="OTHER"
        z=first(ds,rows)
        self.assertIn("CVD_M5_FOLD_SOURCE_UNAVAILABLE",z["blocking_reasons"])
    def test_14_forged_source_witness_flag_is_schema_invalid(self):
        ds,rows=sample()
        rows[0]["independent_proof"]=True
        with self.assertRaisesRegex(AdmissionError,"invalid_evidence_schema"):
            check(ds,rows)
    def test_15_invalid_evaluation_clock_rejected(self):
        for stamp in ("2026-11-23T01:00:00+01:00","bad-time"):
            with self.subTest(stamp=stamp),self.assertRaises(AdmissionError):
                check(now=stamp)
    def test_16_snapshot_cannot_fake_trade_or_coverage(self):
        z=check()
        self.assertFalse(z["holdout_signal_or_pnl"])
        self.assertFalse(z["expected_market_bar_denominator_known"])
        self.assertFalse(z["source_receipts_independently_verified"])
        self.assertFalse(z["frozen_v2_protocol_changed"])
        self.assertFalse(z["live_capture_enabled"])

if __name__=="__main__":
    unittest.main()
