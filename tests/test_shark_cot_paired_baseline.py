"""REMURA Track B matched COT baseline tests (synthetic SQLite only)."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from scripts import shark_cot_paired_baseline as baseline

UTC = timezone.utc
ASOF = "2026-11-04T10:00:00Z"
COST = {
    "EURUSD": {"spreadBps": 1.0, "slippageEachSideBps": 0.25,
               "commissionRoundTripBps": 0.5},
    "XAUUSD": {"spreadBps": 3.0, "slippageEachSideBps": 1.0,
               "commissionRoundTripBps": 0.0},
}


def fixture():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE cot_first_seen(dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT);
        CREATE TABLE squalincome_validation_cohorts(
          symbol TEXT, report_date TEXT, stage TEXT,
          observed_at TEXT,price_time TEXT,cot_side INTEGER,
          relationship TEXT,broker_symbol TEXT,entry_at TEXT,entry_open REAL);
        CREATE TABLE squalincome_validation_outcomes(
          symbol TEXT,report_date TEXT,stage TEXT,horizon_hours INTEGER,
          evaluated_at TEXT,directional_bps REAL,long_benchmark_bps REAL);
    """)
    return db


def insert(db, sym="EURUSD", side=1, long=8., week="2026-10-27",
           first_seen="2026-10-30T20:00:00+00:00",
           observed="2026-11-02T09:01:00+00:00", stage="observation",
           evaluated="2026-11-03T20:00:00+00:00", horizon=4,
           cohort_broker="TEST_BROKER_SECRET"):
    ds, code = baseline.PILOT.get(sym, ("tff", "000000"))
    db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
               (ds,code,week,first_seen))
    previous = (datetime.fromisoformat(week).date()-timedelta(days=7)).isoformat()
    db.execute("INSERT INTO cot_first_seen VALUES(?,?,?,?)",
               (ds,code,previous,"2026-10-25T20:00:00+00:00"))
    db.execute("INSERT INTO squalincome_validation_cohorts VALUES(?,?,?,?,?,?,?,?,?,?)",
               (sym,week,stage,observed,"2026-11-02T09:00:00+00:00",
                side,"aligned",cohort_broker,
                "2026-11-02T09:15:00+00:00",1.1))
    db.execute("INSERT INTO squalincome_validation_outcomes VALUES(?,?,?,?,?,?,?)",
               (sym,week,stage,horizon,evaluated,side*long,long))


class CotBaselineTests(unittest.TestCase):
    def test_price_and_cot_share_same_cohort_and_costs(self):
        with fixture() as db:
            insert(db, side=-1, long=-8)
            result = baseline.evaluate(db, as_of=ASOF, costs=COST)
            h = next(x for x in result["horizons"] if x["hours"]==4)
            self.assertEqual(h["samples"],1)
            # short COT over falling market earns +8bp gross, long -8bp.
            self.assertEqual(h["meanCotNetBps"],6.0)
            self.assertEqual(h["meanLongNetBps"],-10.0)
            self.assertEqual(h["meanCotMinusLongBps"],16.0)
            self.assertIsNone(h["cotHitPct"])
            self.assertEqual(result["edge"],"NOT_ESTABLISHED")
            self.assertFalse(result["returnsExecutable"])
            self.assertNotIn("TEST_BROKER_SECRET",json.dumps(result))

    def test_prior_cot_report_must_also_be_known_before_observation(self):
        with fixture() as db:
            insert(db)
            db.execute("UPDATE cot_first_seen SET first_seen_at=? WHERE report_date=?",
                       ("2026-11-03T20:00:00+00:00", "2026-10-20"))
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["reasons"]["cot_previous_week_not_known"],1)
            self.assertEqual(out["horizons"][1]["samples"],0)

    def test_never_backfill_cot_after_actual_observation(self):
        with fixture() as db:
            insert(db,first_seen="2026-11-03T20:00:00+00:00")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["reasons"]["cot_first_seen_future"],1)
            self.assertEqual(out["horizons"][1]["samples"],0)

    def test_missing_first_seen_and_naive_time_are_exclusions(self):
        with fixture() as db:
            insert(db)
            db.execute("DELETE FROM cot_first_seen")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["reasons"]["cot_first_seen_missing"],1)
            db.execute("UPDATE squalincome_validation_cohorts SET observed_at=?",
                       ("2026-11-02T09:01:00",))
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["reasons"]["invalid_cohort_or_outcome"],1)

    def test_never_count_overlapping_stages_twice(self):
        with fixture() as db:
            insert(db)
            insert(db,stage="technical_confirmation")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["received"],1)
            self.assertEqual(out["horizons"][1]["samples"],1)

    def test_no_hidden_zero_costs_and_require_exact_costs(self):
        with fixture() as db:
            insert(db)
            for bad in ({}, {"EURUSD": COST["EURUSD"]},
                        {"EURUSD":{"spreadBps":0,"slippageEachSideBps":0,
                                   "commissionRoundTripBps":0},
                         "XAUUSD":COST["XAUUSD"]}):
                with self.assertRaises(ValueError):
                    baseline.evaluate(db,as_of=ASOF,costs=bad)

    def test_stale_cot_week_or_stale_m15_cannot_fake_valid_cohort(self):
        with fixture() as db:
            insert(db,week="2026-10-01")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["horizons"][1]["samples"],0)
            self.assertEqual(out["reasons"]["invalid_cohort_or_outcome"],1)
        with fixture() as db:
            insert(db)
            db.execute("UPDATE squalincome_validation_cohorts SET price_time=?",
                       ("2026-11-02T03:00:00+00:00",))
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["horizons"][1]["samples"],0)
            self.assertEqual(out["reasons"]["invalid_cohort_or_outcome"],1)

    def test_outcomes_are_not_known_before_they_mature(self):
        with fixture() as db:
            insert(db,evaluated="2026-11-05T20:00:00+00:00")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["horizons"][1]["samples"],0)
            self.assertEqual(out["reasons"]["invalid_cohort_or_outcome"],1)

    def test_directional_outcome_must_match_recorded_side(self):
        with fixture() as db:
            insert(db,side=-1,long=8)
            db.execute("UPDATE squalincome_validation_outcomes SET directional_bps=8")
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["horizons"][1]["samples"],0)
            self.assertEqual(out["reasons"]["invalid_cohort_or_outcome"],1)

    def test_missing_tables_explicit_unavailable(self):
        with sqlite3.connect(":memory:") as db:
            out = baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertEqual(out["status"],"UNAVAILABLE")
            self.assertEqual(len(out["missingTables"]),3)

    def test_wrong_broker_is_never_returned_publicly(self):
        with fixture() as db:
            insert(db,cohort_broker="PRIVATE_TEST_SECRETS_123")
            out=baseline.evaluate(db,as_of=ASOF,costs=COST)
            self.assertNotIn("PRIVATE_TEST_SECRETS",json.dumps(out))
            self.assertEqual(out["newBrokerCalls"],0)


if __name__ == "__main__":
    unittest.main()
