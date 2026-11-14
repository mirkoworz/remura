#!/usr/bin/env python3
# REMURA OUTCOME LAB v0.8.3 — aggiornamento 11/11/2026 18:00 CET.
# SOLO DATI SINTETICI: nessun prezzo reale, nessun risultato di trading.
import copy
import unittest

from outcome_audit_v1 import evaluate, load_records, session_id
from test_telemetry_v1 import sample, T0

STEP = 300_000


def example_bars(n=13, event=True, retest=False):
    """Genera tutte le barre M5 simulate, ciascuna ricevuta dopo 1 secondo."""
    bars = []
    for i in range(n):
        p = copy.deepcopy(sample())
        t = T0 + i * STEP
        c = 1.111 + i * 0.0001
        p["bar_open_ms"] = t - STEP
        p["bar_close_ms"] = t
        p["sent_clock_ms"] = t + 500
        p["ohlc"] = {
            "open": c - 0.00003, "high": c + 0.00020,
            "low": c - 0.00023, "close": c,
            "prev_close": 1.112 if i == 0 else 1.111 + (i - 1) * 0.0001,
            "atr14": 0.001
        }
        p["level_origin_ms"]["day1"] = T0 - STEP
        if i == 0 and event:
            p["event_type"] = "BAR_EVENT"
            p["events"]["day_level_action"] = "NONE"
            p["events"]["day_level_rank"] = None
            p["events"]["retest_day1"] = retest
        else:
            p["event_type"] = "HEARTBEAT"
            for key in ("peak", "er_positive", "er_negative",
                        "retest_day1", "retest_day2", "retest_day3",
                        "retest_previous_day"):
                p["events"][key] = False
            p["events"]["day_level_action"] = "NONE"
            p["events"]["day_level_rank"] = None
        bars.append({"payload": p, "received_at_ms": t + 1000})
    return bars


class OutcomesTests(unittest.TestCase):
    def test_all_3_6_12_futures_complete(self):
        a = evaluate(example_bars())
        self.assertEqual(a["audit"]["invalid"], 0)
        for h in ("3", "6", "12"):
            cohort = a["event_outcomes"][h]["ER_POS"]
            self.assertEqual(cohort["events_attempted"], 1)
            self.assertEqual(cohort["outcomes_complete"], 1)
            self.assertEqual(cohort["labels"]["CONTINUAZIONE"], 1)

    def test_missing_future_bar_is_not_interpolated(self):
        rows = example_bars()
        rows.pop(2)
        a = evaluate(rows)
        m = a["event_outcomes"]["3"]["ER_POS"]
        self.assertEqual(m["outcomes_complete"], 0)
        self.assertEqual(m["missing_reasons"]["MISSING_BAR"], 1)

    def test_missing_heartbeat_excludes_all_windows(self):
        rows = example_bars(n=1)
        a = evaluate(rows)
        self.assertEqual(a["heartbeat_bars"], 0)
        self.assertEqual(a["event_outcomes"]["3"]["ER_POS"]["outcomes_complete"], 0)
        self.assertIsNone(
            a["event_outcomes"]["3"]["ER_POS"]["matched_baseline_mean_return_atr"])

    def test_no_received_timestamp_cannot_be_prospective(self):
        rows = [r["payload"] for r in example_bars()]
        a = evaluate(rows)
        self.assertEqual(a["audit"]["missing_receipt"], 13)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["NOT_PROSPECTIVE"], 1)

    def test_older_than_two_minutes_excluded(self):
        rows = example_bars()
        rows[0]["received_at_ms"] = T0 + 150_000
        a = evaluate(rows)
        self.assertEqual(a["audit"]["late_receipt"], 1)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["NOT_PROSPECTIVE"], 1)

    def test_late_future_bar_invalidates_window(self):
        rows = example_bars()
        rows[1]["received_at_ms"] += 150_000
        a = evaluate(rows)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["UNVERIFIED_FUTURE_BAR"], 1)

    def test_retest_rifiuto_uses_prior_side(self):
        a = evaluate(example_bars(retest=True))
        rt = next(r for r in a["records"] if
                  r["cohort"] == "RT_DAY1" and r["horizon_bars"] == 3)
        self.assertEqual(rt["label"], "RIFIUTO")
        self.assertEqual(rt["level_origin_ms"], T0 - STEP)
        self.assertTrue(rt["level_survives_at_h"])

    def test_retest_rottura(self):
        rows = example_bars(retest=True)
        rows[0]["payload"]["ohlc"]["prev_close"] = 1.110
        a = evaluate(rows)
        rt = next(r for r in a["records"] if
                  r["cohort"] == "RT_DAY1" and r["horizon_bars"] == 3)
        self.assertEqual(rt["label"], "ROTTURA")

    def test_retest_equal_prevclose_indefinito(self):
        rows = example_bars(retest=True)
        rows[0]["payload"]["ohlc"]["prev_close"] = 1.111
        a = evaluate(rows)
        rt = next(r for r in a["records"] if
                  r["cohort"] == "RT_DAY1" and r["horizon_bars"] == 3)
        self.assertEqual(rt["label"], "INDEFINITO")

    def test_level_disappeared_not_retroactively_removed(self):
        rows = example_bars(retest=True)
        for r in rows[1:]:
            t = r["payload"]["bar_close_ms"]
            r["payload"]["levels"]["day1"] = 1.112
            r["payload"]["level_origin_ms"]["day1"] = t
            r["payload"]["level_scores"]["day1"] = 2500
        a = evaluate(rows)
        rt = next(r for r in a["records"] if
                  r["cohort"] == "RT_DAY1" and r["horizon_bars"] == 3)
        self.assertFalse(rt["level_survives_at_h"])

    def test_level_moves_rank_but_still_alive(self):
        rows = example_bars(retest=True)
        for r in rows[1:]:
            p = r["payload"]
            p["levels"]["day2"] = p["levels"]["day1"]
            p["level_origin_ms"]["day2"] = T0 - STEP
            p["level_scores"]["day2"] = p["level_scores"]["day1"]
            p["levels"]["day1"] = 1.112
            p["level_origin_ms"]["day1"] = p["bar_close_ms"]
            p["level_scores"]["day1"] = 2600
        a = evaluate(rows)
        rt = next(r for r in a["records"] if
                  r["cohort"] == "RT_DAY1" and r["horizon_bars"] == 3)
        self.assertTrue(rt["level_survives_at_h"])

    def test_simultaneous_er_and_rt_not_double_counted_in_any(self):
        a = evaluate(example_bars(retest=True))
        self.assertEqual(
            a["event_outcomes"]["3"]["ANY_EVENT"]["events_attempted"], 1)
        self.assertEqual(
            a["event_outcomes"]["3"]["RT_DAY1"]["events_attempted"], 1)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["events_attempted"], 1)

    def test_duplicate_payload_excluded(self):
        rows = example_bars()
        rows.append(copy.deepcopy(rows[0]))
        a = evaluate(rows)
        self.assertEqual(a["audit"]["duplicates"], 1)
        self.assertEqual(a["event_outcomes"]["3"]["ER_POS"]["outcomes_complete"], 1)

    def test_bar_collision_quarantines_source(self):
        rows = example_bars()
        conflict = copy.deepcopy(rows[0])
        conflict["payload"]["event_type"] = "HEARTBEAT"
        conflict["payload"]["events"]["peak"] = False
        conflict["payload"]["events"]["er_positive"] = False
        rows.append(conflict)
        a = evaluate(rows)
        self.assertEqual(a["audit"]["conflicted_bars"], 1)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["CONFLICTED_ORIGIN"], 1)

    def test_invalid_snapshot_never_enters_cohorts(self):
        rows = example_bars()
        rows[0]["payload"]["source"] = "CME_VERIFIED"
        a = evaluate(rows)
        self.assertEqual(a["audit"]["invalid"], 1)
        self.assertNotIn("ER_POS", a["event_outcomes"]["3"])

    def test_atr_zero_marks_missing(self):
        rows = example_bars()
        rows[0]["payload"]["ohlc"]["atr14"] = 0
        a = evaluate(rows)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["ATR_UNAVAILABLE"], 1)

    def test_baseline_only_heartbeat_bars(self):
        rows = example_bars(26)
        a = evaluate(rows)
        c = a["event_outcomes"]["3"]["ER_POS"]
        self.assertEqual(c["benchmark_status"], "COMPARABILE")
        self.assertGreater(c["matched_baseline_event_count"], 0)

    def test_anchor_changed_blocks_false_comparison(self):
        rows = example_bars()
        rows[1]["payload"]["quality"]["daily_anchor"] = "POC FOOTPRINT"
        a = evaluate(rows)
        self.assertEqual(
            a["event_outcomes"]["3"]["ER_POS"]["missing_reasons"]["ANCHOR_CHANGED"], 1)


if __name__ == "__main__":
    unittest.main()
