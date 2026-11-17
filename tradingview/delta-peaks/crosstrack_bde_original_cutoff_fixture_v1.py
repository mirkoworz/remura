# REMURA v0.8.130 LAB — 17/11/2026 10:56 CET
import sqlite3,json,unittest
from datetime import timedelta
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,CLOSE,insert_history,iso
from fx_m15_decision_preview_v1 import ms
from test_level_receipt_custody_lab_v1 import SCHEMAS,ROOT,RESERVE,STOP,FINAL,PIN
from test_level_transport_receiver_lab_v1 import payload,T
from level_transport_receiver_lab_v1 import decode,digest
from level_receipt_custody_lab_v1 import snapshot
from level_receipt_witness_lab_v1 import genesis
import test_closed_source_custody_lab_v1 as e
from bde_original_cutoff_lab_v1 import summarize
FLAGS=dict(synthetic=True,ingress_closed=True)
KEY=b"b"*32; G="3"*32
class BDETests(unittest.TestCase):
    def setUp(self):
        self.b,doc=create();self.addCleanup(self.b.close)
        self.decision=CLOSE+timedelta(seconds=60);self.audit=CLOSE+timedelta(minutes=10)
        witness.witness(self.b,clock=AT)
        with self.b:
            hid=insert_history(self.b,observed=self.decision,closed=CLOSE)
            p=bundle.record(self.b,history_id=hid,observed_document=doc,clock=self.decision+timedelta(seconds=2))
        self.assertEqual(p["state"],"BOTH_LOCAL_PROOFS_PRESENT")
        self.b.execute("PRAGMA query_only=ON")
        self.e=e.SourceCustodyTests("test_repeat_and_bound_candidate");self.e.setUp();self.addCleanup(self.e.doCleanups)
        binding,bp,m,c=self.e.make()
        self.ec=dict(e_binding=binding,e_binding_pin=bp,e_manifest=m,e_candidate=c,e_source_pin=self.e.source,
                     e_journal_pin=self.e.pin,e_old_generation=e.f.G,e_new_generation=e.f.N)
    def make_d(self,lag=1500,second=True):
        # Build explicitly synthetic messages on the B fixture date, no real historical reconstruction.
        db=sqlite3.connect(":memory:");self.addCleanup(db.close)
        for f in SCHEMAS:db.executescript((ROOT/f).read_text())
        close=ms(CLOSE);shift=close-T
        def shifted(n):
            env=json.loads(payload(n));p=env["snapshot"]
            for k in ("snapshot_open_ms","snapshot_close_ms","sender_clock_ms"):p[k]+=shift
            for level in p["levels"]:
                for k in ("peak_origin_close_ms","period_start_ms","period_end_ms"):
                    if level[k] is not None:level[k]+=shift
            return json.dumps(env,separators=(",",":"))
        p,_,v=decode(shifted(0));cfg=v["configuration_digest"]
        args=(cfg,p["chart_type"],p["timezone"],p["session"],close-300000)
        db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
        db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",(PIN,*args))
        db.execute("UPDATE level_admission_v1 SET enabled=1")
        for n in range(2 if second else 1):
            raw=shifted(n);p,_,v=decode(raw);received=close+n*300000+lag
            db.execute(RESERVE,(PIN,received)).fetchall()
            r=db.execute(FINAL,(PIN,p["snapshot_close_ms"],received,p["sender_clock_ms"],n+1,digest(raw),raw,v["present_levels"],*args,received+100)).fetchall()
            self.assertEqual(r,[("STORED_SYNTHETIC",)])
        db.execute(STOP,(PIN,)).fetchall();db.commit();db.execute("PRAGMA query_only=ON")
        _,pin=snapshot(db,**FLAGS);r,a=genesis(pin,G,KEY,**FLAGS)
        return db,dict(self.ec,d_witness=r,d_key=KEY,d_latest=dict(latest_anchor=a,latest_generation=G,latest_sequence=1))
    def result(self,db,c,**kw):
        return summarize(self.b,db,**dict(dict(as_of_utc=iso(self.audit),custody=c,**FLAGS),**kw))
    def test_actual_b_e_d_original_cutoff(self):
        db,c=self.make_d();before=self.b.total_changes
        r=self.result(db,c)
        self.assertEqual(r["population"],1)
        self.assertEqual(r["decision_counts"],{"D_SNAPSHOT_ASOF_UNATTESTED":1})
        self.assertEqual(r["d_slot_counts"],{"MISSING":2,"PRESENT_UNATTESTED":4})
        self.assertEqual(r["e_quarantine_review_counts"],{"NOT_AVAILABLE_ASOF":1})
        self.assertEqual(self.b.total_changes,before)
        for k in ("predictive_features_available","scientific_admission","operational_signal","price_comparison_performed"):self.assertFalse(r[k])
    def test_receipt_late_and_completion_after_decision(self):
        for lag in (61000,59950):
            db,c=self.make_d(lag)
            self.assertEqual(self.result(db,c)["decision_counts"],{"D_NOT_AVAILABLE_ASOF":1})
    def test_later_snapshot_does_not_change_decision_diagnostics(self):
        db,c=self.make_d(second=False);first=self.result(db,c)
        db,c=self.make_d();self.assertEqual(self.result(db,c),first)
    def test_before_b_proof_committed(self):
        db,c=self.make_d()
        r=self.result(db,c,as_of_utc=iso(self.decision))
        self.assertEqual(r["population"],0);self.assertEqual(r["decision_counts"],{})
    def test_wrong_anchors_and_scope(self):
        db,c=self.make_d()
        for kw in (dict(custody={**c,"e_source_pin":"0"*64}),dict(synthetic=False),dict(ingress_closed=False)):
            with self.assertRaises(ValueError):self.result(db,c,**kw)
if __name__=="__main__":unittest.main()
