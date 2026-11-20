# REMURA v0.8.90 LAB — 16/11/2026 13:04 CET
import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from cvd_incremental_preview_v1 import RollingPreview,repage,PERIOD,M5
from cvd_private_runtime_preview_v1 import plan
from cvd_runtime_private_state_v1 import bucket
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
NOW=bucket(T0+300000)
class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.rows=[r for r,_,_ in triples(20,events=())]
    def full(self,now,rows=None):
        return repage(plan(now),self.rows if rows is None else rows)
    def new(self,c,now,rows=None):
        return repage(c.next_ranges(now),self.rows if rows is None else rows)
    def test_equivalence_and_exact_eviction(self):
        c=RollingPreview(now=NOW,windows=self.full(NOW),synthetic=True)
        for i in range(1,5):
            now=NOW+i*PERIOD
            self.assertEqual(sum((b-a)//M5+1 for a,b in c.next_ranges(now)),3)
            c.advance(now=now,windows=self.new(c,now))
            self.assertEqual(c.compare_reference(self.full(now))["status"],"EXACT_INPUT_MATCH")
        # Stable day after earliest fixture rows expire.
        later=bucket(T0+86400000+300000)
        d=RollingPreview(now=later,windows=self.full(later),synthetic=True)
        self.assertEqual(d.summary()["requested_slots"],289)
        self.assertEqual(d.summary()["valid_unique_bars"],len([r for r in self.rows if plan(later)[0][0]<=r["bar_close_ms"]<=plan(later)[-1][1]]))
        end=later+PERIOD
        d.advance(now=end,windows=self.new(d,end))
        self.assertEqual(d.compare_reference(self.full(end))["status"],"EXACT_INPUT_MATCH")
    def test_late_missing_remains_frozen(self):
        c=RollingPreview(now=NOW,windows=self.full(NOW,[]),synthetic=True)
        now=NOW+PERIOD
        c.advance(now=now,windows=self.new(c,now))
        diff=c.compare_reference(self.full(now))
        self.assertEqual(diff["status"],"INPUT_DIVERGENCE_NO_PROMOTION")
        self.assertGreater(diff["differing_slots"],0)
        self.assertFalse(diff["scientific_admission"])
    def test_rewind_skip_and_bad_windows_atomic(self):
        c=RollingPreview(now=NOW,windows=self.full(NOW),synthetic=True)
        before=c.summary()
        for n in (NOW,NOW-PERIOD,NOW+2*PERIOD,NOW+PERIOD+1):
            with self.assertRaises(ValueError):c.next_ranges(n)
        now=NOW+PERIOD
        with self.assertRaises(ValueError):c.advance(now=now,windows=[])
        self.assertEqual(c.summary(),before)
        w=self.new(c,now);rows=w[0]["rows"]
        if not rows:self.fail("fixture must provide new bars")
        rows.append(dict(rows[0],received_at_ms=rows[0]["received_at_ms"]+1))
        with self.assertRaises(ValueError):c.advance(now=now,windows=w)
        self.assertEqual(c.summary(),before)
    def test_defensive_copy_and_duplicate_evidence(self):
        w=self.full(NOW)
        c=RollingPreview(now=NOW,windows=w,synthetic=True)
        before=c.summary()
        w[-1]["rows"].clear()
        self.assertEqual(c.summary(),before)
        raw=self.full(NOW)
        page=next(x for x in raw if x["rows"])
        page["rows"].append(dict(page["rows"][0]))
        self.assertEqual(c.compare_reference(raw)["status"],"INPUT_DIVERGENCE_NO_PROMOTION")
        with self.assertRaises(ValueError):RollingPreview(now=NOW,windows=self.full(NOW))
