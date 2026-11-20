# REMURA Contributors v0.7 LAB — 14/11/2026 23:39 CET
import unittest
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
from access_policy_v1 import LabIdentity,SESSION_TTL
from session_lab_v1 import SessionLab

class SessionLabTests(unittest.TestCase):
    def setUp(self):
        self.now=int(datetime(2026,11,14,22,39,tzinfo=timezone.utc).timestamp())
        self.lab=SessionLab(synthetic=True,clock=lambda:self.now)
        self.owner=self.login("google-owner-fixture","owner")
        self.a=self.enroll("a","friend-a")
        self.b=self.enroll("b","friend-b")
        self.p=dict(request_id=str(UUID(int=1)),market="NAS100",provider="PEPPERSTONE",
                    ticker="NAS100",product="CFD",contract="",period="WEEK",kind="DELTA_PEAK",
                    price="21000.50",anchor_utc="2026-11-09T00:00:00Z",
                    observed_utc="2026-11-14T22:38:00Z",note="synthetic")
    def tearDown(self):
        self.lab.close()
    def identity(self,subject,email):
        nonce=self.lab.challenge()
        return LabIdentity(subject,email+"@example.invalid",True,nonce),nonce
    def login(self,subject,email):
        return self.lab.login(*self.identity(subject,email))
    def enroll(self,email,slot):
        inv=self.lab.invite(self.owner,email+"@example.invalid",slot)
        return self.lab.redeem(*self.identity("google-"+email+"-fixture",email),inv)
    def test_review_end_to_end(self):
        receipt=self.lab.submit(self.a,self.p)
        self.assertEqual(receipt["status"],"UNREVIEWED")
        self.assertEqual(self.lab.receipts(self.b),[])
        self.assertEqual(self.lab.queue(self.owner)[0]["subject"],"friend-a")
        self.now+=1
        self.assertFalse(self.lab.review(self.owner,receipt["id"],"APPROVED","synthetic")["scientific_admission"])
        self.assertEqual(self.lab.receipts(self.a)[0]["status"],"APPROVED")
    def test_revocation_checks_every_operation(self):
        self.lab.submit(self.a,self.p)
        self.lab.revoke(self.owner,"friend-a")
        for f in (lambda:self.lab.receipts(self.a),lambda:self.lab.submit(self.a,self.p),
                  lambda:self.lab.queue(self.a),lambda:self.lab.review(self.a,1,"APPROVED","fake")):
            with self.assertRaises(PermissionError):f()
        with self.assertRaises(PermissionError):self.login("google-a-fixture","a")
        self.assertEqual(len(self.lab.queue(self.owner)),1)
        self.assertEqual(self.lab.receipts(self.b),[])
        self.lab.submit(self.b,self.p)
        self.assertEqual(len(self.lab.queue(self.owner)),2)
    def test_roles_never_from_payload(self):
        with self.assertRaises(PermissionError):self.lab.queue(self.a)
        with self.assertRaises(PermissionError):self.lab.review(self.a,1,"APPROVED","fake")
        with self.assertRaises(PermissionError):self.lab.submit(self.owner,self.p)
        with self.assertRaises(ValueError):self.lab.submit(self.a,dict(self.p,subject="friend-b"))
        with self.assertRaises(ValueError):self.lab.submit(self.a,dict(self.p,received_utc="2020-01-01T00:00:00Z"))
        self.assertEqual(self.lab.queue(self.owner),[])
    def test_expiry_logout_and_rotation(self):
        new=self.login("google-a-fixture","a")
        with self.assertRaises(PermissionError):self.lab.receipts(self.a)
        self.lab.logout(new)
        with self.assertRaises(PermissionError):self.lab.submit(new,self.p)
        self.now+=SESSION_TTL
        with self.assertRaises(PermissionError):self.lab.submit(self.b,self.p)
        with self.assertRaises(PermissionError):self.lab.queue(self.owner)
    def test_clock_used_for_receipt(self):
        self.lab.submit(self.a,self.p)
        self.assertEqual(self.lab.receipts(self.a)[0]["received_utc"],"2026-11-14T22:39:00Z")
        self.now-=1
        with self.assertRaises(ValueError):self.lab.receipts(self.a)
    def test_fresh_lifetime_no_old_records(self):
        self.lab.submit(self.a,self.p)
        with SessionLab(synthetic=True,clock=lambda:self.now) as other:
            nonce=other.challenge()
            token=other.login(LabIdentity("google-owner-fixture","owner@example.invalid",True,nonce),nonce)
            self.assertEqual(other.queue(token),[])
            with self.assertRaises(PermissionError):other.receipts(self.a)
    def test_cleanup(self):
        with SessionLab(synthetic=True,clock=lambda:self.now) as other:
            root=Path(other._root.name)
            self.assertTrue(root.exists())
        self.assertFalse(root.exists())
        with self.assertRaises(RuntimeError):other.challenge()
        with self.assertRaises(ValueError):SessionLab()

if __name__=="__main__":unittest.main()
