# REMURA v0.8.165 LAB — 18/11/2026
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import abc_v165_bootstrap_provision_candidate_v1 as provision
from abc_v165_bootstrap_source_gate_v1 import verify_sources

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        self.addCleanup(os.close,self.fd)
        self.uid=os.getuid()

    def test_actual_code_copy_and_readonly_gate(self):
        provision.publish(self.fd,self.uid)
        actual=verify_sources(self.fd,[provision.DEST,"sources"],self.uid)
        self.assertEqual(actual,provision.source_bytes())
        for name,b in actual.items():
            self.assertEqual(b,(Path(__file__).parent/name).read_bytes())
        self.assertEqual((self.root/provision.DEST/"CODE_ONLY").read_text(),
                         "CODE_ONLY; INSTALL_AUTHORIZED=NO; EXECUTION_AUTHORIZED=NO\n")

    def test_no_overwrite(self):
        provision.publish(self.fd,self.uid)
        with self.assertRaises(FileExistsError):
            provision.publish(self.fd,self.uid)

    def test_symlink_destination(self):
        (self.root/provision.DEST).symlink_to(self.root)
        with self.assertRaises(FileExistsError):
            provision.publish(self.fd,self.uid)

    def test_writable_parent(self):
        self.root.chmod(0o777)
        with self.assertRaises(ValueError):
            provision.publish(self.fd,self.uid)
        self.assertFalse((self.root/provision.DEST).exists())

    def test_pin_drift_before_write(self):
        name=next(iter(provision.SOURCES))
        with patch.dict(provision.SOURCES,{name:"changed"}):
            with self.assertRaises(ValueError):
                provision.publish(self.fd,self.uid)
        self.assertFalse((self.root/provision.DEST).exists())

    def test_missing_arguments_never_publish(self):
        with patch.object(provision.sys,"argv",["candidate"]),patch.object(provision,"publish") as call:
            self.assertEqual(provision.main(),2)
            call.assert_not_called()
