# REMURA v0.8.102 LAB — 16/11/2026 14:59 CET
import sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_backed_publication_v1 as m
from cvd_joint_encrypted_v1 import NAME,EncryptedCustody
from cvd_joint_backup_v1 import PREFIX
from cvd_joint_recovery_v1 import restore
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import PERIOD,DELAY
from cvd_incremental_preview_v1 import RollingPreview,repage
from cvd_private_runtime_preview_v1 import plan
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import mock_audit
G="f"*32;KEY=b"\x71"*32
class BackedPublicationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.src=Path(t.name)/"source";self.dest=Path(t.name)/"backup"
        for d in (self.src,self.dest):
            d.mkdir(mode=0o700);(d/LOCK).touch(mode=0o600)
        self.path=self.src/NAME;self.c=EncryptedCustody(G,synthetic=True)
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        p=types.ModuleType("scripts");p.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([]))
        ctx=patch.dict(sys.modules,{"scripts":p});ctx.start();self.addCleanup(ctx.stop)
        self.now=T0+DELAY;self.rows=[x for x,_,_ in triples(18,events=(0,14))]
    def store(self):return m.open_backed_joint(self.src,self.dest,self.c,generation=G,key=KEY,synthetic=True)
    def full(self,at):return repage(plan(at),self.rows)
    def copy(self,seq):return self.dest/f"remura-d-backup-synthetic-{G}-{seq:03d}.json"
    def boot(self):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full(self.now),cycles=4)
    def step(self,p,i=1):
        at=self.now+i*PERIOD;old=RollingPreview(now=at-PERIOD,windows=self.full(at-PERIOD),synthetic=True)
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=at,windows=repage(old.next_ranges(at),self.rows))
    def test_backup_before_every_finalize_and_capacity_before_reserve(self):
        original=self.c.finalize;seen=[]
        def finalize(p,out):
            self.assertEqual(self.c.latest().phase,"PENDING")
            self.assertEqual(self.copy(p.sequence).read_bytes(),self.path.read_bytes())
            seen.append(p.sequence)
            return original(p,out)
        with patch.object(self.c,"finalize",side_effect=finalize):
            p,_=self.boot();old=self.copy(1).read_bytes();q,out=self.step(p)
        self.assertEqual(seen,[1,2]);self.assertTrue(out["matching_local_backup"])
        self.assertEqual(self.copy(1).read_bytes(),old)
        with self.assertRaises(ValueError):self.step(q,2)
        self.assertEqual(self.c.latest(),q)
        with self.store() as s:self.assertEqual(s.status(q),out)
    def test_failed_copy_never_finalizes(self):
        p,_=self.boot();old=self.copy(1).read_bytes()
        with patch.object(m.os,"link",side_effect=OSError("backup copy failed")):
            with self.assertRaises(OSError):self.step(p)
        self.assertEqual(self.c.latest().phase,"PENDING")
        self.assertEqual(self.copy(1).read_bytes(),old)
        self.assertFalse(self.copy(2).exists())
        self.assertEqual(len(list(self.dest.glob(PREFIX+"*"))),1)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(p)
    def test_finalization_failure_after_both_copies_still_pending(self):
        p,_=self.boot()
        with patch.object(self.c,"finalize",side_effect=OSError("lost ack")):
            with self.assertRaises(OSError):self.step(p)
        self.assertEqual(self.c.latest().phase,"PENDING")
        self.assertEqual(self.copy(2).read_bytes(),self.path.read_bytes())
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(self.c.latest())
    def test_missing_or_corrupted_current_copy_denies_before_reservation(self):
        p,_=self.boot();raw=self.copy(1).read_bytes()
        self.copy(1).unlink()
        with self.assertRaises(ValueError):self.step(p)
        self.copy(1).write_bytes(raw[:-1]);self.copy(1).chmod(0o600)
        with self.assertRaises(ValueError):self.step(p)
        self.assertEqual(self.c.latest(),p)
    def test_exact_restore_from_latest_copy(self):
        p,_=self.boot();q,out=self.step(p);raw=self.copy(2).read_bytes();self.path.unlink()
        result=restore(self.src,self.c,generation=G,key=KEY,expected=q,backup=raw,synthetic=True)
        self.assertEqual(result["sequence"],2)
        with self.store() as s:self.assertEqual(s.status(q),out)
        self.assertEqual(self.db.total_changes,0)
    def test_genesis_rejects_nonempty_backup_directory(self):
        self.copy(1).write_bytes(b"x");self.copy(1).chmod(0o600)
        with self.assertRaises(ValueError):self.boot()
        self.assertEqual(self.c.latest().phase,"GENESIS")
        self.assertFalse(self.path.exists())
