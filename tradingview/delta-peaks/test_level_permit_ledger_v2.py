# REMURA v0.8.120 LAB — 17/11/2026 07:04 CET (session start)
import concurrent.futures, re, sqlite3, tempfile, unittest
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).parent/"gateway-lab"
PIN="a"*64; CFG="b"*64; T=1800000000000
def query(file,name):
    return re.search(name+r" = \x60([\s\S]+?)\x60;",(ROOT/file).read_text()).group(1)
RESERVE=query("level_admission_candidate.mjs","RESERVE_SQL").replace("RETURNING enabled,allowed","RETURNING enabled,allowed,attempts")
STOP=query("level_admission_candidate.mjs","STOP_SQL")
FINAL=query("level_permit_ledger_candidate.mjs","FINALIZE_SQL")
class PermitLedgerTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        self.path=Path(d.name)/"fixture.sqlite"
        with closing(sqlite3.connect(self.path)) as db, db:
            for f in ("level_admission_candidate.sql","level_receipt_candidate.sql","level_permit_ledger_candidate.sql"):
                db.executescript((ROOT/f).read_text())
            db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
            db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",(PIN,CFG,"forex","UTC","regular",T-300000))
    def q(self,sql,args=()):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            return db.execute(sql,args).fetchall()
    def arm(self): self.q("UPDATE level_admission_v1 SET enabled=1")
    def reserve(self,t=T+1000): return self.q(RESERVE,(PIN,t))
    def finish(self,attempt=1,t=T+1000,close=T,done=None,digest="c"*64,cfg=CFG):
        return self.q(FINAL,(PIN,close,t,close,attempt,digest,"{}",4,cfg,"forex","UTC","regular",T-300000,t+100 if done is None else done))
    def test_default_off_and_wrong_pin(self):
        self.assertEqual(self.reserve(),[])
        self.arm();self.assertEqual(self.q(RESERVE,("d"*64,T+1000)),[])
        self.assertEqual(self.q("SELECT * FROM level_permits_v2"),[])
    def test_later_reservation_no_invalidation(self):
        self.arm();self.reserve();self.reserve(T+1100)
        self.assertEqual(self.finish(),[("STORED_SYNTHETIC",)])
        self.assertEqual(self.finish(2,T+1100),[("DUPLICATE",)])
        self.assertEqual(self.q("SELECT attempt,first_received_ms FROM level_receipts_v2"),[(1,T+1000)])
    def test_conflict_consumes_only_its_own_permit(self):
        self.arm();self.reserve();self.reserve(T+1100)
        self.finish();self.assertEqual(self.finish(2,T+1100,digest="d"*64),[("CONFLICT",)])
        self.assertEqual(self.finish(2,T+1100),[])
        self.assertEqual(self.q("SELECT body FROM level_finalizations_v2 WHERE attempt=2"),[(None,)])
    def test_expiry_clock_pin_and_single_use(self):
        self.arm();self.reserve()
        self.assertEqual(self.finish(done=T+6001),[])
        self.assertEqual(self.finish(done=T+999),[])
        self.assertEqual(self.finish(t=T+1001),[])
        self.assertEqual(self.finish(cfg="d"*64),[])
        self.assertEqual(self.finish(done=T+6000),[("STORED_SYNTHETIC",)])
        self.assertEqual(self.finish(),[])
    def test_stop_and_clock_regression(self):
        self.arm();self.reserve();self.q(RESERVE,(PIN,T+999))
        self.assertEqual(self.finish(),[])
        self.assertEqual(self.reserve(),[])
        self.assertEqual(self.q("SELECT enabled FROM level_admission_v1"),[(0,)])
    def test_caps_and_rate_denied_not_permitted(self):
        self.arm()
        for i in range(21): self.reserve(T+1000+i)
        self.assertEqual(self.q("SELECT count(*) FROM level_permits_v2"),[(20,)])
        self.assertEqual(self.finish(21,T+1020),[])
        for i in range(28):self.reserve(T+60000*(1+i//20)+1000+i)
        self.assertEqual(self.q("SELECT attempts FROM level_admission_v1"),[(48,)])
        self.assertEqual(self.reserve(T+300000),[])
    def test_capacity_and_order(self):
        self.arm()
        for i in range(13):
            t=T+i*300000+1000; self.reserve(t)
            self.assertEqual(self.finish(i+1,t,T+i*300000),[("STORED_SYNTHETIC" if i<12 else "CAPACITY_OR_ORDER",)])
        self.assertEqual(self.q("SELECT count(*) FROM level_receipts_v2"),[(12,)])
    def test_same_permit_concurrent_and_immutable(self):
        self.arm();self.reserve()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            results=list(ex.map(lambda _:self.finish(),range(2)))
        self.assertEqual(sorted(results),[[],[("STORED_SYNTHETIC",)]])
        for table in ("level_permits_v2","level_finalizations_v2"):
            with self.assertRaises(sqlite3.IntegrityError):self.q("DELETE FROM "+table)
            with self.assertRaises(sqlite3.IntegrityError):self.q("UPDATE "+table+" SET attempt=2")
    def test_stop_after_two_reservations(self):
        self.arm();self.reserve();self.reserve(T+1100);self.q(STOP,(PIN,))
        self.assertEqual(self.finish(),[])
        self.assertEqual(self.finish(2,T+1100),[])
if __name__=="__main__":unittest.main()
