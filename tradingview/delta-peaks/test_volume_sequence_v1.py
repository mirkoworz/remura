#!/usr/bin/env python3
# REMURA v0.8.49 LAB — 14/11/2026 10:02 CET — synthetic only.
import unittest
from volume_sequence_v1 import sequential_diagnostics, M5

T = 1800000000000

def snapshot(i, delta=10, effort=1, levels=None, timely=True, symbol="BTC"):
    return {"symbol":symbol, "timeframe":"5", "bar_close_ms":T+i*M5,
            "transport_timely":timely, "observed":{"delta_intrabar_estimate":delta,
            "effort_reported":effort,"levels":levels or []}}

def level(name="day1", touched=False, flag=False, origin=T-M5):
    return {"name":name,"origin_ms":origin,"price":100,
            "range_intersects_prior_level":touched,"pine_retest_flag":flag}

class SequenceTests(unittest.TestCase):
    def counts(self, rows):
        return sequential_diagnostics(rows)["counts"]

    def test_only_prior_30(self):
        r=self.counts([snapshot(i) for i in range(30)]+[snapshot(30,delta=30,effort=3)])
        self.assertEqual(r,{"EFFORT_DEFAULT30_CONSISTENT":1,"EFFORT_DEFAULT30_NOT_EVALUABLE":30})

    def test_mismatch_conditional(self):
        r=self.counts([snapshot(i) for i in range(30)]+[snapshot(30,effort=5)])
        self.assertEqual(r["EFFORT_DEFAULT30_REVIEW"],1)

    def test_gap_or_late_resets(self):
        for rows in ([snapshot(i) for i in range(29)]+[snapshot(30),snapshot(31)],
                     [snapshot(i,timely=i!=15) for i in range(31)]):
            r=self.counts(rows)
            self.assertEqual(r,{"EFFORT_DEFAULT30_NOT_EVALUABLE":31})

    def test_missing_delta_and_zero_baseline(self):
        for delta in (None,0):
            r=self.counts([snapshot(i,delta=delta) for i in range(30)]+[snapshot(30)])
            self.assertEqual(r,{"EFFORT_DEFAULT30_NOT_EVALUABLE":31})

    def test_rank_change_preserves_touch_state(self):
        r=self.counts([snapshot(0,levels=[level(touched=True)]),
                       snapshot(1,levels=[level("day2",touched=True,flag=True)])])
        self.assertEqual(r["RETEST_NEW_VISIT_REVIEW"],1)

    def test_new_visit(self):
        r=self.counts([snapshot(0,levels=[level()]),
                       snapshot(1,levels=[level(touched=True,flag=True)])])
        self.assertEqual(r["RETEST_NEW_VISIT_CONSISTENT"],1)

    def test_gap_or_new_identity_is_unknown(self):
        for rows in ([snapshot(0,levels=[level()]),snapshot(2,levels=[level(flag=True)])],
                     [snapshot(0,levels=[level()]),snapshot(1,levels=[level(flag=True,origin=T)])]):
            self.assertEqual(self.counts(rows)["RETEST_NEW_VISIT_NOT_EVALUABLE"],1)

    def test_symbol_isolation(self):
        r=self.counts([snapshot(i) for i in range(30)]+[snapshot(30,symbol="FX")])
        self.assertEqual(r,{"EFFORT_DEFAULT30_NOT_EVALUABLE":31})

if __name__ == "__main__":
    unittest.main()
