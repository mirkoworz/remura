import unittest
from datetime import date
from decimal import Decimal
from v310_cme_contract import Contract
from v311_futures_window import summarize
C=Contract("RITHMIC","CME","6E","6EH7",date(2027,3,15),"USD",Decimal("0.00005"))
def event(i,side,method,q=2):
    return {"instrument_id":"6EH7","venue":"CME","trade_id":str(i),"exchange_ms":1000+i,"received_ms":2000+i,"price":"1.10000","quantity":q,"aggressor":side,"side_provenance":method}
def run(events):
    return summarize(C,events,1000,3000,4000,approved=True,license_ref="SYNTHETIC_FIXTURE")
class Futures(unittest.TestCase):
    def test_separate_provenance(self):
        a=event(1,"BUY","EXCHANGE_REPORTED")
        d=run([a,a,event(2,"SELL","VENDOR_CLASSIFIED"),event(3,"UNKNOWN","UNKNOWN")])
        self.assertEqual(d["observed_volume"],6)
        self.assertEqual(d["unknown_side_volume"],2)
        self.assertEqual(d["by_provenance"]["EXCHANGE_REPORTED"]["delta"],2)
        self.assertEqual(d["by_provenance"]["VENDOR_CLASSIFIED"]["delta"],-2)
        self.assertFalse(d["cvd_available"])
    def test_conflict(self):
        with self.assertRaisesRegex(ValueError,"conflicting_trade"):run([event(1,"BUY","EXCHANGE_REPORTED"),event(1,"SELL","EXCHANGE_REPORTED")])
    def test_disabled(self):
        with self.assertRaises(PermissionError):summarize(C,[],1000,3000,4000)
