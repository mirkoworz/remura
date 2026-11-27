# REMURA v0.8.123 LAB — 17/11/2026 CET
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
    def test_charset_official_json_variant(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a(headers={"content-type":"application/json; charset=utf-8"})),[[201,"STORED_SYNTHETIC"]])
        self.assertEqual(len(self.rows()),1)
    def test_unsupported_charset_and_extra_parameter(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a(headers={"content-type":"application/json; charset=iso-8859-1"}),self.a(now=T+1600,headers={"content-type":"application/json; charset=utf-8; extra=1"})),[[415,"MEDIA_TYPE"],[415,"MEDIA_TYPE"]])
        self.assertEqual(self.rows(),[])
    def test_post_validation_lease_and_bad_clock(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a(done=T+1499),self.a(now=T+1600,clockThrows=True),self.a(now=T+1700,done=T+6701)),[[503,"DENIED"],[503,"UNAVAILABLE"],[503,"DENIED"]])
        self.assertEqual(self.rows(),[])
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(3,)])
        self.assertEqual(self.run_actions(self.a(now=T+1800,done=T+6800)),[[201,"STORED_SYNTHETIC"]])
    def test_invalid_payload_does_not_sample_completion_clock(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a("{}",clockThrows=True)),[[400,"INVALID"]])
        self.assertEqual(self.rows(),[])
    def test_unauthorized_metadata_never_reaches_db(self):
        self.arm()
        a=[self.a(method="GET",noDb=True),self.a(key="2"*64,noDb=True),
           self.a(headers={"content-type":"text/plain"},noDb=True),
           self.a(headers={"content-length":"15001"},noDb=True),
           self.a(headers={"content-encoding":"gzip"},noDb=True),
           self.a(headers={"content-length":"0"},noDb=True)]
        self.assertEqual(self.run_actions(*a),[[405,"METHOD"],[403,"DENIED"],[415,"MEDIA_TYPE"],[413,"SIZE"],[400,"BAD_REQUEST"],[400,"BAD_REQUEST"]])
        self.assertEqual(self.q("SELECT attempts FROM level_admission_v1"),[(0,)])
    def test_untrusted_headers_cannot_supply_peer(self):
        self.arm()
        h={"cf-connecting-ip":"192.0.2.42","x-real-ip":"192.0.2.42","x-forwarded-for":"192.0.2.42"}
        peers=[None,{"synthetic":True,"origin":"WORKER_SUBREQUEST","ip":"192.0.2.42"},
               {"synthetic":True,"origin":"DIRECT_FIXTURE","ip":"192.0.2.43"},
               {"synthetic":False,"origin":"DIRECT_FIXTURE","ip":"192.0.2.42"}]
        self.assertEqual(self.run_actions(*(self.a(peer=p,headers=h,noDb=True) for p in peers)),[[403,"DENIED"]]*4)
        self.assertEqual(self.run_actions(self.a(headers={"x-remura-fixture-peer":"SYNTHETIC_FIXTURE_PEER"},noDb=True)),[[403,"DENIED"]])
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(0,)])
    def test_alternate_host_and_query_never_reach_db(self):
        self.arm();k="1"*64
        urls=["https://alternate.invalid/lab/levels/v2/"+k,
              "https://example.invalid:8443/lab/levels/v2/"+k,
              "https://example.invalid/lab/levels/v2/"+k+"?x=1",
              "http://example.invalid/lab/levels/v2/"+k]
        self.assertEqual(self.run_actions(*(self.a(url=u,noDb=True) for u in urls)),[[404,"NOT_FOUND"]]*4)
        self.assertEqual(self.q("SELECT attempts FROM level_admission_v1"),[(0,)])
    def test_malformed_admitted_body_still_consumes_attempt(self):
        self.arm()
        self.assertEqual(self.run_actions(self.a("{}"),self.a(now=T+1600)),[[400,"INVALID"],[201,"STORED_SYNTHETIC"]])
        self.assertEqual(self.q("SELECT attempts FROM level_admission_v1"),[(2,)])
        self.assertEqual(self.rows()[0][2],2)
    def test_preflight_abuse_does_not_exhaust_shared_session(self):
        self.arm()
        actions=[self.a(now=T+1500+n,key="2"*64,noDb=True) for n in range(24)]
        self.assertEqual(self.run_actions(*actions),[[403,"DENIED"]]*24)
        self.assertEqual(self.run_actions(self.a(now=T+1600)),[[201,"STORED_SYNTHETIC"]])
        self.assertEqual(self.q("SELECT attempts FROM level_admission_v1"),[(1,)])
if __name__=="__main__":unittest.main()
