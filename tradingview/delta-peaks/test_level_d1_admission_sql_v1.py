# REMURA v0.8.115 LAB — 17/11/2026 CET
import re,sqlite3,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).parent/"gateway-lab"
SCHEMA=(ROOT/"level_admission_candidate.sql").read_text()
SOURCE=(ROOT/"level_admission_candidate.mjs").read_text()
SQL=re.search(r"RESERVE_SQL = `([\s\S]+?)`;",SOURCE).group(1)
STOP=re.search(r"STOP_SQL = `([\s\S]+?)`;",SOURCE).group(1)
PIN="a"*64
T=1794894540000
class D1AdmissionSQLTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"fixture.sqlite"
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)
            db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
    def sql(self,q,args=()):
        db=sqlite3.connect(self.path,timeout=5)
        try:
            with db:return db.execute(q,args).fetchall()
        finally:db.close()
    def arm(self):self.sql("UPDATE level_admission_v1 SET enabled=1")
    def reserve(self,t=T,pin=PIN):return self.sql(SQL,(pin,t))
    def state(self):return self.sql("SELECT enabled,attempts,last_ms,window_count FROM level_admission_v1")[0]
    def test_default_off(self):
        self.assertEqual(self.reserve(),[])
        self.assertEqual(self.state(),(0,0,None,0))
    def test_exact_pin(self):
        self.arm();self.assertEqual(self.reserve(pin="b"*64),[])
        self.assertEqual(self.state()[1],0)
    def test_window_and_total(self):
        self.arm()
        for _ in range(20):self.assertEqual(self.reserve(),[(1,1)])
        self.assertEqual(self.reserve(),[(1,0)])
        self.assertEqual(self.state()[1],21)
        self.assertEqual(self.reserve(T+60000),[(1,1)])
        self.assertEqual(self.state()[3],1)
    def test_terminal_cap(self):
        self.arm()
        for _ in range(48):self.reserve()
        self.assertEqual(self.reserve(T+60000),[])
        self.assertEqual(self.state()[1],48)
    def test_regression_latches_stop(self):
        self.arm();self.reserve()
        self.assertEqual(self.reserve(T-1),[(0,0)])
        self.assertEqual(self.reserve(T+1),[])
        self.assertEqual(self.state(),(0,1,T,1))
    def test_explicit_stop(self):
        self.arm();self.reserve()
        self.assertEqual(self.sql(STOP,(PIN,)),[(0,)])
        self.assertEqual(self.reserve(),[])
    def test_concurrent_atomic_statement(self):
        self.arm()
        with ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(lambda _:self.reserve(),range(40)))
        self.assertEqual(out.count([(1,1)]),20)
        self.assertEqual(out.count([(1,0)]),20)
        self.assertEqual(self.state()[1],40)
    def test_missing_no_auto_creation(self):
        self.sql("DELETE FROM level_admission_v1")
        self.assertEqual(self.reserve(),[])
        self.assertEqual(self.sql("SELECT count(*) FROM level_admission_v1"),[(0,)])
if __name__=="__main__":unittest.main()
