# REMURA v0.8.174 LAB — 18/11/2026
import tempfile,unittest
from pathlib import Path
from abc_rollback_disk_lab_v1 import Journal,atomic,unpack
from abc_v165_phase_state_lab_v1 import inspect

class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-journal-lab-")
        self.w=tempfile.TemporaryDirectory(prefix="remura-witness-lab-")
        self.addCleanup(self.tmp.cleanup);self.addCleanup(self.w.cleanup)
        root=Path(self.tmp.name).resolve()
        (root/"app"/"scripts").mkdir(parents=True)
        self.j=Journal(root,synthetic=True,auth_key=b"x"*32,transaction_id="a"*64,
                       witness_root=Path(self.w.name).resolve())
        self.a=root/"app"/"scripts"/"a.py"
        self.a.write_bytes(b"before");self.a.chmod(0o640)
        self.j.prepare({"scripts/a.py":b"before"},{"scripts/a.py":b"after","nav.js":b"new"})
    def state(self):
        with self.j.lock():return inspect(self.j,synthetic=True)
    def test_unknown_and_mismatch(self):
        self.a.write_bytes(b"unknown")
        r=self.state()
        self.assertEqual(r["status"],"STOP_UNKNOWN_FILE_STATE")
        self.assertEqual(r["counts"]["unknown"],1)
        self.assertFalse(r["restore_authorized"])
        self.a.write_bytes(b"after")
        self.assertEqual(self.state()["status"],"STOP_PHASE_FILE_MISMATCH")
    def test_interrupted_and_read_only(self):
        with self.j.lock():
            d=self.j.read_doc()
            self.j.witness_write(d,"applying")
            row=d["rows"][0]
            b,mode=unpack(row["after"])
            atomic(self.j.target(row["path"]),b,mode)
        before=(self.j.path.read_bytes(),self.j.witness.read_bytes())
        r=self.state()
        self.assertEqual(r["status"],"INTERRUPTED_PHASE_REVIEW_REQUIRED")
        self.assertEqual(r["counts"],dict(before=1,after=1,unknown=0))
        self.assertEqual(before,(self.j.path.read_bytes(),self.j.witness.read_bytes()))
    def test_reject_untrusted_witness(self):
        self.j.witness.write_bytes(b"{}")
        with self.assertRaises(ValueError):self.state()
        with self.assertRaises(ValueError):inspect(self.j)
if __name__=="__main__":unittest.main()
