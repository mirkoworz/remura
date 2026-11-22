# REMURA TradingView v0.8.189 — only NEW per-decision junction tests.
import copy
import unittest
from decision_evidence_junction_v0189_lab import inspect_join, AdmissionError

D0 = "2026-11-23T00:02:00Z"
CLOSE = "2026-11-23T00:00:00Z"
RECEIVED = "2026-11-23T00:01:00Z"
SPOT = dict(market="FX", provider="TV", ticker="EURUSD", product="SPOT", contract="")
FUT = dict(market="CME", provider="CFTC", ticker="EUR", product="FUTURE", contract="6E")
DIGEST = "a" * 64

def decision(did="TEST_DECISION_1"):
    return dict(decision_id=did, decision_utc=D0, instrument=dict(SPOT),
        evidence_ids=dict(CVD_M5="CVD1", PRICE_ONLY_M5="PRICE1",
                          RETAIL="RETAIL1", COT_TFF="COT1"))

def row(name, kind, *, decision_id="TEST_DECISION_1"):
    obs = CLOSE if kind in ("CVD_M5", "PRICE_ONLY_M5") else (
        "2026-11-22T23:59:00Z" if kind == "RETAIL" else "2026-11-17T00:00:00Z")
    received = RECEIVED if kind in ("CVD_M5", "PRICE_ONLY_M5") else (
        "2026-11-22T23:59:30Z" if kind == "RETAIL" else "2026-11-20T20:03:00Z")
    return dict(evidence_id=name, decision_id=decision_id, kind=kind,
        instrument=dict(FUT if kind == "COT_TFF" else SPOT),
        observed_utc=obs, received_utc=received,
        published_utc="2026-11-20T20:00:00Z" if kind == "COT_TFF" else None,
        source_sha256=DIGEST)

def sample():
    return [row("CVD1","CVD_M5"), row("PRICE1","PRICE_ONLY_M5"),
            row("RETAIL1","RETAIL"), row("COT1","COT_TFF")]

def inspect(d=None, rows=None):
    return inspect_join([decision() if d is None else d],
                        sample() if rows is None else rows)

def reasons(output):
    return set(output["decisions"][0]["blocking_reasons"])

class DecisionJunctionTests(unittest.TestCase):
    def test_01_structural_four_source_join_never_proves_alpha(self):
        out = inspect()
        self.assertEqual(out["decision_count"], 1)
        self.assertEqual(out["status"], "ABSTAIN_RESEARCH_ONLY")
        self.assertFalse(out["institutional_edge_proven"])
        self.assertFalse(out["price_outcomes_computed"])

    def test_02_permutation_cannot_change_exact_id_join(self):
        a = inspect()
        b = inspect(rows=list(reversed(sample())))
        self.assertEqual(a["decisions"], b["decisions"])
        self.assertEqual(set(a["decisions"][0]["links"]), 
                         {"CVD_M5", "PRICE_ONLY_M5", "RETAIL", "COT_TFF"})

    def test_03_missing_retail_not_zero_or_bearish(self):
        d = decision()
        d["evidence_ids"]["RETAIL"] = None
        out = inspect(d)
        self.assertIn("RETAIL_MISSING_NOT_ZERO", reasons(out))
        self.assertTrue(out["decisions"][0]["no_market_missingness_imputed"])

    def test_04_missing_comparator_blocks_comparison(self):
        d = decision()
        d["evidence_ids"]["PRICE_ONLY_M5"] = None
        self.assertIn("PRICE_ONLY_M5_MISSING_NOT_ZERO", reasons(inspect(d)))

    def test_05_swapped_pointer_does_not_allow_positional_guess(self):
        d = decision()
        d["evidence_ids"]["CVD_M5"] = "PRICE1"
        d["evidence_ids"]["PRICE_ONLY_M5"] = "CVD1"
        self.assertIn("CVD_M5_WRONG_EVIDENCE_KIND", reasons(inspect(d)))

    def test_06_cross_decision_evidence_rejected(self):
        rows = sample()
        rows[0]["decision_id"] = "OTHER_DECISION"
        self.assertIn("CVD_M5_CROSS_DECISION_LINK", reasons(inspect(rows=rows)))

    def test_07_cvd_over_120s_late_rejected(self):
        rows = sample()
        rows[0]["received_utc"] = "2026-11-23T00:02:01Z"
        self.assertIn("CVD_M5_RECEIPT_V2_LATE", reasons(inspect(rows=rows)))

    def test_08_cvd_received_after_decision_rejected(self):
        rows = sample()
        rows[0]["received_utc"] = "2026-11-23T00:02:30Z"
        self.assertIn("RECEIPT_LATE_OR_UNKNOWN_AT_DECISION", reasons(inspect(rows=rows)))

    def test_09_cvd_non_m5_close_rejected(self):
        rows = sample()
        rows[0]["observed_utc"] = "2026-11-23T00:00:01Z"
        self.assertIn("CVD_M5_BAR_NOT_M5_ALIGNED", reasons(inspect(rows=rows)))

    def test_10_price_comparator_requires_same_m5_bar(self):
        rows = sample()
        rows[1]["observed_utc"] = "2026-11-22T23:55:00Z"
        self.assertIn("PRICE_COMPARATOR_BAR_NOT_IDENTICAL", reasons(inspect(rows=rows)))

    def test_11_retail_sample_after_decision_is_future(self):
        rows = sample()
        rows[2]["observed_utc"] = "2026-11-23T00:03:00Z"
        self.assertIn("RETAIL_OBSERVATION_FUTURE_OR_UNKNOWN", reasons(inspect(rows=rows)))

    def test_12_cot_publication_after_decision_rejected(self):
        rows = sample()
        rows[3]["published_utc"] = "2026-11-23T00:03:00Z"
        self.assertIn("COT_PUBLICATION_CHAIN_LATE_OR_UNKNOWN", reasons(inspect(rows=rows)))

    def test_13_fake_spot_cot_does_not_confer_mapping(self):
        rows = sample()
        rows[3]["instrument"] = dict(SPOT)
        a = reasons(inspect(rows=rows))
        self.assertIn("COT_INSTRUMENT_NOT_FUTURE", a)
        self.assertIn("COT_FUTURES_SPOT_MAPPING_UNVERIFIED", a)

    def test_14_duplicate_evidence_id_rejected_globally(self):
        rows = sample()
        rows.append(copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(AdmissionError, "duplicate_evidence_id"):
            inspect(rows=rows)

    def test_15_duplicate_decision_id_never_fifo_repaired(self):
        with self.assertRaisesRegex(AdmissionError, "duplicate_decision_id"):
            inspect_join([decision(),decision()], sample())

    def test_16_untrusted_verified_claim_is_schema_error(self):
        rows = sample()
        rows[0]["signed_independent_timestamp"] = True
        with self.assertRaisesRegex(AdmissionError, "invalid_evidence_schema"):
            inspect(rows=rows)

    def test_17_unreferenced_evidence_is_reported_not_backfilled(self):
        rows = sample() + [row("EXTRA1", "CVD_M5")]
        out = inspect(rows=rows)
        self.assertEqual(out["unreferenced_evidence_ids"], ["EXTRA1"])
        self.assertTrue(out["source_join_ambiguous"])
        self.assertFalse(out["backfill_performed"])

    def test_18_futures_spot_claim_cannot_prove_mapping_or_first_seen(self):
        out = inspect()
        self.assertIn("COT_FUTURES_SPOT_MAPPING_UNVERIFIED", reasons(out))
        self.assertIn("INDEPENDENT_SOURCE_RECEIPTS_NOT_VERIFIED", reasons(out))
        self.assertFalse(out["decisions"][0]["first_seen_independently_proven"])
        self.assertFalse(out["real_holdout_evidence_inferred"])

if __name__ == "__main__":
    unittest.main()
