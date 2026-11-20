# REMURA Contributors v0.39 LAB — 17/11/2026 06:44 CET
import unittest
from recovery_journal_candidate import ZERO,append,verify,digest
from closed_generation_exclusion_lab_v1 import plan,check_candidate
O,A,B="a"*64,"b"*64,"c"*64
EO,EA,EB="d"*64,"e"*64,"f"*64
G,N="1"*32,"2"*32
T="2026-11-17T05:44:00Z"
class ClosedGenerationTests(unittest.TestCase):
    def setUp(self):
        self.events=[];self.pin=ZERO
        for s,t,role,slot,kind in [(O,EO,"OWNER","owner","ENROLL"),(A,EA,"CONTRIBUTOR","friend-a","ENROLL"),
          (B,EB,"CONTRIBUTOR","friend-b","ENROLL"),(A,EA,"CONTRIBUTOR","friend-a","REVOKE")]:
            self.events,self.pin=append(self.events,self.pin,kind,T,s,t,role,slot)
        self.records=verify(self.events,self.pin)
        self.inventory=[self.records[O],self.records[B]]
        self.manifest,self.md=self.make()
    def make(self,**kw):
        args=dict(subject=A,ingress_closed=True,synthetic=True)
        return plan(self.events,self.pin,G,N,**dict(args,**kw))
    def check(self,**kw):
        args=dict(candidate_generation=N,inventory=self.inventory,ingress_closed=True,synthetic=True)
        return check_candidate(self.manifest,self.md,**dict(args,**kw))
    def test_closed_only_no_subject_disclosure(self):
        out=self.check()
        self.assertEqual(out["retired_count"],1)
        self.assertEqual(out["retained_count"],2)
        for k in ("may_open","restore_authorized","all_copies_erased","enrollment_authorized"):self.assertFalse(out[k])
        for s in (O,A,B,EO,EA,EB):self.assertNotIn(s,str(out))
    def test_stale_backup_rejected(self):
        with self.assertRaises(ValueError):self.check(candidate_generation=G)
        with self.assertRaises(ValueError):self.check(inventory=list(self.records.values()))
    def test_retired_slot_cannot_rebind(self):
        fake={**self.records[A],"subject":"9"*64,"email_tag":"8"*64,"revoked":False}
        with self.assertRaises(ValueError):self.check(inventory=self.inventory+[fake])
    def test_active_or_owner_cannot_be_excluded(self):
        for s in (O,B,"9"*64):
            with self.assertRaises(ValueError):self.make(subject=s)
    def test_manifest_tamper_and_pin(self):
        m={**self.manifest,"retired_slots":[]}
        with self.assertRaises(ValueError):check_candidate(m,self.md,candidate_generation=N,inventory=self.inventory,ingress_closed=True,synthetic=True)
        with self.assertRaises(ValueError):plan(self.events,"0"*64,G,N,subject=A,ingress_closed=True,synthetic=True)
    def test_missing_or_changed_retained_identity(self):
        with self.assertRaises(ValueError):self.check(inventory=[self.records[O]])
        with self.assertRaises(ValueError):self.check(inventory=[self.records[O],{**self.records[B],"email_tag":"9"*64}])
    def test_closed_and_synthetic_required(self):
        for k in ("synthetic","ingress_closed"):
            with self.assertRaises(ValueError):self.make(**{k:False})
            with self.assertRaises(ValueError):self.check(**{k:False})
    def test_two_retired_slots(self):
        self.events,self.pin=append(self.events,self.pin,"REVOKE",T,B,EB,"CONTRIBUTOR","friend-b")
        self.manifest,self.md=self.make()
        self.assertEqual(self.check(inventory=[self.records[O]])["retired_count"],2)
if __name__=="__main__":unittest.main()
