# REMURA Level Confluence v0.11 LAB — 14/11/2026 23:47 CET
import unittest
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from integrated_lab_v1 import IntegratedLab
from access_policy_v1 import LabIdentity
from level_confluence_v1 import Rule
from confluence_dashboard_v1 import owner_report

KEY=dict(market="EURUSD",provider="OANDA",ticker="EURUSD",product="SPOT",
         contract="",period="WEEK",anchor_utc="2026-11-09T00:00:00Z",kind="DELTA_PEAK")
RULE=Rule(("EURUSD","OANDA","EURUSD","SPOT",""),"0.00001",10)

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.now=int(datetime(2026,11,14,22,46,tzinfo=timezone.utc).timestamp())
        self.lab=IntegratedLab(Path(self.temp.name).resolve(),synthetic=True,initialize=True,clock=lambda:self.now)
        self.owner=self.lab.login(*self.identity("google-owner-fixture","owner"))
        inv=self.lab.invite(self.owner,"a@example.invalid","friend-a")
        self.friend=self.lab.redeem(*self.identity("google-a-fixture","a"),inv)
        self.lab.submit(self.friend,dict(KEY,request_id=str(UUID(int=1)),price="1.08535",
            observed_utc="2026-11-14T22:45:00Z",note="<script>PRIVATE NOTE</script>"))
        self.receipt=self.lab._stamp(self.now)
        self.now+=1
        self.lab.review(self.owner,1,"APPROVED","synthetic review")
        self.auto=dict(KEY,id="auto-1",price="1.08540",
            observed_utc="2026-11-14T22:44:00Z",available_utc="2026-11-14T22:45:00Z")
    def tearDown(self):
        self.lab.close();self.temp.cleanup()
    def identity(self,sub,email):
        nonce=self.lab.challenge()
        return LabIdentity(sub,email+"@example.invalid",True,nonce),nonce
    def report(self,**kwargs):
        return owner_report(self.lab,self.owner,kwargs.pop("automatic",[self.auto]),
                            kwargs.pop("rules",[RULE]),synthetic=True,**kwargs)
    def test_owner_report(self):
        data=self.report()
        self.assertEqual(data["result"]["automatic"][0]["near_count"],1)
        self.assertIn("1.08535",data["html"])
        self.assertIn("5.00000000 tick",data["html"])
        self.assertIn("SOLO DATI SINTETICI",data["html"])
        self.assertIn("v0.11 LAB",data["html"])
        self.assertNotIn("PRIVATE NOTE",data["html"])
        self.assertNotIn(self.friend,data["html"])
        self.assertFalse(data["result"]["operational_signal"])
    def test_owner_only(self):
        for token in (self.friend,"unknown"):
            with self.assertRaises(PermissionError):
                owner_report(self.lab,token,[],[],synthetic=True)
    def test_logout(self):
        self.lab.logout(self.owner)
        with self.assertRaises(PermissionError):self.report()
    def test_cutoff_and_future(self):
        html=self.report(asof_utc=self.receipt)["html"]
        self.assertNotIn("1.08535",html)
        self.assertIn("N/D — nessun manuale confrontabile",html)
        with self.assertRaises(ValueError):
            self.report(asof_utc="2026-11-15T00:00:00Z")
    def test_missing_rules(self):
        data=self.report(rules=[])
        self.assertEqual(data["result"]["automatic"][0]["status"],"NOT_COMPARABLE_NO_RULE")
        self.assertIn("regola di confronto assente",data["html"])
    def test_no_auto(self):
        data=self.report(automatic=[])
        self.assertIn("N/D — nessun automatico disponibile",data["html"])
        self.assertIn("1.08535",data["html"])
    def test_revoked_contribution(self):
        self.now+=1
        self.lab.review(self.owner,1,"REVOKED","synthetic")
        self.assertNotIn("1.08535",self.report()["html"])
    def test_no_mutation(self):
        before=self.lab.queue(self.owner)
        self.report()
        self.assertEqual(before,self.lab.queue(self.owner))
    def test_capacity_and_explicit_mode(self):
        with self.assertRaises(ValueError):self.report(automatic=[self.auto]*21)
        with self.assertRaises(ValueError):owner_report(self.lab,self.owner,[],[])
if __name__=="__main__":unittest.main()
