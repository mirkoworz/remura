"""Synthetic-only Track B walk-forward causality and execution tests."""
from datetime import datetime, timedelta, timezone
import copy
import json
import unittest

from scripts import shark_walkforward as wf

UTC = timezone.utc
START = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def markets(n=200):
    bars = []
    for i in range(n):
        o = 1.1000+i*0.0001
        bars.append({"t": iso(START+timedelta(minutes=15*i)),
                     "o": o, "h": o+0.00008, "l": o-0.00007,
                     "c": o+0.00005})
    return {"EURUSD": {"provider": "ctrader", "providerSymbol": "BROKER_PRIVATE_TEST",
                       "M15": bars}}


def expenses():
    return {"EURUSD": {"spreadBps": 1.0, "slippageEachSideBps": 0.25,
                       "commissionRoundTripBps": 0.5}}


def event(i=40, *, cvd=True):
    observed = START+timedelta(minutes=15*i+5)
    out = {"symbol": "EURUSD", "provider": "ctrader",
           "brokerSymbol": "BROKER_PRIVATE_TEST", "qualityVerified": True,
           "observationVerified": True,
           "side": 1, "confirmedAt": iso(observed-timedelta(minutes=35)),
           "availableAt": iso(observed)}
    if cvd:
        out.update({"cvdQualityVerified": True,
                    "cvdAlgorithm": "cvd-divergence-proxy-m15-v1",
                    "cvdState": "confirmed_technical_not_trade_signal",
                    "cvdSide": "bullish",
                    "cvdConfirmedAt": iso(observed-timedelta(minutes=35)),
                    "cvdAvailableAt": iso(observed-timedelta(minutes=2))})
    return out


def run(signals, sources=None, costs=None, **options):
    return wf.evaluate(signals, markets() if sources is None else sources,
                       expenses() if costs is None else costs,
                       as_of="2026-11-04T12:00:00Z",
                       train_end="2026-11-01T18:00:00Z",
                       validation_end="2026-11-02T08:00:00Z", **options)


class WalkforwardTests(unittest.TestCase):
    def test_chronological_train_validation_test_with_fixed_costs(self):
        sample = [event(40), event(90, cvd=False), event(140)]
        saved = copy.deepcopy(sample)
        report = run(sample)
        self.assertEqual(report["status"], "RESEARCH_ONLY")
        self.assertEqual(report["folds"]["train"]["priceOnly"]["samples"], 1)
        self.assertEqual(report["folds"]["validation"]["priceOnly"]["samples"], 1)
        self.assertEqual(report["folds"]["test"]["priceOnly"]["samples"], 1)
        self.assertEqual(report["folds"]["validation"]["cvdFiltered"]["samples"], 0)
        self.assertEqual(report["folds"]["test"]["cvdFiltered"]["samples"], 1)
        self.assertIsNone(report["folds"]["test"]["priceOnly"]["netHitPct"])
        self.assertFalse(report["capitalDrawdownValidated"])
        self.assertFalse(report["notificationEnabled"])
        self.assertEqual(sample, saved)
        self.assertNotIn("BROKER_PRIVATE_TEST", json.dumps(report))

    def test_boundary_label_purged_and_embargo_applied(self):
        sample = [event(70), event(74), event(130)]
        report = run(sample)
        self.assertGreaterEqual(report["excluded"].get("purged_or_embargoed", 0), 2)

    def test_cvd_detected_later_cannot_qualify_old_price_entry(self):
        e = event(40)
        e["cvdAvailableAt"] = iso(START+timedelta(minutes=15*40+6))
        report = run([e])
        self.assertEqual(report["folds"]["train"]["priceOnly"]["samples"], 1)
        self.assertEqual(report["folds"]["train"]["cvdFiltered"]["samples"], 0)

    def test_opposite_direction_cvd_or_unverified_observation_never_qualifies(self):
        e = event(40)
        e["cvdSide"] = "bearish"
        report = run([e])
        self.assertEqual(report["folds"]["train"]["cvdFiltered"]["samples"], 0)
        e = event(40)
        e["observationVerified"] = False
        report = run([e])
        self.assertEqual(report["excluded"]["invalid_signal_lineage"], 1)

    def test_cvd_pivot_time_without_observation_is_not_a_fill(self):
        e = event(40)
        e.pop("availableAt")
        report = run([e])
        self.assertEqual(report["folds"]["train"]["priceOnly"]["samples"], 0)
        self.assertEqual(report["excluded"]["invalid_signal"], 1)

    def test_future_gap_and_changed_broker_excluded(self):
        e = event(40)
        e["brokerSymbol"] = "OTHER_BROKER"
        self.assertEqual(run([e])["excluded"]["invalid_signal_lineage"], 1)
        e = event(40)
        doc = markets()
        doc["EURUSD"]["M15"].pop(42)
        result = run([e], sources=doc)
        self.assertGreater(result["excluded"].get("future_session_gap", 0), 0)

    def test_missing_m15_at_observation_blocks_unexecutable_entry_bridge(self):
        # Event is observed five minutes into M15 #40, with planned
        # execution at the opening of #41. Deleting #40 must NOT allow
        # the simulator to jump from the last closed bar #39 to #41.
        missing_current = markets()
        missing_current["EURUSD"]["M15"].pop(40)
        report = run([event(40)], sources=missing_current)
        self.assertEqual(report["excluded"].get("entry_history_gap"), 1)
        self.assertEqual(report["folds"]["train"]["priceOnly"]["samples"], 0)
        self.assertEqual(report["folds"]["train"]["cvdFiltered"]["samples"], 0)

    def test_missing_last_closed_m15_cannot_be_ignored_by_old_atr_window(self):
        # #39 would have closed at the observation's latest eligible
        # boundary, but earlier #38 still gives a valid contiguous ATR.
        # The bridge to opening #41 must fail nevertheless.
        missing_closed = markets()
        missing_closed["EURUSD"]["M15"].pop(39)
        report = run([event(40)], sources=missing_closed)
        self.assertEqual(report["excluded"].get("entry_history_gap"), 1)
        self.assertEqual(report["folds"]["train"]["priceOnly"]["samples"], 0)

    def test_complete_observation_to_next_open_bridge_still_admitted(self):
        baseline = run([event(40)])
        self.assertEqual(baseline["excluded"].get("entry_history_gap", 0), 0)
        self.assertEqual(baseline["folds"]["train"]["priceOnly"]["samples"], 1)

    def test_spread_and_slippage_reduce_net_return(self):
        cheap = run([event(40)], costs={"EURUSD": {
            "spreadBps": 0.1, "slippageEachSideBps": 0,
            "commissionRoundTripBps": 0}})
        dear = run([event(40)], costs={"EURUSD": {
            "spreadBps": 10, "slippageEachSideBps": 3,
            "commissionRoundTripBps": 2}})
        x = cheap["folds"]["train"]["priceOnly"]["meanNetR"]
        y = dear["folds"]["train"]["priceOnly"]["meanNetR"]
        self.assertLess(y, x)

    def test_no_silent_zero_costs_and_no_retroactive_future_data(self):
        with self.assertRaises(ValueError):
            run([event(40)], costs={"EURUSD": {
                "spreadBps": 0, "slippageEachSideBps": 0,
                "commissionRoundTripBps": 0}})
        with self.assertRaises(ValueError):
            run([event(40)], costs={})
        e = event(40)
        e["availableAt"] = "2026-11-05T12:00:00Z"
        self.assertEqual(run([e])["excluded"]["signal_not_known_asof"], 1)

    def test_same_bar_stop_first_not_optimistic_target(self):
        d = markets()
        # Make both loss and profit threshold reachable on the first future M15.
        o = d["EURUSD"]["M15"][41]["o"]
        d["EURUSD"]["M15"][41]["l"] = o - 0.01
        d["EURUSD"]["M15"][41]["h"] = o + 0.01
        report = run([event(40)], sources=d)
        self.assertLess(report["folds"]["train"]["priceOnly"]["meanNetR"], 0)

    def test_long_stop_gap_through_open_is_worse_than_stop_level(self):
        # Both have a valid continuous M15 series and the same ATR / entry.
        # Only the stop-hit bar differs: intrabar touch versus opening lower.
        touched = markets()
        touched["EURUSD"]["M15"][42]["l"] -= 0.01
        gapped = markets()
        entry = gapped["EURUSD"]["M15"][41]["o"]
        bar = gapped["EURUSD"]["M15"][42]
        bar["o"] = entry - 0.003
        bar["c"] = bar["o"] + 0.00004
        bar["h"] = bar["c"] + 0.00002
        bar["l"] = bar["o"] - 0.00002
        at_stop = run([event(40)], sources=touched)
        beyond_stop = run([event(40)], sources=gapped)
        regular_r = at_stop["folds"]["train"]["priceOnly"]["meanNetR"]
        gap_r = beyond_stop["folds"]["train"]["priceOnly"]["meanNetR"]
        self.assertIsNotNone(regular_r)
        self.assertIsNotNone(gap_r)
        self.assertLess(gap_r, regular_r)
        self.assertLess(gap_r, -1.0)
        self.assertEqual(beyond_stop["folds"]["train"]["priceOnly"]["samples"], 1)

    def test_short_stop_gap_through_open_is_worse_than_stop_level(self):
        short = event(40, cvd=False)
        short["side"] = -1
        touched = markets()
        touched["EURUSD"]["M15"][42]["h"] += 0.01
        gapped = markets()
        entry = gapped["EURUSD"]["M15"][41]["o"]
        bar = gapped["EURUSD"]["M15"][42]
        bar["o"] = entry + 0.003
        bar["c"] = bar["o"] - 0.00004
        bar["h"] = bar["o"] + 0.00002
        bar["l"] = bar["c"] - 0.00002
        at_stop = run([short], sources=touched)
        beyond_stop = run([short], sources=gapped)
        self.assertLess(
            beyond_stop["folds"]["train"]["priceOnly"]["meanNetR"],
            at_stop["folds"]["train"]["priceOnly"]["meanNetR"])
        self.assertLess(
            beyond_stop["folds"]["train"]["priceOnly"]["meanNetR"], -1.0)
        self.assertEqual(beyond_stop["folds"]["train"]["priceOnly"]["samples"], 1)

    def test_target_gap_does_not_award_unverified_better_fill(self):
        # Favourable opening beyond take-profit is still capped at target.
        touched = markets()
        entry = touched["EURUSD"]["M15"][41]["o"]
        touched["EURUSD"]["M15"][42]["h"] = entry + 0.003
        gapped = markets()
        bar = gapped["EURUSD"]["M15"][42]
        bar["o"] = entry + 0.003
        bar["c"] = bar["o"] + 0.00004
        bar["h"] = bar["c"] + 0.00002
        bar["l"] = bar["o"] - 0.00002
        touch_r = run([event(40)], sources=touched)[
            "folds"]["train"]["priceOnly"]["meanNetR"]
        gap_r = run([event(40)], sources=gapped)[
            "folds"]["train"]["priceOnly"]["meanNetR"]
        self.assertIsNotNone(touch_r)
        self.assertEqual(gap_r, touch_r)

    def test_repeat_alerts_do_not_manufacture_30_independent_trades(self):
        start = START + timedelta(hours=9)
        one = {"symbol": "EURUSD", "observed": start-timedelta(minutes=5),
               "entry": start, "exit": start+timedelta(minutes=15),
               "netR": 1.0}
        report = wf._stats([one.copy() for _ in range(40)])
        self.assertEqual(report["samples"], 40)
        self.assertEqual(report["timeDisjointEpisodeCount"], 1)
        self.assertEqual(report["timeDisjointIsoWeeks"], 1)
        self.assertIsNone(report["netHitPct"])
        self.assertIsNone(report["timeDisjointHitPct"])
        self.assertFalse(report["timeDisjointIsIndependentSampling"])

    def test_many_nonoverlapping_alerts_from_one_week_not_enough(self):
        # Monday: all 35 consecutive intraday entries remain in ONE ISO week.
        start = datetime(2026, 11, 2, 9, tzinfo=UTC)
        rows = []
        for i in range(35):
            t = start + timedelta(minutes=30*i)
            rows.append({"symbol": "EURUSD",
                         "observed": t-timedelta(minutes=5),
                         "entry": t, "exit": t+timedelta(minutes=15),
                         "netR": 1.0 if i%2 == 0 else -0.5})
        report = wf._stats(rows)
        self.assertEqual(report["timeDisjointEpisodeCount"], 35)
        self.assertEqual(report["timeDisjointIsoWeeks"], 1)
        self.assertIsNone(report["netHitPct"])
        self.assertIsNone(report["timeDisjointHitPct"])
        self.assertEqual(report["hitRateGate"],
                         "INSUFFICIENT_DISJOINT_WEEKS")

    def test_eight_weeks_are_only_descriptive_not_independent_proof(self):
        start = datetime(2026, 1, 5, 8, tzinfo=UTC)
        rows = []
        for i in range(40):
            t = start + timedelta(weeks=i//5, hours=2*(i%5))
            rows.append({"symbol": "EURUSD",
                         "observed": t-timedelta(minutes=5),
                         "entry": t, "exit": t+timedelta(minutes=15),
                         "netR": 1.0 if i%2 else -0.5})
        report = wf._stats(rows)
        self.assertEqual(report["timeDisjointEpisodeCount"], 40)
        self.assertEqual(report["timeDisjointIsoWeeks"], 8)
        self.assertEqual(report["netHitPct"], 50.0)
        self.assertEqual(report["timeDisjointHitPct"], 50.0)
        self.assertFalse(report["timeDisjointIsIndependentSampling"])
        self.assertEqual(report["hitRateGate"],
                         "DESCRIPTIVE_ONLY_NOT_INDEPENDENT")
        # A duplicate cannot inflate the all-alert percentage.
        duplicated = wf._stats(rows + [rows[0].copy()])
        self.assertEqual(duplicated["samples"], 41)
        self.assertEqual(duplicated["timeDisjointEpisodeCount"], 40)
        self.assertIsNone(duplicated["netHitPct"])
        self.assertEqual(duplicated["timeDisjointHitPct"], 50.0)

    def test_simultaneous_markets_cannot_inflate_disjoint_episode_count(self):
        t = datetime(2026, 1, 5, 8, tzinfo=UTC)
        observations = [
            {"symbol": symbol, "observed": t-timedelta(minutes=5),
             "entry": t, "exit": t+timedelta(minutes=15), "netR": 1.0}
            for symbol in ("EURUSD", "XAUUSD")
        ]
        out = wf._stats(observations)
        self.assertEqual(out["samples"], 2)
        self.assertEqual(out["timeDisjointEpisodeCount"], 1)
        self.assertEqual(out["overlappingAlertsExcludedOnlyFromEpisodeScreen"],1)

    def test_historical_close_is_required_to_compute_atr(self):
        e = event(14)
        out = run([e])
        self.assertEqual(out["excluded"]["missing_closed_atr_history"], 1)


if __name__ == "__main__":
    unittest.main()
