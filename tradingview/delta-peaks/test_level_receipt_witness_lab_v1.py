# REMURA v0.8.126 LAB — 17/11/2026 CET
import unittest
from level_receipt_witness_lab_v1 import genesis,advance,verify_witness,verify_recovery,ZERO
from level_receipt_custody_lab_v1 import hashobj
import test_level_receipt_custody_lab_v1 as custody
KEY=b"x"*32
G,N="1"*32,"2"*32
P,Q="a"*64,"b"*64
FLAGS=dict(synthetic=True,ingress_closed=True)
class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.first,self.anchor=genesis(P,G,KEY,**FLAGS)
        self.next,self.latest=advance(self.first,KEY,latest_anchor=self.anchor,latest_generation=G,latest_sequence=1,new_generation=N,new_snapshot_pin=Q,**FLAGS)
    def verify(self,r,**kw):
        args=dict(latest_anchor=self.latest,latest_generation=N,latest_sequence=2,**FLAGS)
        return verify_witness(r,KEY,**dict(args,**kw))
    def test_chain_and_exact_latest(self):
        self.assertEqual(self.next["body"]["previous_anchor"],self.anchor)
        self.assertEqual(self.verify(self.next),Q)
        self.assertEqual(self.first["body"]["previous_anchor"],ZERO)
    def test_old_valid_witness_rejected(self):
        with self.assertRaises(ValueError):self.verify(self.first)
        with self.assertRaises(ValueError):self.verify(self.first,latest_generation=G,latest_sequence=1)
    def test_tamper_even_rehashed(self):
        record={**self.next,"body":{**self.next["body"],"snapshot_pin":P}}
        with self.assertRaises(ValueError):self.verify(record,latest_anchor=hashobj(record))
    def test_wrong_key_and_context(self):
        with self.assertRaises(ValueError):verify_witness(self.next,b"y"*32,latest_anchor=self.latest,latest_generation=N,latest_sequence=2,**FLAGS)
        for kwargs in ({"latest_anchor":self.anchor},{"latest_sequence":1},{"latest_generation":G},{"synthetic":False},{"ingress_closed":False}):
            with self.assertRaises(ValueError):self.verify(self.next,**kwargs)
    def test_advance_wrong_authority_or_same_generation(self):
        args=dict(latest_anchor=self.anchor,latest_generation=G,latest_sequence=1,new_generation=N,new_snapshot_pin=Q,**FLAGS)
        for bad in ({"latest_anchor":self.latest},{"new_generation":G},{"new_snapshot_pin":ZERO},{"ingress_closed":False}):
            with self.assertRaises(ValueError):advance(self.first,KEY,**dict(args,**bad))
    def test_malformed_genesis(self):
        for p,g,k in ((ZERO,G,KEY),(P,"0"*32,KEY),(P,G,b"x")):
            with self.assertRaises(ValueError):genesis(p,g,k,**FLAGS)
    def test_actual_snapshot_and_stale_copy(self):
        f=custody.ReceiptCustodyTests("test_exact_sqlite_backup_and_closed_flags")
        try:
            f.setUp()
            old=f.copy();_,p=f.seal(old)
            first,a=genesis(p,G,KEY,**FLAGS)
            f.reserve(custody.T+1600);new=f.copy();_,q=f.seal(new)
            r,b=advance(first,KEY,latest_anchor=a,latest_generation=G,latest_sequence=1,new_generation=N,new_snapshot_pin=q,**FLAGS)
            args=dict(latest_anchor=b,latest_generation=N,latest_sequence=2,**FLAGS)
            out=verify_recovery(new,r,KEY,**args)
            self.assertTrue(out["fixture_mac_verified"])
            for flag in ("independent_pin_verified","generation_migration_verified","restore_authorized","may_open","scientific_admission","backup_encrypted"):self.assertFalse(out[flag])
            with self.assertRaises(ValueError):verify_recovery(old,r,KEY,**args)
            with self.assertRaises(ValueError):verify_recovery(old,first,KEY,**args)
        finally:f.doCleanups()
if __name__=="__main__":unittest.main()
