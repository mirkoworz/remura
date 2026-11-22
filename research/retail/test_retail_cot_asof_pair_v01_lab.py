# REMURA retail x COT: NEW temporal contract fixture checks ONLY.
import dataclasses
import unittest

from retail_cot_asof_pair_v01_lab import (
    GateError, make_fixture_sample, pair_for_decision, select_asof,
)

T0="2026-11-20T09:59:59Z"
T1="2026-11-20T10:00:00Z"
TM="2026-11-20T12:00:00Z"
T2="2026-11-20T14:00:00Z"
T3="2026-11-20T16:00:00Z"

def retail(t=T1,n=55,version=1,obs=T1,source="R1"):
    return make_fixture_sample(provider="MYFXBOOK_RETAIL",
        instrument="EURUSD",receipt_utc=t,
        observation_utc=obs,payload={"long_pct":n},version=version,source_id=source)

def cot(t=T1,n=20,version=1,obs=T1,source="C1"):
    return make_fixture_sample(provider="CFTC_FUTURES",
        instrument="099741",receipt_utc=t,
        observation_utc=obs,payload={"asset_mgr_net":n},version=version,source_id=source)

def paired(decision=TM, rs=None, cs=None, mapping="fixture-not-external"):
    return pair_for_decision(
        decision_id="TV-SYNTHETIC-001",decision_utc=decision,
        retail_samples=[retail()] if rs is None else rs,
        cot_samples=[cot()] if cs is None else cs,
        retail_symbol="EURUSD",cot_futures_code="099741",
        declared_mapping=mapping)

class RetailCotAsOfTests(unittest.TestCase):
    def test_01_both_sources_local_earlier_than_decision_admit_only_fixture_pair(self):
        r=paired()
        self.assertEqual(r["status"],"LOCAL_PAIR_UNATTESTED_FIXTURE_ONLY")
        self.assertEqual(r["retail"]["provider"],"MYFXBOOK_RETAIL")
        self.assertEqual(r["cot"]["provider"],"CFTC_FUTURES")

    def test_02_late_retail_snapshot_is_not_used_for_earlier_decision(self):
        r=paired(rs=[retail(t=T2,obs=T2)])
        self.assertEqual(r["status"],"UNKNOWN_NOT_AVAILABLE")
        self.assertIsNone(r["retail"])

    def test_03_late_cot_revision_is_not_used_for_earlier_decision(self):
        r=paired(cs=[cot(t=T2,obs=T2)])
        self.assertEqual(r["status"],"UNKNOWN_NOT_AVAILABLE")
        self.assertIsNone(r["cot"])

    def test_04_cot_asof_before_revision_preserves_old_value(self):
        old=cot(t=T1,n=20,version=1,obs=T1)
        new=cot(t=T2,n=90,version=2,obs=T2,source="C2")
        earlier=paired(cs=[old,new])
        later=paired(decision=T3,cs=[old,new])
        self.assertEqual(earlier["cot"]["payload"],{"asset_mgr_net":20})
        self.assertEqual(later["cot"]["payload"],{"asset_mgr_net":90})

    def test_05_retail_asof_before_update_preserves_old_sentiment(self):
        old=retail(t=T1,n=55,version=1,obs=T1)
        new=retail(t=T2,n=65,version=2,obs=T2,source="R2")
        self.assertEqual(paired(rs=[old,new])["retail"]["payload"],{"long_pct":55})
        self.assertEqual(paired(decision=T3,rs=[old,new])["retail"]["payload"],{"long_pct":65})

    def test_06_undeclared_mapping_never_compares_fx_futures(self):
        r=paired(mapping=None)
        self.assertEqual(r["status"],"NON_COMPARABLE")
        self.assertEqual(r["reason"],"missing_explicit_mapping")

    def test_07_unknown_source_is_not_replaced_by_other_instrument(self):
        different=make_fixture_sample(provider="CFTC_FUTURES",
            instrument="112741",receipt_utc=T1,
            observation_utc=T1,payload={"net":8},source_id="C")
        self.assertEqual(paired(cs=[different])["status"],"UNKNOWN_NOT_AVAILABLE")

    def test_08_corrupted_retail_payload_quarantines_entire_join(self):
        bad=dataclasses.replace(retail(),content_json='{"long_pct":100}')
        self.assertEqual(paired(rs=[bad])["status"],"QUARANTINE")

    def test_09_corrupted_cot_payload_quarantines_entire_join(self):
        bad=dataclasses.replace(cot(),content_sha256="0"*64)
        self.assertEqual(paired(cs=[bad])["reason"],"INTEGRITY_ERROR")

    def test_10_future_observation_preceding_local_receipt_is_clock_conflict(self):
        bad=retail(t=T1,obs=T2)
        self.assertEqual(paired(rs=[bad])["reason"],"CLOCK_CONFLICT")

    def test_11_same_receipt_conflicting_values_dont_pick_winner(self):
        a=cot(n=20,source="C1")
        b=cot(n=25,source="C2")
        self.assertEqual(paired(cs=[a,b])["reason"],"SOURCE_CONFLICT")

    def test_12_out_of_order_revision_numbers_are_quarantined(self):
        earlier=cot(t=T1,version=4)
        later=cot(t=T2,version=2,obs=T2,source="C2")
        self.assertEqual(paired(decision=T3,cs=[earlier,later])["reason"],
                         "VERSION_ORDER_CONFLICT")

    def test_13_no_independent_time_or_mapping_claims_in_provisional_result(self):
        r=paired()
        self.assertFalse(r["mapping_independently_verified"])
        self.assertFalse(r["external_first_seen_verified"])
        self.assertFalse(r["institutional_edge_established"])

    def test_14_missing_both_does_not_translate_to_zero(self):
        r=paired(rs=[],cs=[])
        self.assertEqual(r["status"],"UNKNOWN_NOT_AVAILABLE")
        self.assertIsNone(r["retail"])
        self.assertIsNone(r["cot"])

    def test_15_source_provider_cannot_be_silently_interchanged(self):
        r=paired(rs=[cot()],cs=[retail()])
        self.assertEqual(r["status"],"UNKNOWN_NOT_AVAILABLE")

    def test_16_invalid_decision_clock_is_rejected(self):
        with self.assertRaises(GateError):
            paired(decision="2026-11-20T12:00:00+01:00")

    def test_17_non_object_or_nan_payload_rejected_before_join(self):
        with self.assertRaises(GateError):
            make_fixture_sample(provider="MYFXBOOK_RETAIL",instrument="EURUSD",
                                receipt_utc=T1,payload={"n":float("nan")},
                                source_id="R")
        with self.assertRaises(GateError):
            make_fixture_sample(provider="MYFXBOOK_RETAIL",instrument="EURUSD",
                                receipt_utc=T1,payload=[],source_id="R")

    def test_18_replay_of_legacy_hash_without_original_payload_remains_unknown(self):
        r=paired(rs=[],cs=[cot()])
        self.assertEqual(r["status"],"UNKNOWN_NOT_AVAILABLE")

    def test_19_sample_provenance_type_is_validated(self):
        with self.assertRaises(GateError):
            paired(rs=[{"timestamp":T1}])

    def test_20_newest_version_mismatch_with_duplicate_number_is_quarantined(self):
        a=cot(t=T1,version=1)
        b=cot(t=T2,n=90,version=1,obs=T2,source="C2")
        self.assertEqual(paired(decision=T3,cs=[a,b])["reason"],
                         "VERSION_ORDER_CONFLICT")

if __name__=="__main__":
    unittest.main()
