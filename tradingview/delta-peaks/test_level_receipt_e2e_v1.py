# REMURA v0.8.119 LAB — 17/11/2026 CET
import json,sqlite3,subprocess,tempfile,unittest
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,T
from level_transport_receiver_lab_v1 import decode,digest
ROOT=Path(__file__).parent/"gateway-lab"
PIN="a"*64;CUT=T-300000
class ReceiptEndToEndTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"remura-level-e2e-fixture.sqlite"
        p,_,v=decode(payload())
        self.expected={k:p[k] for k in ("chart_type","timezone","session")}
        self.expected["configuration_digest"]=v["configuration_digest"]
        with sqlite3.connect(self.path) as db:
            db.executescript((ROOT/"level_admission_candidate.sql").read_text())
            db.executescript((ROOT/"level_receipt_candidate.sql").read_text())
            db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
            db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",(PIN,v["configuration_digest"],p["chart_type"],p["timezone"],p["session"],CUT))
    def arm(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE level_admission_v1 SET enabled=1")
    def reserve(self,id,now=T+1300,**kw):return dict(kind="reserve",id=id,now=now,**kw)
    def store(self,id,raw=None,now=T+1500,**kw):return dict(kind="store",id=id,raw=payload() if raw is None else raw,now=now,**kw)
    def sequence(self,*actions):
        spec=dict(synthetic=True,pin=PIN,expected=self.expected,cutoff=CUT,actions=list(actions))
        out=subprocess.run(["node",str(ROOT/"level_receipt_e2e_fixture.mjs"),str(self.path)],input=json.dumps(spec),text=True,capture_output=True,check=True,timeout=25)
        return json.loads(out.stdout)
    def rows(self):
        with sqlite3.connect(self.path) as db:return db.execute("SELECT close_ms,first_received_ms,attempt,body_digest,body,present_levels FROM level_receipts_v1 ORDER BY close_ms").fetchall()
    def test_real_sql_valid_and_first_receipt(self):
        self.arm();raw=payload()
        self.assertEqual(self.sequence(self.reserve("a"),self.store("a",raw)),["RESERVED","STORED_SYNTHETIC"])
        self.assertEqual(self.rows(),[(T,T+1500,1,digest(raw),raw,4)])
    def test_duplicate_conflict_across_process_restart(self):
        self.arm();raw=payload()
        self.sequence(self.reserve("a"),self.store("a",raw))
        original=self.rows()
        alt=json.loads(raw);alt["snapshot"]["levels"][0]["price"]="1.08599"
        self.assertEqual(self.sequence(self.reserve("b",T+1600),self.store("b",raw,T+1700),self.reserve("c",T+1800),self.store("c",json.dumps(alt),T+1900)),["RESERVED","DUPLICATE","RESERVED","CONFLICT"])
        self.assertEqual(self.rows(),original)
    def test_bad_contract_and_external_pin(self):
        self.arm();p=json.loads(payload());p["snapshot"]["configuration"]["lookback"]=31
        self.assertEqual(self.sequence(self.reserve("a"),self.store("a",json.dumps(p)),self.reserve("b",T+1600),self.store("b",now=T+1700,expected={**self.expected,"configuration_digest":"0"*64})),["RESERVED","INVALID","RESERVED","INVALID"])
        self.assertEqual(self.rows(),[])
    def test_stale_permit_and_persistent_stop(self):
        self.arm()
        self.assertEqual(self.sequence(self.reserve("a"),self.reserve("b",T+1400),self.store("a"),dict(kind="stop"),self.store("b")),["RESERVED","RESERVED","CLOSED_STALE_OR_CAPACITY","STOPPED","CLOSED_STALE_OR_CAPACITY"])
        self.assertEqual(self.sequence(self.reserve("c",T+1600),self.store("c",now=T+1700)),["DENIED","DENIED"])
        self.assertEqual(self.rows(),[])
    def test_default_off(self):
        self.assertEqual(self.sequence(self.reserve("a"),self.store("a")),["DENIED","DENIED"])
        self.assertEqual(self.rows(),[])
    def test_12_row_cap_on_entire_path(self):
        self.arm();actions=[]
        for n in range(13):
            t=T+n*300000;actions.extend([self.reserve(str(n),t+1300),self.store(str(n),payload(n),t+1500)])
        self.assertEqual(self.sequence(*actions),["RESERVED","STORED_SYNTHETIC"]*12+["RESERVED","CLOSED_STALE_OR_CAPACITY"])
        self.assertEqual(len(self.rows()),12)
    def test_late_and_pre_sender_denied(self):
        self.arm()
        self.assertEqual(self.sequence(self.reserve("a",T+1000),self.store("a",now=T+1233),self.reserve("b",T+120001),self.store("b",now=T+120001)),["RESERVED","INVALID","RESERVED","INVALID"])
        self.assertEqual(self.rows(),[])
if __name__=="__main__":unittest.main()
