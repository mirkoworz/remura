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

    def test_event_diagnostic_contains_only_safe_metadata(self):
        try:
            raise AttributeError("accessToken=TOPSECRET-12345")
        except AttributeError as exc:
            result = feed.safe_event_diagnostic("ProtoOASymbolsListRes", exc)
        self.assertIn("fase=ProtoOASymbolsListRes", result)
        self.assertIn("tipo=AttributeError", result)
        self.assertRegex(result, r"riga=[0-9]+")
        self.assertNotIn("TOPSECRET", result)
        self.assertNotIn("accessToken", result)
        try:
            raise RuntimeError("refresh_token=TOPSECRET")
        except RuntimeError as exc:
            other = feed.safe_event_diagnostic("secret-id-user-supplied", exc)
        self.assertIn("fase=other", other)
        self.assertNotIn("TOPSECRET", other)

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
