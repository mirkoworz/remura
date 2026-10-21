"""Offline tests for the cTrader private Demo selector. No network/credentials."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace

# Mock token dependency before importing selector, to keep the tests offline.
sys.modules.setdefault("ctrader_tokens",
                       types.SimpleNamespace(access_token=lambda *_a, **_kw: "mock"))
from scripts import ctrader_account_setup as setup


class AccountSetupTests(unittest.TestCase):
    def test_demo_only_and_no_raw_ids_in_labels(self):
        accounts = [
            SimpleNamespace(ctidTraderAccountId=12345, isLive=False,
                            brokerTitleShort="DemoBroker", traderLogin=998877),
            SimpleNamespace(ctidTraderAccountId=88888, isLive=True,
                            brokerTitleShort="LiveBroker", traderLogin=55555),
        ]
        labels = setup.demo_labels(accounts)
        self.assertEqual(labels, [(12345, "DemoBroker", "877")])
        self.assertNotIn("12345", str(labels[0][1:]))
        self.assertNotIn("LiveBroker", str(labels))

    def test_private_update_keeps_credentials_and_collector_off(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "remura.env"
            file.write_text("CTRADER_CLIENT_SECRET=secret==\\nCTRADER_CLIENT_ID=abc\\nREMURA_COLLECTOR_ENABLED=0\\n".replace("\\n", "\n"))
            setup.save_demo_selection(file, 87654321)
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            data = file.read_text()
            self.assertIn("CTRADER_ACCOUNT_ID=87654321", data)
            self.assertIn("CTRADER_ENV=demo", data)
            self.assertIn("CTRADER_CLIENT_SECRET=secret==", data)
            self.assertIn("REMURA_COLLECTOR_ENABLED=0", data)
            setup.save_demo_selection(file, 123)
            self.assertEqual(file.read_text().count("CTRADER_ACCOUNT_ID="), 1)

    def test_reject_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "remura.env"
            file.write_text("CTRADER_CLIENT_ID=a\\nCTRADER_CLIENT_ID=b\\n".replace("\\n", "\n"))
            with self.assertRaises(ValueError):
                setup.read_environment(file)

    def test_reject_invalid_account_id(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "remura.env"
            file.write_text("X=y\\n".replace("\\n", "\n"))
            for candidate in (0, -1, "123", 1 << 64):
                with self.assertRaises(ValueError):
                    setup.save_demo_selection(file, candidate)


if __name__ == "__main__":
    unittest.main()
