# REMURA TV v0.8.184 LAB — ONLY new requested-slot coverage tests.
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import explicit_m5_coverage_v0184_lab as m

class ExplicitCoverageNewTests(unittest.TestCase):
    def setUp(self):
        self.plan=m.demo()
    def output(self):
        x=m.coverage(self.plan)
        self.assertEqual(x["decision"], "NO_GO_LIVE")
        self.assertFalse(x["edge_claim_allowed"])
        self.assertFalse(x["exchange_calendar_attested"])
        self.assertFalse(x["market_coverage_attested"])
        self.assertFalse(x["future_outcomes_used"])
        return x
    def test_01_mixed_sample(self):
        x=self.output()
        self.assertEqual((x["planned_slots"],x["timely_captures"],x["late_captures"],x["uncaptured_requested_slots"]),(3,1,1,1))
    def test_02_empty_observation_batch(self):
        self.plan["observations"]=[]
        x=self.output()
        self.assertEqual(x["uncaptured_requested_slots"],3)
        self.assertFalse(x["zero_captures_prove_no_market_activity"])
    def test_03_all_on_time(self):
        self.plan["observations"][1]["received_utc"]="2026-11-23T00:12:00Z"
        self.assertEqual(self.output()["timely_captures"],2)
    def test_04_one_additional_valid(self):
        self.plan["observations"].append({
            "source":"OFFLINE_SYNTHETIC_M5","decision_digest":"c"*64,
            "bar_close_utc":"2026-11-23T00:15:00Z",
            "next_close_utc":"2026-11-23T00:20:00Z",
            "received_utc":"2026-11-23T00:15:05Z"})
        self.assertEqual(self.output()["uncaptured_requested_slots"],0)
    def test_05_late_not_silently_retried(self):
        self.assertEqual(self.output()["late_captures"],1)
    def test_06_unplanned_capture_rejected(self):
        self.plan["observations"][1]["bar_close_utc"]="2026-11-23T00:20:00Z"
        self.plan["observations"][1]["next_close_utc"]="2026-11-23T00:25:00Z"
        self.plan["observations"][1]["received_utc"]="2026-11-23T00:20:15Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_07_duplicate_planned_slot_rejected(self):
        self.plan["requested_closes_utc"][1]=self.plan["requested_closes_utc"][0]
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_08_unordered_planned_slots_rejected(self):
        self.plan["requested_closes_utc"].reverse()
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_09_non_m5_request_rejected(self):
        self.plan["requested_closes_utc"][0]="2026-11-23T00:06:00Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_10_fold_two_only(self):
        self.plan["fold"]="HOLDOUT_2"
        self.plan["requested_closes_utc"]=["2026-11-30T00:05:00Z"]
        self.plan["observations"]=[]
        self.assertEqual(self.output()["fold"],"HOLDOUT_2")
    def test_11_fold_two_must_not_accept_fold_one(self):
        self.plan["fold"]="HOLDOUT_2"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_12_cross_fold_plan_rejected(self):
        self.plan["requested_closes_utc"][2]="2026-11-30T00:15:00Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_13_development_not_held_out(self):
        self.plan["requested_closes_utc"][0]="2026-11-22T00:05:00Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_14_missing_source_rejected(self):
        del self.plan["source"]
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_15_untrusted_source_rejected(self):
        self.plan["source"]="LIVE"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_16_invalid_event_denied(self):
        self.plan["observations"][0]["decision_digest"]="not-a-sha"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_17_conflicting_event_rejected(self):
        self.plan["observations"][1]["bar_close_utc"]="2026-11-23T00:05:00Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_18_invalid_next_close_rejected(self):
        self.plan["observations"][0]["next_close_utc"]="2026-11-23T00:15:00Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_19_received_before_close_denied(self):
        self.plan["observations"][0]["received_utc"]="2026-11-23T00:04:59Z"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_20_requested_tz_offset_denied(self):
        self.plan["requested_closes_utc"][0]="2026-11-23T01:05:00+01:00"
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_21_empty_plan_rejected(self):
        self.plan["requested_closes_utc"]=[]
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_22_overbounded_plan_rejected(self):
        self.plan["requested_closes_utc"]=["2026-11-23T00:05:00Z"]*61
        self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_23_protocol_drift_rejected(self):
        with patch.object(m,"guard",side_effect=m.FreezeError("drift")):
            self.assertEqual(self.output()["status"],"INVALID_OR_UNVERIFIED")
    def test_24_cli_bad_args(self):
        self.assertEqual(m.main([]),2)
    def test_25_cli_self_check(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
if __name__ == "__main__": unittest.main()
