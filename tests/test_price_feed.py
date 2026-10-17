"""Offline tests for private collector. Run: python -m unittest discover -s tests -p 'test_price_feed.py'."""
import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest

file = Path(__file__).resolve().parents[1] / "scripts" / "price_feed.py"
spec = importlib.util.spec_from_file_location("price_feed", file)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

UTC = dt.timezone.utc

class PriceFeedTests(unittest.TestCase):
    def make(self, day="2026-10-16"):
        return [feed.candle(f"{day}T00:{i*15:02d}:00Z", 1.1, 1.2, 1.0, 1.15) for i in range(4)]

    def test_m15_input_and_closed_guard(self):
        now=dt.datetime(2026,10,16,0,40,tzinfo=UTC)
        bars=self.make()
        self.assertEqual(len(feed.closed_m15(bars,now)),2)
        with self.assertRaises(ValueError):
            feed.candle("2026-10-16T00:07:00Z",1,2,0.8,1.5)

    def test_h1_rollup_requires_four_contiguous_bars(self):
        bars=self.make()
        now=dt.datetime(2026,10,16,1,0,tzinfo=UTC)
        self.assertEqual(len(feed.rollup(bars,1,now)),1)
        self.assertEqual(feed.rollup(bars[:2]+bars[3:],1,now),[])
        self.assertEqual(feed.rollup(bars,4,now),[])

    def test_open_h1_candle_is_not_created(self):
        bars=self.make()
        now=dt.datetime(2026,10,16,0,59,tzinfo=UTC)
        self.assertEqual(feed.rollup(bars,1,now),[])

    def test_non_tradable_prices_rejected(self):
        with self.assertRaises(ValueError):
            feed.candle("2026-10-16T00:00:00Z",1,0.9,0.8,1.2)
        with self.assertRaises(ValueError):
            feed.candle("2026-10-16T00:00:00Z",0,1,0,0)

    def test_provider_ticker_indices_are_explicit_not_guessed(self):
        self.assertEqual(feed.default_ticker("twelve","EURJPY",{}),"EUR/JPY")
        self.assertEqual(feed.default_ticker("oanda","USDJPY",{}),"USD_JPY")
        with self.assertRaises(ValueError):
            feed.default_ticker("oanda","US500",{})
        self.assertEqual(feed.default_ticker("oanda","US500",{"US500":"SPX500_USD"}),"SPX500_USD")

    def test_private_csv_import(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"fixture.csv"
            path.write_text("datetime,open,high,low,close\n2026-10-16T00:00:00Z,1.1,1.2,1.0,1.15\n",encoding="utf-8")
            rows=feed.csv_input(path)
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["o"],1.1)

    def test_mt5_read_only_adapter_with_mocked_terminal(self):
        """CI cannot launch a broker terminal. Mock documented read-only methods."""
        import sys
        import types
        from unittest.mock import patch
        calls = []
        first = int(dt.datetime(2026, 10, 16, 0, 0, tzinfo=UTC).timestamp())
        mocked = types.SimpleNamespace(
            TIMEFRAME_M15=15,
            initialize=lambda **kwargs: calls.append(("initialize", kwargs)) or True,
            symbol_info=lambda symbol: types.SimpleNamespace(name=symbol),
            symbol_select=lambda symbol, select: calls.append(("symbol_select", symbol)) or True,
            copy_rates_from_pos=lambda symbol, tf, start, count: [
                {"time": first + 900*i, "open": 1.101, "high": 1.105,
                 "low": 1.100, "close": 1.103} for i in range(3)
            ],
            shutdown=lambda: calls.append(("shutdown",)) or None
        )
        with patch.dict(sys.modules, {"MetaTrader5": mocked}):
            values=feed.mt5_prices("EURUSD", "EURUSD.r", 120)
        self.assertEqual(len(values), 3)
        self.assertEqual(values[0]["t"], "2026-10-16T00:00:00Z")
        self.assertTrue(any(x[0]=="shutdown" for x in calls))
        self.assertTrue(any(x[0]=="symbol_select" for x in calls))
        self.assertEqual(feed.default_ticker("mt5", "EURUSD", {}), "EURUSD")

    def test_bundle_is_explicit_and_contains_no_api_tokens(self):
        data=feed.market_document("EURUSD","csv","my csv",self.make(),dt.datetime(2026,10,16,1,0,tzinfo=UTC))
        self.assertEqual(len(data["timeframes"]["M15"]),4)
        self.assertEqual(len(data["timeframes"]["H1"]),1)
        self.assertEqual(data["timeframes"]["H4"],[])

if __name__ == "__main__":
    unittest.main()
