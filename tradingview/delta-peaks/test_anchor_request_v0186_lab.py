# REMURA TradingView v0.8.186 LAB — ONLY NEW anchor-request tests
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import anchor_request_v0186_lab as m
from local_capture_ledger_v0185_lab import demo,digest, ZERO

class AnchorNewTests(unittest.TestCase):
    def setUp(self):
        self.x=demo()
    def check(self):
        result=m.request(self.x)
        self.assertEqual(result["decision"],"NO_GO_LIVE")
        self.assertFalse(result["request_submitted_to_tsa"])
        self.assertFalse(result["independent_timestamp_token_verified"])
        self.assertFalse(result["trusted_anchor_established"])
        self.assertFalse(result["capture_clock_proven"])
        self.assertFalse(result["trade_edge_proven"])
        self.assertEqual(result["network_calls_performed"],0)
        return result
    def test_01_ready_unsubmitted(self):
        self.assertEqual(self.check()["status"],"REQUEST_HASH_READY_UNSUBMITTED")
    def test_02_digest_64_lowercase(self):
        self.assertRegex(self.check()["request_digest_sha256"],"^[a-f0-9]{64}$")
    def test_03_deterministic(self):
        self.assertEqual(self.check()["request_digest_sha256"],self.check()["request_digest_sha256"])
    def test_04_deepcopy_same_hash(self):
        expected=self.check()["request_digest_sha256"]
        self.x=deepcopy(self.x)
        self.assertEqual(self.check()["request_digest_sha256"],expected)
    def test_05_local_tamper_fails(self):
        self.x["ledger"][0]["received_utc"]="2026-11-23T00:08:01Z"
        self.assertEqual(self.check()["status"],"INVALID_OR_NOT_PREPARED")
    def test_06_mutated_plan_fails(self):
        self.x["requested_closes_utc"][0]="2026-11-23T00:25:00Z"
        self.assertEqual(self.check()["status"],"INVALID_OR_NOT_PREPARED")
    def test_07_empty_ledger_fails(self):
        self.x["ledger"]=[]
        self.assertEqual(self.check()["status"],"INVALID_OR_NOT_PREPARED")
    def test_08_protocol_drift_fails(self):
        with patch.object(m,"guard",side_effect=m.FreezeError("drift")):
            self.assertEqual(self.check()["status"],"INVALID_OR_NOT_PREPARED")
    def test_09_no_data_in_output(self):
        s=str(self.check())
        self.assertNotIn("2026-11-23T00:05:00Z",s)
        self.assertNotIn("decision_digest",s)
        self.assertNotIn("Bearer",s)
    def test_10_no_external_receipt(self):
        result=m.receipt_review(self.check(),None)
        self.assertFalse(result["independent_timestamp_attested"])
        self.assertFalse(result["signature_verified"])
    def test_11_fake_receipt_rejected(self):
        r=m.receipt_review(self.check(),{"signed":True,"timestamp":"TODAY"})
        self.assertEqual(r["status"],"RECEIPT_UNVERIFIED_OR_INVALID")
    def test_12_matching_placeholder_not_verified(self):
        digest=self.check()["request_digest_sha256"]
        receipt={"request_digest_sha256":digest,"token_format":"RFC3161_UNVERIFIED_PLACEHOLDER","issuer":"UNVERIFIED"}
        r=m.receipt_review(self.check(),receipt)
        self.assertEqual(r["status"],"DIGEST_MATCH_ONLY_SIGNATURE_NOT_VERIFIED")
        self.assertFalse(r["signature_verified"])
    def test_13_replay_wrong_digest_denied(self):
        receipt={"request_digest_sha256":"0"*64,"token_format":"RFC3161_UNVERIFIED_PLACEHOLDER","issuer":"UNVERIFIED"}
        self.assertEqual(m.receipt_review(self.check(),receipt)["status"],"RECEIPT_UNVERIFIED_OR_INVALID")
    def test_14_unknown_issuer_denied(self):
        digest=self.check()["request_digest_sha256"]
        receipt={"request_digest_sha256":digest,"token_format":"RFC3161_UNVERIFIED_PLACEHOLDER","issuer":"FAKE_TSA"}
        self.assertEqual(m.receipt_review(self.check(),receipt)["status"],"RECEIPT_UNVERIFIED_OR_INVALID")
    def test_15_bad_cli(self):
        self.assertEqual(m.main(["--submit"]),2)
    def test_16_synthetic_cli(self):
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
if __name__=="__main__":
    unittest.main()
