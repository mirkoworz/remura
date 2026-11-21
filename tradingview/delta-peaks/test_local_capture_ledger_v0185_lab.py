# REMURA TradingView v0.8.185 LAB — only NEW local hash-chain tests
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_capture_ledger_v0185_lab as m

class LedgerNewTests(unittest.TestCase):
    def setUp(self):
        self.plan=m.demo()
    def check(self,valid=None):
        r=m.review(self.plan)
        self.assertEqual(r["decision"],"NO_GO_LIVE")
        self.assertFalse(r["independent_timestamp_anchor"])
        self.assertFalse(r["institutional_edge_established"])
        self.assertFalse(r["automatic_capture_enabled"])
        if valid is not None:self.assertEqual(r["local_hash_chain_consistent"],valid)
        return r
    def fix(self):
        p=m.ZERO
        for row in self.plan["ledger"]:
            row["previous_hash"]=p
            row["entry_hash"]=m.digest({k:v for k,v in row.items() if k!="entry_hash"})
            p=row["entry_hash"]
    def test_01_valid_unanchored(self):
        r=self.check(True)
        self.assertEqual((r["timely"],r["late"],r["not_captured"]),(1,1,1))
    def test_02_raw_tamper_fails(self):
        self.plan["ledger"][0]["received_utc"]="2026-11-23T00:08:00Z"
        self.check(False)
    def test_03_chain_link_tamper(self):
        self.plan["ledger"][1]["previous_hash"]="f"*64
        self.check(False)
    def test_04_reordering_records_fails(self):
        self.plan["ledger"].reverse()
        self.check(False)
    def test_05_missing_entry_fails(self):
        self.plan["ledger"].pop()
        self.check(False)
    def test_06_extra_entry_fails(self):
        self.plan["ledger"].append(copy.deepcopy(self.plan["ledger"][-1]))
        self.check(False)
    def test_07_wrong_source_fails(self):
        self.plan["source"]="REAL"
        self.check(False)
    def test_08_wrong_fold_fails(self):
        self.plan["fold"]="HOLDOUT_2"
        self.check(False)
    def test_09_tampered_schedule_fails(self):
        self.plan["requested_closes_utc"][0]="2026-11-23T00:20:00Z"
        self.check(False)
    def test_10_false_timely_claim_rehashed_still_rejected(self):
        self.plan["ledger"][0]["received_utc"]="2026-11-23T00:07:01Z"
        self.fix()
        self.check(False)
    def test_11_false_late_claim_rehashed_still_rejected(self):
        self.plan["ledger"][1]["received_utc"]="2026-11-23T00:12:00Z"
        self.fix()
        self.check(False)
    def test_12_missing_capture_cannot_have_identity(self):
        self.plan["ledger"][2]["decision_digest"]="c"*64
        self.fix()
        self.check(False)
    def test_13_missing_capture_cannot_have_received(self):
        self.plan["ledger"][2]["received_utc"]="2026-11-23T00:16:00Z"
        self.fix()
        self.check(False)
    def test_14_preclose_received_fails(self):
        self.plan["ledger"][0]["received_utc"]="2026-11-23T00:04:59Z"
        self.fix()
        self.check(False)
    def test_15_duplicate_digest_fails(self):
        self.plan["ledger"][1]["decision_digest"]="a"*64
        self.fix()
        self.check(False)
    def test_16_not_m5_slot_rejected(self):
        self.plan["requested_closes_utc"][0]="2026-11-23T00:06:00Z"
        self.check(False)
    def test_17_invalid_timezone_rejected(self):
        self.plan["requested_closes_utc"][0]="2026-11-23T01:05:00+01:00"
        self.check(False)
    def test_18_protocol_drift_fail_closed(self):
        with patch.object(m,"guard",side_effect=m.FreezeError("drift")):
            self.check(False)
    def test_19_no_pii_or_outcomes(self):
        r=str(self.check(True))
        for forbidden in ("@", "pnl", "private_key", "account_id"):
            self.assertNotIn(forbidden,r.lower())
    def test_20_bad_cli(self):
        self.assertEqual(m.main([]),2)
    def test_21_good_cli(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
    def test_22_duplicate_schedule(self):
        self.plan["requested_closes_utc"][1]=self.plan["requested_closes_utc"][0]
        self.check(False)
if __name__=="__main__":unittest.main()
