import unittest
from v304_source_context import sentiment,eurusd_cot
T=1800000000000
from datetime import datetime,timezone
def ts(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat()
def retail(t=T):
    return {"status":"ok","source":"Myfxbook Community Outlook","updatedAt":ts(t),"symbols":{"EURUSD":{"t":ts(t),"lPct":65,"sPct":35}}}
def cot():
    return {"schema":"remura-b-v223-public-export-only-v1","publicReadAtUtc":ts(T),"dashboard":{"factors":[{"currency":"EUR","cftcContractCode":"099741","reportDate":"2026-11-17","weeklyAssetManagerChangePp":-2}],"crosses":[{"symbol":"EURUSD","reportDate":"2026-11-17","legs":[{"currency":"EUR","weight":1}],"assetManagerWeeklyRelativeChangePp":-2,"leveragedFundsWeeklyRelativeChangePp":1,"derivedNotDirectSpot":True}]}}
class Sources(unittest.TestCase):
    def test_sentiment(self):
        self.assertEqual(sentiment(retail(),T,T)["imbalance_pp"],30)
        self.assertFalse(sentiment(retail(),T,T)["vendor_freshness_verified"])
        self.assertEqual(sentiment(retail(),T,T+3600001)["status"],"STALE")
    def test_future_and_invalid(self):
        with self.assertRaises(ValueError):sentiment(retail(T+1),T,T)
        d=retail();d["symbols"]["EURUSD"]["sPct"]=80
        with self.assertRaises(ValueError):sentiment(d,T,T)
    def test_cot_reference(self):
        self.assertFalse(eurusd_cot(cot(),T)["bilateral_independent"])
        self.assertEqual(eurusd_cot(cot(),T-1)["status"],"NOT_AVAILABLE_ASOF")
