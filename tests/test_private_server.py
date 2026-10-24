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
        for filename in ("capital-cloud-config.js","capital-cloud.js","impostazioni.html","impostazioni.js"):
            with self.subTest(filename=filename):
                self.assertIsNotNone(server.resolve_asset("/"+filename),
                                     "Google login/settings must be served by private Oracle app")

    def test_every_precached_page_and_script_is_servable(self):
        # Catch regressions where Firebase login disappears after Oracle deploy:
        # service worker precache can only work for allowlisted static files.
        import re
        sw=(ROOT/"sw.js").read_text(encoding="utf-8")
        match=re.search(r"const STATIC=(\[[^\n]*?\]);",sw)
        self.assertIsNotNone(match)
        for filename in json.loads(match.group(1)):
            with self.subTest(asset=filename):
                self.assertIsNotNone(server.resolve_asset("/"+filename.removeprefix("./")))

    def test_autoupdate_status_is_private_and_sanitized(self):
        private=Path(self.path).resolve().parent
        metadata=private/"autoupdate-state.json"
        metadata.write_text(json.dumps({"enabled":True,"state":"configured",
                                        "installedSha":"a"*40,
                                        "CAPITAL_API_PASSWORD":"never-expose"}),encoding="utf-8")
        doc=server.safe_update_status(self.path)
        self.assertEqual(doc["state"],"configured")
        self.assertNotIn("CAPITAL_API_PASSWORD",doc)
        self.assertNotIn("never-expose",json.dumps(doc))

    def test_market_batches_are_bounded_and_cover_each_symbol(self):
        selected=sorted(store.MARKETS)
        batches=server.collector_batches(selected)
        self.assertTrue(all(len(b)<=5 for b in batches))
        self.assertEqual([x for batch in batches for x in batch],selected)
        self.assertEqual(len(batches),8)
        self.assertEqual(server.collector_batches(["EURUSD","EURUSD"]),[["EURUSD"]])
        with self.assertRaises(ValueError):
            server.collector_batches(["BAD!"])

    def test_first_batch_status_is_real_batch_not_next_batch(self):
        selected=sorted(store.MARKETS)[:6]
        class StopOnce:
            stopped=False
            def is_set(self):return self.stopped
            def wait(self,seconds):self.stopped=True
        def collect(db_path,symbols,days=2,source="primary"):
            return {"saved":{symbol:1 for symbol in symbols},"errors":{}}
        with patch.dict(os.environ,{"REMURA_SYMBOLS":",".join(selected)},clear=False):
            with patch.object(server,"collect_once",side_effect=collect):
                with patch.object(server,"backup_ctrader_status",
                                  return_value={"configuration":"incomplete","enabled":False}):
                    server.collector_loop(self.path,StopOnce())
        self.assertEqual(store.get_status(self.db)["collector_batch"],"1/2")

    def test_diagnostics_summarize_only_non_sensitive_messages(self):
        reason=server.safe_ctrader_reason({"errors":{"EURUSD":"Ticker non disponibile o ambiguo: EUR/USD"}})
        self.assertIn("simboli",reason)
        self.assertNotIn("EUR/USD",reason)
        self.assertIn("Timeout",server.safe_ctrader_reason({"errors":{"connection":"Timeout della raccolta: dati incompleti."}}))
        snapshot={"status":"missing","configuration":"incomplete","environment":"demo"}
        with patch.object(server.importlib.util,"find_spec",return_value=None):
            details=server.ctrader_preflight(self.path)
        self.assertEqual(details["sdk"],"missing")
        self.assertNotIn("CTRADER_ACCESS_TOKEN",json.dumps(details))

    def test_ctrader_problem_reports_only_stage_and_error_class(self):
        sample={"errors":{"connection":
                "Risposta cTrader inattesa nella fase account_list (AttributeError)."}}
        result=server.safe_ctrader_reason(sample)
        self.assertEqual(result,"Risposta cTrader non attesa durante account_list (AttributeError).")
        poison=server.safe_ctrader_reason({"errors":{"connection":
            "Risposta cTrader inattesa nella fase token123 (SecretError) TOKEN123"}})
        self.assertEqual(poison,"Formato di risposta cTrader non atteso.")
        api=server.safe_ctrader_reason({"errors":{"connection":
            "cTrader ha segnalato un errore API nella fase symbols_list."}})
        self.assertIn("symbols_list",api)

    def test_cotrader_schema_failure_has_safe_status(self):
        self.assertIn("incoerente",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"Schema o metadati cTrader della risposta storica non coerenti."}}))
        self.assertIn("M15",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"Candela cTrader incompatibile o invalida."}}))

    def test_backup_requires_explicit_consent_and_separate_authorisation(self):
        env={"REMURA_CTRADER_BACKUP_ENABLED":"1",
             "CTRADER_CLIENT_ID":"app","CTRADER_CLIENT_SECRET":"secret",
             "CTRADER_BACKUP_ACCOUNT_ID":"2345","CTRADER_BACKUP_ENV":"live",
             "CTRADER_BACKUP_REFRESH_TOKEN":"test-private-token"}
        with patch.dict(os.environ,env,clear=True):
            p=server.backup_ctrader_environment(self.path)
            self.assertEqual(p["CTRADER_ACCOUNT_ID"],"2345")
            self.assertEqual(p["CTRADER_ENV"],"live")
        env["CTRADER_BACKUP_ENV"]="incorrect"
        with patch.dict(os.environ,env,clear=True):
            self.assertIsNone(server.backup_ctrader_environment(self.path))
        env["REMURA_CTRADER_BACKUP_ENABLED"]="0"
        with patch.dict(os.environ,env,clear=True):
            self.assertFalse(server.backup_ctrader_status(self.path)["enabled"])

    def test_price_sources_never_share_history(self):
        data=make_bundle()
        data["markets"]["EURUSD"]["providerSymbol"]="BACKUP · EUR/USD"
        store.ingest(self.db,data,now=NOW)
        self.assertEqual(store.latest(self.db,"EURUSD")["providerSymbol"],"BACKUP · EUR/USD")
        store.ingest(self.db,make_bundle(count=96),now=NOW)
        self.assertEqual(store.latest(self.db,"EURUSD")["providerSymbol"],"EUR/USD")
        self.assertEqual(len(store.latest(self.db,"EURUSD")["timeframes"]["M15"]),96)

    def test_cotrader_failure_codes_are_sanitized(self):
        self.assertIn("timeframe",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"ctrader_validation:timeframe_mismatch"}}))
        self.assertIn("conto",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"ctrader_validation:account_mismatch"}}))

    def test_failover_only_macro_market_sources(self):
        self.assertEqual(server.BACKUP_ALLOWED_MARKETS,frozenset(("DXY","VIX")))
        calls=[]
        class StopOnce:
            stopped=False
            def is_set(self):return self.stopped
            def wait(self,seconds):self.stopped=True
        def collect(db_path,symbols,days=2,source="primary"):
            calls.append((tuple(symbols),days,source))
            if source=="primary":
                return {"saved":{},"errors":{symbol:"no_data" for symbol in symbols}}
            return {"saved":{symbol:10 for symbol in symbols},"errors":{}}
        with patch.dict(os.environ,{"REMURA_SYMBOLS":"DXY,VIX,EURUSD,GER30"},clear=False):
            with patch.object(server,"collect_once",side_effect=collect):
                with patch.object(server,"backup_ctrader_status",return_value={"enabled":True,"configuration":"ready"}):
                    server.collector_loop(self.path,StopOnce())
        self.assertEqual(calls[0],(("DXY","VIX","EURUSD","GER30"),21,"primary"))
        self.assertEqual(calls[1],(("DXY","VIX"),21,"backup"))
        self.assertEqual(len(calls),2)

    def test_no_backup_call_when_primary_saved_all_symbols(self):
        calls=[]
        class StopOnce:
            stopped=False
            def is_set(self):return self.stopped
            def wait(self,seconds):self.stopped=True
        def collect(db_path,symbols,days=2,source="primary"):
            calls.append((tuple(symbols),source))
            return {"saved":{symbol:10 for symbol in symbols},"errors":{}}
        with patch.dict(os.environ,{"REMURA_SYMBOLS":"EURUSD,XAUUSD"},clear=False):
            with patch.object(server,"collect_once",side_effect=collect):
                with patch.object(server,"backup_ctrader_status",return_value={"enabled":True,"configuration":"ready"}):
                    server.collector_loop(self.path,StopOnce())
        self.assertEqual(calls,[(("EURUSD","XAUUSD"),"primary")])

    def test_private_fp_setup_never_replaces_primary_credentials(self):
        import configure_ctrader_backup as helper
        original=("CTRADER_CLIENT_ID=application\n"
                  "CTRADER_CLIENT_SECRET=private-secret\n"
                  "CTRADER_ACCOUNT_ID=12345\n"
                  "CTRADER_ENV=demo\n"
                  "REMURA_CTRADER_BACKUP_ENABLED=0\n")
        values=helper.parse_environment(original)
        self.assertEqual(values["CTRADER_ENV"],"demo")
        result=helper.update_environment(original,{
            "REMURA_CTRADER_BACKUP_ENABLED":"1",
            "CTRADER_BACKUP_ACCOUNT_ID":"67890",
            "CTRADER_BACKUP_ENV":"live",
        })
        self.assertIn("CTRADER_ACCOUNT_ID=12345",result)
        self.assertIn("CTRADER_CLIENT_SECRET=private-secret",result)
        self.assertEqual(result.count("REMURA_CTRADER_BACKUP_ENABLED="),1)
        self.assertIn("CTRADER_BACKUP_ACCOUNT_ID=67890",result)
        self.assertNotIn("REFRESH_TOKEN=",result)
        result_accounts=helper.account_options([
            types.SimpleNamespace(isLive=False,brokerTitleShort="FP Markets",traderLogin=123),
            types.SimpleNamespace(isLive=True,brokerTitleShort="FP Markets",traderLogin=456789),
        ])
        self.assertEqual(len(result_accounts),1)
        self.assertEqual(result_accounts[0][2],"••789")

    def test_failed_subprocess_marks_each_attempt_without_secret(self):
        with patch.dict(os.environ,{"CTRADER_CLIENT_ID":"app",
              "CTRADER_CLIENT_SECRET":"secret","CTRADER_ACCOUNT_ID":"123",
              "CTRADER_ENV":"demo","CTRADER_ACCESS_TOKEN":"test-access"},clear=False):
            with patch.object(server,"source_configured",return_value=True):
                with patch.object(server,"ctrader_preflight",return_value={
                      "sdk":"installed","configuration":"ready","environment":"demo","enabled":True}):
                    with patch.object(server,"access_token",return_value="token"):
                        def run(*args,**kwargs):
                            raise RuntimeError("secret returned by SDK")
                        report=server.collect_once(self.path,["EURUSD","USOIL"],runner=run,now=NOW)
        self.assertEqual(report["saved"],{})
        state=store.get_status(self.db)
        for symbol in ("EURUSD","USOIL"):
            self.assertEqual(json.loads(state["price_attempt:"+symbol])["outcome"],
                             "request_failed")
            self.assertNotIn("secret",state["price_attempt:"+symbol])
        self.assertNotIn("secret",state.get("last_error",""))
        self.assertEqual(server.price_failure_code("Risposta cTrader inattesa nella fase trendbars (AttributeError)."),
                         "request_failed")

    def test_ctrader_pagination_failure_does_not_claim_success(self):
        self.assertIn("incompleto",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"ctrader_validation:pagination_exhausted"}}))
        self.assertIn("parziale",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"ctrader_validation:page_incomplete"}}))
        self.assertIn("troppe",server.safe_ctrader_reason(
            {"errors":{"EURUSD":"ctrader_validation:bars_oversized"}}))

    def test_scheduler_aligns_to_utc_quarter_plus_delay(self):
        value=server.seconds_to_next_quarter(dt.datetime(2026,10,17,9,14,10,tzinfo=UTC))
        self.assertEqual(value,140)

    def test_collector_fails_closed_without_credentials(self):
        with patch.dict(os.environ,{"CTRADER_CLIENT_ID":"","CTRADER_CLIENT_SECRET":"",
                                    "CTRADER_ACCESS_TOKEN":"","CTRADER_ACCOUNT_ID":""}):
            result=server.collect_once(self.path,["EURUSD"],runner=lambda *a,**k: None,now=NOW)
        self.assertEqual(result["saved"],{})
        self.assertEqual(store.get_status(self.db)["collector"],"awaiting_approval")

    def test_lightweight_price_overview_distinguishes_saved_and_missing(self):
        store.ingest(self.db,make_bundle(count=96),now=NOW)
        store.set_status(self.db,**{
            "price_attempt:EURUSD":json.dumps({"time":iso(NOW),"outcome":"ok"}),
            "price_attempt:DXY":json.dumps({"time":iso(NOW),"outcome":"ticker_unavailable"})
        })
        overview=store.price_overview(self.db,now=NOW)
        self.assertEqual(overview["total"],len(store.MARKETS))
        rows={row["symbol"]:row for row in overview["markets"]}
        self.assertEqual(rows["EURUSD"]["counts"]["M15"],96)
        self.assertEqual(rows["EURUSD"]["source"],"primary")
        self.assertEqual(rows["EURUSD"]["lastOutcome"],"ok")
        self.assertIsNone(rows["DXY"]["lastComplete"])
        self.assertEqual(rows["DXY"]["lastOutcome"],"ticker_unavailable")
        self.assertNotIn("timeframes",json.dumps(overview))
        self.assertNotIn("CTRADER_REFRESH_TOKEN",json.dumps(overview))
        self.assertEqual(server.price_failure_code("Ticker non disponibile o ambiguo: USDX"),"ticker_unavailable")
        self.assertEqual(server.price_failure_code("ctrader_validation:page_incomplete"),"incomplete_history")
        self.assertEqual(server.price_failure_code("top-secret unknown"),"unknown_error")


    def test_38_market_quality_metadata_is_lightweight_and_sanitized(self):
        store.ingest(self.db,make_bundle(),now=NOW)
        overview=store.price_overview(self.db,now=NOW)
        row=next(m for m in overview["markets"] if m["symbol"]=="EURUSD")
        self.assertEqual(row["quality"]["integrity"],"verified")
        self.assertEqual(row["quality"]["freshness"],"recent")
        self.assertEqual(row["quality"]["h1"]["verified"],30)
        self.assertEqual(row["quality"]["h4"]["verified"],30)
        self.assertEqual(row["quality"]["recentGaps"],0)
        self.assertEqual(overview["qualityTotals"]["verified"],1)
        self.assertEqual(overview["qualityTotals"]["missing"],len(store.MARKETS)-1)
        self.assertNotIn('"timeframes":',json.dumps(overview))
        self.assertNotIn("CTRADER_ACCESS_TOKEN",json.dumps(overview))

    def test_quality_rejects_damaged_rollup_or_missing_m15_and_short_history(self):
        store.ingest(self.db,make_bundle(),now=NOW)
        original=store.latest(self.db,"EURUSD")
        changed=json.loads(json.dumps(original))
        changed["timeframes"]["H4"][-1]["h"]*=1.5
        self.assertEqual(store.audit_market(changed,NOW)["integrity"],"invalid")
        changed=json.loads(json.dumps(original))
        changed["timeframes"]["M15"].pop(-12)
        self.assertEqual(store.audit_market(changed,NOW)["integrity"],"partial")
        self.assertGreater(store.audit_market(changed,NOW)["h1"]["missingInputs"],0)
        changed=json.loads(json.dumps(original))
        changed["timeframes"]["H4"]=changed["timeframes"]["H4"][:10]
        self.assertEqual(store.audit_market(changed,NOW)["integrity"],"insufficient")

    def test_weekend_quality_not_misreported_as_live(self):
        store.ingest(self.db,make_bundle(),now=NOW)
        document=store.latest(self.db,"EURUSD")
        target=dt.datetime(2026,10,23,20,45,tzinfo=UTC)
        previous=dt.datetime.fromisoformat(document["lastComplete"].replace("Z","+00:00"))
        shift=target-previous
        for timeframe in ("M15","H1","H4"):
            for bar in document["timeframes"][timeframe]:
                timestamp=dt.datetime.fromisoformat(bar["t"].replace("Z","+00:00"))
                bar["t"]=iso(timestamp+shift)
        document["lastComplete"]=iso(target)
        saturday=dt.datetime(2026,10,24,14,0,tzinfo=UTC)
        result=store.audit_market(document,saturday)
        self.assertEqual(result["freshness"],"weekend")
        self.assertEqual(result["integrity"],"verified")
        monday=dt.datetime(2026,10,26,12,0,tzinfo=UTC)
        self.assertEqual(store.audit_market(document,monday)["freshness"],"stale")


    def test_cot_monitor_defaults_to_existing_approved_collector(self):
        self.assertTrue(server.cot_sync_enabled({"REMURA_COLLECTOR_ENABLED":"1"}))
        self.assertFalse(server.cot_sync_enabled({"REMURA_COLLECTOR_ENABLED":"0"}))
        self.assertFalse(server.cot_sync_enabled({"REMURA_COLLECTOR_ENABLED":"1",
                                                 "REMURA_COT_SYNC_ENABLED":"0"}))
        self.assertTrue(server.cot_sync_enabled({"REMURA_COLLECTOR_ENABLED":"0",
                                                "REMURA_COT_SYNC_ENABLED":"1"}))

    def test_cot_private_http_endpoint_returns_only_sanitized_status(self):
        import cot_monitor as cot
        cot.collect_once(self.path,NOW,lambda ds,now:[
            {"report_date_as_yyyy_mm_dd":"2026-10-13T00:00:00",
             "cftc_contract_market_code":code,"open_interest_all":"1000",
             **{field:"100" for field in cot.DATASETS[ds]["keys"]}}
            for code in cot.DATASETS[ds]["codes"]])
        site=ThreadingHTTPServer(("127.0.0.1",0),server.http_handler(self.path))
        worker=threading.Thread(target=site.serve_forever,daemon=True)
        worker.start()
        try:
            with patch.dict(os.environ,{"REMURA_COT_SYNC_ENABLED":"1"},clear=False):
                with urlopen("http://127.0.0.1:"+str(site.server_port)+
                             "/private-api/cot/status",timeout=5) as response:
                    self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                    payload=json.load(response)
            self.assertEqual(payload["schema"],"remura-cot-status-v1")
            self.assertEqual(payload["datasets"]["tff"]["contracts"],11)
            self.assertNotIn("first_long",json.dumps(payload))
            self.assertNotIn("api_key",json.dumps(payload))
        finally:
            site.shutdown();site.server_close();worker.join(timeout=2)

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
            with urlopen(base+"/private-api/prices/status",timeout=5) as response:
                self.assertEqual(response.headers.get("Cache-Control"),"no-store, max-age=0")
                summary=json.load(response)
                self.assertEqual(summary["schema"],"remura-price-status-v1")
                self.assertEqual(summary["total"],len(store.MARKETS))
                self.assertEqual(len(summary["markets"]),len(store.MARKETS))
                self.assertNotIn("timeframes",json.dumps(summary))
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
