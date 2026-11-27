# REMURA Contributors v0.54 LAB — synthetic POSIX filesystem only
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from fixture_durable_claim_lab import claim, MARKER, RECORD

class DurableClaim(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
    def child(self, path):
        return subprocess.Popen([sys.executable, "-B", "-c",
            "import sys; from fixture_durable_claim_lab import claim; claim(sys.argv[1])", str(path)],
            cwd=Path(__file__).resolve().parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def test_claim_and_restart(self):
        self.assertEqual(claim(self.root)["authorization_granted"],False)
        self.assertEqual((self.root/MARKER).read_bytes(),RECORD)
        self.assertEqual((self.root/MARKER).stat().st_mode & 0o777,0o600)
        self.assertNotEqual(self.child(self.root).wait(timeout=10),0)
    def test_concurrent_processes(self):
        children=[self.child(self.root) for _ in range(8)]
        self.assertEqual(sum(c.wait(timeout=10)==0 for c in children),1)
    def test_partial_marker_blocks(self):
        (self.root/MARKER).touch()
        with self.assertRaises(FileExistsError):claim(self.root)
    def test_wrong_marker_blocks(self):
        (self.root/MARKER).write_text("incomplete")
        with self.assertRaises(FileExistsError):claim(self.root)
    def test_symlink_marker_blocks(self):
        target=self.root/"target"
        target.write_text("unchanged")
        (self.root/MARKER).symlink_to(target)
        with self.assertRaises(FileExistsError):claim(self.root)
        self.assertEqual(target.read_text(),"unchanged")
    def test_directory_alias_blocks(self):
        d=self.root/"dir";d.mkdir(mode=0o700)
        link=self.root/"alias";link.symlink_to(d,target_is_directory=True)
        with self.assertRaises(RuntimeError):claim(link)
    def test_insecure_directory_blocks(self):
        self.root.chmod(0o755)
        with self.assertRaises(RuntimeError):claim(self.root)
    def test_relative_path_blocks(self):
        with self.assertRaises(RuntimeError):claim(Path("."))
    def test_directory_fsync_failure_leaves_claim(self):
        from unittest.mock import patch
        real=os.fsync
        calls=0
        def fail_second(fd):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError("synthetic fsync failure")
            return real(fd)
        with patch("fixture_durable_claim_lab.os.fsync",side_effect=fail_second):
            with self.assertRaises(OSError):claim(self.root)
        with self.assertRaises(FileExistsError):claim(self.root)
    def test_write_failure_leaves_claim(self):
        from unittest.mock import patch
        with patch("fixture_durable_claim_lab.os.write",return_value=0):
            with self.assertRaises(RuntimeError):claim(self.root)
        with self.assertRaises(FileExistsError):claim(self.root)
