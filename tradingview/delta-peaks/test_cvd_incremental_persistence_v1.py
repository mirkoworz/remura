# REMURA v0.8.92 LAB — 16/11/2026 13:13 CET
import json,os,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_incremental_persistence_v1 as m
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import bucket,PERIOD,encoded,digest
from cvd_incremental_preview_v1 import repage,RollingPreview
from cvd_private_runtime_preview_v1 import plan,preview
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,mock_audit

class IncrementalPersistenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);(self.root/LOCK).touch(mode=0o600)
        self.path=self.root/m.NAME
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        packages=types.ModuleType("scripts")
        packages.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
        p=patch.dict(sys.modules,{"scripts":packages});p.start();self.addCleanup(p.stop)
        self.now=bucket(T0+300000)
        self.rows=[r for r,_,_ in triples(25,events=(0,14),missing=(5,))]
    def full(self,now):
        return repage(plan(now),self.rows)
    def new(self,now):
        prior=RollingPreview(now=now-PERIOD,windows=self.full(now-PERIOD),synthetic=True)
        return repage(prior.next_ranges(now),self.rows)
    def store(self):
        return m.open_store(self.root,synthetic=True)
    def bootstrap(self):
        with self.store() as s:
            s.initialize(self.now)
            return s.complete(self.db,cutoff=self.now,windows=self.full(self.now))
    def test_restart_equivalence_and_single_claim(self):
        first=self.bootstrap()
        self.assertEqual(first["status"],"CURRENT_SYNTHETIC")
        self.assertEqual(first["preview"]["notice"]["tv_cvd_match_count"],1)
        for i in range(1,4):
            now=self.now+i*PERIOD
            with self.store() as s:
                self.assertTrue(s.claim(now))
                self.assertFalse(s.claim(now))
                self.assertEqual(s.status()["status"],"INCOMPLETE_CLAIM")
                result=s.complete(self.db,cutoff=now,windows=self.new(now))
                self.assertEqual(result["preview"],preview(self.db,self.full(now),now=now,origin="SYNTHETIC"))
                self.assertNotIn("raw_json",json.dumps(result))
                self.assertFalse(result["scientific_admission"])
                with self.assertRaises(ValueError):s.complete(self.db,cutoff=now,windows=self.new(now))
            with self.store() as s:self.assertEqual(s.status(),result)
        self.assertEqual(self.db.total_changes,0)
    def test_pending_claim_preserves_old_preview_and_no_skip(self):
        first=self.bootstrap();now=self.now+PERIOD
        with self.store() as s:self.assertTrue(s.claim(now))
        with self.store() as s:
            status=s.status()
            self.assertEqual(status["status"],"INCOMPLETE_CLAIM")
            self.assertEqual(status["preview"],first["preview"])
            self.assertEqual(status["last_cutoff_ms"],self.now)
            self.assertFalse(s.claim(now))
            for bad in (self.now,now+PERIOD):
                with self.assertRaises(ValueError):s.claim(bad)
            # No automatic recovery or recollection; trusted explicit caller only.
    def test_pre_rename_failure_blocks_restart_without_losing_old_bundle(self):
        self.bootstrap();before=self.path.read_bytes()
        with self.store() as s:
            with patch.object(m.os,"replace",side_effect=OSError("synthetic crash")):
                with self.assertRaises(OSError):s.claim(self.now+PERIOD)
            with self.assertRaises(ValueError):s.status()
        self.assertEqual(self.path.read_bytes(),before)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
        self.assertEqual(len(list(self.root.glob(m.TMP_PREFIX+"*"))),1)
    def test_post_rename_fsync_ambiguity_is_not_retried(self):
        self.bootstrap();now=self.now+PERIOD
        with self.store() as s:
            s.claim(now)
            original=os.fsync
            def fault(fd):
                if os.path.isdir("/proc/self/fd/"+str(fd)):raise OSError("directory fsync")
                return original(fd)
            with patch.object(m.os,"fsync",side_effect=fault):
                with self.assertRaises(OSError):s.complete(self.db,cutoff=now,windows=self.new(now))
            with self.assertRaises(ValueError):s.status()
        # This simulates ambiguity, not power-loss durability. Explicit readback
        # in this process sees the complete atomic file, never a mixed generation.
        with self.store() as s:
            result=s.status()
            self.assertEqual(result["status"],"CURRENT_SYNTHETIC")
            self.assertFalse(s.claim(now))
            self.assertEqual(result["preview"],preview(self.db,self.full(now),now=now,origin="SYNTHETIC"))
    def test_corruption_and_semantic_rehash(self):
        self.bootstrap();raw=self.path.read_bytes()
        self.path.write_bytes(raw[:-1])
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
        w=json.loads(raw);w["state"]["last"]["preview"]["coverage"]["valid_unique_bars"]+=1
        w["sha256"]=digest(w["state"]);self.path.write_bytes(encoded(w))
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
    def test_no_reset_no_links_no_nonprivate_file(self):
        with self.store() as s:
            with self.assertRaises(FileNotFoundError):s.status()
        self.bootstrap()
        with self.store() as s:
            with self.assertRaises(ValueError):s.initialize(self.now)
        self.path.chmod(0o644)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
        self.path.chmod(0o600)
        extra=self.root/"copy";os.link(self.path,extra)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
        self.path.unlink();self.path.symlink_to(extra)
        with self.store() as s:
            with self.assertRaises(OSError):s.status()
    def test_existing_lock_and_explicit_synthetic(self):
        with self.assertRaises(ValueError):
            with m.open_store(self.root):pass
        with self.store():
            with self.assertRaises(ValueError):
                with self.store():pass
    def test_late_row_in_rehashed_snapshot_denied(self):
        self.bootstrap();now=self.now+PERIOD
        with self.store() as s:
            s.claim(now);s.complete(self.db,cutoff=now,windows=self.new(now))
        w=json.loads(self.path.read_bytes())
        last=w["state"]["last"]
        row=next(r for p in last["windows"] for r in p["rows"] if r["bar_close_ms"]==T0)
        row["received_at_ms"]=self.now+1000
        w["sha256"]=digest(w["state"]);self.path.write_bytes(encoded(w))
        with self.store() as s:
            with self.assertRaises(ValueError):s.status()
