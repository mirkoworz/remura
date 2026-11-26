import unittest,json,hashlib
from decimal import Decimal
from v310_multifeed import tv_bar,m15,compare,TV,CT,M5,M15
T=1800000000000
def rec(t):
    m={"symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","bar_close_ms":t+M5,"received_at_ms":t+M5+1000}
    p={"schema":"remura.tv.flow.cvd.preview.v1","snapshot":{**m,"schema":"remura.tv.flow.cvd.snapshot.preview.v1","feed":"FX","bar_open_ms":t,"confirmed":True,"realtime":True,"quality":{"bar_closed":True},"ohlc":{"open":1.1,"high":1.102,"low":1.099,"close":1.101}}}
    raw=json.dumps(p).encode()
    return m,raw,hashlib.sha256(raw).hexdigest()
class Multi(unittest.TestCase):
    def bars(self):
        return [tv_bar(*rec(T+i*M5),T+M15+1000) for i in range(3)]
    def test_complete(self):
        b=m15(self.bars(),T+M15+1000)
        self.assertEqual(len(b),1)
        self.assertEqual(b[0]["available_ms"],T+M15+1000)
        self.assertEqual(b[0]["c"],Decimal("1.101"))
    def test_gap(self):
        self.assertEqual(m15(self.bars()[:2],T+M15+1000),[])
    def test_duplicate(self):
        b=self.bars()
        with self.assertRaises(ValueError):m15(b+b[:1],T+M15+1000)
    def test_future_and_digest(self):
        with self.assertRaises(ValueError):tv_bar(*rec(T),T+M5)
        m,r,h=rec(T)
        with self.assertRaises(ValueError):tv_bar(m,r,"0"*64,T+M5+1000)
    def test_compare(self):
        a=m15(self.bars(),T+M15+1000)
        b=[{**a[0],"source":CT,"c":Decimal("1.1011")}]
        d=compare(a,b,T+M15+1000)
        self.assertEqual(d["matched_m15"],1)
        self.assertEqual(Decimal(d["max_close_diff_pips"]),1)
        self.assertFalse(d["interchangeable"])
