# REMURA COT v0.8 — 15 NEW offline spot-vs-futures sign/mapping gates.
import unittest
from cot_forward_only_v06_lab import ForwardOnlyCOT
from cot_spot_futures_mapping_v08_lab import sketch_spot_mapping,MappingError

CODE="112741"
D1="2026-11-10"
D2="2026-11-17"
T0="2026-11-20T10:00:00Z"
T1="2026-11-20T11:00:00Z"
T2="2026-11-20T12:00:00Z"
ROWS={("tff",CODE,D1):(1000.,60.,40.,80.,50.),
      ("tff",CODE,D2):(1000.,90.,40.,70.,50.)}
HASH="a"*64

def props(**kwargs):
    x={"fx_symbol":"EURUSD","cftc_code_claim":CODE,
       "future_underlying_currency_claim":"EUR",
       "future_quote_currency_claim":"USD",
       "mapping_artifact_sha256_claim":HASH,
       "mapping_document_ref_claim":"fixture/docs/eurusd",
       "evidence_status":"UNVERIFIED_LOCAL_CLAIM"}
    x.update(kwargs);return x

class MappingTests(unittest.TestCase):
    def setUp(self):
        self.fx=ForwardOnlyCOT(synthetic=True)
    def tearDown(self):
        self.fx.close()
    def seed(self,rows=ROWS,at=T0):
        self.fx.capture(rows,received_utc=at,source_claim="CFTC_PRIMARY_CLAIM")
    def review(self,p=None,at=T1):
        return sketch_spot_mapping(self.fx,proposal=props() if p is None else p,
                                   report_dates=(D1,D2),decision_utc=at)
    def test_01_valid_synthetic_eurusd_claim_never_confirms_mapping(self):
        self.seed()
        z=self.review()
        self.assertEqual(z["status"],"UNATTESTED_USD_LEG_DIRECTION_SKETCH_NOT_SIGNAL")
        self.assertFalse(z["cftc_code_to_currency_independently_proven"])
        self.assertFalse(z["scientific_admission"])
    def test_02_eurusd_claim_same_sign(self):
        self.seed()
        z=self.review()
        self.assertEqual(z["assumed_orientation"],"SAME_SIGN_AS_NON_USD_FUTURE")
        self.assertEqual(z["cohort_deltas"],{"ASSET_MANAGER":3.,"LEVERAGED_FUNDS":-1.})
    def test_03_usdjpy_claim_inverts_nonusd_futures_sign(self):
        self.seed()
        z=self.review(props(fx_symbol="USDJPY",future_underlying_currency_claim="JPY"))
        self.assertEqual(z["assumed_orientation"],"INVERTED_VERSUS_NON_USD_FUTURE")
        self.assertEqual(z["cohort_deltas"],{"ASSET_MANAGER":-3.,"LEVERAGED_FUNDS":1.})
        self.assertFalse(z["signal_allowed"])
    def test_04_eurjpy_cross_not_assumed_as_single_leg(self):
        self.seed()
        z=self.review(props(fx_symbol="EURJPY"))
        self.assertEqual(z["status"],"UNKNOWN_UNSUPPORTED_OR_CROSS_MAPPING")
        self.assertIsNone(z["cohort_deltas"])
    def test_05_nonusd_underlying_not_in_pair_is_unknown(self):
        self.seed()
        z=self.review(props(future_underlying_currency_claim="GBP"))
        self.assertIsNone(z["assumed_orientation"])
    def test_06_unsupported_futures_quote_not_silently_mapped(self):
        self.seed()
        z=self.review(props(future_quote_currency_claim="JPY"))
        self.assertEqual(z["status"],"UNKNOWN_UNSUPPORTED_OR_CROSS_MAPPING")
    def test_07_same_currency_pair_rejected(self):
        with self.assertRaisesRegex(MappingError,"same_currency"):
            self.review(props(fx_symbol="USDUSD"))
    def test_08_malformed_fx_symbol_rejected(self):
        with self.assertRaises(MappingError):
            self.review(props(fx_symbol="EUR/USD"))
    def test_09_unmapped_unknown_cftc_code_refused(self):
        with self.assertRaises(ValueError):
            self.review(props(cftc_code_claim="000000"))
    def test_10_non_tff_disagg_code_refused(self):
        with self.assertRaises(ValueError):
            self.review(props(cftc_code_claim="088691"))
    def test_11_missing_week_has_no_percentage_proxy(self):
        z=self.review()
        self.assertEqual(z["status"],"UNKNOWN_COT_WEEK_AT_DECISION")
        self.assertIsNone(z["cohort_deltas"])
        self.assertEqual(z["missing_report_dates"],[D1,D2])
    def test_12_future_capture_does_not_backfill_an_earlier_decision(self):
        self.seed(at=T2)
        z=self.review(at=T1)
        self.assertEqual(z["status"],"UNKNOWN_COT_WEEK_AT_DECISION")
    def test_13_proof_fields_claim_only_no_self_certification(self):
        self.seed()
        with self.assertRaisesRegex(MappingError,"mapping_claim_schema_invalid"):
            self.review(props(verified=True))
        with self.assertRaisesRegex(MappingError,"unverifiable_or_unpinned"):
            self.review(props(evidence_status="PROVIDER_VERIFIED"))
        with self.assertRaisesRegex(MappingError,"unverifiable_or_unpinned"):
            self.review(props(mapping_artifact_sha256_claim="abc"))
    def test_14_other_store_denied(self):
        with self.assertRaisesRegex(MappingError,"forward_only_synthetic_store_required"):
            sketch_spot_mapping("oracle.sqlite",proposal=props(),
                                report_dates=(D1,D2),decision_utc=T1)
    def test_15_proxies_never_promoted_to_price_or_institutional_edge(self):
        self.seed()
        z=self.review()
        for name in ("futures_contract_specification_verified",
                     "futures_publication_time_verified",
                     "spot_feed_contract_verified",
                     "independent_first_seen_verified",
                     "basis_and_roll_adjustments_verified",
                     "execution_basis_proven","signal_allowed","real_data_used"):
            self.assertFalse(z[name])
        self.assertEqual(z["provider_calls"],0)
        self.assertFalse(z["oracle_queried"])

if __name__=="__main__":
    unittest.main()
