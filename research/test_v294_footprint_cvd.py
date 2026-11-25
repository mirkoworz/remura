"""New synthetic tests only. Run locally with python -m unittest."""
import hashlib,json,unittest
from v294_footprint_cvd import derive
T=1800000000000
def record(c,d=2,available=True,lag=1000):
    m={"symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","is_timely":0,"bar_close_ms":c,"received_at_ms":c+lag}
    p={"schema":"remura.tv.flow.cvd.preview.v1","configuration":{},"snapshot":{**m,"confirmed":True,"footprint":{"available":available,"delta":d,"buy":10+d,"sell":10}}}
    raw=json.dumps(p).encode()
    return {"metadata":m,"original":raw,"sha256":hashlib.sha256(raw).hexdigest()}
class Footprint(unittest.TestCase):
    def test_accumulate_and_gap(self):
        a=derive([record(T),record(T+300000,-1),record(T+900000,3)],T+1000000)
        self.assertEqual([x["segment_cvd"] for x in a],["2","1","3"])
        self.assertTrue(all(not x["prospective_admitted"] for x in a))
    def test_no_future(self):
        self.assertEqual(derive([record(T)],T),[])
    def test_invalid_break(self):
        a=derive([record(T),record(T+300000,available=False),record(T+600000)],T+700000)
        self.assertEqual([x["segment_bars"] for x in a],[1,1])
    def test_digest(self):
        a=record(T);a["original"]+=b" "
        with self.assertRaisesRegex(ValueError,"custody_digest"):derive([a],T+2000)
    def test_conflict(self):
        with self.assertRaisesRegex(ValueError,"conflict"):derive([record(T),record(T,3)],T+2000)
