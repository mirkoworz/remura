"""Offline tests for private interactive Myfxbook setup; no real credentials."""
import contextlib
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import setup_myfxbook as setup


class MyfxbookSetupTests(unittest.TestCase):
    def test_quotes_special_characters_for_systemd_environment_file(self):
        value = "test\\\"'$" + "`" + "= spaces!"
        encoded = setup.quote_systemd(value)
        self.assertTrue(encoded.startswith('"') and encoded.endswith('"'))
        self.assertIn('\\\"', encoded)
        self.assertIn('\\$', encoded)
        self.assertIn('\\`', encoded)
        self.assertIn('\\\\', encoded)

    def test_preserves_other_variables_and_deduplicates_keys(self):
        orig = ("REMURA_SYMBOLS=EURUSD,USDJPY\n"
                "CTRADER_CLIENT_ID=not-a-real-token\n"
                "REMURA_RETAIL_ENABLED=0\n"
                "MYFXBOOK_EMAIL=old@test.invalid\n"
                "MYFXBOOK_PASSWORD=old\n"
                "REMURA_RETAIL_ENABLED=0\n")
        result = setup.updated_environment(orig, "new@test.invalid", "fake$\\\"password")
        self.assertIn("REMURA_SYMBOLS=EURUSD,USDJPY", result)
        self.assertIn("CTRADER_CLIENT_ID=not-a-real-token", result)
        for key in setup.RETAIL_KEYS:
            self.assertEqual(result.count(key + "="), 1)
        self.assertIn("REMURA_RETAIL_ENABLED=1", result)

    def test_atomic_write_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "remura.env"
            file.write_text("REMURA_SYMBOLS=EURUSD\nREMURA_RETAIL_ENABLED=0\n", encoding="utf-8")
            os.chmod(file, 0o600)
            setup.save_private_credentials(file, "test@example.invalid", "dummy password")
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
            self.assertIn("REMURA_RETAIL_ENABLED=1", file.read_text("utf-8"))
            self.assertIn("REMURA_SYMBOLS=EURUSD", file.read_text("utf-8"))
            setup.save_private_credentials(file, "test@example.invalid", "dummy password")
            self.assertEqual(file.read_text("utf-8").count("MYFXBOOK_PASSWORD="), 1)

    def test_invalid_values_fail_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "remura.env"
            file.write_text("REMURA_SYMBOLS=EURUSD\n", encoding="utf-8")
            os.chmod(file, 0o600)
            with self.assertRaises(ValueError):
                setup.save_private_credentials(file, "not-an-email", "dummy")
            with self.assertRaises(ValueError):
                setup.save_private_credentials(file, "test@example.invalid", "bad\npassword")
            self.assertEqual(file.read_text("utf-8"), "REMURA_SYMBOLS=EURUSD\n")

    def test_refuses_symlinks_or_unsafe_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real.env"
            real.write_text("REMURA_SYMBOLS=EURUSD\n", encoding="utf-8")
            alias = Path(directory) / "alias.env"
            alias.symlink_to(real)
            with self.assertRaises(RuntimeError):
                setup.save_private_credentials(alias, "a@b.test", "dummy")
            os.chmod(real, 0o644)
            with self.assertRaises(RuntimeError):
                setup.save_private_credentials(real, "a@b.test", "dummy")
            self.assertEqual(real.read_text("utf-8"), "REMURA_SYMBOLS=EURUSD\n")

    def test_non_interactive_does_not_prompt(self):
        with patch.object(setup.sys.stdin, "isatty", return_value=False), \
             patch.object(setup.getpass, "getpass") as prompt, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(), 1)
        prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
