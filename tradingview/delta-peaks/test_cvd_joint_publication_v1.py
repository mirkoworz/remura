# REMURA v0.8.96 LAB — 16/11/2026 13:46 CET
import json,os,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_publication_v1 as m
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import bucket,PERIOD,encoded,digest
from cvd_incremental_preview_v1 import repage,RollingPreview
from cvd_private_runtime_preview_v1 import plan,preview
from cvd_first_observation_ledger_v1 import Ledger
from cvd_telemetry_preview_v1 import M5
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,mock_audit
G="a"*32
class JointPublicationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);(self.root/LOCK).touch(mode=0o600)
        self.path=self.root/m.NAME
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        p=types.ModuleType("scripts");p.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
        ctx=patch.dict(sys.modules,{"scripts":p});ctx.start();self.addCleanup(ctx.stop)
        self.c=m.JointCustody(G,synthetic=True)
        self.now=bucket(T0+289*M5)
        self.rows=[r for r,_,_ in triples(330,events=(0,14,290),missing=(290,))]
    def store(self):return m.open_joint(self.root,self.c,generation=G,synthetic=True)
    def full(self,now):return repage(plan(now),self.rows)
    def incoming(self,now):
        old=RollingPreview(now=now-PERIOD,windows=self.full(now-PERIOD),synthetic=True)
        return repage(old.next_ranges(now),self.rows)
    def boot(self,cycles=4):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full(self.now),cycles=cycles)
    def step(self,p,i=1):
        now=self.now+i*PERIOD
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=now,windows=self.incoming(now))
    def test_four_cycles_one_commit_and_no_baseline_archive(self):
        p,r=self.boot()
        self.assertEqual(r["archive"]["slots_observed"],3)
        self.assertEqual(r["preview"]["coverage"]["valid_unique_bars"],289)
        for i in range(1,4):
            p,r=self.step(p,i)
            with self.store() as s:self.assertEqual(s.status(p),r)
            self.assertEqual(r["preview"],preview(self.db,self.full(self.now+i*PERIOD),now=self.now+i*PERIOD,origin="SYNTHETIC"))
            self.assertEqual(r["archive"]["cycles_recorded"],i+1)
        self.assertEqual(r["archive"]["slots_observed"],11)
        self.assertEqual(r["archive"]["slots_empty_at_first_observation"],1)
        self.assertTrue(r["archive"]["complete_schedule_recorded"])
        self.assertFalse(r["scientific_admission"])
        self.assertNotIn("raw_json",json.dumps(r))
        self.assertEqual(self.db.total_changes,0)
        self.assertEqual({x.name for x in self.root.iterdir()},{m.NAME,LOCK})
        self.assertLessEqual(self.path.stat().st_size,m.MAX_FILE)
        with self.store() as s:
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+4*PERIOD,windows=self.incoming(self.now+4*PERIOD))
        self.assertEqual(self.c.latest(),p)
    def test_valid_old_bundle_rollback_denied(self):
        p,_=self.boot();old=self.path.read_bytes();q,_=self.step(p)
        self.path.write_bytes(old)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(q)
            with self.assertRaises(ValueError):s.status(p)
    def test_before_rename_failure_preserves_prior_joint_bytes(self):
        p,_=self.boot();old=self.path.read_bytes()
        with patch.object(m.os,"replace",side_effect=OSError("fault")):
            with self.assertRaises(OSError):self.step(p)
        self.assertEqual(self.path.read_bytes(),old)
        self.assertEqual(self.c.latest().phase,"PENDING")
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(p)
        self.assertEqual(len(list(self.root.glob(m.TMP+"*"))),1)
    def test_after_rename_before_finalize_no_publication(self):
        p,_=self.boot();old=self.path.read_bytes()
        with patch.object(self.c,"finalize",side_effect=OSError("fault")):
            with self.assertRaises(OSError):self.step(p)
        self.assertNotEqual(old,self.path.read_bytes())
        self.assertEqual(self.c.latest().phase,"PENDING")
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(self.c.latest())
            with self.assertRaises(ValueError):s.status(p)
        with self.assertRaises(ValueError):self.step(p)
    def test_rehashed_divergent_archive_denied_semantically(self):
        p,_=self.boot()
        w=json.loads(self.path.read_bytes());s=w["state"];a=s["archive"]
        l=Ledger(cohort=G,first_cutoff=self.now,cycles=a["cycles"],synthetic=True)
        window=a["records"][0]["record"]["window"];window["rows"]=[]
        l.observe(cutoff=self.now,window=window)
        a["records"]=[json.loads(x) for x in l.synthetic_records(explicit=True)]
        a["head"]=l.summary()["head"];w["sha256"]=digest(s)
        self.path.write_bytes(encoded(w))
        # Direct validation, without relying on independent digest mismatch.
        with self.assertRaises(ValueError):m.validate(s,G)
        with self.store() as j:
            with self.assertRaises(ValueError):j.status(p)
    def test_invalid_new_window_stops_pending_without_partial_archive(self):
        p,_=self.boot();old=self.path.read_bytes()
        with self.store() as s:
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+PERIOD,windows=[])
        self.assertEqual(old,self.path.read_bytes());self.assertEqual(self.c.latest().phase,"PENDING")
        with self.assertRaises(ValueError):self.step(p)
    def test_bound_and_genesis_no_overwrite(self):
        p,_=self.boot();old=self.path.read_bytes()
        other=m.JointCustody(G,synthetic=True)
        with m.open_joint(self.root,other,generation=G,synthetic=True) as s:
            with self.assertRaises(ValueError):s.bootstrap(self.db,expected=other.latest(),cutoff=self.now,windows=self.full(self.now),cycles=4)
        with patch.object(m,"MAX_FILE",1):
            with self.store() as s:
                with self.assertRaises(ValueError):s.status(p)
        self.assertEqual(old,self.path.read_bytes())
    def test_unapproved_gap_does_not_burn_reservation(self):
        p,_=self.boot()
        with self.store() as s:
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+2*PERIOD,windows=[])
        self.assertEqual(self.c.latest(),p)
