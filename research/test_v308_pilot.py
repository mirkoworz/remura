import json,sqlite3,unittest
from datetime import datetime,timezone
from v308_queue import capture_tick,digest
from v308_history import initialize,archive,evaluate_pending,totals
T=1800000000000;M=900000;F=300000
def ts(v):return datetime.fromtimestamp(v/1000,timezone.utc).isoformat()
def price(now,start,count,close=1.1005):
    p={"provider":"ctrader","providerSymbol":"EURUSD","timeframes":{"M15":[{"t":ts(start+i*M),"o":1.1,"h":1.101,"l":1.099,"c":close} for i in range(count)]}}
    return json.dumps(["EURUSD","ctrader","EURUSD",ts(now),json.dumps(p)]).encode()
def sources(now):
    records=[]
    for i in range(12,0,-1):
        c=now-i*F
        m={"bar_close_ms":c,"received_at_ms":c+1,"symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","is_timely":0}
        p={"schema":"remura.tv.flow.cvd.preview.v1","configuration":{},"snapshot":{**m,"confirmed":True,"footprint":{"available":True,"delta":1,"buy":2,"sell":1}}}
        v=json.dumps(p).encode()
        records.append({"metadata":m,"original_hex":v.hex(),"sha256":digest(v)})
    cot={"schema":"remura-b-v223-public-export-only-v1","publicReadAtUtc":ts(T-M),"dashboard":{"factors":[{"currency":"EUR","cftcContractCode":"099741","weeklyAssetManagerChangePp":1,"reportDate":"2026-11-17"}]}}
    return {"price":price(now,now-4*M,4),"footprint":json.dumps(records).encode(),"cot":json.dumps(cot).encode()}
class Pilot(unittest.TestCase):
    def setUp(self):self.db=sqlite3.connect(":memory:");initialize(self.db)
    def tearDown(self):self.db.close()
    def capture(self,t):
        raw=sources(t)
        archive(self.db,raw["price"],t)
        return capture_tick(self.db,raw,t,lambda:t,b"fixture",enabled=True)
    def test_end_to_end_custody_and_dedup(self):
        self.assertEqual(self.capture(T)["status"],"LOCAL_RECORDED_UNWITNESSED")
        self.assertEqual(self.capture(T)["status"],"ALREADY_OBSERVED_BAR")
        self.assertEqual(totals(self.db)["price_snapshots"],1)
        self.assertEqual(totals(self.db)["local_observations"],1)
        self.assertFalse(totals(self.db)["prospective_admitted"])
    def test_stale(self):
        r=sources(T);r["price"]=price(T-3*M,T-7*M,4)
        self.assertEqual(capture_tick(self.db,r,T,lambda:T,b"fixture",enabled=True)["status"],"WAIT_FRESH_PRICE")
    def test_missing_does_not_block_later(self):
        self.capture(T);self.capture(T+M)
        archive(self.db,price(T+6*M,T+2*M,4),T+6*M)
        self.assertEqual(evaluate_pending(self.db,T+6*M)["saved_cost_horizon_rows"],3)
        self.assertEqual(evaluate_pending(self.db,T+6*M)["saved_cost_horizon_rows"],0)
        self.assertEqual(evaluate_pending(self.db,T+6*M)["pending_missing_horizons"],1)
    def test_conflict_quarantine(self):
        self.capture(T)
        archive(self.db,price(T+5*M,T+M,4),T+5*M)
        archive(self.db,price(T+5*M,T+M,4,1.1006),T+5*M)
        self.assertEqual(totals(self.db)["conflicted_bars"],4)
        self.assertEqual(evaluate_pending(self.db,T+5*M)["saved_cost_horizon_rows"],0)
    def test_bad_digest(self):
        r=sources(T)
        rec=json.loads(r["footprint"]);rec[0]["sha256"]="0"*64
        r["footprint"]=json.dumps(rec).encode()
        with self.assertRaisesRegex(ValueError,"custody_digest"):
            capture_tick(self.db,r,T,lambda:T,b"fixture",enabled=True)
