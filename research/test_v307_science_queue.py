import json,sqlite3,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from v307_science_queue import initialize,capture_tick,outcome_tick,summary,digest
from v304_local_freeze import canonical
T=1800000000000;M=900000
def ts(v):return datetime.fromtimestamp(v/1000,timezone.utc).isoformat()
def price(now,start,count):
    p={"provider":"ctrader","providerSymbol":"EURUSD","timeframes":{"M15":[{"t":ts(start+i*M),"o":1.1,"h":1.101,"l":1.099,"c":1.1005} for i in range(count)]}}
    return json.dumps(["EURUSD","ctrader","EURUSD",ts(now),json.dumps(p)]).encode()
class Queue(unittest.TestCase):
    def setUp(self):self.db=sqlite3.connect(":memory:");initialize(self.db)
    def tearDown(self):self.db.close()
    def record(self):
        raw={"price":price(T,T-4*M,4),"footprint":b"[]","cot":b"{}"};rule=b"fixture"
        p={"prepared_ms":T,"entry_not_before_ms":T+M,"prospective_admitted":False,"source_sha256":{k:digest(v) for k,v in raw.items()},"rule_sha256":digest(rule),"sides":{"price_only":1,"footprint_only":-1,"footprint_plus_cot":0}}
        with patch("v307_science_queue.assemble",return_value={"status":"PREPARED_ONLY","packet":p,"commitment":digest(canonical(p))}):
            self.assertEqual(capture_tick(self.db,raw,T,lambda:T,rule,enabled=True)["status"],"LOCAL_RECORDED_UNWITNESSED")
            self.assertEqual(capture_tick(self.db,raw,T,lambda:T,rule,enabled=True)["status"],"ALREADY_OBSERVED_BAR")
    def test_wait_stale(self):
        raw={"price":price(T-3*M,T-7*M,4),"footprint":b"[]","cot":b"{}"}
        self.assertEqual(capture_tick(self.db,raw,T,lambda:T,b"rule",enabled=True)["status"],"WAIT_FRESH_PRICE")
        self.assertEqual(summary(self.db)["local_observations"],0)
    def test_record_and_append_only(self):
        self.record()
        self.assertEqual(summary(self.db)["local_observations"],1)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("DELETE FROM observations")
    def test_outcomes_once(self):
        self.record()
        p=price(T+5*M,T+M,4)
        self.assertEqual(outcome_tick(self.db,p,T+5*M,enabled=True)["saved_cost_horizon_rows"],3)
        self.assertEqual(outcome_tick(self.db,p,T+5*M,enabled=True)["saved_cost_horizon_rows"],0)
        self.assertFalse(summary(self.db)["prospective_admitted"])
    def test_missing_bars(self):
        self.record()
        p=price(T+5*M,T+2*M,3)
        self.assertEqual(outcome_tick(self.db,p,T+5*M,enabled=True)["saved_cost_horizon_rows"],0)
