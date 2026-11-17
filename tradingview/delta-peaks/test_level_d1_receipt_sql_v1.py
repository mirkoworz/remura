# REMURA v0.8.118 LAB — 17/11/2026 CET
import re,sqlite3,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).parent/"gateway-lab"
SRC=(ROOT/"level_receipt_candidate.mjs").read_text()
ADM=(ROOT/"level_admission_candidate.mjs").read_text()
def query(src,name):return re.search(name+r" = \x60([\s\S]+?)\x60;",src).group(1)
INSERT=query(SRC,"INSERT_SQL");EXISTING=query(SRC,"EXISTING_SQL")
RESERVE=query(ADM,"RESERVE_SQL").replace("RETURNING enabled,allowed","RETURNING enabled,allowed,attempts")
STOP=query(ADM,"STOP_SQL")
PIN="a"*64;CFG="b"*64;T=1794859200000;CUT=T-300000
class ReceiptSQLTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"fixture.sqlite"
        with sqlite3.connect(self.path) as db:
            db.executescript((ROOT/"level_admission_candidate.sql").read_text())
            db.executescript((ROOT/"level_receipt_candidate.sql").read_text())
            db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
            db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",(PIN,CFG,"forex","Etc/UTC","regular",CUT))
    def sql(self,q,args=()):
        db=sqlite3.connect(self.path,timeout=5)
        try:
            with db:return db.execute(q,args).fetchall()
        finally:db.close()
    def arm(self):self.sql("UPDATE level_admission_v1 SET enabled=1")
    def reserve(self,now=T+1000):return self.sql(RESERVE,(PIN,now))[0][2]
    def insert(self,attempt=1,close=T,now=None,digest="c"*64,config=CFG,pin=PIN,cutoff=CUT,body="{}",present=4):
        now=close+1500 if now is None else now
        return self.sql(INSERT,(pin,close,now,close+1000,attempt,digest,body,present,config,"forex","Etc/UTC","regular",cutoff))
    def rows(self):return self.sql("SELECT close_ms,first_received_ms,attempt,body_digest FROM level_receipts_v1 ORDER BY close_ms")
    def test_default_closed_and_wrong_pin(self):
        self.assertEqual(self.insert(),[])
        self.arm();self.reserve()
        self.assertEqual(self.insert(pin="d"*64),[])
        self.assertEqual(self.insert(config="d"*64),[])
        self.assertEqual(self.insert(cutoff=T),[])
        self.assertEqual(self.rows(),[])
    def test_first_receipt_and_duplicate_conflict(self):
        self.arm();a=self.reserve();self.assertEqual(self.insert(a),[(T,)])
        b=self.reserve(T+1600)
        self.assertEqual(self.insert(b,now=T+1700),[])
        self.assertEqual(self.insert(b,now=T+1700,digest="d"*64),[])
        self.assertEqual(self.sql(EXISTING,(PIN,T,b,CFG,"forex","Etc/UTC","regular",CUT,T+1700)),[("c"*64,T+1500)])
        self.assertEqual(self.rows(),[(T,T+1500,a,"c"*64)])
    def test_reservation_superseded_and_reuse(self):
        self.arm();a=self.reserve();b=self.reserve(T+1100)
        self.assertEqual(self.insert(a),[])
        self.assertEqual(self.insert(b),[(T,)])
        self.assertEqual(self.insert(b,T+300000),[])
    def test_stop_between_reservation_and_insert(self):
        self.arm();a=self.reserve();self.sql(STOP,(PIN,))
        self.assertEqual(self.insert(a),[]);self.assertEqual(self.rows(),[])
    def test_capacity_and_order(self):
        self.arm()
        for n in range(12):
            t=T+n*300000;a=self.reserve(t+1000);self.assertEqual(self.insert(a,t),[(t,)])
        t=T+12*300000;a=self.reserve(t+1000)
        self.assertEqual(self.insert(a,t),[])
        self.assertEqual(len(self.rows()),12)
    def test_out_of_order_and_cutoff(self):
        self.arm();a=self.reserve(T+301000);self.insert(a,T+300000)
        b=self.reserve(T+302000)
        self.assertEqual(self.insert(b,T,now=T+302500),[])
        self.assertEqual(self.insert(b,CUT,now=T+302500),[])
    def test_immutable_tables(self):
        self.arm();self.insert(self.reserve())
        for q in ("UPDATE level_receipts_v1 SET present_levels=0","DELETE FROM level_receipts_v1","DELETE FROM level_receipt_session_v1","UPDATE level_receipt_session_v1 SET cutoff_ms=1"):
            with self.assertRaises(sqlite3.IntegrityError):self.sql(q)
    def test_concurrent_same_permit_single_insert(self):
        self.arm();a=self.reserve()
        with ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(lambda _:self.insert(a),range(8)))
        self.assertEqual(out.count([(T,)]),1)
        self.assertEqual(out.count([]),7)
    def test_sql_bounds(self):
        self.arm();a=self.reserve()
        for kw in (dict(body="x"*15001),dict(present=7),dict(now=T+120001)):
            with self.assertRaises(sqlite3.IntegrityError):self.insert(a,**kw)
        self.assertEqual(self.rows(),[])
if __name__=="__main__":unittest.main()
