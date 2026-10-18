"""Offline tests: only DEMO, request cap, numeric validation, private storage."""
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_capital as c

NOW=dt.datetime(2026,10,18,9,0,tzinfo=dt.timezone.utc)

class Response:
    status=200
    def __init__(self,payload,headers=None):
        self.data=json.dumps(payload).encode()
        self.headers=headers or {}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,maximum):return self.data[:maximum]

class Transport:
    def __init__(self):
        self.responses=[
            Response({},{"CST":"private-token","X-SECURITY-TOKEN":"private-account"}),
            Response({"clientSentiments":[{"marketId":"SILVER",
                "longPositionPercentage":78.5,"shortPositionPercentage":21.5}]})]
        self.requests=[]
    def open(self,req,timeout):
        self.requests.append((req.full_url,req.get_method(),req.data))
        return self.responses.pop(0)

class CapitalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dir=Path(self.temp.name)/"private"/"capital"
        self.budget=c.Budget(self.dir,clock=lambda:NOW)
    def tearDown(self):self.temp.cleanup()

    def test_two_demo_only_requests_and_private_numbers(self):
        http=Transport()
        snapshot=c.collect(self.budget,{"XAGUSD":"SILVER"},
                           "not-a-real-key","user@example.org","fake-key-password",
                           opener=http,clock=lambda:NOW)
        self.assertEqual(len(http.requests),2)
        self.assertEqual(http.requests[0][0],c.BASE+"/api/v1/session")
        self.assertEqual(http.requests[0][1],"POST")
        self.assertTrue(http.requests[1][0].startswith(c.BASE+"/api/v1/clientsentiment?marketIds="))
        self.assertEqual(http.requests[1][1],"GET")
        self.assertEqual(snapshot["symbols"]["XAGUSD"]["lPct"],78.5)
        c.save(self.dir,snapshot,clock=lambda:NOW)
        latest=(self.dir/"latest.json").read_text()
        self.assertNotIn("not-a-real-key",latest)
        self.assertNotIn("user@example",latest)
        self.assertNotIn("private-token",latest)
        self.assertNotIn("marketId",latest)
        self.assertEqual(len(json.loads((self.dir/"history"/"XAGUSD.json").read_text())["records"]),1)
        self.assertEqual(json.loads(self.budget.ledger.read_text())["used"],2)

    def test_day_cap_is_strict_and_persistent(self):
        for _ in range(36):self.budget.spend()
        with self.assertRaises(c.Stop):self.budget.spend()
        self.assertEqual(json.loads(self.budget.ledger.read_text())["used"],36)
        self.assertEqual(c.Budget(self.dir,clock=lambda:NOW).ledger,self.budget.ledger)

    def test_cooldown_even_after_failed_login(self):
        self.budget.start()
        self.budget.spend()
        with self.assertRaises(c.Stop):self.budget.start()
        self.assertEqual(json.loads(self.budget.ledger.read_text())["used"],1)

    def test_corrupt_ledger_fails_closed(self):
        self.budget.ledger.write_text("{bad")
        with self.assertRaises(c.Stop):self.budget.spend()

    def test_invalid_market_and_percentage_rejected(self):
        for x in (None,True,"NaN",float("inf"),101,-1,""):
            self.assertIsNone(c.percent(x))
        with self.assertRaises(c.Stop):c.parse({},{"XAGUSD":"SILVER"},"T")
        with self.assertRaises(c.Stop):
            c.parse({"clientSentiments":[{"marketId":"SILVER","longPositionPercentage":80,
                      "shortPositionPercentage":30}]},{"XAGUSD":"SILVER"},"T")
        self.assertEqual(c.market_map(self.dir),{"XAGUSD":"SILVER"})
        (self.dir/"markets.json").write_text('{"XAUUSD":"https://example.org"}')
        with self.assertRaises(c.Stop):c.market_map(self.dir)

    def test_trading_endpoint_cannot_even_consume_budget(self):
        with self.assertRaises(c.Stop):
            c.api_json(self.budget,"POST","/api/v1/positions",{})
        with self.assertRaises(c.Stop):
            c.api_json(self.budget,"GET","https://api-capital.backend-capital.com",{})
        self.assertFalse(self.budget.ledger.exists())

if __name__=="__main__":unittest.main()
