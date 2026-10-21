"""Offline integration tests for REMURA private always-on server.

No cTrader SDK, internet, cloud account, API credentials, or production data.
"""
import datetime as dt
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from price_feed import UTC, iso
import price_store as store
import private_server as server

NOW=dt.datetime(2026,10,17,9,0,tzinfo=UTC)


def make_bundle(symbol="EURUSD", start=None, count=1344, price=1.13, name="EUR/USD"):
    start=start or (NOW-dt.timedelta(minutes=15*count))
    bars=[]
    for i in range(count):
        t=start+dt.timedelta(minutes=i*15)
        if t+dt.timedelta(minutes=15)>NOW:
            break
        p=price+i*.000001
        bars.append({"t":iso(t),"o":p,"h":p+.001,"l":p-.001,"c":p+.0001})
    return {"schema":"remura-price-v1","generatedAt":iso(NOW),
            "markets":{symbol:{"symbol":symbol,"provider":"ctrader","providerSymbol":name,
                               "timeframes":{"M15":bars}}}}


class PrivateStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"private"/"prices.sqlite"
        self.db=store.connect(self.path)
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_persists_real_ohlc_and_rebuilds_timeframes(self):
        report=store.ingest(self.db,make_bundle(),now=NOW)
        self.assertTrue(report["saved"]["EURUSD"]>=1000)
        doc=store.api_document(self.db,"EURUSD",now=NOW)
        self.assertEqual(doc["schema"],"remura-price-v1")
        m=doc["markets"]["EURUSD"]
        self.assertEqual(m["provider"],"ctrader")
        self.assertGreaterEqual(len(m["timeframes"]["H4"]),55)
        self.assertEqual(len(m["timeframes"]["H1"]),336)
        self.assertEqual(len(m["timeframes"]["M15"]),1344)
        self.assertNotIn("CTRADER_ACCESS_TOKEN",json.dumps(doc))

    def test_incremental_refresh_merges_not_replace(self):
        store.ingest(self.db,make_bundle(count=96),now=NOW)
        earlier=len(store.latest(self.db,"EURUSD")["timeframes"]["M15"])
        more=make_bundle(start=NOW-dt.timedelta(minutes=15*8),count=8)
        result=store.ingest(self.db,more,now=NOW)
        self.assertEqual(result["saved"]["EURUSD"],earlier)
        self.assertEqual(len(store.latest(self.db,"EURUSD")["timeframes"]["M15"]),earlier)

    def test_switch_broker_does_not_mix_mismatched_prices(self):
        store.ingest(self.db,make_bundle(count=96,name="EUR/USD"),now=NOW)
        other=make_bundle(count=8,name="EURUSD.special")
        result=store.ingest(self.db,other,now=NOW)
        self.assertEqual(result["saved"]["EURUSD"],8)
        self.assertEqual(store.latest(self.db,"EURUSD")["providerSymbol"],"EURUSD.special")

    def test_ohlc_invalid_and_future_export_fail_without_overwrite(self):
        store.ingest(self.db,make_bundle(count=96),now=NOW)
        bad=make_bundle(count=3)
        bad["markets"]["EURUSD"]["timeframes"]["M15"][0]["h"]=.1
        self.assertIn("EURUSD",store.ingest(self.db,bad,now=NOW)["errors"])
        self.assertEqual(len(store.latest(self.db,"EURUSD")["timeframes"]["M15"]),96)
        future=make_bundle(count=3)
        future["generatedAt"]="2030-01-01T00:00:00Z"
        with self.assertRaises(ValueError):
            store.ingest(self.db,future,now=NOW)

    def test_real_gap_never_becomes_invented_hour(self):
        data=make_bundle(count=100)
        bars=data["markets"]["EURUSD"]["timeframes"]["M15"]
        missing_time=bars[-15]["t"]
        data["markets"]["EURUSD"]["timeframes"]["M15"]=[x for x in bars if x["t"]!=missing_time]
        store.ingest(self.db,data,now=NOW)
        m=store.latest(self.db,"EURUSD")
        self.assertEqual(len(m["timeframes"]["M15"]),99)
        self.assertLess(len(m["timeframes"]["H1"]),25)

    def test_database_is_not_served_as_a_static_asset(self):
        for path in ["/private/prices.sqlite","/scripts/private_server.py","/.env",
                     "/../private/prices.sqlite","/%2e%2e/private/x"]:
            self.assertIsNone(server.resolve_asset(path))
        self.assertIsNotNone(server.resolve_asset("/asset.html"))
        self.assertIsNotNone(server.resolve_asset("/quicklook.js"))
        self.assertIsNotNone(server.resolve_asset("/quicklook.css"))
        for name in ("simple-layout.js", "simple-layout.css", "sentiment-core.js",
                     "capital-cloud.js", "capital-cloud-config.js",
                     "squalo-core.js","squalo.js","squalo-scanner.js","squalo.css",
                     "squalo.html","remura-settings.js"):
            self.assertIsNotNone(server.resolve_asset("/" + name))

    def test_scheduler_aligns_to_utc_quarter_plus_delay(self):
        value=server.seconds_to_next_quarter(dt.datetime(2026,10,17,9,14,10,tzinfo=UTC))
        self.assertEqual(value,140)

    def test_collector_skips_if_another_cTrader_process_owns_lock(self):
        with patch.object(server, "collection_guard", side_effect=TimeoutError("busy")):
            report=server.collect_once(self.path, ["EURUSD"], runner=lambda *a,**k: None, now=NOW)
        self.assertEqual(report["saved"], {})
        self.assertIn("collector", report["errors"])
        self.assertNotIn("collector", store.get_status(self.db))

    def test_collector_fails_closed_without_credentials(self):
        with patch.dict(os.environ,{"CTRADER_CLIENT_ID":"","CTRADER_CLIENT_SECRET":"",
                                    "CTRADER_ACCESS_TOKEN":"","CTRADER_ACCOUNT_ID":""}):
            result=server.collect_once(self.path,["EURUSD"],runner=lambda *a,**k: None,now=NOW)
        self.assertEqual(result["saved"],{})
        self.assertEqual(store.get_status(self.db)["collector"],"awaiting_approval")

    def test_http_only_serves_allowlisted_static_and_verified_price(self):
        store.ingest(self.db,make_bundle(count=96),now=NOW)
        site=ThreadingHTTPServer(("127.0.0.1",0),server.http_handler(self.path))
        worker=threading.Thread(target=site.serve_forever,daemon=True)
        worker.start()
        base=f"http://127.0.0.1:{site.server_address[1]}"
        try:
            with urlopen(base+"/private-api/prices/EURUSD",timeout=5) as response:
                self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                payload=json.load(response)
                self.assertEqual(payload["markets"]["EURUSD"]["symbol"],"EURUSD")
            with urlopen(base+"/private-api/health",timeout=5) as response:
                self.assertIn("EURUSD",json.load(response)["instruments"])
            for path in ("/private/prices.sqlite","/scripts/private_server.py"):
                with self.assertRaises(HTTPError) as e:
                    urlopen(base+path,timeout=5)
                self.assertEqual(e.exception.code,404)
            with self.assertRaises(HTTPError) as e:
                urlopen(base+"/private-api/prices/NAS100",timeout=5)
            self.assertEqual(e.exception.code,503)
        finally:
            site.shutdown();site.server_close();worker.join(timeout=5)


if __name__=="__main__":
    unittest.main()
