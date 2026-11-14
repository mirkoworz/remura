# REMURA Level Confluence v0.10 LAB — 14/11/2026 23:45 CET
import unittest
from copy import deepcopy
from level_confluence_v1 import Rule,compare

ANCHOR="2026-11-09T00:00:00Z"
OBS="2026-11-14T20:00:00Z"
REC="2026-11-14T20:01:00Z"
APP="2026-11-14T20:02:00Z"
ASOF="2026-11-14T20:03:00Z"
FUTURE="2026-11-14T20:04:00Z"
KEY=dict(market="EURUSD",provider="OANDA",ticker="EURUSD",product="SPOT",
         contract="",period="WEEK",anchor_utc=ANCHOR,kind="DELTA_PEAK")
RULE=Rule(("EURUSD","OANDA","EURUSD","SPOT",""),"0.00001",10)
def manual(i=1,price="1.08530",group="shared",**changes):
    return dict(id=i,subject="friend-a" if i==1 else "friend-b",received_utc=REC,
                data=dict(KEY,price=price,source_group=group,observed_utc=OBS,**changes),
                status="APPROVED",history=[dict(action="APPROVED",at_utc=APP)])
def auto(**changes):
    return dict(dict(KEY,id="auto-1",price="1.08540",observed_utc=OBS,available_utc=REC),**changes)
def run(m,a=None,rules=None,cutoff=ASOF):
    return compare(m,[auto()] if a is None else a,[RULE] if rules is None else rules,
                   asof_utc=cutoff,synthetic=True)

class ConfluenceTests(unittest.TestCase):
    def test_exact_boundary_and_grouping(self):
        res=run([manual(),manual(2,"1.08535")])
        a=res["automatic"][0]
        self.assertEqual(a["status"],"NEAR")
        self.assertEqual(a["near_count"],2)
        self.assertEqual(a["declared_source_groups"],1)
        self.assertEqual(a["pairs"][0]["distance_ticks"],"10.00000000")
        self.assertFalse(res["source_independence_verified"])
        self.assertFalse(res["scientific_admission"])
        self.assertFalse(res["operational_signal"])
    def test_outside_tolerance(self):
        a=run([manual(price="1.08529")])["automatic"][0]
        self.assertEqual(a["status"],"DISTANT")
        self.assertEqual(a["near_count"],0)
    def test_exact_keys_only(self):
        for change in ({"provider":"FXCM"},{"product":"CFD"},{"ticker":"EURUSD.A"},
                       {"period":"DAY"},{"anchor_utc":"2026-11-08T00:00:00Z"},{"kind":"EFFORT_RESULT"}):
            res=run([manual()],[auto(**change)])
            self.assertEqual(res["automatic"][0]["status"],"NO_COMPARABLE_MANUAL")
            self.assertEqual(res["manual"][0]["status"],"NO_COMPARABLE_AUTOMATIC")
    def test_missing_rule_is_unknown(self):
        res=run([manual()],rules=[])
        self.assertEqual(res["automatic"][0]["status"],"NOT_COMPARABLE_NO_RULE")
        self.assertIsNone(res["automatic"][0]["pairs"][0]["distance_ticks"])
    def test_late_approval(self):
        m=manual();m["history"][0]["at_utc"]=FUTURE
        self.assertEqual(run([m])["excluded_manual"],1)
    def test_revoked_as_of(self):
        m=manual();m["history"].append(dict(action="REVOKED",at_utc=FUTURE));m["status"]="REVOKED"
        self.assertEqual(run([m])["automatic"][0]["status"],"NEAR")
        self.assertEqual(run([m],cutoff=FUTURE)["excluded_manual"],1)
    def test_late_auto_and_preserve_manual(self):
        res=run([manual()],[auto(available_utc=FUTURE)])
        self.assertEqual(res["excluded_automatic"],1)
        self.assertEqual(res["manual"][0]["status"],"NO_COMPARABLE_AUTOMATIC")
    def test_unreviewed_and_rejected(self):
        m=manual();m["history"]=[];m["status"]="UNREVIEWED"
        n=manual(2);n["history"]=[dict(action="REJECTED",at_utc=APP)];n["status"]="REJECTED"
        self.assertEqual(run([m,n])["excluded_manual"],2)
    def test_bad_history(self):
        m=manual();m["history"][0]["at_utc"]=OBS
        with self.assertRaises(ValueError):run([m])
        m=manual();m["status"]="UNREVIEWED"
        with self.assertRaises(ValueError):run([m])
    def test_duplicates_invalid_rule_and_opt_in(self):
        with self.assertRaises(ValueError):run([manual(),manual()])
        with self.assertRaises(ValueError):run([],rules=[RULE,RULE])
        with self.assertRaises(ValueError):run([],rules=[Rule(RULE.instrument,"0",10)])
        with self.assertRaises(ValueError):compare([],[],[],asof_utc=ASOF)
    def test_non_mutating_deterministic(self):
        m=[manual(2),manual()];a=[auto()];before=deepcopy((m,a))
        self.assertEqual(run(m,a),run(list(reversed(m)),a))
        self.assertEqual((m,a),before)
    def test_no_auto_lookahead(self):
        with self.assertRaises(ValueError):run([],[auto(available_utc=ANCHOR)])

if __name__=="__main__":unittest.main()
