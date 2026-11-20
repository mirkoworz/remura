# REMURA Level Confluence v0.14 LAB — 14/11/2026 23:53 CET
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
from access_policy_v1 import LabIdentity
from integrated_lab_v1 import IntegratedLab
from cohort_report_v1 import owner_statistics
from test_cohort_study_v1 import plan,manual,auto,window,END

class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.now=int(datetime(2026,11,14,22,53,tzinfo=timezone.utc).timestamp())
        self.lab=IntegratedLab(Path(self.tmp.name).resolve(),synthetic=True,initialize=True,clock=lambda:self.now)
        self.owner=self.lab.login(*self.identity("google-owner-fixture","owner"))
        inv=self.lab.invite(self.owner,"a@example.invalid","friend-a")
        self.friend=self.lab.redeem(*self.identity("google-a-fixture","a"),inv)
    def tearDown(self):
        self.lab.close();self.tmp.cleanup()
    def identity(self,sub,email):
        nonce=self.lab.challenge()
        return LabIdentity(sub,email+"@example.invalid",True,nonce),nonce
    def report(self,p,w=None,token=None,at=END):
        return owner_statistics(self.lab,self.owner if token is None else token,p["manifest"],p["digest"],
                                {} if w is None else w,evaluated_utc=at,synthetic=True)
    def test_contact_and_excursions(self):
        p=plan();u=p["manifest"]["units"][0]
        r=self.report(p,{u["unit_id"]:window(u)})
        s=r["report"]["groups"][0]["stats"]
        self.assertEqual((s["total"],s["valid"],s["touched"],s["n_d"]),(1,1,1,0))
        self.assertEqual(s["contact_percent"],"100.00")
        self.assertEqual(s["crossing_percent"],"0.00")
        self.assertEqual(s["away"]["median"],"0.0016")
        self.assertIn("SOLO DATI SINTETICI",r["html"])
        self.assertIn("1 / 1",r["html"])
        self.assertNotIn(self.owner,r["html"])
        self.assertFalse(r["report"]["scientific_admission"])
    def test_missing_not_failure(self):
        p=plan();r=self.report(p)
        s=r["report"]["groups"][0]["stats"]
        self.assertEqual((s["total"],s["valid"],s["n_d"]),(1,0,1))
        self.assertIsNone(s["contact_percent"])
        self.assertIsNone(s["away"])
        self.assertIn("WINDOW_ABSENT",r["html"])
    def test_no_contact(self):
        p=plan();u=p["manifest"]["units"][0]
        s=self.report(p,{u["unit_id"]:window(u,touch=False)})["report"]["groups"][0]["stats"]
        self.assertEqual(s["contact_percent"],"0.00")
        self.assertIsNone(s["crossing_percent"])
    def test_separate_feeds_and_anchors(self):
        p=plan(a=[auto(),auto("other",provider="FXCM"),auto("day",period="DAY")])
        r=self.report(p)["report"]
        self.assertEqual(len(r["groups"]),3)
        self.assertEqual(sum(g["stats"]["total"] for g in r["groups"]),3)
        self.assertEqual(sum(v["total"] for v in r["cohort_counts"].values()),3)
    def test_permissions_and_future(self):
        p=plan()
        with self.assertRaises(PermissionError):self.report(p,token=self.friend)
        with self.assertRaises(ValueError):self.report(p,at="2026-11-15T00:00:00Z")
        self.lab.logout(self.owner)
        with self.assertRaises(PermissionError):self.report(p)
    def test_digest_and_no_mutation(self):
        p=plan();before=self.lab.queue(self.owner)
        self.report(p)
        self.assertEqual(before,self.lab.queue(self.owner))
        p["manifest"]["units"][0]["price"]="9"
        with self.assertRaises(ValueError):self.report(p)
    def test_empty(self):
        r=self.report(plan(m=[],a=[]))
        self.assertEqual(r["report"]["total_units"],0)
        self.assertIn("nessuna unità",r["html"])
if __name__=="__main__":unittest.main()
