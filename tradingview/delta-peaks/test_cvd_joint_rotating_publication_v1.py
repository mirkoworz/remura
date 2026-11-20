# REMURA v0.8.103 LAB — 16/11/2026 15:02 CET
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_rotating_publication_v1 as m
import test_cvd_joint_backed_publication_v1 as fixture

class RotationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.BackedPublicationTests(methodName="test_exact_restore_from_latest_copy")
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.f.store=self.store
    def store(self):
        f=self.f
        return m.open_rotating_joint(f.src,f.dest,f.c,generation=fixture.G,key=fixture.KEY,synthetic=True)
    def three(self):
        p,_=self.f.boot();q,_=self.f.step(p);return self.f.step(q,2)
    def test_third_copy_before_finalize_and_explicit_rotation(self):
        f=self.f;p,_=f.boot();q,_=f.step(p);first=f.copy(1).read_bytes();second=f.copy(2).read_bytes()
        original=f.c.finalize
        def finalize(p,out):
            self.assertEqual(f.copy(1).read_bytes(),first)
            self.assertEqual(f.copy(2).read_bytes(),second)
            self.assertEqual(f.copy(3).read_bytes(),f.path.read_bytes())
            return original(p,out)
        with patch.object(f.c,"finalize",side_effect=finalize):r,out=f.step(q,2)
        self.assertTrue(out["rotation_required"])
        with self.assertRaises(ValueError):f.step(r,3)
        self.assertEqual(f.c.latest(),r)
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(r)
            out=j.prune(r,allow_synthetic_prune=True)
            self.assertEqual(out["backup_count"],2)
            with self.assertRaises(ValueError):j.prune(r,allow_synthetic_prune=True)
        self.assertFalse(f.copy(1).exists());self.assertEqual(f.copy(2).read_bytes(),second)
        s,out=f.step(r,3);self.assertEqual(s.sequence,4);self.assertTrue(out["rotation_required"])
        self.assertEqual(f.db.total_changes,0)
    def test_no_prune_with_stale_pin_or_corrupt_latest(self):
        f=self.f;p,_=f.boot();q,_=f.step(p);r,_=f.step(q,2)
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(q,allow_synthetic_prune=True)
        raw=f.copy(3).read_bytes();f.copy(3).write_bytes(raw[:-1])
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(r,allow_synthetic_prune=True)
        self.assertTrue(f.copy(1).exists());self.assertTrue(f.copy(2).exists())
    def test_prune_failed_unlink_no_copy_removed(self):
        f=self.f;r,_=self.three()
        with self.store() as j:
            with patch.object(m.os,"unlink",side_effect=OSError("fixture")):
                with self.assertRaises(OSError):j.prune(r,allow_synthetic_prune=True)
            with self.assertRaises(ValueError):j.status(r)
        self.assertTrue(all(f.copy(i).exists() for i in (1,2,3)))
        self.assertEqual(f.c.latest(),r)
    def test_pending_third_publication_cannot_prune(self):
        f=self.f;p,_=f.boot();q,_=f.step(p)
        with patch.object(f.c,"finalize",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):f.step(q,2)
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(f.c.latest(),allow_synthetic_prune=True)
        self.assertTrue(all(f.copy(i).exists() for i in (1,2,3)))
    def test_foreign_or_unexpected_sequence_denies(self):
        f=self.f;r,_=self.three()
        f.copy(1).rename(f.copy(9))
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(r,allow_synthetic_prune=True)
        self.assertTrue(f.copy(9).exists())
    def test_no_prune_with_two_copies(self):
        f=self.f;p,_=f.boot();q,_=f.step(p)
        with self.store() as j:
            with self.assertRaises(ValueError):j.prune(q,allow_synthetic_prune=True)
        self.assertTrue(f.copy(1).exists());self.assertTrue(f.copy(2).exists())
