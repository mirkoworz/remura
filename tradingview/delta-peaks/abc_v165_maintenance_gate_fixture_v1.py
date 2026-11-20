# REMURA v0.8.145 LAB — 18/11/2026
import fcntl,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from abc_v165_maintenance_gate_v1 import build_candidate,create_inhibit_lab,MARKER
from abc_integration_runner_lab_v1 import HERE,CHECKOUTS,SOURCES
from abc_overlay_transaction_fixture_v1 import exact

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=HERE.parents[1]/CHECKOUTS["main"]
        cls.raw=exact(root,SOURCES["main"],"deploy/oracle/autoupdate.py")
        cls.candidate=build_candidate(cls.raw)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-inhibit-lab-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.lock=self.root/"lock";self.lock.touch(mode=0o600)
        self.ns={"__name__":"candidate_offline"}
        exec(compile(self.candidate,"candidate_offline","exec"),self.ns)
        self.ns["WORK"]=self.root
        self.calls=[]
        self.ns["load_state"]=lambda:self.calls.append("load") or {"enabled":False}
        self.ns["save_state"]=lambda x:self.calls.append("save")
        self.ns["remote_sha"]=lambda: self.fail("network forbidden")
        self.rootpatch=patch.object(os,"geteuid",return_value=0)
        self.rootpatch.start();self.addCleanup(self.rootpatch.stop)
    def test_original_behavior_when_no_marker(self):
        self.assertEqual(self.ns["check_once"](),0)
        self.assertEqual(self.calls,["load"])
        self.ns["initialize_state"]("a"*40)
        self.assertEqual(self.calls,["load","save"])
    def test_marker_persists_after_creator_exit(self):
        pid=os.fork()
        if pid==0:
            try:create_inhibit_lab(self.root,"a"*64,synthetic=True)
            except BaseException:os._exit(76)
            os._exit(75)
        _,status=os.waitpid(pid,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),75)
        self.assertTrue((self.root/MARKER).is_file())
        self.assertEqual(self.ns["check_once"](),0)
        with self.assertRaises(RuntimeError):self.ns["initialize_state"]("a"*40)
        self.assertEqual(self.calls,[])
        with self.assertRaises(FileExistsError):create_inhibit_lab(self.root,"b"*64,synthetic=True)
    def test_empty_or_dangling_marker_blocks(self):
        marker=self.root/MARKER
        marker.touch()
        self.assertEqual(self.ns["check_once"](),0)
        marker.unlink();marker.symlink_to(self.root/"missing")
        self.assertEqual(self.ns["check_once"](),0)
        self.assertEqual(self.calls,[])
    def test_shared_lock_busy_and_unsafe(self):
        with self.lock.open("rb") as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.ns["check_once"](),0)
            with self.assertRaises(BlockingIOError):self.ns["initialize_state"]("a"*40)
            with self.assertRaises(BlockingIOError):create_inhibit_lab(self.root,"a"*64,synthetic=True)
        self.assertEqual(self.calls,[])
        self.lock.unlink();self.lock.symlink_to(self.root/"missing")
        with self.assertRaises(OSError):self.ns["check_once"]()
    def test_source_pin_and_scope(self):
        with self.assertRaises(ValueError):build_candidate(self.raw+b"\n")
        with self.assertRaises(ValueError):create_inhibit_lab(self.root,"a"*64)
if __name__=="__main__":unittest.main()
