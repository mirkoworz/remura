# REMURA v0.8.101 LAB — 16/11/2026 14:57 CET
import hashlib,json,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_backup_v1 as b
import cvd_joint_encrypted_v1 as m
from cvd_joint_recovery_v1 import restore
from cvd_runtime_singleflight_v1 import NAME as LOCK,single_flight
from cvd_runtime_private_state_v1 import PERIOD,DELAY,encoded
from cvd_incremental_preview_v1 import RollingPreview,repage
from cvd_private_runtime_preview_v1 import plan
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import mock_audit
G="e"*32;KEY=b"\x57"*32
class BackupTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.source=Path(t.name)/"source";self.dest=Path(t.name)/"backup"
        for root in (self.source,self.dest):
            root.mkdir(mode=0o700);(root/LOCK).touch(mode=0o600)
        self.path=self.source/m.NAME;self.c=m.EncryptedCustody(G,synthetic=True)
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        p=types.ModuleType("scripts");p.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([]))
        ctx=patch.dict(sys.modules,{"scripts":p});ctx.start();self.addCleanup(ctx.stop)
        self.now=T0+DELAY;self.rows=[x for x,_,_ in triples(18,events=(0,14))]
    def store(self):
        return m.open_encrypted_joint(self.source,self.c,generation=G,key=KEY,synthetic=True)
    def full(self,at):return repage(plan(at),self.rows)
    def boot(self):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full(self.now),cycles=4)
    def step(self,p,i):
        at=self.now+i*PERIOD;old=RollingPreview(now=at-PERIOD,windows=self.full(at-PERIOD),synthetic=True)
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=at,windows=repage(old.next_ranges(at),self.rows))
    def copy(self,p,**kw):
        args=dict(generation=G,key=KEY,expected=p,synthetic=True);args.update(kw)
        return b.backup(self.source,self.dest,self.c,**args)
    def test_backup_restore_resume_from_actual_copy(self):
        p,_=self.boot();q,expected=self.step(p,1)
        out=self.copy(q);file=self.dest/out["name"];raw=file.read_bytes()
        self.assertEqual(raw,self.path.read_bytes())
        self.assertEqual(out["ciphertext_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(set(json.loads(raw)),{"v","nonce","ct","tag"})
        self.assertFalse(out["independent_failure_domain_verified"])
        self.path.unlink()
        result=restore(self.source,self.c,generation=G,key=KEY,expected=q,backup=file.read_bytes(),synthetic=True)
        self.assertEqual(result["sequence"],2)
        with self.store() as s:self.assertEqual(s.status(q),expected)
        nextp,_=self.step(q,2)
        self.assertEqual(nextp.sequence,3);self.assertEqual(self.db.total_changes,0)
    def test_two_copy_cap_and_no_overwrite(self):
        p,_=self.boot();one=self.copy(p);old=(self.dest/one["name"]).read_bytes()
        with self.assertRaises(ValueError):self.copy(p)
        q,_=self.step(p,1);two=self.copy(q)
        later,_=self.step(q,2)
        with self.assertRaises(ValueError):self.copy(later)
        self.assertEqual((self.dest/one["name"]).read_bytes(),old)
        self.assertEqual({x.name for x in self.dest.iterdir()},{LOCK,one["name"],two["name"]})
    def test_wrong_key_old_pin_and_tampered_source_no_write(self):
        p,_=self.boot();q,_=self.step(p,1)
        for pin,kw in ((p,{}),(q,{"key":b"\x12"*32}),(q,{"synthetic":False})):
            with self.assertRaises(ValueError):self.copy(pin,**kw)
            self.assertEqual({x.name for x in self.dest.iterdir()},{LOCK})
        e=json.loads(self.path.read_bytes());e["tag"]=("0" if e["tag"][0]!="0" else "1")+e["tag"][1:]
        self.path.write_bytes(encoded(e))
        with self.assertRaises(ValueError):self.copy(q)
        self.assertEqual({x.name for x in self.dest.iterdir()},{LOCK})
    def test_destination_identity_and_lock(self):
        p,_=self.boot()
        with self.assertRaises(ValueError):b.backup(self.source,self.source,self.c,generation=G,key=KEY,expected=p,synthetic=True)
        with single_flight(self.dest):
            with self.assertRaises(ValueError):self.copy(p)
        self.dest.chmod(0o755)
        with self.assertRaises(ValueError):self.copy(p)
        self.dest.chmod(0o700)
        self.assertEqual({x.name for x in self.dest.iterdir()},{LOCK})
    def test_unexpected_orphan_or_symlink_denies(self):
        p,_=self.boot();extra=self.dest/(b.PREFIX+"test");extra.touch()
        with self.assertRaises(ValueError):self.copy(p)
        extra.unlink()
        fake=self.dest/f"remura-d-backup-synthetic-{G}-002.json";fake.symlink_to(self.path)
        with self.assertRaises(ValueError):self.copy(p)
        self.assertTrue(fake.is_symlink())
    def test_failed_link_leaves_ciphertext_only_blocks_future(self):
        p,_=self.boot();raw=self.path.read_bytes()
        with patch.object(b.os,"link",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):self.copy(p)
        files=list(self.dest.glob(b.PREFIX+"*"));self.assertEqual(len(files),1)
        self.assertEqual(files[0].read_bytes(),raw)
        with self.assertRaises(ValueError):self.copy(p)
        self.assertEqual(self.path.read_bytes(),raw)
    def test_pending_pin_never_copied(self):
        p,_=self.boot();pending=self.c.reserve(p,self.now+PERIOD)
        with self.assertRaises(ValueError):self.copy(pending)
        self.assertEqual({x.name for x in self.dest.iterdir()},{LOCK})
