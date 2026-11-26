import unittest,sqlite3,json
from datetime import datetime,timezone
from v311_science import initialize,ingest,observe_tick,evaluate_tick,totals,digest
T=1800000000000;F=300000;M=900000
def fixture(close):
    m={"symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","bar_close_ms":close,"received_at_ms":close+1000,"is_timely":0}
    s={**m,"schema":"remura.tv.flow.cvd.snapshot.preview.v1","feed":"FX","bar_open_ms":close-F,"confirmed":True,"realtime":True,"quality":{"bar_closed":True},"ohlc":{"open":1.1,"high":1.102,"low":1.099,"close":1.101},"footprint":{"available":True,"delta":1,"buy":2,"sell":1}}
    raw=json.dumps({"schema":"remura.tv.flow.cvd.preview.v1","configuration":{},"snapshot":s}).encode()
    return m,raw,digest(raw)
COT=json.dumps({"schema":"remura-b-v223-public-export-only-v1","publicReadAtUtc":datetime.fromtimestamp((T-M)/1000,timezone.utc).isoformat(),"dashboard":{"factors":[{"currency":"EUR","cftcContractCode":"099741","weeklyAssetManagerChangePp":1,"reportDate":"2026-11-17"}]}}).encode()
class Science(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");initialize(self.db)
    def tearDown(self):self.db.close()
    def initial(self):
        now=T+400000
        rows=[fixture(T-i*F) for i in range(11,-1,-1)]
        self.assertEqual(ingest(self.db,rows,now),12)
        self.assertEqual(ingest(self.db,rows,now),0)
        return now
    def test_local_observation(self):
        now=self.initial()
        self.assertEqual(observe_tick(self.db,COT,b"fixture",lambda:now,now),"LOCAL_RECORDED_UNWITNESSED")
        self.assertEqual(observe_tick(self.db,COT,b"fixture",lambda:now,now),"ALREADY_OBSERVED_BAR")
        self.assertEqual(totals(self.db,now)["local_observations"],1)
        self.assertFalse(totals(self.db,now)["prospective_admitted"])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("DELETE FROM observations")
    def test_same_feed_outcomes(self):
        now=self.initial();observe_tick(self.db,COT,b"fixture",lambda:now,now)
        end=T+5*M
        ingest(self.db,[fixture(t) for t in range(T+M+F,end+1,F)],end+1000)
        self.assertEqual(evaluate_tick(self.db,end+1000)["new_outcome_rows"],3)
        self.assertEqual(evaluate_tick(self.db,end+1000)["new_outcome_rows"],0)
    def test_stale_footprint(self):
        now=self.initial()+600000
        self.assertEqual(observe_tick(self.db,COT,b"fixture",lambda:now,now),"WAIT_SOURCE_CONTEXT")
    def test_conflict(self):
        now=self.initial();m,r,h=fixture(T)
        m={**m,"received_at_ms":T+2000}
        with self.assertRaisesRegex(ValueError,"conflicting_event"):ingest(self.db,[(m,r,h)],now)
    def test_future_receipt(self):
        with self.assertRaises(ValueError):ingest(self.db,[fixture(T)],T)
        self.assertEqual(totals(self.db,T)["m5"],0)
