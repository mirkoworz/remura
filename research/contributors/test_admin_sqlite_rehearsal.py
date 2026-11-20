# REMURA Contributors v0.24 LAB — 16/11/2026 07:17 CET
import unittest,sqlite3
from unittest.mock import patch
from admin_sqlite_rehearsal import AdminRehearsal
from admin_identity_candidate import CLOSED,plan_change
from recovery_journal_candidate import ZERO,append
from test_d1_lab_review import I,K,T
O="a"*64;A="b"*64;B="c"*64;EO="d"*64;EA="e"*64;EB="f"*64
G="1"*32;N="2"*32;R="3"*32;S="4"*32;U="5"*32
L="2026-11-16T06:17:00Z"
AUTH=dict(ingress_closed=True,quiesced=True,identity_verified=True,owner_authorized=True)
class AdminSQLTests(unittest.TestCase):
    def setUp(self):
        self.a=AdminRehearsal(G,synthetic=True);self.events=[];self.pin=ZERO
    def tearDown(self):self.a.close()
    def planned(self,kind,s,t,role,slot,new):
        p=plan_change(self.events,self.pin,self.a.inventory(),self.a.pin()[0],new,kind=kind,at=L,subject=s,email_tag=t,role=role,slot=slot,gates=CLOSED,**AUTH)
        e,pin=append(self.events,self.pin,kind,L,s,t,role,slot)
        return p,e,pin
    def change(self,*args):
        p,e,pin=self.planned(*args)
        out=self.a.apply(p,e,pin,**AUTH);self.events,self.pin=e,pin
        self.assertFalse(out["may_open"]);return out
    def setup_two(self):
        self.change("ENROLL",O,EO,"OWNER","owner",N)
        self.change("ENROLL",A,EA,"CONTRIBUTOR","friend-a",R)
    def test_enroll_revoke_no_rebind(self):
        self.setup_two()
        self.change("REVOKE",A,EA,"CONTRIBUTOR","friend-a",S)
        self.assertTrue(next(r for r in self.a.inventory() if r["subject"]==A)["revoked"])
        with self.assertRaises(ValueError):self.planned("ENROLL",B,EB,"CONTRIBUTOR","friend-a",U)
        self.assertEqual(self.a.db.execute("SELECT count(*) FROM lab_admin_events").fetchone()[0],3)
        self.assertEqual(self.a.gates(),CLOSED)
    def test_journal_ahead_and_rollback(self):
        self.setup_two();old=self.a.pin()
        p,e,pin=self.planned("REVOKE",A,EA,"CONTRIBUTOR","friend-a",S)
        with patch.object(self.a,"_rotate",side_effect=RuntimeError("failed after event")):
            with self.assertRaises(RuntimeError):self.a.apply(p,e,pin,**AUTH)
        self.assertEqual(self.a.pin(),old)
        self.assertFalse(next(r for r in self.a.inventory() if r["subject"]==A)["revoked"])
        self.assertEqual(self.a.db.execute("SELECT count(*) FROM lab_admin_events").fetchone()[0],2)
        self.assertEqual(self.a.gates(),CLOSED)
        # A mismatched latest external pin must never open the candidate.
        with self.assertRaises(ValueError):self.a.apply(p,e,self.pin,**AUTH)
    def test_tampered_plan_or_authority(self):
        p,e,pin=self.planned("ENROLL",O,EO,"OWNER","owner",N)
        with self.assertRaises(ValueError):self.a.apply({**p,"expected_inventory":[]},e,pin,**AUTH)
        with self.assertRaises(ValueError):self.a.apply(p,e,pin,**(AUTH|{"quiesced":False}))
        self.assertEqual(self.a.inventory(),[])
    def test_restore_actual_sqlite_copy(self):
        self.setup_two()
        self.a.db.execute("INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)",K+("fixture-fx",))
        self.a.db.execute("UPDATE lab_state SET write_enabled=1,read_enabled=1")
        self.a.db.execute(I["insert"],(A,"00000000-0000-0000-0000-000000000001",*K,"WEEK","DELTA_PEAK","1.0854",T,T,T,"synthetic",*K))
        with self.a.copy_snapshot() as restored:
            self.a.db.execute("UPDATE lab_state SET write_enabled=0,read_enabled=0")
            self.change("REVOKE",A,EA,"CONTRIBUTOR","friend-a",S)
            out=restored.recover(self.events,self.pin,U,ingress_closed=True,quiesced=True)
            self.assertFalse(out["may_open"]);self.assertEqual(restored.gates(),CLOSED)
            self.assertTrue(next(r for r in restored.inventory() if r["subject"]==A)["revoked"])
            self.assertEqual(restored.db.execute("SELECT subject FROM lab_entries").fetchone()[0],A)
            self.assertEqual(restored.pin(),(U,self.pin))
            self.assertEqual(restored.db.execute("SELECT count(*) FROM lab_admin_events").fetchone()[0],3)
    def test_restore_missing_enrollment_and_stale_pin(self):
        self.change("ENROLL",O,EO,"OWNER","owner",N)
        with self.a.copy_snapshot() as old:
            self.change("ENROLL",A,EA,"CONTRIBUTOR","friend-a",R)
            with self.assertRaises(ValueError):old.recover(self.events,self.pin,U,ingress_closed=True,quiesced=True)
            self.assertEqual(old.gates(),CLOSED)
        with self.assertRaises(ValueError):self.a.recover(self.events[:-1],self.events[-1]["prev"],U,ingress_closed=True,quiesced=True)
    def test_owner_revocation_no_restore(self):
        self.setup_two()
        out=self.change("REVOKE",O,EO,"OWNER","owner",S);self.assertFalse(out["owner_active"])
        with self.assertRaises(ValueError):self.a.recover(self.events,self.pin,U,ingress_closed=True,quiesced=True)
    def test_audit_immutable_and_cap(self):
        self.setup_two()
        for q in ["DELETE FROM lab_admin_events","UPDATE lab_admin_events SET at_utc='x'"]:
            with self.assertRaises(sqlite3.IntegrityError):self.a.db.execute(q)
    def test_synthetic_only(self):
        with self.assertRaises(ValueError):AdminRehearsal(G)
