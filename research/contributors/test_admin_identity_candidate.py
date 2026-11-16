# REMURA Contributors v0.23 LAB — 16/11/2026 07:14 CET
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from recovery_journal_candidate import ZERO,verify
from recovery_journal_storage_lab import Journal,name
from admin_identity_candidate import plan_change,reconcile,CLOSED
T="2026-11-16T06:14:00Z";L="2026-11-16T06:15:00Z"
O="a"*64;A="b"*64;EO="c"*64;EA="d"*64;G="1"*32;N="2"*32
class JournalStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def init(self):return Journal(self.root,ZERO,synthetic=True,initialize=True)
    def owner(self,j):return j.record("ENROLL",T,O,EO,"OWNER","owner",expected_pin=ZERO)
    def test_restart_external_pin(self):
        with self.init() as j:p=self.owner(j)
        with Journal(self.root,p,synthetic=True) as j:
            events,pin=j.snapshot();self.assertEqual(pin,p);self.assertIn(O,verify(events,p))
        with self.assertRaises(ValueError):Journal(self.root,ZERO,synthetic=True)
    def test_lock_no_overwrite(self):
        with self.init() as j:
            p=self.owner(j)
            with self.assertRaises(BlockingIOError):Journal(self.root,p,synthetic=True)
            with self.assertRaises(ValueError):self.owner(j)
            self.assertEqual(j.snapshot()[1],p)
        with self.assertRaises(ValueError):self.init()
    def test_partial_or_unexpected_file(self):
        with self.init() as j:p=self.owner(j)
        bad=self.root/name(2);bad.write_text("{");bad.chmod(0o600)
        with self.assertRaises(ValueError):Journal(self.root,p,synthetic=True)
    def test_permissions_and_symlink(self):
        with self.init() as j:p=self.owner(j)
        f=self.root/name(1);f.chmod(0o644)
        with self.assertRaises(ValueError):Journal(self.root,p,synthetic=True)
        f.unlink();f.symlink_to("journal.lock")
        with self.assertRaises(OSError):Journal(self.root,p,synthetic=True)
    def test_failed_fsync_poisoned(self):
        with self.init() as j:
            with patch("recovery_journal_storage_lab.os.fsync",side_effect=OSError("simulated")):
                with self.assertRaises(OSError):self.owner(j)
            with self.assertRaises(RuntimeError):j.snapshot()
        with self.assertRaises(ValueError):Journal(self.root,ZERO,synthetic=True)
    def test_opt_in_required(self):
        with self.assertRaises(ValueError):Journal(self.root,ZERO,initialize=True)
    def test_external_rollback_detection(self):
        with self.init() as j:
            p=self.owner(j)
            q=j.record("ENROLL",L,A,EA,"CONTRIBUTOR","friend-a",expected_pin=p)
        (self.root/name(2)).unlink()
        with self.assertRaises(ValueError):Journal(self.root,q,synthetic=True)
        # Both journal and independent pin rolled back would be indistinguishable.
        with Journal(self.root,p,synthetic=True) as j:self.assertEqual(j.snapshot()[1],p)
class AdminPlanTests(unittest.TestCase):
    def setUp(self):
        from recovery_journal_candidate import append
        self.events,self.pin=append([],ZERO,"ENROLL",T,O,EO,"OWNER","owner")
        self.before=list(verify(self.events,self.pin).values())
        self.options=dict(kind="ENROLL",at=L,subject=A,email_tag=EA,role="CONTRIBUTOR",slot="friend-a",gates=dict(CLOSED),ingress_closed=True,quiesced=True,identity_verified=True,owner_authorized=True)
    def plan(self,**changes):
        return plan_change(self.events,self.pin,self.before,G,N,**(self.options|changes))
    def test_enroll_and_reconcile(self):
        p=self.plan();self.assertFalse(p["may_open"])
        events=self.events+[p["event"]]
        out=reconcile(events,p["new_pin"],p["expected_inventory"],expected_generation=N,db_generation=N,db_pin=p["new_pin"],gates=CLOSED,ingress_closed=True,quiesced=True)
        self.assertTrue(out["inventory_matches"]);self.assertFalse(out["may_open"])
        with self.assertRaises(ValueError):reconcile(events,p["new_pin"],self.before,expected_generation=N,db_generation=N,db_pin=p["new_pin"],gates=CLOSED,ingress_closed=True,quiesced=True)
    def test_require_closed_and_verified(self):
        for opt in ({"ingress_closed":False},{"quiesced":False},{"identity_verified":False},{"owner_authorized":False},{"gates":{**CLOSED,"read_enabled":True}}):
            with self.assertRaises(ValueError):self.plan(**opt)
    def test_revocation_and_stale_inventory(self):
        p=self.plan();self.events.append(p["event"]);self.pin=p["new_pin"];self.before=p["expected_inventory"];self.options["kind"]="REVOKE"
        r=self.plan();self.assertTrue(next(x for x in r["expected_inventory"] if x["subject"]==A)["revoked"])
        self.before[0]["revoked"]=True
        with self.assertRaises(ValueError):self.plan()
    def test_wrong_generation_or_pin(self):
        p=self.plan();ev=self.events+[p["event"]]
        for g,pin in ((G,p["new_pin"]),(N,self.pin)):
            with self.assertRaises(ValueError):reconcile(ev,p["new_pin"],p["expected_inventory"],expected_generation=N,db_generation=g,db_pin=pin,gates=CLOSED,ingress_closed=True,quiesced=True)
