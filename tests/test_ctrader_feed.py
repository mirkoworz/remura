"""Offline contract tests for cTrader reader. No SDK, account or broker network required."""
import datetime as dt
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("ctrader_feed",ROOT/"scripts"/"ctrader_feed.py")
feed=importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

class CTraderTests(unittest.TestCase):
    def bar(self,minutes=29873410,low=112344,delta_open=20,delta_high=38,delta_close=25):
        return types.SimpleNamespace(
            utcTimestampInMinutes=minutes,
            low=low,deltaOpen=delta_open,deltaHigh=delta_high,deltaClose=delta_close
        )

    def test_protocol_failure_exposes_only_approved_phase_and_error_type(self):
        original=ValueError("MY_SECRET_TOKEN=test123, account 123456")
        reason=feed.protocol_failure("account_list",original)
        self.assertEqual(reason,"Risposta cTrader inattesa nella fase account_list (ValueError).")
        self.assertNotIn("test123",reason)
        self.assertNotIn("123456",reason)
        self.assertEqual(feed.protocol_failure("custom_secret_stage",original),
                         "Risposta cTrader inattesa nella fase unknown (ValueError).")
        class SecretException(Exception):pass
        self.assertIn("(Exception)",feed.protocol_failure("trendbars",SecretException("secret")))

    def test_validates_cotrader_bars_without_optional_fields_or_hasfield(self):
        # The request is tied to one pending symbol; protobuf symbolId is optional.
        class MinimalReply:
            ctidTraderAccountId=1234
            period=7
            trendbar=[self.bar(minutes=29873415)]
            # Intentionally no symbolId, hasMore, HasField.
        reply=MinimalReply()
        self.assertEqual(len(feed.validated_trendbars_response(reply,1234,77)),1)
        self.assertAlmostEqual(feed.convert_trendbar(
            feed.validated_trendbars_response(reply,1234,77)[0],5)["c"],1.12369)

    def test_rejects_wrong_account_symbol_period_or_incomplete_response(self):
        class Reply:
            def __init__(self,account=2,symbol=22,period=7,more=False,rows=None):
                self.ctidTraderAccountId=account
                self.symbolId=symbol
                self.period=period
                self.hasMore=more
                self.trendbar=rows if rows is not None else [self.bar()]
            def bar(self):
                return types.SimpleNamespace(low=112344,deltaOpen=20,deltaHigh=38,
                                             deltaClose=25,utcTimestampInMinutes=29873415)
        ok=Reply()
        self.assertEqual(len(feed.validated_trendbars_response(ok,2,22)),1)
        for wrong in (Reply(account=3),Reply(symbol=23),Reply(period=9)):
            with self.assertRaises(ValueError):
                feed.validated_trendbars_response(wrong,2,22)
        with self.assertRaisesRegex(ValueError,"page_incomplete"):
            feed.validated_trendbars_response(Reply(more=True),2,22)
        with self.assertRaisesRegex(ValueError,"bars_oversized"):
            feed.validated_trendbars_response(Reply(rows=[self.bar()]*101),2,22)

    def test_partial_historic_window_is_split_not_accepted(self):
        day=24*60*60*1000
        start=1760918400000
        segments=feed.split_historic_window(start,start+day)
        self.assertEqual(segments,((start,start+day//2),(start+day//2,start+day)))
        self.assertTrue(all((a%feed.INTERVAL_MS)==0 and (b%feed.INTERVAL_MS)==0
                            for a,b in segments))
        self.assertIsNone(feed.split_historic_window(start,start+feed.INTERVAL_MS))
        with self.assertRaisesRegex(ValueError,"historic_window_invalid"):
            feed.split_historic_window(start,start)
        import inspect
        self.assertNotIn("request.count =",inspect.getsource(feed.collect))

    def test_relative_ohlc_and_utc_timestamp_are_decoded(self):
        bar=self.bar(minutes=29873415)
        item=feed.convert_trendbar(bar,5)
        self.assertAlmostEqual(item["o"],1.12364)
        self.assertAlmostEqual(item["h"],1.12382)
        self.assertAlmostEqual(item["l"],1.12344)
        self.assertAlmostEqual(item["c"],1.12369)
        self.assertTrue(item["t"].endswith(":00Z"))

    def test_bogus_broker_prices_are_rejected(self):
        with self.assertRaises(ValueError):
            feed.convert_trendbar(self.bar(delta_high=10,delta_open=30),5)
        with self.assertRaises(ValueError):
            feed.convert_trendbar(self.bar(low=-1),5)

    def test_missing_cfd_symbol_must_not_be_assumed(self):
        rows=[types.SimpleNamespace(symbolName="EUR/USD",symbolId=101,enabled=True),
              types.SimpleNamespace(symbolName="Gold",symbolId=102,enabled=True),
              types.SimpleNamespace(symbolName="US500.cash",symbolId=103,enabled=True)]
        resolved,errors=feed.exact_symbols(rows,["EURUSD","XAUUSD","US500"])
        self.assertEqual(resolved["EURUSD"].symbolId,101)
        self.assertIn("US500",errors)
        self.assertIn("XAUUSD",errors)
        explicit,err=feed.exact_symbols(rows,["XAUUSD","US500"],
          {"XAUUSD":"Gold","US500":"US500.cash"})
        self.assertEqual(len(err),0)
        self.assertEqual(explicit["US500"].symbolId,103)

    def test_ambiguous_market_names_are_rejected(self):
        rows=[types.SimpleNamespace(symbolName="EURUSD",symbolId=i,enabled=True) for i in (1,2)]
        resolved,errors=feed.exact_symbols(rows,["EURUSD"])
        self.assertEqual(resolved,{})
        self.assertIn("EURUSD",errors)

    def test_daily_utc_windows_are_bounded(self):
        now=dt.datetime(2026,10,17,8,0,tzinfo=dt.timezone.utc)
        windows=feed.utc_chunks(now,14)
        self.assertEqual(len(windows),14)
        self.assertTrue(all((y-x)==86400000 for x,y in windows))
        self.assertTrue(all(windows[i][1]==windows[i+1][0] for i in range(13)))
        with self.assertRaises(ValueError):
            feed.utc_chunks(now,999)

    def test_trendbar_validation_does_not_include_provider_payloads(self):
        class Reply:
            ctidTraderAccountId=5
            period=7
            symbolId=123
            trendbar=[]
            hasMore=False
        with self.assertRaisesRegex(ValueError,"account_mismatch"):
            feed.validated_trendbars_response(Reply(),7,123)
        Reply.period=9
        with self.assertRaisesRegex(ValueError,"timeframe_mismatch"):
            feed.validated_trendbars_response(Reply(),5,123)
        Reply.period=7;Reply.symbolId=124
        with self.assertRaisesRegex(ValueError,"symbol_mismatch"):
            feed.validated_trendbars_response(Reply(),5,123)

    def test_read_only_environment_fails_closed_before_approval(self):
        with patch.dict("os.environ",{
            "CTRADER_CLIENT_ID":"", "CTRADER_CLIENT_SECRET":"",
            "CTRADER_ACCESS_TOKEN":"", "CTRADER_ACCOUNT_ID":""
        }):
            with self.assertRaisesRegex(RuntimeError,"Parametri cTrader assenti"):
                feed.settings_from_environment()

    def test_environment_requires_selected_broker_account_and_env(self):
        data={"CTRADER_CLIENT_ID":"test","CTRADER_CLIENT_SECRET":"test",
              "CTRADER_ACCESS_TOKEN":"test","CTRADER_ACCOUNT_ID":"123","CTRADER_ENV":"demo"}
        with patch.dict("os.environ",data):
            result=feed.settings_from_environment()
            self.assertEqual(result["account_id"],123)
            self.assertEqual(result["environment"],"demo")

if __name__=="__main__":
    unittest.main()
