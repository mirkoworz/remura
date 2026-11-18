# REMURA v0.8.159 LAB — 18/11/2026, sessione successiva alle 13:29 CET
"""Actual pinned 90 path candidate on disposable disk; no service or private data."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from abc_rollback_disk_lab_v1 import Journal
import abc_v165_overlay_manifest_fixture_v1 as overlay
import abc_v165_repository_manifest_fixture_v1 as repository
from abc_v165_repository_manifest_lab_v1 import build

PIN="73635db92dd9f709ae078119a161ab12b7c9a63ca18782b99e7e1f6357c3c2c1"
def digest(b):return hashlib.sha256(b).hexdigest()
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repository.Tests.setUpClass()
        cls.base=repository.Tests.base
        cls.candidate=repository.Tests.overlay
        cls.manifest=build(cls.base,cls.candidate,repository.Tests.deploy,synthetic=True)
        assert cls.manifest["manifest_sha256"]==PIN
        cls.old={p:cls.base[p] for p in cls.candidate if p in cls.base}
        assert len(cls.candidate)==90 and len(cls.old)==14 and len(cls.base)==79
        assert all(digest({**cls.base,**cls.candidate}[r["path"]])==r["candidate_sha256"] for r in cls.manifest["application"])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-journal-lab-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.app=self.root/"app"
        (self.app/"scripts").mkdir(parents=True)
        for p,b in self.base.items():
            f=self.app/p;f.write_bytes(b);f.chmod(0o640)
        self.key=os.urandom(32)
        self.transaction=os.urandom(32).hex()
        self.j=self.reopen()
    def reopen(self):
        return Journal(self.root,synthetic=True,auth_key=self.key,transaction_id=self.transaction)
    def verify(self,expected):
        actual={p.relative_to(self.app).as_posix():p.read_bytes() for p in self.app.rglob("*") if p.is_file()}
        self.assertEqual(actual,expected)
        for p in expected:
            self.assertEqual((self.app/p).stat().st_mode&0o777,0o640 if p in self.base else 0o644)
    def test_exact_manifest_disk_apply_and_rollback(self):
        self.j.prepare(self.old,self.candidate);self.j.apply()
        self.verify({**self.base,**self.candidate})
        self.assertEqual(self.j.rollback(),"rolled_back")
        self.verify(self.base)
    def test_actual_overlay_crash_reopen(self):
        self.j.prepare(self.old,self.candidate)
        pid=os.fork()
        if pid==0:
            try:self.reopen().apply(crash_after=45)
            except BaseException:os._exit(76)
            os._exit(77)
        _,status=os.waitpid(pid,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),75)
        self.assertEqual(self.reopen().rollback(),"rolled_back")
        self.verify(self.base)
    def test_authentication_rejects_tamper_wrong_key_and_downgrade(self):
        self.j.prepare(self.old,self.candidate)
        raw=self.j.path.read_bytes()
        with self.assertRaises(ValueError):
            Journal(self.root,synthetic=True,auth_key=os.urandom(32),transaction_id=self.transaction).apply()
        with self.assertRaises(ValueError):
            Journal(self.root,synthetic=True,auth_key=self.key,transaction_id=os.urandom(32).hex()).apply()
        with self.assertRaises(ValueError):
            Journal(self.root,synthetic=True).apply()
        envelope=json.loads(raw)
        envelope["body"]["payload"]["rows"][0]["after"]["mode"]=0o777
        self.j.path.write_text(json.dumps(envelope))
        with self.assertRaises(ValueError): self.reopen().apply()
        self.verify(self.base)
        self.j.path.write_bytes(raw)
        self.assertEqual(self.reopen().rollback(),"rolled_back")
        self.verify(self.base)
if __name__=="__main__":unittest.main()
