# REMURA Contributors v0.29 LAB — 16/11/2026 08:24 CET
import json,tempfile,unittest,os
from pathlib import Path
from recovery_journal_candidate import ZERO,verify
from encrypted_journal_storage_lab import EncryptedJournal,canonical
from recovery_journal_storage_lab import name,Journal
from admin_identity_candidate import CLOSED,plan_change
from admin_sqlite_rehearsal import AdminRehearsal
KEY=bytes.fromhex("12"*32); OTHER=bytes.fromhex("34"*32); J="4"*32
O="a"*64; A="b"*64; EO="c"*64; EA="d"*64
T="2026-11-16T07:24:00Z"; L="2026-11-16T07:25:00Z"
G="1"*32; N="2"*32; R="3"*32; S="5"*32; U="6"*32
AUTH=dict(ingress_closed=True,quiesced=True,identity_verified=True,owner_authorized=True)
class EncryptedJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def open(self,pin=ZERO,*,init=False,key=KEY,jid=J):
        return EncryptedJournal(self.root,pin,key=key,journal_id=jid,synthetic=True,initialize=init)
    def owner(self,j):
        return j.record("ENROLL",T,O,EO,"OWNER","owner",expected_pin=ZERO)
    def test_restart_encrypted_no_plaintext(self):
        with self.open(init=True) as j:p=self.owner(j)
        raw=(self.root/name(1)).read_bytes()
        for val in (O,EO,"ENROLL","owner"):self.assertNotIn(val.encode(),raw)
        self.assertEqual(set(json.loads(raw)),{"v","nonce","ct","tag"})
        with self.open(p) as j:self.assertIn(O,verify(*j.snapshot()))
        for k,i in ((OTHER,J),(KEY,"5"*32)):
            with self.assertRaises(ValueError):self.open(p,key=k,jid=i)
        with self.assertRaises(ValueError):self.open(ZERO)
        with self.assertRaises(ValueError):Journal(self.root,p,synthetic=True)
    def test_tamper_and_swap(self):
        with self.open(init=True) as j:
            p=self.owner(j);q=j.record("ENROLL",L,A,EA,"CONTRIBUTOR","friend-a",expected_pin=p)
        a=self.root/name(1);b=self.root/name(2);ar=a.read_bytes();br=b.read_bytes()
        e=json.loads(ar);e["ct"]=("1" if e["ct"][0]=="0" else "0")+e["ct"][1:];a.write_bytes(canonical(e))
        with self.assertRaises(ValueError):self.open(q)
        a.write_bytes(br);b.write_bytes(ar)
        with self.assertRaises(ValueError):self.open(q)
        a.write_bytes(ar);b.write_bytes(br)
        with self.open(q) as j:self.assertEqual(j.snapshot()[1],q)
    def test_external_pin_rollback(self):
        with self.open(init=True) as j:
            p=self.owner(j);q=j.record("ENROLL",L,A,EA,"CONTRIBUTOR","friend-a",expected_pin=p)
        (self.root/name(2)).unlink()
        with self.assertRaises(ValueError):self.open(q)
        with self.open(p) as j:self.assertEqual(j.snapshot()[1],p)
    def test_explicit_synthetic_only(self):
        with self.assertRaises(ValueError):EncryptedJournal(self.root,ZERO,key=KEY,journal_id=J,initialize=True)
        with self.assertRaises(ValueError):self.open(init=True,key=bytes(32))
    def test_encrypted_journal_admin_restore(self):
        with self.open(init=True) as j, AdminRehearsal(G,synthetic=True) as db:
            def change(kind,s,t,role,slot,gen):
                events,pin=j.snapshot()
                p=plan_change(events,pin,db.inventory(),db.pin()[0],gen,kind=kind,at=L,subject=s,email_tag=t,role=role,slot=slot,gates=CLOSED,**AUTH)
                new=j.record(kind,L,s,t,role,slot,expected_pin=pin)
                self.assertEqual(new,p["new_pin"])
                events,external=j.snapshot() # synthetic stand-in for independent pin custody
                return db.apply(p,events,external,**AUTH)
            change("ENROLL",O,EO,"OWNER","owner",N)
            change("ENROLL",A,EA,"CONTRIBUTOR","friend-a",R)
            with db.copy_snapshot() as old:
                change("REVOKE",A,EA,"CONTRIBUTOR","friend-a",S)
                events,pin=j.snapshot()
                out=old.recover(events,pin,U,ingress_closed=True,quiesced=True)
                self.assertFalse(out["may_open"])
                self.assertTrue(next(x for x in old.inventory() if x["subject"]==A)["revoked"])
                self.assertEqual(old.gates(),CLOSED)
