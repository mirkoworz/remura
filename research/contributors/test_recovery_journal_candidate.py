# REMURA Contributors v0.22 LAB — 16/11/2026 07:08 CET
import unittest
from recovery_journal_candidate import append,verify,restore_plan,ZERO
T="2026-11-16T06:08:00Z"; L="2026-11-16T06:09:00Z"
O="a"*64; A="b"*64; EO="c"*64; EA="d"*64
class RecoveryJournalTests(unittest.TestCase):
    def setUp(self):
        self.events,self.pin=append([],ZERO,"ENROLL",T,O,EO,"OWNER","owner")
        self.events,self.pin=append(self.events,self.pin,"ENROLL",T,A,EA,"CONTRIBUTOR","friend-a")
        self.snapshot=list(verify(self.events,self.pin).values())
        self.before=self.pin
        self.events,self.pin=append(self.events,self.pin,"REVOKE",L,A,EA,"CONTRIBUTOR","friend-a")
    def plan(self,**kw):
        return restore_plan(self.events,self.pin,self.snapshot,"1"*32,"2"*32,ingress_closed=True,**kw)
    def test_restore_stays_closed(self):
        p=self.plan();self.assertEqual(p["revoke_subjects"],[A]);self.assertFalse(p["may_open"])
        self.assertFalse(any(p[k] for k in ("write_enabled","read_enabled","recovery_enabled")))
    def test_stale_or_tampered_journal(self):
        with self.assertRaises(ValueError):verify(self.events[:-1],self.pin)
        with self.assertRaises(ValueError):verify(self.events,self.before)
        z=[dict(e) for e in self.events];z[0]["slot"]="friend-a"
        with self.assertRaises(ValueError):verify(z,self.pin)
    def test_no_rebind(self):
        for s,email,role,slot in [(A,EA,"CONTRIBUTOR","friend-b"),("e"*64,EA,"CONTRIBUTOR","friend-b"),("e"*64,"f"*64,"CONTRIBUTOR","friend-a")]:
            with self.assertRaises(ValueError):append(self.events,self.pin,"ENROLL",L,s,email,role,slot)
    def test_missing_and_stale(self):
        self.snapshot.pop()
        with self.assertRaises(ValueError):self.plan()
        self.snapshot=list(verify(self.events,self.pin).values());self.snapshot[0]["revoked"]=True
        with self.assertRaises(ValueError):self.plan()
    def test_owner_revoked_and_generation(self):
        e,p=append(self.events,self.pin,"REVOKE",L,O,EO,"OWNER","owner")
        with self.assertRaises(ValueError):restore_plan(e,p,self.snapshot,"1"*32,"2"*32,ingress_closed=True)
        for g,closed in [("1"*32,True),("2"*32,False)]:
            with self.assertRaises(ValueError):restore_plan(self.events,self.pin,self.snapshot,"1"*32,g,ingress_closed=closed)
    def test_owner_first_and_time(self):
        with self.assertRaises(ValueError):append([],ZERO,"ENROLL",T,A,EA,"CONTRIBUTOR","friend-a")
        with self.assertRaises(ValueError):append(self.events,self.pin,"ENROLL","2026-11-15T00:00:00Z","e"*64,"f"*64,"CONTRIBUTOR","friend-b")
