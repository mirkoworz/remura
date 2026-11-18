# REMURA v0.8.146 LAB — 18/11/2026
import os,tempfile,unittest
from pathlib import Path
from abc_v165_start_guard_v1 import evaluate,MARKERS
class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-start-guard-")
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.uid=os.getuid()
    def check(self,c,u):
        self.assertEqual(evaluate(self.work,"collector",self.uid),c)
        self.assertEqual(evaluate(self.work,"updater",self.uid),u)
    def test_separate_release_gates(self):
        self.check(0,0)
        u=self.work/MARKERS["updater"];c=self.work/MARKERS["collector"]
        u.touch();c.touch();self.check(1,1)
        c.unlink();self.check(0,1)
        u.unlink();self.check(0,0)
    def test_persistent_markers_after_process_exit(self):
        pid=os.fork()
        if pid==0:
            try:
                for name in MARKERS.values():
                    fd=os.open(self.work/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    os.fsync(fd);os.close(fd)
                fd=os.open(self.work,os.O_RDONLY|os.O_DIRECTORY)
                os.fsync(fd);os.close(fd);os._exit(75)
            except BaseException:os._exit(76)
        _,status=os.waitpid(pid,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),75)
        self.check(1,1)
    def test_invalid_objects_do_not_bypass(self):
        p=self.work/MARKERS["collector"]
        p.symlink_to(self.work/"missing");self.check(1,0)
        p.unlink();p.mkdir();self.check(1,0)
    def test_unsafe_directory_or_role(self):
        self.work.chmod(0o755);self.check(255,255)
        self.work.chmod(0o700)
        self.assertEqual(evaluate(self.work,"collector",self.uid+1),255)
        self.assertEqual(evaluate(self.work/"missing","collector",self.uid),255)
        self.assertEqual(evaluate(self.work,"wrong",self.uid),255)
    def test_dropin_candidates_exact(self):
        here=Path(__file__).resolve().parent
        for role in MARKERS:
            p=here/("v165-"+role+"-maintenance.conf.txt")
            lines=[x for x in p.read_text().splitlines() if x and not x.startswith("#")]
            self.assertEqual(lines,["[Service]","ExecCondition=+/usr/bin/python3 -I -B /var/lib/remura-autoupdate/v165-start-guard.py "+role])
