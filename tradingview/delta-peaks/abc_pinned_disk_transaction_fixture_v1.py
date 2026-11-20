# REMURA v0.8.163 LAB — 18/11/2026, sessione successiva alle 13:37 CET
"""Actual pinned 90 path candidate on disposable disk; no service or private data."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from abc_rollback_disk_lab_v1 import Journal
from abc_v165_stage_bundle_v1 import descriptor
from abc_v165_transaction_plan_v1 import prepare_plan
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
        cls.desc=descriptor(cls.manifest)
        cls.full={**cls.base,**cls.candidate}
        cls.old,planned=prepare_plan(cls.desc,cls.full,cls.base)
        assert planned==cls.candidate
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
        self.wtmp=tempfile.TemporaryDirectory(prefix="remura-witness-lab-")
        self.addCleanup(self.wtmp.cleanup)
        self.wroot=Path(self.wtmp.name).resolve()
        self.j=self.reopen()
    def reopen(self):
        return Journal(self.root,synthetic=True,auth_key=self.key,transaction_id=self.transaction,witness_root=self.wroot)
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
            Journal(self.root,synthetic=True,auth_key=os.urandom(32),transaction_id=self.transaction,witness_root=self.wroot).apply()
        with self.assertRaises(ValueError):
            Journal(self.root,synthetic=True,auth_key=self.key,transaction_id=os.urandom(32).hex(),witness_root=self.wroot).apply()
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
    def test_replay_after_terminal_rollback_and_witness_downgrade(self):
        self.j.prepare(self.old,self.candidate)
        old=self.j.path.read_bytes()
        with self.assertRaises(ValueError):
            Journal(self.root,synthetic=True,auth_key=self.key,transaction_id=self.transaction).apply()
        self.j.apply()
        self.j.rollback()
        self.j.path.write_bytes(old)
        with self.assertRaises(ValueError): self.reopen().apply()
        with self.assertRaises(ValueError): self.reopen().rollback()
        self.verify(self.base)

    def test_interrupted_apply_cannot_be_restarted(self):
        self.j.prepare(self.old,self.candidate)
        pid=os.fork()
        if pid==0:
            try:self.reopen().apply(crash_after=0)
            except BaseException:os._exit(76)
            os._exit(77)
        _,status=os.waitpid(pid,0)
        self.assertEqual(os.waitstatus_to_exitcode(status),75)
        with self.assertRaises(ValueError): self.reopen().apply()
        self.assertEqual(self.reopen().rollback(),"rolled_back")
        self.verify(self.base)

    def test_witness_missing_or_changed_fails_closed(self):
        self.j.prepare(self.old,self.candidate)
        witness=self.wroot/"phase.json"
        original=witness.read_bytes()
        witness.unlink()
        with self.assertRaises((OSError,ValueError)):self.reopen().apply()
        witness.write_bytes(original);witness.chmod(0o600)
        env=json.loads(original)
        env["payload"]["phase"]="applying"
        witness.write_text(json.dumps(env))
        with self.assertRaises(ValueError):self.reopen().rollback()
        self.verify(self.base)
    def test_exact_plan_rejects_incomplete_baseline_and_drift(self):
        for path in (next(iter(self.old)),next(p for p in self.base if p not in self.candidate)):
            missing=dict(self.base);missing.pop(path)
            with self.assertRaises(ValueError):prepare_plan(self.desc,self.full,missing)
            altered=dict(self.base);altered[path]+=b"x"
            with self.assertRaises(ValueError):prepare_plan(self.desc,self.full,altered)
        added=next(p for p in self.candidate if p not in self.base)
        occupied={**self.base,added:b"existing"}
        with self.assertRaises(ValueError):prepare_plan(self.desc,self.full,occupied)
        tampered={**self.full,added:self.full[added]+b"x"}
        with self.assertRaises(ValueError):prepare_plan(self.desc,tampered,self.base)

    def test_actual_old_stamp_is_preserved_in_rollback_bytes(self):
        from abc_v165_transaction_plan_v1 import STAMP
        base=dict(self.base)
        self.assertEqual(base["nav.js"].count(STAMP),1)
        base["nav.js"]=base["nav.js"].replace(STAMP,b"18/11/2026 13:37 (Italia)",1)
        path=self.app/"nav.js";path.write_bytes(base["nav.js"])
        old,new=prepare_plan(self.desc,self.full,base)
        self.assertEqual(old["nav.js"],base["nav.js"])
        self.j.prepare(old,new)
        self.j.apply()
        self.j.rollback()
        self.verify(base)
if __name__=="__main__":unittest.main()
