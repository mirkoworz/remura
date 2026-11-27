# REMURA Contributors v0.6 LAB — 14/11/2026 23:37 CET
import unittest
from access_policy_v1 import LabAccess,LabIdentity,SESSION_TTL,INVITE_TTL,CHALLENGE_TTL

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.now=100000
        self.access=LabAccess("google-owner-fixture",synthetic=True)
        self.owner=self.login("google-owner-fixture","owner@example.invalid")
    def identity(self,sub,email,verified=True):
        nonce=self.access.challenge(now=self.now)
        return LabIdentity(sub,email,verified,nonce),nonce
    def login(self,sub,email):
        ident,nonce=self.identity(sub,email)
        return self.access.login(ident,nonce,now=self.now)
    def invite(self,email="a@example.invalid",slot="friend-a"):
        return self.access.invite(self.owner,email,slot,now=self.now)
    def redeem(self,invite,sub="google-a-fixture",email="a@example.invalid"):
        ident,nonce=self.identity(sub,email)
        return self.access.redeem(ident,nonce,invite,now=self.now)
    def test_invitation_and_stable_subject(self):
        token=self.redeem(self.invite())
        p=self.access.principal(token,now=self.now)
        self.assertEqual((p.subject,p.role),("friend-a","CONTRIBUTOR"))
        new=self.login("google-a-fixture","changed@example.invalid")
        self.assertEqual(self.access.principal(new,now=self.now),p)
        with self.assertRaises(PermissionError):self.access.principal(token,now=self.now)
        with self.assertRaises(PermissionError):self.login("different-sub","a@example.invalid")
    def test_unknown_and_unverified(self):
        with self.assertRaises(PermissionError):self.login("unknown","unknown@example.invalid")
        ident,nonce=self.identity("google-owner-fixture","owner@example.invalid",False)
        with self.assertRaises(PermissionError):self.access.login(ident,nonce,now=self.now)
        nonce=self.access.challenge(now=self.now)
        with self.assertRaises(PermissionError):self.access.login({"subject":"google-owner-fixture"},nonce,now=self.now)
    def test_wrong_email_and_single_use(self):
        inv=self.invite()
        with self.assertRaises(PermissionError):self.redeem(inv,email="wrong@example.invalid")
        self.redeem(inv)
        with self.assertRaises(PermissionError):self.redeem(inv,sub="other-sub")
    def test_nonce_bound_and_consumed(self):
        ident,nonce=self.identity("google-owner-fixture","owner@example.invalid")
        other=self.access.challenge(now=self.now)
        with self.assertRaises(PermissionError):self.access.login(ident,other,now=self.now)
        self.access.login(ident,nonce,now=self.now)
        with self.assertRaises(PermissionError):self.access.login(ident,nonce,now=self.now)
    def test_contributor_permissions(self):
        token=self.redeem(self.invite())
        for f in (lambda:self.access.invite(token,"b@example.invalid","friend-b",now=self.now),
                  lambda:self.access.revoke(token,"friend-a",now=self.now),
                  lambda:self.access.cancel_invite(token,"a"*43,now=self.now)):
            with self.assertRaises(PermissionError):f()
    def test_revocation_no_rebind(self):
        token=self.redeem(self.invite())
        self.access.revoke(self.owner,"friend-a",now=self.now)
        with self.assertRaises(PermissionError):self.access.principal(token,now=self.now)
        with self.assertRaises(PermissionError):self.login("google-a-fixture","a@example.invalid")
        with self.assertRaises(ValueError):self.invite(slot="friend-a",email="b@example.invalid")
    def test_logout(self):
        token=self.redeem(self.invite())
        self.access.logout(token,now=self.now)
        with self.assertRaises(PermissionError):self.access.principal(token,now=self.now)
    def test_expiration(self):
        inv=self.invite();ident,nonce=self.identity("google-a-fixture","a@example.invalid")
        self.now+=CHALLENGE_TTL
        with self.assertRaises(PermissionError):self.access.redeem(ident,nonce,inv,now=self.now)
        self.now+=INVITE_TTL
        with self.assertRaises(PermissionError):self.redeem(inv)
        with self.assertRaises(PermissionError):self.access.principal(self.owner,now=self.now)
    def test_session_boundary(self):
        self.now+=SESSION_TTL
        with self.assertRaises(PermissionError):self.access.principal(self.owner,now=self.now)
    def test_cancel_and_slot_limits(self):
        inv=self.invite()
        with self.assertRaises(ValueError):self.invite(email="b@example.invalid")
        with self.assertRaises(ValueError):self.invite(slot="owner")
        with self.assertRaises(ValueError):self.invite(email="real@gmail.com",slot="friend-b")
        self.access.cancel_invite(self.owner,inv,now=self.now)
        with self.assertRaises(PermissionError):self.redeem(inv)
    def test_same_subject_no_second_slot(self):
        self.redeem(self.invite())
        inv=self.invite(email="b@example.invalid",slot="friend-b")
        with self.assertRaises(PermissionError):self.redeem(inv,email="b@example.invalid")
        token=self.redeem(inv,sub="google-b-fixture",email="b@example.invalid")
        self.assertEqual(self.access.principal(token,now=self.now).subject,"friend-b")
    def test_clock_and_explicit(self):
        with self.assertRaises(ValueError):LabAccess("owner")
        with self.assertRaises(ValueError):self.access.principal(self.owner,now=self.now-1)
        with self.assertRaises(ValueError):self.access.challenge(now=True)

if __name__=="__main__":unittest.main()
