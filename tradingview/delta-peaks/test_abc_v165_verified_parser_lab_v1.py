# REMURA v0.8.168 LAB — 18/11/2026, after 16:21 CET.
import os
from pathlib import Path
import sys
import tempfile
import unittest
from abc_v165_bootstrap_source_gate_v1 import PINS
from abc_v165_verified_parser_lab_v1 import verified_parser, ORDER

class VerifiedParserTests(unittest.TestCase):
    def setUp(self):
        root=tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root=Path(root.name)
        self.sources=self.root/"sources"
        self.sources.mkdir(mode=0o700)
        for name in PINS:
            f=self.sources/name
            f.write_bytes(Path(__file__).with_name(name).read_bytes())
            f.chmod(0o400)
        self.fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        self.addCleanup(os.close,self.fd)
    def parser(self,**kw):
        return verified_parser(self.fd,("sources",),os.getuid(),**kw)
    def test_explicit_lab_only(self):
        with self.assertRaises(ValueError):self.parser()
    def test_snapshot_and_no_import_registration(self):
        before={name:sys.modules.get(name) for name in ORDER}
        parser=self.parser(synthetic=True)
        self.assertEqual(before,{name:sys.modules.get(name) for name in ORDER})
        self.assertEqual(parser.__name__,"inspect_bundle_bytes")
        for name in PINS:(self.sources/name).unlink()
        with self.assertRaises(ValueError):parser(b"bad candidate")
    def test_modified_source_rejected_before_execution(self):
        f=self.sources/next(iter(PINS))
        f.chmod(0o600)
        raw=f.read_bytes()
        f.write_bytes(bytes([raw[0]^1])+raw[1:])
        with self.assertRaises(ValueError):self.parser(synthetic=True)
    def test_extra_module_rejected(self):
        (self.sources/"hashlib.py").write_text("raise RuntimeError()")
        with self.assertRaises(ValueError):self.parser(synthetic=True)
if __name__=="__main__":unittest.main()
