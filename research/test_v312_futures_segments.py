import unittest
from v312_futures_segments import segments
def w(start,provider="RITHMIC"):
    return {"provider":provider,"instrument_id":"6EH7","expiry":"2027-03-15","start_ms":start,"end_ms":start+300000,"unknown_side_volume":1,"by_provenance":{"EXCHANGE_REPORTED":{"buy":4,"sell":1,"delta":3}}}
class Segments(unittest.TestCase):
    def test_reset_on_gap(self):
        a=segments([w(300000),w(600000),w(1200000)],"EXCHANGE_REPORTED")
        self.assertEqual([v["observed_cumulative_delta"] for v in a],[3,6,3])
        self.assertFalse(a[-1]["cvd_certified"])
    def test_provider_reset(self):
        a=segments([w(300000),w(600000,"TRADOVATE")],"EXCHANGE_REPORTED")
        self.assertEqual(a[-1]["observed_cumulative_delta"],3)
    def test_overlap(self):
        with self.assertRaises(ValueError):segments([w(300000),w(300000)],"EXCHANGE_REPORTED")
