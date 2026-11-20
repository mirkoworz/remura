"""REMURA v0.8.167 LAB — 18/11/2026, after 16:21 CET."""
import fcntl
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from abc_v165_dual_inhibit_boundary_v1 import _boundary, MARKERS

class DualBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.stage = self.root / "stage"
        for p in (self.work, self.stage):
            p.mkdir(mode=0o700)
        for name in ("lock", *MARKERS):
            self.put(self.work / name, b"")
        self.data = b"disposable fixture"
        self.put(self.stage / "remura-v165-candidate.tar", self.data)
        self.anchor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.anchor)
    def put(self, p, data):
        p.write_bytes(data)
        p.chmod(0o600)
    def boundary(self):
        return _boundary(self.anchor, ("work",), ("stage",), os.getuid(),
                         len(self.data), hashlib.sha256(self.data).hexdigest())
    def test_lock_and_exact_bytes(self):
        with self.boundary() as data:
            self.assertEqual(data, self.data)
            with open(self.work / "lock", "rb+") as f:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.boundary() as data:
            self.assertEqual(data, self.data)
    def test_each_marker_required(self):
        for name in MARKERS:
            p = self.work / name
            p.unlink()
            with self.assertRaises(OSError):
                with self.boundary(): self.fail("yield")
            self.put(p, b"")
    def test_marker_symlink_rejected(self):
        p = self.work / MARKERS[1]
        p.unlink()
        p.symlink_to(self.work / MARKERS[0])
        with self.assertRaises(ValueError):
            with self.boundary(): self.fail("yield")
    def test_marker_mutation_detected_at_exit(self):
        with self.assertRaises(ValueError):
            with self.boundary():
                self.put(self.work / MARKERS[1], b"changed")
    def test_lock_replacement_detected_at_exit(self):
        with self.assertRaises(ValueError):
            with self.boundary():
                (self.work / "lock").rename(self.work / "old-lock")
                self.put(self.work / "lock", b"")
    def test_bad_candidate(self):
        self.put(self.stage / "remura-v165-candidate.tar", b"x" * len(self.data))
        with self.assertRaises(ValueError):
            with self.boundary(): self.fail("yield")
    def test_missing_lock_not_created(self):
        (self.work / "lock").unlink()
        with self.assertRaises(OSError):
            with self.boundary(): self.fail("yield")
        self.assertFalse((self.work / "lock").exists())

if __name__ == "__main__":
    unittest.main()
