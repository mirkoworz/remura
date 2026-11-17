# REMURA v0.8.121 LAB — 17/11/2026 07:04 CET (session start)
import json,sqlite3,subprocess,tempfile,unittest
from contextlib import closing
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,T
from level_transport_receiver_lab_v1 import decode,digest
ROOT=Path(__file__).parent/"gateway-lab"
PIN="a"*64;CUT=T-300000
class PermitWorkerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"remura-level-permits-worker-fixture.sqlite"
        p,_,v=decode(payload())
        self.expected={k:p[k] for k in ("chart_type","timezone","session")}
        self.expected["configuration_digest"]=v["configuration_digest"]
        with closing(sqlite3.connect(self.path)) as db,db:
            for f in ("level_admission_candidate.sql","level_receipt_candidate.sql","level_permit_ledger_candidate.sql"):
                db.executescript((ROOT/f).read_text())
            db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
            db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",(PIN,v["configuration_digest"],p["chart_type"],p["timezone"],p["session"],CUT))
    def q(self,sql):
        with closing(sqlite3.connect(self.path)) as db,db:return db.execute(sql).fetchall()
    def arm(self):self.q("UPDATE level_admission_v1 SET enabled=1")
    def a(self,raw=None,now=T+1500,**kw):return dict(raw=payload() if raw is None else raw,now=now,**kw)
    def run_actions(self,*actions):
        spec=dict(synthetic=True,pin=PIN,expected=self.expected,cutoff=CUT,actions=list(actions))
        out=subprocess.run(["node",str(ROOT/"level_permit_worker_fixture.mjs"),str(self.path)],input=json.dumps(spec),text=True,capture_output=True,check=True,timeout=30)
        return json.loads(out.stdout)
    def rows(self):return self.q("SELECT close_ms,first_received_ms,attempt,body_digest,body,present_levels FROM level_receipts_v2")
    def test_hard_off_and_db_default_off(self):
        self.assertEqual(self.run_actions(self.a(kind="hardoff"),self.a()),[[503,"OFF"],[503,"UNAVAILABLE"]])
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(0,)])
        self.arm()
        self.assertEqual(self.run_actions(self.a(enabled=False),self.a(kind="hardoff")),[[503,"OFF"],[503,"OFF"]])
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(0,)])
    def test_real_request_and_sql_receipt(self):
        self.arm();raw=payload()
        self.assertEqual(self.run_actions(self.a(raw)),[[201,"STORED_SYNTHETIC"]])
        self.assertEqual(self.rows(),[(T,T+1500,1,digest(raw),raw,4)])
    def test_overlap_does_not_invalidate_first(self):
        self.arm();raw=payload()
        actions=dict(kind="overlap",first=self.a(raw),second=self.a("{}",now=T+1600))
        self.assertEqual(self.run_actions(actions),[[[201,"STORED_SYNTHETIC"],[400,"INVALID"]]])
        self.assertEqual(self.rows(),[(T,T+1500,1,digest(raw),raw,4)])
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(2,)])
    def test_duplicate_conflict_across_process(self):
        self.arm();raw=payload();self.run_actions(self.a(raw))
        alt=json.loads(raw);alt["snapshot"]["levels"][0]["price"]="1.08599"
        self.assertEqual(self.run_actions(self.a(raw,T+1600),self.a(json.dumps(alt),T+1700)),[[200,"DUPLICATE"],[409,"CONFLICT"]])
        self.assertEqual(self.rows(),[(T,T+1500,1,digest(raw),raw,4)])
        self.assertEqual(self.q("SELECT count(*) FROM level_finalizations_v2"),[(3,)])
    def test_fake_peer_key_media_and_invalid_utf8(self):
        self.arm()
        a=[self.a(headers={"x-remura-fixture-peer":"false"}),self.a(now=T+1600,key="2"*64),self.a(now=T+1700,headers={"content-type":"text/plain"}),self.a(now=T+1800,bytes=[255])]
        self.assertEqual(self.run_actions(*a),[[403,"DENIED"],[403,"DENIED"],[415,"MEDIA_TYPE"],[400,"BAD_REQUEST"]])
        self.assertEqual(self.rows(),[])
    def test_bad_length_size_and_cutoff(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a(headers={"content-length":"1"}),self.a(now=T+1600,headers={"content-length":"15001"}),self.a(now=T+120001)),[[400,"BAD_REQUEST"],[413,"SIZE"],[400,"INVALID"]])
        self.assertEqual(self.rows(),[])
    def test_lease_expiry_and_stop(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a(done=T+6501),dict(kind="stop"),self.a(now=T+1600)),[[503,"DENIED"],[200,"STOPPED"],[503,"UNAVAILABLE"]])
        self.assertEqual(self.rows(),[])
    def test_capacity_via_native_request(self):
        self.arm();actions=[self.a(payload(n),T+n*300000+1500) for n in range(13)]
        self.assertEqual(self.run_actions(*actions),[[201,"STORED_SYNTHETIC"]]*12+[[409,"CAPACITY_OR_ORDER"]])
        self.assertEqual(len(self.rows()),12)
if __name__=="__main__":unittest.main()
