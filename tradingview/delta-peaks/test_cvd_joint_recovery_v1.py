# REMURA v0.8.100 LAB — 16/11/2026 14:54 CET
import json,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_recovery_v1 as r
import cvd_joint_encrypted_v1 as m
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import PERIOD,DELAY,encoded
from cvd_incremental_preview_v1 import RollingPreview,repage
from cvd_private_runtime_preview_v1 import plan
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import mock_audit
G="e"*32;KEY=b"\x23"*32
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);(self.root/LOCK).touch(mode=0o600)
        self.path=self.root/m.NAME;self.c=m.EncryptedCustody(G,synthetic=True)
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        p=types.ModuleType("scripts");p.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([]))
        ctx=patch.dict(sys.modules,{"scripts":p});ctx.start();self.addCleanup(ctx.stop)
        self.now=T0+DELAY
        self.rows=[x for x,_,_ in triples(18,events=(0,14))]
    def store(self):
        return m.open_encrypted_joint(self.root,self.c,generation=G,key=KEY,synthetic=True)
    def full(self,at):return repage(plan(at),self.rows)
    def step(self,p,i):
        at=self.now+i*PERIOD
        old=RollingPreview(now=at-PERIOD,windows=self.full(at-PERIOD),synthetic=True)
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=at,windows=repage(old.next_ranges(at),self.rows))
    def boot(self):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full(self.now),cycles=4)
    def recover(self,p,raw,**kw):
        args=dict(generation=G,key=KEY,expected=p,backup=raw,synthetic=True);args.update(kw)
        return r.restore(self.root,self.c,**args)
    def test_exact_restore_and_resume_no_recollection(self):
        p,_=self.boot();q,expected=self.step(p,1);raw=self.path.read_bytes();self.path.unlink()
        result=self.recover(q,raw)
        self.assertEqual(result["status"],"EXACT_SYNTHETIC_BACKUP_RESTORED")
        self.assertEqual(self.path.read_bytes(),raw);self.assertEqual(self.c.latest(),q)
        self.assertFalse(result["custody_advanced"]);self.assertFalse(result["live_authorized"])
        with self.store() as s:self.assertEqual(s.status(q),expected)
        nextp,out=self.step(q,2)
        self.assertEqual(nextp.sequence,3);self.assertEqual(out["archive"]["cycles_recorded"],3)
        self.assertEqual(self.db.total_changes,0)
    def test_existing_target_never_overwritten(self):
        p,_=self.boot();raw=self.path.read_bytes()
        with self.assertRaises(ValueError):self.recover(p,raw)
        self.assertEqual(self.path.read_bytes(),raw)
        self.path.unlink();self.path.symlink_to("missing")
        with self.assertRaises(ValueError):self.recover(p,raw)
        self.assertTrue(self.path.is_symlink())
    def test_stale_backup_wrong_pin_or_key_denied_without_write(self):
        p,_=self.boot();old=self.path.read_bytes();q,_=self.step(p,1)
        latest=self.path.read_bytes();self.path.unlink()
        for pin,raw,kw in ((q,old,{}),(p,old,{}),(q,latest,{"key":b"\x24"*32}),(q,latest,{"generation":"c"*32})):
            with self.assertRaises(ValueError):self.recover(pin,raw,**kw)
            self.assertEqual({x.name for x in self.root.iterdir()},{LOCK})
        self.assertEqual(self.c.latest(),q)
    def test_invalid_ciphertext_never_written(self):
        p,_=self.boot();raw=self.path.read_bytes();self.path.unlink()
        e=json.loads(raw);e["tag"]=("0" if e["tag"][0]!="0" else "1")+e["tag"][1:]
        for bad in (b"",raw[:-1],encoded(e),b"x"*(m.MAX_CIPHER+1)):
            with self.assertRaises(ValueError):self.recover(p,bad)
            self.assertEqual({x.name for x in self.root.iterdir()},{LOCK})
    def test_pending_authority_or_orphan_denies(self):
        p,_=self.boot();raw=self.path.read_bytes();self.path.unlink()
        orphan=self.root/(m.TMP+"fixture");orphan.write_bytes(raw)
        with self.assertRaises(ValueError):self.recover(p,raw)
        orphan.unlink()
        q=self.c.reserve(p,self.now+PERIOD)
        with self.assertRaises(ValueError):self.recover(q,raw)
        self.assertFalse(self.path.exists())
    def test_failed_link_preserves_ciphertext_orphan_and_blocks(self):
        p,_=self.boot();raw=self.path.read_bytes();self.path.unlink()
        with patch.object(r.os,"link",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):self.recover(p,raw)
        self.assertFalse(self.path.exists())
        files=list(self.root.glob(m.TMP+"*"));self.assertEqual(len(files),1)
        self.assertEqual(files[0].read_bytes(),raw)
        with self.assertRaises(ValueError):self.recover(p,raw)
    def test_failed_unlink_blocks_even_if_target_exists(self):
        p,_=self.boot();raw=self.path.read_bytes();self.path.unlink()
        with patch.object(r.os,"unlink",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):self.recover(p,raw)
        self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(self.path.stat().st_nlink,2)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(p)
    def test_explicit_synthetic_required(self):
        p,_=self.boot();raw=self.path.read_bytes();self.path.unlink()
        with self.assertRaises(ValueError):self.recover(p,raw,synthetic=False)
        self.assertFalse(self.path.exists())
