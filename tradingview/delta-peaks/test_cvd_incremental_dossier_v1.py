# REMURA v0.8.91 LAB — 16/11/2026 13:08 CET
"""White-box synthetic replay; same existing B mock and D runtime, no network."""
import sqlite3,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from cvd_incremental_preview_v1 import RollingPreview,repage,PERIOD,M5
from cvd_private_runtime_preview_v1 import plan,preview
from cvd_runtime_private_state_v1 import bucket
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import pair,mock_audit

class IncrementalDossierTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA query_only=ON")
        self.addCleanup(self.db.close)
        self.rows=[r for r,_,_ in triples(310,events=(0,14,290),missing=(5,17,295))]
    def full(self,now,rows=None):
        return repage(plan(now),self.rows if rows is None else rows)
    def output(self,windows,now,pairs):
        packages=types.ModuleType("scripts")
        packages.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit(pairs))
        before=self.db.total_changes
        with patch.dict(sys.modules,{"scripts":packages}):
            result=preview(self.db,windows,now=now,origin="SYNTHETIC")
        self.assertEqual(self.db.total_changes,before)
        self.assertFalse(result["orders_enabled"])
        self.assertFalse(result["notice"]["sent"])
        self.assertFalse(result["notifications_enabled"])
        self.assertEqual(result["edge"],"NOT_ESTABLISHED")
        return result
    def test_output_equivalence_same_inputs_and_cutoff(self):
        # Use the existing B causal pair mock, not a fabricated real B observation.
        now=bucket(T0+300000)
        cache=RollingPreview(now=now,windows=self.full(now),synthetic=True)
        for step in range(4):
            cutoff=now+step*PERIOD
            if step:
                cache.advance(now=cutoff,windows=repage(cache.next_ranges(cutoff),self.rows))
            full=self.full(cutoff)
            self.assertEqual(cache.compare_reference(full)["status"],"EXACT_INPUT_MATCH")
            # White-box read of frozen synthetic pages; not a new runtime or public API.
            left=self.output(cache._windows,cutoff,[pair()])
            right=self.output(full,cutoff,[pair()])
            self.assertEqual(left,right)
            self.assertEqual(left["notice"]["tv_cvd_match_count"],1)
    def test_dense_window_eviction_and_notice_equivalence(self):
        now=bucket(T0+287*M5+300000)
        cache=RollingPreview(now=now,windows=self.full(now),synthetic=True)
        for step in range(1,5):
            cutoff=now+step*PERIOD
            cache.advance(now=cutoff,windows=repage(cache.next_ranges(cutoff),self.rows))
            full=self.full(cutoff)
            self.assertEqual(cache.compare_reference(full)["status"],"EXACT_INPUT_MATCH")
            self.assertEqual(cache.summary()["requested_slots"],289)
            self.assertEqual(self.output(cache._windows,cutoff,[]),self.output(full,cutoff,[]))
    def test_late_backfill_cannot_promote_frozen_notice(self):
        now=bucket(T0+300000)
        cache=RollingPreview(now=now,windows=self.full(now,[]),synthetic=True)
        cutoff=now+PERIOD
        cache.advance(now=cutoff,windows=repage(cache.next_ranges(cutoff),self.rows))
        full=self.full(cutoff)
        diff=cache.compare_reference(full)
        self.assertEqual(diff["status"],"INPUT_DIVERGENCE_NO_PROMOTION")
        self.assertFalse(diff["scientific_admission"])
        frozen=self.output(cache._windows,cutoff,[pair()])
        reference=self.output(full,cutoff,[pair()])
        self.assertEqual(frozen["notice"]["tv_cvd_match_count"],0)
        self.assertEqual(reference["notice"]["tv_cvd_match_count"],1)
        self.assertEqual(cache.compare_reference(full),diff)
    def test_conflict_does_not_change_existing_dossier(self):
        now=bucket(T0+300000)
        cache=RollingPreview(now=now,windows=self.full(now),synthetic=True)
        before=self.output(cache._windows,now,[pair()])
        cutoff=now+PERIOD
        pages=repage(cache.next_ranges(cutoff),self.rows)
        r=pages[0]["rows"][0]
        pages[0]["rows"].append(dict(r,received_at_ms=r["received_at_ms"]+1))
        with self.assertRaises(ValueError):
            cache.advance(now=cutoff,windows=pages)
        self.assertEqual(self.output(cache._windows,now,[pair()]),before)
