# REMURA v0.8.162 LAB — 18/11/2026
import os
from pathlib import Path
import tempfile
import unittest
from abc_v165_bootstrap_source_gate_v1 import PINS,verify_sources

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.stage=self.root/"review"
        self.stage.mkdir(mode=0o700)
        self.actual={n:(Path(__file__).resolve().parent/n).read_bytes() for n in PINS}
        for n,b in self.actual.items():
            f=self.stage/n;f.write_bytes(b);f.chmod(0o600)
        self.fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        self.addCleanup(os.close,self.fd)
        self.first=self.stage/next(iter(PINS))

    def verify(self):
        return verify_sources(self.fd,["review"],os.getuid())

    def deny(self):
        with self.assertRaises((OSError,ValueError)):
            self.verify()

    def test_exact_repository_sources(self):
        self.assertEqual(self.verify(),self.actual)

    def test_extra_module(self):
        (self.stage/"hashlib.py").write_text("unexpected")
        self.deny()

    def test_changed_same_size_source(self):
        b=self.first.read_bytes()
        self.first.write_bytes(bytes([b[0]^1])+b[1:])
        self.deny()

    def test_symlink_source(self):
        dest=self.root/"copy"
        self.first.rename(dest)
        self.first.symlink_to(dest)
        self.deny()

    def test_hardlink_source(self):
        os.link(self.first,self.root/"copy")
        self.deny()

    def test_writable_source(self):
        self.first.chmod(0o666)
        self.deny()

    def test_writable_directory(self):
        self.stage.chmod(0o777)
        self.deny()

    def test_symlink_directory(self):
        dest=self.root/"other"
        self.stage.rename(dest)
        self.stage.symlink_to(dest,target_is_directory=True)
        self.deny()

    def test_traversal(self):
        with self.assertRaises(ValueError):
            verify_sources(self.fd,["review",".."],os.getuid())

    def test_missing_file(self):
        self.first.unlink()
        self.deny()
