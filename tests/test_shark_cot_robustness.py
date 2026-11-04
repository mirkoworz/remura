"""Synthetic chronological robustness and cost-stress regression tests."""
import json
import sqlite3
import unittest
from datetime import date, timedelta

from scripts import shark_cot_paired_baseline as base
from scripts import shark_cot_robustness as research

ASOF = "2026-11-20T12:00:00Z"
TRAIN = "2026-11-05T00:00:00Z"
VALIDATION = "2026-11-12T00:00:00Z"
COST = {
    "EURUSD": {"spreadBps": 1.0, "slippageEachSideBps": 0.25,
               "commissionRoundTripBps": 0.5},  # 2bps roundtrip
    "XAUUSD": {"spreadBps": 3.0, "slippageEachSideBps": 1.0,
               "commissionRoundTripBps": 0.0},
}
BASE = {
    "train": ("2026-10-27", "2026-10-28T20:00:00+00:00",
              "2026-10-29T09:01:00+00:00",
              "2026-10-30T20:00:00+00:00"),
    "validation": ("2026-11-03", "2026-11-06T20:00:00+00:00",
                   "2026-11-07T09:01:00+00:00",
                   "2026-11-08T20:00:00+00:00"),
    "test": ("2026-11-10", "2026-11-13T20:00:00+00:00",
             "2026-11-14T09:01:00+00:00",
             "2026-11-15T20:00:00+00:00"),
}


def db_fixture():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
    CREATE TABLE cot_first_seen(
      dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT);
    CREATE TABLE squalincome_validation_cohorts(
      symbol TEXT,report_date TEXT,stage TEXT,observed_at TEXT,
      price_time TEXT,cot_side INTEGER,relationship TEXT,
      broker_symbol TEXT,entry_at TEXT,entry_open REAL);
    CREATE TABLE squalincome_validation_outcomes(
      symbol TEXT,report_date TEXT,stage TEXT,horizon_hours INTEGER,
      evaluated_at TEXT,directional_bps REAL,long_benchmark_bps REAL);
    """)
    return conn


def insert(conn, fold="train", *, sym="EURUSD", side=-1,
           gross_long=-5., override_week=None,
           override_evaluated=None, override_observed=None,
           override_first_seen=None):
    report, seen, observed, evaluated = BASE[fold]
    report = override_week or report
    seen = override_first_seen or seen
    observed = override_observed or observed
    evaluated = override_evaluated or evaluated
    ds, code = base.PILOT[sym]
    # observed is HH:01, price candle HH:00, entry HH:15
    clock = observed[:14]
    closed_at = clock + "00:00+00:00"
    entry_at = clock + "15:00+00:00"
    conn.execute("INSERT INTO cot_first_seen VALUES (?,?,?,?)",
                 (ds, code, report, seen))
    prior = (date.fromisoformat(report)-timedelta(days=7)).isoformat()
    conn.execute("INSERT INTO cot_first_seen VALUES (?,?,?,?)",
                 (ds, code, prior, "2026-10-25T20:00:00+00:00"))
    conn.execute(
        "INSERT INTO squalincome_validation_cohorts VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sym,report,"observation",observed,closed_at,side,
         "aligned","FAKE_PRIVATE_BROKER_XYZ",entry_at,1.1))
    conn.execute("INSERT INTO squalincome_validation_outcomes VALUES (?,?,?,?,?,?,?)",
                 (sym,report,"observation",4,evaluated,side*gross_long,gross_long))


def evaluate(conn, **overrides):
    args = {"as_of": ASOF, "train_end": TRAIN,
            "validation_end": VALIDATION, "costs": COST,
            "embargo_hours": 24}
    args.update(overrides)
    return research.evaluate(conn,**args)


def arm(out, fold, multiple, label="cot", hours=4):
    block = next(h for h in out["folds"][fold] if h["horizonHours"] == hours)
    return next(s for s in block["costScenarios"] if s["costMultiple"] == multiple)["arms"][label]


class RobustnessTests(unittest.TestCase):
    def test_same_eligible_cohorts_as_descriptive_baseline(self):
        with db_fixture() as db:
            for fold in BASE:
                insert(db,fold)
            plain = base.evaluate(db,as_of=ASOF,costs=COST)
            out = evaluate(db)
            self.assertEqual(plain["reasons"]["paired_valid"], 3)
            self.assertEqual(out["eligibleProvenance"],3)
            for fold in BASE:
                self.assertEqual(arm(out,fold,1)["meanNetBps"],3.0)
                self.assertEqual(arm(out,fold,1,"long")["meanNetBps"],-7.0)
                self.assertEqual(arm(out,fold,1,"invertedCot")["meanNetBps"],-7.0)
            self.assertEqual(arm(out,"train",2)["meanNetBps"],1.0)
            self.assertEqual(arm(out,"train",3)["meanNetBps"],-1.0)
            self.assertFalse(out["independentOutOfSample"])
            self.assertFalse(out["measuredBrokerCosts"])
            self.assertFalse(out["alertsEnabled"])
            self.assertEqual(out["brokerCalls"], 0)
            self.assertNotIn("FAKE_PRIVATE_BROKER_XYZ",json.dumps(out))
            self.assertNotIn("2026-10-29",json.dumps(out))
            self.assertIsNone(out["probability"])
            self.assertIsNone(next(s for s in out["folds"]["train"][1]["costScenarios"]
                                  if s["costMultiple"] == 1)["arms"]["cot"]["positivePct"])

    def test_previous_week_backfill_cannot_enter_a_fold(self):
        with db_fixture() as db:
            insert(db, "train")
            db.execute("UPDATE cot_first_seen SET first_seen_at=? WHERE report_date=?",
                       ("2026-11-15T20:00:00+00:00","2026-10-20"))
            out = evaluate(db)
            self.assertEqual(out["excluded"]["cot_previous_week_not_known"],1)
            self.assertIsNone(arm(out,"train",1)["meanNetBps"])

    def test_same_cot_week_cannot_contribute_to_two_folds(self):
        with db_fixture() as db:
            insert(db,"train")
            insert(db,"validation",sym="XAUUSD",override_week="2026-10-27")
            out=evaluate(db)
            self.assertEqual(out["excluded"]["cot_week_crosses_folds"],2)
            self.assertIsNone(arm(out,"train",1)["meanNetBps"])
            self.assertIsNone(arm(out,"validation",1)["meanNetBps"])

    def test_delayed_outcome_evaluation_purges_training(self):
        with db_fixture() as db:
            insert(db,"train",override_evaluated="2026-11-04T12:00:00+00:00")
            out=evaluate(db)
            self.assertEqual(out["excluded"]["embargo_or_unobserved_outcome"],1)
            self.assertEqual(arm(out,"train",1)["positiveCount"],0)

    def test_embargo_excludes_observation_near_validation_start(self):
        with db_fixture() as db:
            insert(db,"validation",
                   override_observed="2026-11-05T00:01:00+00:00",
                   override_first_seen="2026-11-04T20:00:00+00:00")
            # Need matching price open / next candle generated by fixture.
            out=evaluate(db)
            self.assertEqual(out["excluded"]["embargo_or_unobserved_outcome"],1)

    def test_missing_schema_yields_no_false_data(self):
        with sqlite3.connect(":memory:") as db:
            out=evaluate(db)
            self.assertEqual(out["status"],"UNAVAILABLE")
            self.assertEqual(len(out["missingTables"]),3)

    def test_invalid_time_boundaries_or_spread_rejected(self):
        with db_fixture() as db:
            insert(db)
            for dates in [
                {"train_end": VALIDATION, "validation_end": TRAIN},
                {"train_end": TRAIN,"validation_end":ASOF},
            ]:
                with self.assertRaises(ValueError):
                    evaluate(db,**dates)
            with self.assertRaises(ValueError):
                evaluate(db,embargo_hours=-1)
            with self.assertRaises(ValueError):
                evaluate(db,embargo_hours=169)
            invalid = dict(COST)
            invalid["EURUSD"] = dict(COST["EURUSD"], spreadBps=0)
            with self.assertRaises(ValueError):
                evaluate(db,costs=invalid)

    def test_untested_positive_results_never_claim_edge(self):
        with db_fixture() as db:
            insert(db,"train")
            insert(db,"validation")
            insert(db,"test")
            out=evaluate(db)
            self.assertEqual(out["edge"],"NOT_ESTABLISHED")
            self.assertFalse(out["preRegisteredBeforeSeeingData"])
            self.assertFalse(out["independentTradingSamples"])
            self.assertEqual(out["folds"]["test"][1]["costScenarios"][0]["sampleGate"],
                             "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
