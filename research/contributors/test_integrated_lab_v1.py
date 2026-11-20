# REMURA Contributors v0.9 LAB — 14/11/2026 23:43 CET
import tempfile
import unittest
from pathlib import Path
from uuid import UUID
from datetime import datetime,timezone
from unittest.mock import patch
from access_policy_v1 import LabIdentity
from integrated_lab_v1 import IntegratedLab
from archive_v1 import FILENAME

class IntegratedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.now=int(datetime(2026,11,14,22,43,tzinfo=timezone.utc).timestamp())
        self.lab=IntegratedLab(self.root,synthetic=True,initialize=True,clock=lambda:self.now)
        self.owner=self.login("google-owner-fixture","owner")
        self.p=dict(request_id=str(UUID(int=1)),market="NAS100",provider="PEPPERSTONE",
                    ticker="NAS100",product="CFD",contract="",period="WEEK",kind="DELTA_PEAK",
                    price="21000.50",anchor_utc="2026-11-09T00:00:00Z",
                    observed_utc="2026-11-14T22:42:00Z",note="synthetic")
    def tearDown(self):
        if not self.lab._closed:self.lab.close()
        self.temp.cleanup()
    def identity(self,subject,email):
        nonce=self.lab.challenge()
        return LabIdentity(subject,email+"@example.invalid",True,nonce),nonce
    def login(self,subject,email):
        return self.lab.login(*self.identity(subject,email))
    def enroll(self,email="a",slot="friend-a"):
        inv=self.lab.invite(self.owner,email+"@example.invalid",slot)
        return self.lab.redeem(*self.identity("google-"+email+"-fixture",email),inv)
    def restart(self):
        self.lab.close()
        self.lab=IntegratedLab(self.root,synthetic=True,clock=lambda:self.now)
        self.owner=self.login("google-owner-fixture","owner")
    def test_restart_preserves_attribution_and_review(self):
        token=self.enroll()
        self.lab.submit(token,self.p)
        self.now+=1
        self.lab.review(self.owner,1,"APPROVED","synthetic")
        self.restart()
        with self.assertRaises(PermissionError):self.lab.receipts(token)
        with self.assertRaises(PermissionError):self.login("other-subject","a")
        new=self.login("google-a-fixture","changed")
        self.assertEqual(self.lab.receipts(new)[0]["status"],"APPROVED")
        self.assertEqual(self.lab.queue(self.owner)[0]["subject"],"friend-a")
    def test_revocation_persists_with_records(self):
        token=self.enroll()
        self.lab.submit(token,self.p)
        self.lab.revoke(self.owner,"friend-a")
        self.restart()
        with self.assertRaises(PermissionError):self.login("google-a-fixture","a")
        with self.assertRaises(ValueError):self.enroll("b","friend-a")
        b=self.enroll("b","friend-b")
        self.assertEqual(self.lab.receipts(b),[])
        self.assertEqual(len(self.lab.queue(self.owner)),1)
    def test_missing_registry_rejects_reopen(self):
        self.lab._archive.db.execute("DROP TABLE synthetic_identity_registry")
        self.lab.close()
        import sqlite3
        with self.assertRaises(sqlite3.OperationalError):
            IntegratedLab(self.root,synthetic=True)
    def test_unbound_records_reject_reopen(self):
        token=self.enroll()
        self.lab.submit(token,self.p)
        self.lab._archive.db.execute("UPDATE synthetic_identity_registry SET state=?",(
            '{"version":1,"owner":"google-owner-fixture","last_binding":0,"users":[]}',))
        self.lab.close()
        with self.assertRaises(ValueError):IntegratedLab(self.root,synthetic=True)
    def test_lock_and_no_reinit(self):
        with self.assertRaises(BlockingIOError):IntegratedLab(self.root,synthetic=True)
        with self.assertRaises(ValueError):IntegratedLab(self.root,synthetic=True,initialize=True)
    def test_missing_file_never_recreated(self):
        self.lab.close()
        (self.root/FILENAME).unlink()
        with self.assertRaises(FileNotFoundError):IntegratedLab(self.root,synthetic=True)
        with self.assertRaises(ValueError):IntegratedLab(self.root,synthetic=True,initialize=True)
        self.assertFalse((self.root/FILENAME).exists())
    def test_persistence_failure_stops_access(self):
        token=self.enroll()
        with patch.object(self.lab._archive,"_write",side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):self.lab.revoke(self.owner,"friend-a")
        with self.assertRaises(RuntimeError):self.lab.receipts(token)
        with self.assertRaises(RuntimeError):self.lab.queue(self.owner)
    def test_pending_invite_dies_on_restart(self):
        inv=self.lab.invite(self.owner,"a@example.invalid","friend-a")
        self.restart()
        with self.assertRaises(PermissionError):
            self.lab.redeem(*self.identity("google-a-fixture","a"),inv)

if __name__=="__main__":unittest.main()
