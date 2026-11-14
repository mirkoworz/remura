# REMURA Contributors v0.8 LAB — 14/11/2026 23:41 CET
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from access_policy_v1 import LabIdentity
from durable_access_v1 import DurableAccess,STATE,LOCK

class DurableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.now=100000
        self.db=DurableAccess(self.root,"google-owner-fixture",synthetic=True,initialize=True)
        self.owner=self.login("google-owner-fixture","owner")
    def tearDown(self):
        if not self.db._closed:self.db.close()
        self.temp.cleanup()
    def identity(self,subject,email):
        nonce=self.db.challenge(now=self.now)
        return LabIdentity(subject,email+"@example.invalid",True,nonce),nonce
    def login(self,subject,email):
        return self.db.login(*self.identity(subject,email),now=self.now)
    def enroll(self,email="a",slot="friend-a"):
        inv=self.db.invite(self.owner,email+"@example.invalid",slot,now=self.now)
        return self.db.redeem(*self.identity("google-"+email+"-fixture",email),inv,now=self.now)
    def restart(self):
        self.db.close()
        self.db=DurableAccess(self.root,"google-owner-fixture",synthetic=True)
    def test_binding_and_restart(self):
        token=self.enroll()
        self.restart()
        with self.assertRaises(PermissionError):self.db.principal(token,now=self.now)
        with self.assertRaises(PermissionError):self.db.principal(self.owner,now=self.now)
        new=self.login("google-a-fixture","changed")
        self.assertEqual(self.db.principal(new,now=self.now).subject,"friend-a")
        with self.assertRaises(PermissionError):self.login("new-subject","a")
        self.assertEqual((self.root/STATE).stat().st_mode&0o777,0o600)
    def test_durable_revocation(self):
        token=self.enroll()
        self.now+=1
        self.db.revoke(self.owner,"friend-a",now=self.now)
        self.restart()
        for sub,email in (("google-a-fixture","a"),("other-subject","a")):
            with self.assertRaises(PermissionError):self.login(sub,email)
        self.owner=self.login("google-owner-fixture","owner")
        with self.assertRaises(ValueError):self.enroll("b","friend-a")
        token=self.enroll("b","friend-b")
        self.assertEqual(self.db.principal(token,now=self.now).subject,"friend-b")
    def test_pending_invites_and_challenges_die(self):
        inv=self.db.invite(self.owner,"a@example.invalid","friend-a",now=self.now)
        identity,nonce=self.identity("google-a-fixture","a")
        self.restart()
        with self.assertRaises(PermissionError):self.db.redeem(identity,nonce,inv,now=self.now)
        with self.assertRaises(PermissionError):self.db.redeem(*self.identity("google-a-fixture","a"),inv,now=self.now)
    def test_private_registry_has_no_bearer_or_email(self):
        token=self.enroll()
        raw=(self.root/STATE).read_text()
        self.assertNotIn(token,raw);self.assertNotIn(self.owner,raw)
        self.assertNotIn("@example.invalid",raw)
        self.assertEqual(json.loads(raw)["users"],[dict(subject="google-a-fixture",slot="friend-a",revoked=False)])
    def test_lock_and_explicit_reinit(self):
        with self.assertRaises(BlockingIOError):
            DurableAccess(self.root,"google-owner-fixture",synthetic=True)
        with self.assertRaises(ValueError):
            DurableAccess(self.root,"google-owner-fixture",synthetic=True,initialize=True)
    def test_missing_fail_closed(self):
        self.db.close()
        (self.root/STATE).unlink()
        with self.assertRaises(FileNotFoundError):
            DurableAccess(self.root,"google-owner-fixture",synthetic=True)
        with self.assertRaises(ValueError):
            DurableAccess(self.root,"google-owner-fixture",synthetic=True,initialize=True)
    def test_wrong_owner_or_corruption(self):
        self.db.close()
        with self.assertRaises(ValueError):
            DurableAccess(self.root,"different-owner",synthetic=True)
        (self.root/STATE).write_text("{}")
        with self.assertRaises(ValueError):
            DurableAccess(self.root,"google-owner-fixture",synthetic=True)
    def test_persist_failure_blocks_further_actions(self):
        token=self.enroll()
        with patch.object(self.db,"_save",side_effect=OSError("synthetic disk error")):
            with self.assertRaises(OSError):self.db.revoke(self.owner,"friend-a",now=self.now)
        with self.assertRaises(RuntimeError):self.db.principal(token,now=self.now)
        with self.assertRaises(RuntimeError):self.db.principal(self.owner,now=self.now)
    def test_clock_floor(self):
        self.enroll()
        self.restart()
        with self.assertRaises(ValueError):self.db.challenge(now=self.now-1)
    def test_initialize_guard(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            with self.assertRaises(ValueError):DurableAccess(root,"owner",initialize=True)
            with self.assertRaises(FileNotFoundError):DurableAccess(root,"owner",synthetic=True)
            root.chmod(0o755)
            with self.assertRaises(ValueError):DurableAccess(root,"owner",synthetic=True,initialize=True)

if __name__=="__main__":unittest.main()
