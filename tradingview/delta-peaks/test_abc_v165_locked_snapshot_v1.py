"""REMURA v0.8.158 LAB — 18/11/2026, 13:29 CET. Disposable fixtures only."""
import fcntl
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from abc_v165_locked_snapshot_v1 import _locked_snapshot, locked_candidate_bytes, MARKER

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "work"
        self.stage = self.root / "stage"
        for p in (self.work, self.stage):
            p.mkdir(mode=0o700)
        self.data = b"disposable candidate"
        self.tar = self.stage / "remura-v165-candidate.tar"
        for p, content in ((self.work / "lock", b""), (self.work / MARKER, b"inhibit"), (self.tar, self.data)):
            p.write_bytes(content)
            p.chmod(0o600)
        self.anchor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.anchor)
        self.uid = os.getuid()
        self.digest = hashlib.sha256(self.data).hexdigest()

    def snapshot(self):
        return _locked_snapshot(self.anchor, ["work"], ["stage"], self.uid, len(self.data), self.digest)

    def denied(self):
        with self.assertRaises((OSError, ValueError)):
            with self.snapshot():
                self.fail("unsafe snapshot admitted")

    def test_lock_held_and_released(self):
        with open(self.work / "lock", "rb+") as other:
            with self.snapshot() as data:
                self.assertEqual(data, self.data)
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_existing_busy_lock(self):
        with open(self.work / "lock", "rb+") as other:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.denied()

    def test_missing_lock_never_recreated(self):
        (self.work / "lock").unlink()
        self.denied()
        self.assertFalse((self.work / "lock").exists())

    def test_missing_marker(self):
        (self.work / MARKER).unlink()
        self.denied()

    def test_changed_bytes_same_length(self):
        self.tar.write_bytes(b"x" * len(self.data))
        self.denied()

    def test_symlink_bundle(self):
        self.tar.rename(self.stage / "other")
        self.tar.symlink_to("other")
        self.denied()

    def test_hardlink_bundle(self):
        os.link(self.tar, self.stage / "other")
        self.denied()

    def test_writable_stage(self):
        self.stage.chmod(0o770)
        self.denied()

    def test_untrusted_ancestor(self):
        self.root.chmod(0o777)
        self.denied()

    def test_symlink_stage(self):
        self.stage.rename(self.root / "real_stage")
        self.stage.symlink_to("real_stage", target_is_directory=True)
        self.denied()

    def test_public_pin_cannot_accept_fixture(self):
        with self.assertRaises(ValueError):
            with locked_candidate_bytes(self.anchor, ["work"], ["stage"], self.uid):
                self.fail("fixture accepted as release")

if __name__ == "__main__":
    unittest.main()
