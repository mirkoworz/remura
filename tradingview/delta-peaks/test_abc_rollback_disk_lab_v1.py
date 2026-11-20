# REMURA v0.8.142 LAB — 18/11/2026
import json,os,stat,tempfile,unittest
from pathlib import Path
from abc_rollback_disk_lab_v1 import Journal

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-journal-lab-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.app=self.root/"app";(self.app/"scripts").mkdir(parents=True)
        self.a=self.app/"scripts/a.py";self.a.write_bytes(b"old")
        self.a.chmod(0o640)
        self.b=self.app/"nav.js"
        self.j=Journal(self.root,synthetic=True)
        self.old={"scripts/a.py":b"old"}
        self.new={"scripts/a.py":b"new","nav.js":b"asset"}
    def prepare(self):self.j.prepare(self.old,self.new)
    def original(self):
        self.assertEqual(self.a.read_bytes(),b"old")
        self.assertEqual(stat.S_IMODE(self.a.stat().st_mode),0o640)
        self.assertFalse(self.b.exists())
    def crash(self,method,n):
        pid=os.fork()
        if pid==0:
            try:getattr(Journal(self.root,synthetic=True),method)(crash_after=n)
            except BaseException:os._exit(76)
            os._exit(77)
        _,status=os.waitpid(pid,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),75)
    def test_success_and_idempotent_rollback(self):
        self.prepare();self.j.apply()
        self.assertEqual(self.a.read_bytes(),b"new");self.assertEqual(self.b.read_bytes(),b"asset")
        self.assertEqual(self.j.rollback(),"rolled_back");self.original()
        self.assertEqual(self.j.rollback(),"already_rolled_back")
    def test_crash_before_first_write(self):
        self.prepare();self.crash("apply",0)
        Journal(self.root,synthetic=True).rollback();self.original()
    def test_crash_between_writes(self):
        self.prepare();self.crash("apply",1)
        self.assertTrue(self.b.exists());self.assertEqual(self.a.read_bytes(),b"old")
        Journal(self.root,synthetic=True).rollback();self.original()
    def test_crash_after_last_write(self):
        self.prepare();self.crash("apply",2)
        Journal(self.root,synthetic=True).rollback();self.original()
    def test_crash_during_rollback(self):
        self.prepare();self.j.apply();self.crash("rollback",1)
        self.assertEqual(self.a.read_bytes(),b"old");self.assertTrue(self.b.exists())
        Journal(self.root,synthetic=True).rollback();self.original()
    def test_conflict_prevents_all_rollback_writes(self):
        self.prepare();self.j.apply();self.a.write_bytes(b"external")
        with self.assertRaises(ValueError):self.j.rollback()
        self.assertEqual(self.b.read_bytes(),b"asset")
        self.assertEqual(self.a.read_bytes(),b"external")
    def test_tamper_and_symlink_and_scope(self):
        self.prepare()
        data=json.loads(self.j.path.read_bytes());data["payload"]["phase"]="applied"
        self.j.path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.j.apply()
        self.original()
        self.j.path.unlink();self.b.symlink_to(self.a)
        with self.assertRaises(ValueError):self.prepare()
        with self.assertRaises(ValueError):Journal(self.root)
    def test_wrong_baseline_and_reused_journal(self):
        with self.assertRaises(ValueError):self.j.prepare({"scripts/a.py":b"wrong"},self.new)
        self.assertFalse(self.j.path.exists());self.original()
        self.prepare()
        with self.assertRaises(ValueError):self.prepare()
