# REMURA v0.8.104 LAB — 16/11/2026 15:05 CET
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_historical_backup_v1 as m
import test_cvd_joint_backed_publication_v1 as fixture
from cvd_runtime_private_state_v1 import encoded
from cvd_joint_recovery_v1 import restore

class HistoricalBackupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.BackedPublicationTests(methodName="test_exact_restore_from_latest_copy")
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.h=m.History(self.f.c,synthetic=True)
        self.f.store=self.store
    def store(self):
        f=self.f
        return m.open_historical_joint(f.src,f.dest,f.c,generation=fixture.G,key=fixture.KEY,history=self.h,synthetic=True)
    def three(self):
        p,_=self.f.boot();q,_=self.f.step(p);r,out=self.f.step(q,2)
        return p,q,r,out
    def test_historical_authentication_and_prune(self):
        f=self.f;p,q,r,out=self.three()
        self.assertEqual(out["authenticated_retained_copies"],2)
        prev=f.copy(2).read_bytes()
        with self.store() as j:
            out=j.prune(r,allow_synthetic_prune=True)
        self.assertEqual(out["authenticated_retained_copies"],2)
        self.assertFalse(f.copy(1).exists())
        self.assertEqual(f.copy(2).read_bytes(),prev)
        s,out=f.step(r,3)
        self.assertEqual(s.sequence,4)
        self.assertEqual(out["authenticated_retained_copies"],2)
    def test_damaged_previous_blocks_prune_even_with_valid_latest(self):
        f=self.f;p,q,r,_=self.three()
        raw=f.copy(2).read_bytes()
        f.copy(2).write_bytes(raw[:-1])
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(r,allow_synthetic_prune=True)
        self.assertTrue(f.copy(1).exists())
        self.assertEqual(f.c.latest(),r)
    def test_old_valid_ciphertext_wrong_sequence_denied(self):
        f=self.f;p,q,r,_=self.three()
        f.copy(2).write_bytes(f.copy(1).read_bytes())
        with self.store() as j:
            with self.assertRaises(ValueError):j.audit(r)
        self.assertTrue(f.copy(1).exists())
    def test_old_pin_cannot_restore_or_authorize_current(self):
        f=self.f;p,q,r,_=self.three()
        raw=f.copy(2).read_bytes();f.path.unlink()
        with self.assertRaises(ValueError):
            restore(f.src,f.c,generation=fixture.G,key=fixture.KEY,expected=q,backup=raw,synthetic=True)
        self.assertFalse(f.path.exists())
        self.assertEqual(f.c.latest(),r)
    def test_missing_receipt_after_finalize_blocks_next_operation(self):
        f=self.f;p,_=f.boot()
        with patch.object(self.h,"record",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):f.step(p)
        q=f.c.latest()
        self.assertEqual(q.phase,"STABLE")
        with self.store() as j:
            with self.assertRaises(ValueError):j.audit(q)
            with self.assertRaises(ValueError):j.prune(q,allow_synthetic_prune=True)
        with self.assertRaises(ValueError):f.step(q,2)
        self.assertEqual(q,f.c.latest())
        self.assertTrue(f.copy(1).exists() and f.copy(2).exists())
    def test_historical_decrypt_and_digest_are_both_required(self):
        f=self.f;p,q,r,_=self.three()
        raw=f.copy(2).read_bytes()
        old,_=self.h.receipt(r,2)
        with self.assertRaises(ValueError):m.historical_open(raw,p,fixture.KEY)
        with self.assertRaises(ValueError):m.historical_open(raw,old,b"x"*32)
        prev=m.historical_open(raw,old,fixture.KEY)
        self.assertEqual(prev["cache"]["claim_ms"],q.cutoff_ms)
    def test_history_cannot_be_reinitialized_after_genesis(self):
        p,_=self.f.boot()
        with self.assertRaises(ValueError):m.History(self.f.c,synthetic=True)
        self.assertEqual(self.h.receipt(p,1)[0],p)
