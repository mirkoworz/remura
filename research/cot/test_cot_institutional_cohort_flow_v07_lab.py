# REMURA Shark Science v0.7 — 17 NEW institutional category descriptive cases.
import unittest
from cot_forward_only_v06_lab import ForwardOnlyCOT
from cot_institutional_cohort_flow_v07_lab import compare_tff_asof
from cot_revision_lineage_v01_lab import RevisionError

D1="2026-11-03"
D2="2026-11-10"
D3="2026-11-17"
S1="2026-11-20T10:00:00Z"
S2="2026-11-20T12:00:00Z"
DEC="2026-11-20T11:00:00Z"
CODE="112741"
SOURCE="CFTC_PRIMARY_CLAIM"
A=(1000.,80.,40.,50.,70.)
B=(1000.,100.,40.,40.,70.)
C=(1000.,120.,40.,30.,70.)

class TFFFlowTests(unittest.TestCase):
    def setUp(self):
        self.store=ForwardOnlyCOT(synthetic=True)
    def tearDown(self):
        self.store.close()
    def seed(self, rows=None, at=S1):
        rows=rows if rows is not None else {("tff",CODE,D1):A,("tff",CODE,D2):B,
                                            ("tff",CODE,D3):C}
        return self.store.capture(rows,received_utc=at,source_claim=SOURCE)
    def compare(self, dates=(D1,D2,D3),decision=DEC,code=CODE):
        return compare_tff_asof(self.store,code=code,
                                report_dates=dates,decision_utc=decision)

    def test_01_must_have_forward_only_fixture_not_mock_or_path(self):
        with self.assertRaisesRegex(RevisionError,"synthetic_sidecar_required"):
            compare_tff_asof("some/oracle.sqlite",code=CODE,report_dates=[D1,D2],decision_utc=DEC)

    def test_02_two_week_asset_manager_net_oi_share(self):
        self.seed()
        out=self.compare((D1,D2))
        self.assertEqual(out["status"],"LOCAL_TFF_COHORT_FLOW_DESCRIPTIVE_UNATTESTED")
        self.assertEqual(out["cohorts"]["ASSET_MANAGER"]["net_to_open_interest_percent_by_week"],[4.,6.])
        self.assertEqual(out["calculated_weeks"],2)

    def test_03_leveraged_funds_net_change_is_different_cohort(self):
        self.seed()
        out=self.compare((D1,D2))
        self.assertEqual(out["cohorts"]["LEVERAGED_FUNDS"]["net_to_open_interest_percent_by_week"],[-2.,-3.])
        self.assertEqual(out["cohorts"]["LEVERAGED_FUNDS"]["latest_change_percentage_points"],-1.)

    def test_04_weekly_share_changes_not_raw_position_growth(self):
        self.seed()
        z=self.compare((D1,D2))
        self.assertEqual(z["cohorts"]["ASSET_MANAGER"]["week_over_week_percentage_point_change"],[2.])
        self.assertIsNone(z["cohorts"]["ASSET_MANAGER"]["weekly_acceleration_percentage_points"])

    def test_05_three_week_acceleration_requires_three_weeks(self):
        self.seed()
        z=self.compare()
        self.assertEqual(z["cohorts"]["ASSET_MANAGER"]["weekly_acceleration_percentage_points"],0.)
        self.assertEqual(z["cohorts"]["LEVERAGED_FUNDS"]["weekly_acceleration_percentage_points"],0.)

    def test_06_opposed_cohort_changes_must_not_be_merged(self):
        self.seed()
        z=self.compare()
        self.assertEqual(z["change_agreement"],"DIVERGENT")
        self.assertTrue(z["position_groupings_are_not_individual_institutions"])

    def test_07_both_increasing_can_be_described_without_signal(self):
        self.seed({("tff",CODE,D1):A,("tff",CODE,D2):(1000.,100.,40.,70.,70.)})
        z=self.compare((D1,D2))
        self.assertEqual(z["change_agreement"],"CO_MOVING")
        self.assertFalse(z["trading_signals_generated"])

    def test_08_flat_share_not_marked_directional(self):
        self.seed({("tff",CODE,D1):A,("tff",CODE,D2):A})
        z=self.compare((D1,D2))
        self.assertEqual(z["change_agreement"],"UNCHANGED_OR_MIXED_FLAT")
        self.assertEqual(z["cohorts"]["ASSET_MANAGER"]["latest_change_class"],"NO_CHANGE")

    def test_09_open_interest_growth_is_separately_reported(self):
        self.seed({("tff",CODE,D1):A,
                   ("tff",CODE,D2):(2000.,100.,40.,40.,70.)})
        z=self.compare((D1,D2))
        self.assertEqual(z["open_interest_change_pct"],100.)

    def test_10_missing_middle_week_means_no_partial_percentages(self):
        self.seed({("tff",CODE,D1):A,("tff",CODE,D3):C})
        z=self.compare()
        self.assertEqual(z["status"],"UNKNOWN_INCOMPLETE_ASOF")
        self.assertEqual(z["missing_report_dates"],[D2])
        self.assertIsNone(z["cohorts"])
        self.assertEqual(z["calculated_weeks"],0)

    def test_11_future_local_capture_cannot_enter_past_decision(self):
        self.seed(at=S2)
        z=self.compare(decision=DEC)
        self.assertEqual(z["missing_report_dates"],[D1,D2,D3])
        self.assertIsNone(z["open_interest_change_pct"])

    def test_12_revised_position_after_decision_not_promoted(self):
        self.seed()
        before=self.compare((D1,D2))
        self.seed(rows={("tff",CODE,D2):(1000.,900.,30.,0.,100.)},at=S2)
        after=self.compare((D1,D2))
        self.assertEqual(before["cohorts"],after["cohorts"])
        self.assertEqual(self.compare((D1,D2),decision="2026-11-20T13:00:00Z")
                         ["cohorts"]["ASSET_MANAGER"]["net_to_open_interest_percent_by_week"][-1],87.)

    def test_13_weekday_not_tuesday_is_rejected(self):
        self.seed()
        with self.assertRaisesRegex(RevisionError,"non_tuesday"):
            self.compare((D1,"2026-11-11"))

    def test_14_gap_in_weekly_reports_is_rejected(self):
        self.seed()
        with self.assertRaisesRegex(RevisionError,"consecutive_tuesday"):
            self.compare((D1,D3))

    def test_15_only_tff_known_contracts_no_disagg_aliases(self):
        self.seed()
        with self.assertRaises(RevisionError):
            self.compare((D1,D2),code="088691")

    def test_16_different_tff_contract_does_not_steal_rows(self):
        self.seed()
        z=self.compare((D1,D2),code="092741")
        self.assertEqual(z["missing_report_dates"],[D1,D2])
        self.assertIsNone(z["cohorts"])

    def test_17_future_tuesday_and_long_rosters_denied(self):
        self.seed()
        with self.assertRaises(RevisionError):
            self.compare((D1,"2026-11-24"))
        with self.assertRaisesRegex(RevisionError,"two_or_three_weeks"):
            self.compare((D1,D2,D3,D3))
        z=self.compare()
        self.assertFalse(z["source_publication_independently_verified"])
        self.assertFalse(z["spot_futures_mapping_verified"])
        self.assertFalse(z["institutional_predictive_edge_proven"])
        self.assertFalse(z["actual_trading_enabled"])
        self.assertEqual(z["provider_calls"],0)

if __name__=="__main__":
    unittest.main()
