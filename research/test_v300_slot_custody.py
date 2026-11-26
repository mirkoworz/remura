import json,sqlite3,unittest
from v294_d1_oracle_custody import initialize
from v300_slot_custody import key,request_slots,initialize_coverage,ingest_slots,plan_slots,plan_missing
from v300_local_quota import Budget
T=1800000000000
M=300000
def row(c,extra=0):
    m={"event_key":key(c),"symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","is_timely":0,"bar_close_ms":c,"received_at_ms":c+1000,"event_type":"HEARTBEAT"}
    p={"schema":"remura.tv.flow.cvd.preview.v1","snapshot":m,"cvd":{},"fixture":extra}
    return {**m,"raw_json":json.dumps(p)}
class NewSlotTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        initialize(self.db);initialize_coverage(self.db)
    def tearDown(self):self.db.close()
    def test_slots_and_gap_repair(self):
        slots=[T,T+M,T+2*M]
        end=T+3*M
        self.assertEqual(plan_slots(self.db,T,T+2*M),slots)
        self.assertEqual(ingest_slots(self.db,slots,end,end,[row(T),row(T+2*M)])["missing_at_check"],1)
        self.assertEqual(plan_slots(self.db,T,T+2*M),[])
        self.assertEqual(plan_missing(self.db,T,T+2*M,end),[T+M])
        self.assertEqual(ingest_slots(self.db,[T+M],end,end+1000,[row(T+M)])["new"],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tv_test_custody").fetchone()[0],3)
    def test_conflict_atomic(self):
        end=T+3*M
        ingest_slots(self.db,[T+M],end,end,[row(T+M)])
        with self.assertRaisesRegex(ValueError,"custody_conflict"):
            ingest_slots(self.db,[T,T+M],end,end+1,[row(T),row(T+M,1)])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tv_test_custody").fetchone()[0],1)
    def test_missing_existing_stops(self):
        end=T+M
        ingest_slots(self.db,[T],end,end,[row(T)])
        with self.assertRaisesRegex(ValueError,"upstream_missing_existing"):
            ingest_slots(self.db,[T],end,end+1,[])
    def test_query_only_exact_keys(self):
        q=request_slots([T,T+M],T+2*M)
        self.assertEqual(q["params"],[key(T),key(T+M),T+2*M])
        with self.assertRaises(ValueError):request_slots([T],T)
class NewBudgetTests(unittest.TestCase):
    def test_pending_and_daily_cap(self):
        db=sqlite3.connect(":memory:")
        try:
            b=Budget(db,2,20000)
            i=b.reserve("2026-11-26",10000)
            with self.assertRaisesRegex(ValueError,"unresolved"):b.reserve("2026-11-27",10000)
            b.finish(i,2)
            i=b.reserve("2026-11-26",10000);b.finish(i,2)
            with self.assertRaisesRegex(ValueError,"daily_budget"):b.reserve("2026-11-26",10000)
        finally:db.close()
