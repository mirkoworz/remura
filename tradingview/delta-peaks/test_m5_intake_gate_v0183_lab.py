# REMURA TradingView v0.8.183 LAB — only new timing/intake tests.
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import m5_intake_gate_v0183_lab as m

def e(close="2026-11-23T00:05:00Z",receive="2026-11-23T00:06:59Z",digest="a"):
    dt=m.parse_utc(close)
    nxt=dt+m.M5
    return {
        "source":"OFFLINE_SYNTHETIC_M5","decision_digest":digest*64,
        "bar_close_utc":close,
        "next_close_utc":nxt.isoformat().replace("+00:00","Z"),
        "received_utc":receive,
    }
class NewIntakeTests(unittest.TestCase):
    def check(self,rows,status=None):
        s=m.evaluate(rows)
        self.assertEqual(s["decision"],"NO_GO_LIVE")
        self.assertFalse(s["outcomes_evaluated"])
        self.assertFalse(s["edge_claim_allowed"])
        self.assertFalse(s["capture_activated"])
        if status:self.assertEqual(s["status"],status)
        return s
    def test_01_h1_timely(self):
        self.assertEqual(self.check([e()])["holdout_1"],1)
    def test_02_boundary_120_seconds_inclusive(self):
        self.assertEqual(self.check([e(receive="2026-11-23T00:07:00Z")])["eligible"],1)
    def test_03_boundary_121_late(self):
        s=self.check([e(receive="2026-11-23T00:07:01Z")])
        self.assertEqual(s["late"],1)
        self.assertEqual(s["eligible"],0)
    def test_04_exact_next_close_late(self):
        self.assertEqual(self.check([e(receive="2026-11-23T00:10:00Z")])["late"],1)
    def test_05_preclose_invalid(self):
        self.check([e(receive="2026-11-23T00:04:59Z")],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_06_h2_phase(self):
        self.assertEqual(self.check([e(close="2026-11-30T00:00:00Z",receive="2026-11-30T00:01:00Z")])["holdout_2"],1)
    def test_07_dev_phase(self):
        self.assertEqual(self.check([e(close="2026-11-22T00:00:00Z",receive="2026-11-22T00:01:00Z")])["development"],1)
    def test_08_end_exclusive(self):
        self.assertEqual(self.check([e(close="2026-12-07T00:00:00Z",receive="2026-12-07T00:01:00Z")])["out_of_window"],1)
    def test_09_before_dev_outside(self):
        self.assertEqual(self.check([e(close="2026-11-15T00:00:00Z",receive="2026-11-15T00:01:00Z")])["out_of_window"],1)
    def test_10_duplicate_digest_denied(self):
        self.check([e(),e(close="2026-11-23T00:10:00Z",receive="2026-11-23T00:11:00Z")],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_11_conflicting_same_m5_close(self):
        self.check([e(),e(digest="b")],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_12_bad_source(self):
        a=e();a["source"]="LIVE"
        self.check([a],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_13_bad_digest(self):
        a=e();a["decision_digest"]="not sha"
        self.check([a],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_14_non_m5(self):
        self.check([e(close="2026-11-23T00:06:00Z",receive="2026-11-23T00:06:30Z")],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_15_wrong_next_close(self):
        a=e();a["next_close_utc"]="2026-11-23T00:11:00Z"
        self.check([a],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_16_missing_rows(self):
        self.check([],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_17_protocol_drift(self):
        with patch.object(m,"guard",side_effect=m.FreezeError("drift")):
            self.check([e()],"INVALID_OR_PROTOCOL_DRIFT_NO_GO")
    def test_18_cli(self):
        self.assertEqual(m.main([]),2)
        self.assertEqual(m.main(["--synthetic-self-check"]),0)
if __name__=="__main__":unittest.main()
