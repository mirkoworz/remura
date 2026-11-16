# REMURA v0.8.109 LAB — 16/11/2026
import json,unittest
from test_level_local_probe_v1 import fixture,T
from level_local_probe_batch_v1 import review

def row(step=0):
    p=fixture();p["mode"]="REALTIME_LOCAL_LOG"
    p.update(snapshot_open_ms=T+step*300000-300000,
             snapshot_close_ms=T+step*300000,
             sender_clock_ms=T+step*300000+1234)
    # Fixture current period made long enough for multiple new snapshots.
    for level in p["levels"][:-1]:
        level["period_end_ms"]=T+3600000
    return p
def run(*rows,cutoff=T-300000):
    return review([json.dumps(p) for p in rows],after_close_ms=cutoff)
class LocalBatchTests(unittest.TestCase):
    def test_contiguous_claims_and_shared_origins(self):
        r=run(row(),row(1))
        self.assertEqual(r["rows"],2)
        self.assertTrue(r["continuous_elapsed_grid"])
        self.assertEqual(r["snapshots"][0]["origin_groups"],2)
        self.assertEqual(r["snapshots"][0]["shared_origin_groups"],1)
        self.assertEqual(r["snapshots"][0]["present_slots"],4)
        self.assertFalse(r["independent_sources_established"])
        self.assertFalse(r["prospective_admission"])
        self.assertFalse(r["receipt_authenticated"])
        self.assertNotIn("1.085301",str(r))
    def test_same_origin_price_disagreement_is_visible(self):
        p=row();p["levels"][3]["price"]="1.085400"
        r=run(p)
        self.assertEqual(r["snapshots"][0]["origin_groups"],2)
        self.assertEqual(r["snapshots"][0]["same_origin_price_disagreement_groups"],1)
    def test_missing_grid_slots_not_hidden(self):
        r=run(row(1),row(3))
        self.assertEqual(r["totals"]["elapsed_grid_slots_missing"],2)
        self.assertFalse(r["continuous_elapsed_grid"])
    def test_duplicate_reverse_and_cutoff_rejected(self):
        for rows,cutoff in (([row(),row()],T-300000),([row(1),row()],T-300000),([row()],T)):
            with self.assertRaises(ValueError):run(*rows,cutoff=cutoff)
    def test_historical_and_wrong_identity_rejected(self):
        p=row();p["mode"]="HISTORICAL_RECONSTRUCTION"
        with self.assertRaises(ValueError):run(p)
        p=row(1);p["timezone"]="America/New_York"
        with self.assertRaises(ValueError):run(row(),p)
        p=row(1);p["configuration"]["daily_min_effort"]=2
        with self.assertRaises(ValueError):run(row(),p)
    def test_sender_regression_and_short_bar_rejected(self):
        a=row();a["sender_clock_ms"]=T+600000
        with self.assertRaises(ValueError):run(a,row(1))
        p=row();p["snapshot_open_ms"]+=1000
        with self.assertRaises(ValueError):run(p)
    def test_capacity_and_no_mutation(self):
        p=row();before=json.dumps(p)
        run(p);self.assertEqual(json.dumps(p),before)
        with self.assertRaises(ValueError):run()
        with self.assertRaises(ValueError):run(*[row()]*13)
if __name__=="__main__":unittest.main()
