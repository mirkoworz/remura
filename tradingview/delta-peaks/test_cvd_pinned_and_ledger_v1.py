# REMURA v0.8.95 LAB — 16/11/2026 13:22 CET
import json,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from cvd_incremental_pinned_v1 import SyntheticCustody,open_pinned
from cvd_incremental_persistence_v1 import NAME
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import bucket,PERIOD,DELAY,encoded,digest
from cvd_incremental_preview_v1 import repage,RollingPreview
from cvd_private_runtime_preview_v1 import plan
from cvd_telemetry_preview_v1 import M5
from cvd_first_observation_ledger_v1 import Ledger,verify
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,mock_audit
G="a"*32
class PinnedTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);(self.root/LOCK).touch(mode=0o600)
        self.path=self.root/NAME
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        packages=types.ModuleType("scripts")
        packages.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()]))
        p=patch.dict(sys.modules,{"scripts":packages});p.start();self.addCleanup(p.stop)
        self.c=SyntheticCustody(G,synthetic=True)
        self.now=bucket(T0+300000)
        self.rows=[r for r,_,_ in triples(20,events=(0,14),missing=(5,))]
    def store(self):return open_pinned(self.root,self.c,generation=G,synthetic=True)
    def full(self):return repage(plan(self.now),self.rows)
    def new(self):
        prior=RollingPreview(now=self.now,windows=self.full(),synthetic=True)
        return repage(prior.next_ranges(self.now+PERIOD),self.rows)
    def boot(self):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full())[0]
    def step(self,p):
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=self.now+PERIOD,windows=self.new())[0]
    def test_valid_rollback_denied_even_with_recomputed_digest(self):
        p=self.boot();old=self.path.read_bytes();q=self.step(p)
        self.assertEqual(q.sequence,2)
        with self.store() as s:
            self.assertTrue(s.status(q)["synthetic_pin_matched"])
            with self.assertRaises(ValueError):s.status(p)
        self.path.write_bytes(old)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(q)
            with self.assertRaises(ValueError):s.status(p)
    def test_local_delete_and_genesis_reset_denied(self):
        p=self.boot()
        with self.store() as s:
            with self.assertRaises(ValueError):s.bootstrap(self.db,expected=p,cutoff=self.now,windows=self.full())
        self.path.unlink()
        with self.store() as s:
            with self.assertRaises(FileNotFoundError):s.status(p)
            with self.assertRaises(ValueError):s.bootstrap(self.db,expected=p,cutoff=self.now,windows=self.full())
    def test_new_generation_cannot_overwrite_existing_file(self):
        self.boot();c=SyntheticCustody("b"*32,synthetic=True)
        with open_pinned(self.root,c,generation="b"*32,synthetic=True) as s:
            with self.assertRaises(ValueError):s.bootstrap(self.db,expected=c.latest(),cutoff=self.now,windows=self.full())
        with self.assertRaises(ValueError):
            with open_pinned(self.root,self.c,generation="b"*32,synthetic=True):pass
    def test_reservation_without_local_write_blocks_all_retries(self):
        p=self.boot();raw=self.path.read_bytes()
        pending=self.c.reserve(p,self.now+PERIOD)
        self.assertEqual(raw,self.path.read_bytes())
        with self.store() as s:
            for pin in (p,pending):
                with self.assertRaises(ValueError):s.status(pin)
                with self.assertRaises(ValueError):s.cycle(self.db,expected=pin,cutoff=self.now+PERIOD,windows=self.new())
        self.assertEqual(self.path.read_bytes(),raw)
    def test_local_completion_before_custody_finalize_is_ambiguous(self):
        p=self.boot();old=self.path.read_bytes()
        with patch.object(self.c,"finalize",side_effect=OSError("synthetic acknowledgement loss")):
            with self.assertRaises(OSError):self.step(p)
        self.assertNotEqual(self.path.read_bytes(),old)
        self.assertEqual(self.c.latest().phase,"PENDING")
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(self.c.latest())
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+PERIOD,windows=self.new())
    def test_invalid_progression_never_reserves(self):
        p=self.boot()
        with self.store() as s:
            for cutoff in (self.now,self.now+2*PERIOD):
                with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=cutoff,windows=[])
        self.assertEqual(self.c.latest(),p)
    def test_bad_window_after_reserved_claim_cannot_retry(self):
        p=self.boot()
        with self.store() as s:
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+PERIOD,windows=[])
        self.assertEqual(self.c.latest().phase,"PENDING")
        with self.store() as s:
            with self.assertRaises(ValueError):s.cycle(self.db,expected=p,cutoff=self.now+PERIOD,windows=self.new())

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.first=T0+DELAY
        self.rows=[r for r,_,_ in triples(12,events=(0,))]
        self.l=Ledger(cohort=G,first_cutoff=self.first,cycles=3,synthetic=True)
    def win(self,i,rows=None):
        end=self.first+i*PERIOD-DELAY
        return repage([(end-2*M5,end)],self.rows if rows is None else rows)[0]
    def verify(self,records,head):
        return verify(cohort=G,first_cutoff=self.first,cycles=3,records=records,expected_head=head,synthetic=True)
    def test_empty_vs_unobserved_and_no_rewrite(self):
        self.l.observe(cutoff=self.first,window=self.win(0))
        first=self.l.summary()
        self.assertEqual((first["slots_observed"],first["slots_empty_at_first_observation"]),(1,2))
        self.l.gap(cutoff=self.first+PERIOD,reason="COLLECTION_UNCERTAIN")
        with self.assertRaises(ValueError):self.l.observe(cutoff=self.first+PERIOD,window=self.win(1))
        out=self.l.observe(cutoff=self.first+2*PERIOD,window=self.win(2,[]))
        self.assertEqual((out["slots_observed"],out["slots_empty_at_first_observation"],out["slots_unobserved"]),(1,5,3))
        self.assertTrue(out["complete_schedule_recorded"]);self.assertFalse(out["scientific_admission"])
        self.assertEqual(self.verify(self.l.synthetic_records(explicit=True),out["head"]),out)
        with self.assertRaises(ValueError):self.l.gap(cutoff=self.first+3*PERIOD,reason="COLLECTION_UNCERTAIN")
    def test_exact_duplicates_frozen_and_no_raw_summary(self):
        w=self.win(0);w["rows"].append(dict(w["rows"][0]))
        out=self.l.observe(cutoff=self.first,window=w)
        self.assertEqual(out["duplicate_rows"],1)
        w["rows"].clear()
        self.assertEqual(self.l.summary(),out)
        self.assertNotIn("raw_json",json.dumps(out))
    def test_conflict_wrong_scope_and_skip_atomic(self):
        before=self.l.summary();w=self.win(0)
        w["rows"].append(dict(w["rows"][0],received_at_ms=T0+7000))
        for cutoff,window in ((self.first,w),(self.first+PERIOD,self.win(1)),(self.first,self.win(1))):
            with self.assertRaises(ValueError):self.l.observe(cutoff=cutoff,window=window)
        self.assertEqual(self.l.summary(),before)
    def test_chain_reorder_truncate_and_rehash_denied(self):
        self.l.observe(cutoff=self.first,window=self.win(0))
        self.l.observe(cutoff=self.first+PERIOD,window=self.win(1))
        records=self.l.synthetic_records(explicit=True);h=self.l.summary()["head"]
        for bad in (records[:-1],records[::-1]):
            with self.assertRaises(ValueError):self.verify(bad,h)
        w=json.loads(records[-1]);w["record"]["stats"]["valid_unique_bars"]=0
        w["sha256"]=digest(w["record"])
        with self.assertRaises(ValueError):self.verify((records[0],encoded(w)),w["sha256"])
    def test_byte_cap_rejects_before_state_change(self):
        before=self.l.summary()
        with patch("cvd_first_observation_ledger_v1.MAX_BYTES",1):
            with self.assertRaises(ValueError):self.l.observe(cutoff=self.first,window=self.win(0))
        self.assertEqual(self.l.summary(),before)
