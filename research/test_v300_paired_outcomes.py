import unittest
from v300_paired_outcomes import evaluate
T=1800000000000
M=900000
D={"symbol":"EURUSD","mode":"TEST_DESCRIPTIVE_ONLY","frozen_ms":T,"sides":{"price_only":1,"footprint_only":-1,"footprint_plus_cot":0}}
def bars():
    return [{"open_ms":T+i*M,"o":"1.1000","h":"1.1010","l":"1.0990","c":"1.1005"} for i in range(1,5)]
class Paired(unittest.TestCase):
    def test_cost_and_flat(self):
        r=evaluate(D,bars(),T+5*M,"1",1)
        self.assertEqual({k:float(v) for k,v in r["net_pips"].items()},{"price_only":4,"footprint_only":-6,"footprint_plus_cot":0})
        self.assertFalse(r["prospective_admitted"])
    def test_unmatured(self):
        self.assertEqual(evaluate(D,bars(),T+4*M,1,1)["status"],"NOT_MATURE")
    def test_gap(self):
        self.assertEqual(evaluate(D,bars()[1:],T+5*M,1,1)["status"],"MISSING_CONTIGUOUS_BARS")
