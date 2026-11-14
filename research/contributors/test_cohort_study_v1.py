# REMURA Level Confluence v0.13 LAB — 14/11/2026 23:50 CET
import unittest
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from cohort_study_v1 import freeze,evaluate
from level_confluence_v1 import Rule

T="2026-11-14T20:00:00Z"
END="2026-11-14T22:00:00Z"
KEY=dict(market="EURUSD",provider="OANDA",ticker="EURUSD",product="SPOT",
         contract="",period="WEEK",anchor_utc="2026-11-09T00:00:00Z",kind="DELTA_PEAK")
RULE=Rule(("EURUSD","OANDA","EURUSD","SPOT",""),"0.00001",10)
def manual(i=1,price="1.08535",**changes):
    p=dict(KEY,price=price,source_group="shared",observed_utc="2026-11-14T19:57:00Z")
    p.update(changes)
    return dict(id=i,subject="friend-a",received_utc="2026-11-14T19:58:00Z",
                data=p,status="APPROVED",history=[dict(action="APPROVED",at_utc="2026-11-14T19:59:00Z")])
def auto(i="a",price="1.08540",**changes):
    p=dict(KEY,id=i,price=price,observed_utc="2026-11-14T19:55:00Z",available_utc="2026-11-14T19:56:00Z")
    p.update(changes);return p
def plan(m=None,a=None,rules=None):
    return freeze([manual()] if m is None else m,[auto()] if a is None else a,[RULE] if rules is None else rules,cutoff_utc=T,synthetic=True)
def window(unit,*,touch=True):
    bars=[]
    base=datetime(2026,11,14,20,0,tzinfo=timezone.utc)
    for i in range(1,25):
        t=(base+timedelta(minutes=i*5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        bars.append(dict(close_utc=t,available_utc=t,open="1.086",high="1.087",low="1.0854" if touch else "1.0859",close="1.086"))
    return dict(instrument=unit["key"][:5],previous_close=dict(close_utc=T,available_utc=T,close="1.086"),bars=bars)
def run(p,windows=None,at=END):
    return evaluate(p["manifest"],p["digest"],windows or {},evaluated_utc=at,synthetic=True)

class CohortTests(unittest.TestCase):
    def test_four_cohorts(self):
        p=plan([manual(),manual(2,provider="FXCM")],[auto(),auto("b","1.09000"),auto("c",period="DAY")])
        self.assertEqual({u["cohort"] for u in p["manifest"]["units"]},
                         {"A_NEAR","B_DISTANT","C_NO_MANUAL","D_MANUAL_ISOLATED"})
    def test_dedup_stable(self):
        a=[auto(),auto("same","1.085400")]
        p=plan(a=a)
        self.assertEqual(p,plan(a=list(reversed(a))))
        self.assertEqual(len(p["manifest"]["units"]),1)
        self.assertEqual(p["manifest"]["units"][0]["labels"],["auto:a","auto:same"])
    def test_missing_units_retained(self):
        p=plan(a=[auto(),auto("b","1.0900")])
        u=next(u for u in p["manifest"]["units"] if u["cohort"]=="A_NEAR")
        r=run(p,{u["unit_id"]:window(u)})
        self.assertEqual(r["metrics"]["A_NEAR"]["contact_rate"],"1.000000")
        self.assertEqual(r["metrics"]["B_DISTANT"]["n_d"],1)
        self.assertIsNone(r["metrics"]["B_DISTANT"]["contact_rate"])
        self.assertEqual(len(r["results"]),2)
        self.assertFalse(r["independent_observations_verified"])
    def test_zero_contact_denominator(self):
        p=plan();u=p["manifest"]["units"][0]
        s=run(p,{u["unit_id"]:window(u,touch=False)})["metrics"]["A_NEAR"]
        self.assertEqual((s["valid"],s["no_touch"],s["contact_rate"]),(1,1,"0.000000"))
        self.assertIsNone(s["crossing_rate_given_contact"])
    def test_bad_digest_and_extra_window(self):
        p=plan();changed=deepcopy(p);changed["manifest"]["units"][0]["price"]="9"
        with self.assertRaises(ValueError):run(changed)
        with self.assertRaises(ValueError):run(p,{"not-in-manifest":{}})
    def test_missing_rule(self):
        p=plan(rules=[])
        s=run(p)["metrics"]["N_D_RULE"]
        self.assertEqual(s["reasons"],{"COMPARISON_RULE_ABSENT":1})
    def test_feed_mismatch(self):
        p=plan();u=p["manifest"]["units"][0];w=window(u);w["instrument"][1]="FXCM"
        self.assertEqual(run(p,{u["unit_id"]:w})["metrics"]["A_NEAR"]["reasons"],{"FEED_MISMATCH":1})
    def test_future_and_unapproved_not_admitted(self):
        m=manual();m["history"][0]["at_utc"]="2026-11-14T20:01:00Z"
        p=plan([m],[auto(),auto("future",available_utc="2026-11-14T20:01:00Z")])
        self.assertEqual(p["manifest"]["excluded_manual"],1)
        self.assertEqual(p["manifest"]["excluded_automatic"],1)
        self.assertEqual(p["manifest"]["units"][0]["cohort"],"C_NO_MANUAL")
    def test_inconsistent_feed_windows(self):
        p=plan(a=[auto(),auto("b","1.09")])
        u,v=p["manifest"]["units"]
        with self.assertRaises(ValueError):run(p,{u["unit_id"]:window(u),v["unit_id"]:window(v,touch=False)})
    def test_immature_and_opt_in(self):
        p=plan();u=p["manifest"]["units"][0]
        self.assertEqual(run(p,{u["unit_id"]:window(u)},at=T)["metrics"]["A_NEAR"]["reasons"],{"WINDOW_NOT_MATURE":1})
        with self.assertRaises(ValueError):freeze([],[],[],cutoff_utc=T)
if __name__=="__main__":unittest.main()
