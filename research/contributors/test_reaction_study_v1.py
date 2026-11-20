# REMURA Level Confluence v0.12 LAB — 14/11/2026 23:48 CET
import unittest
from datetime import datetime,timedelta,timezone
from reaction_study_v1 import reaction
START=datetime(2026,11,14,20,0,tzinfo=timezone.utc)
def stamp(t):return t.strftime("%Y-%m-%dT%H:%M:%SZ")
CUTOFF=stamp(START)
END=stamp(START+timedelta(hours=2))
def fixture():
    bars=[]
    for i in range(1,25):
        t=stamp(START+timedelta(minutes=i*5))
        bars.append(dict(close_utc=t,available_utc=t,open="101",high="102",low="100.5",close="101"))
    return bars
def run(bars=None,**kwargs):
    args=dict(level="100",cutoff_utc=CUTOFF,evaluated_utc=END,
              previous_close=dict(close_utc=CUTOFF,available_utc=CUTOFF,close="101"),
              bars=fixture() if bars is None else bars,synthetic=True)
    args.update(kwargs)
    return reaction(**args)
class ReactionTests(unittest.TestCase):
    def test_no_touch(self):
        self.assertEqual(run()["status"],"NO_TOUCH")
    def test_touch_and_follow(self):
        b=fixture()
        b[0].update(low="99",high="110",close="101")
        b[1].update(low="98",high="103",close="99")
        r=run(b)
        self.assertEqual(r["status"],"TOUCHED")
        self.assertEqual(r["away_excursion"],"3")
        self.assertEqual(r["through_excursion"],"2")
        self.assertTrue(r["closed_across"])
        self.assertFalse(r["operational_signal"])
    def test_touch_last_slot(self):
        b=fixture();b[11]["low"]="100"
        b[23]["high"]="105"
        self.assertEqual(run(b)["away_excursion"],"5")
    def test_after_search_not_touch(self):
        b=fixture();b[12]["low"]="100"
        self.assertEqual(run(b)["status"],"NO_TOUCH")
    def test_from_below(self):
        b=fixture()
        for x in b:x.update(open="99",high="99.5",low="98",close="99")
        b[0]["high"]="100"
        b[1].update(high="101",low="97",close="100.5")
        r=run(b,previous_close=dict(close_utc=CUTOFF,available_utc=CUTOFF,close="99"))
        self.assertEqual(r["direction"],"FROM_BELOW")
        self.assertEqual(r["away_excursion"],"3")
        self.assertEqual(r["through_excursion"],"1")
        self.assertTrue(r["closed_across"])
    def test_gap(self):
        b=fixture();b[0].update(open="99",high="99.5",low="98",close="99")
        self.assertEqual(run(b)["reason"],"GAP_ACROSS_BEFORE_TOUCH")
    def test_immature_and_missing(self):
        self.assertEqual(run(evaluated_utc=CUTOFF)["reason"],"WINDOW_NOT_MATURE")
        self.assertEqual(run(fixture()[:-1])["reason"],"INCOMPLETE_WINDOW")
        b=fixture();b[2]["close_utc"]=b[1]["close_utc"]
        self.assertEqual(run(b)["reason"],"MISSING_OR_UNORDERED_BAR")
    def test_late_available(self):
        b=fixture();b[23]["available_utc"]=stamp(START+timedelta(hours=2,seconds=1))
        self.assertEqual(run(b)["reason"],"BAR_NOT_AVAILABLE")
    def test_invalid_chronology_and_ohlc(self):
        b=fixture();b[0]["available_utc"]=CUTOFF
        with self.assertRaises(ValueError):run(b)
        b=fixture();b[0]["high"]="99"
        with self.assertRaises(ValueError):run(b)
    def test_previous_close_gate(self):
        p=dict(close_utc=CUTOFF,available_utc=stamp(START+timedelta(seconds=1)),close="101")
        self.assertEqual(run(previous_close=p)["reason"],"PREVIOUS_CLOSE_NOT_AVAILABLE")
        p["available_utc"]=stamp(START-timedelta(seconds=1))
        with self.assertRaises(ValueError):run(previous_close=p)
        p.update(available_utc=CUTOFF,close="100")
        self.assertEqual(run(previous_close=p)["reason"],"ALREADY_AT_LEVEL")
    def test_explicit_mode(self):
        with self.assertRaises(ValueError):run(synthetic=False)
if __name__=="__main__":unittest.main()
