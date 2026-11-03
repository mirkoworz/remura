"""Offline replay tests on synthetic archived data. No GitHub or broker access."""
import copy
import datetime as dt
import json
import unittest

from scripts import cvd_session_replay as replay
from scripts import cvd_benchmark as benchmark

STEP=900_000
BASE=1793577600000

def make_day(offset=0, count=45, *, volume=100):
    bars=[]
    for i in range(count):
        lo=10 if i==10 else 9.7 if i==22 else 10.4
        bars.append({"t":dt.datetime.fromtimestamp(
            (BASE+offset*86_400_000+i*STEP)/1000,dt.timezone.utc
        ).isoformat().replace("+00:00","Z"),
        "o":10.8,"h":11.2,"l":lo,"c":11.0,"v":volume})
    return bars

def bundle(days=(0,1), *, count=45, volume=100):
    allbars=[]
    for day in days:
        allbars.extend(make_day(day,count,volume=volume))
    return {"schema":"remura-price-v1","markets":{
        "EURUSD":{"symbol":"EURUSD","provider":"ctrader",
                   "providerSymbol":"SECRET_BROKER_ACCOUNT",
                   "sourceTimeframe":"M15","timezone":"UTC",
                   "timeframes":{"M15":allbars,"H1":[],"H4":[]}}
    }}


class ReplayTests(unittest.TestCase):
    def test_two_real_shape_sessions_aggregate_without_payload_leak(self):
        doc=bundle()
        before=copy.deepcopy(doc)
        out=replay.analyze_document(doc,"EURUSD")
        self.assertEqual(out["status"],"ready")
        self.assertEqual(out["sessionsEligible"],2)
        self.assertEqual(out["priceOnly"]["candidates"],2)
        self.assertEqual(out["cvdFiltered"]["candidates"],2)
        self.assertEqual(out["cvdFiltered"]["matured"],2)
        self.assertIsNone(out["cvdFiltered"]["favorableFraction"])
        self.assertEqual(out["sessionsExcluded"],0)
        self.assertEqual(len(out["rotatedVolumes"]),3)
        self.assertNotIn("SECRET_BROKER_ACCOUNT",json.dumps(out))
        self.assertNotIn("10.8",json.dumps(out))
        self.assertEqual(out["newBrokerCalls"],0)
        self.assertEqual(doc,before)

    def test_incomplete_or_gapped_day_is_excluded_not_fabricated(self):
        doc=bundle()
        doc["markets"]["EURUSD"]["timeframes"]["M15"].pop(5)
        out=replay.analyze_document(doc,"EURUSD")
        self.assertEqual(out["sessionsEligible"],1)
        self.assertEqual(out["sessionsExcluded"],1)
        self.assertEqual(out["exclusionCounts"].get("partial"),1)

    def test_days_are_evaluated_at_historical_close_not_now(self):
        doc=bundle(days=(0,1,2))
        out=replay.analyze_document(doc,"EURUSD",max_sessions=2)
        self.assertEqual(out["sessionsConsidered"],2)
        self.assertEqual(out["sessionsEligible"],2)
        self.assertEqual(out["priceOnly"]["candidates"],2)

    def test_missing_volume_cannot_create_cvd_events(self):
        doc=bundle(volume=0)
        out=replay.analyze_document(doc,"EURUSD")
        self.assertEqual(out["priceOnly"]["candidates"],2)
        self.assertEqual(out["cvdFiltered"]["candidates"],0)
        self.assertEqual(out["rotatedVolumes"][0]["candidates"],0)

    def test_missing_some_volumes_excludes_day_with_no_invented_ticks(self):
        doc=bundle()
        doc["markets"]["EURUSD"]["timeframes"]["M15"][3].pop("v")
        out=replay.analyze_document(doc,"EURUSD")
        self.assertEqual(out["sessionsEligible"],1)
        self.assertEqual(out["exclusionCounts"].get("missing"),1)

    def test_reject_bad_source_schema_or_symbols(self):
        doc=bundle()
        self.assertRaises(ValueError,replay.analyze_document,doc,"USOIL")
        broken=copy.deepcopy(doc)
        broken["markets"]["EURUSD"]["provider"]="csv"
        self.assertRaises(ValueError,replay.analyze_document,broken,"EURUSD")
        broken=copy.deepcopy(doc)
        broken["markets"]["EURUSD"]["timeframes"]["M15"][0]["v"]=-1
        self.assertRaises(ValueError,replay.analyze_document,broken,"EURUSD")
        broken=copy.deepcopy(doc)
        broken["markets"]["EURUSD"]["timeframes"]["M15"][1]["t"]=broken["markets"]["EURUSD"]["timeframes"]["M15"][0]["t"]
        self.assertRaises(ValueError,replay.analyze_document,broken,"EURUSD")
        broken=copy.deepcopy(doc)
        broken["markets"]["EURUSD"]["providerSymbol"]=""
        self.assertRaises(ValueError,replay.analyze_document,broken,"EURUSD")
        broken=copy.deepcopy(doc)
        broken["markets"]["EURUSD"]["timeframes"]["M15"][0]["o"]="SECRET_PRICE"
        self.assertRaises(ValueError,replay.analyze_document,broken,"EURUSD")

    def test_reject_invalid_limits(self):
        doc=bundle()
        for size in (-1,0,46,True,3.5):
            self.assertRaises(ValueError,replay.analyze_document,doc,"EURUSD",max_sessions=size)

    def test_only_one_day_end_does_not_create_forward_outcomes_from_next_day(self):
        doc=bundle(days=(0,1),count=25)
        report=replay.analyze_document(doc,"EURUSD")
        self.assertEqual(report["sessionsEligible"],2)
        self.assertEqual(report["cvdFiltered"]["pending"],2)
        self.assertEqual(report["cvdFiltered"]["matured"],0)
        self.assertIsNone(report["cvdFiltered"]["favorableFraction"])

    def test_price_only_candidate_is_super_set_of_cvd_and_controls(self):
        doc=bundle(days=tuple(range(7)))
        report=replay.analyze_document(doc,"EURUSD")
        base=report["priceOnly"]["candidates"]
        self.assertGreaterEqual(base,report["cvdFiltered"]["candidates"])
        for control in report["rotatedVolumes"]:
            self.assertGreaterEqual(base,control["candidates"])
        self.assertEqual(report["statistics"],"descriptive_correlated_not_walk_forward")
        self.assertEqual(report["edge"],"NOT_ESTABLISHED")


if __name__=="__main__":
    unittest.main()
