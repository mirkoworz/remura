# REMURA Cloudflare D1 READ-ONLY Audit tests v0.3 — aggiornamento 12/11/2026 ore 23:21 CET
# Prove locali senza rete; mai importare token e non eseguire operazioni remote.
"""Offline unit tests for Cloudflare D1 read-only guardrails."""
import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).with_name("cloudflare_d1_readonly_audit.py")
SPEC = importlib.util.spec_from_file_location("remura_cf_d1_audit", FILE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

TEST_UUID = "3bfe9fd1-d711-48cb-bce8-51f8c736a8bc"


class CloudflareD1ReadOnlyAuditTests(unittest.TestCase):
    def fixture(self, name="remura-tv-lab-test", jurisdiction="eu"):
        return {"success": True, "result": [
            {"name": name, "jurisdiction": jurisdiction, "uuid": TEST_UUID}
        ]}

    def record(self, **changes):
        row = {"event_key": audit.TEST_KEY, "symbol": "LAB:TEST_ONLY",
               "version": "synthetic-test-v0.1", "is_timely": 0}
        row.update(changes)
        return {"success": True, "result": [
            {"success": True, "results": [row]}
        ]}

    def test_active_account_token(self):
        self.assertIsNone(audit.verify_account_token(
            {"success": True, "result": {"status": "active", "id": "redacted"}}))

    def test_disabled_account_token_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.verify_account_token(
                {"success": True, "result": {"status": "disabled"}})

    def test_unverified_account_token_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.verify_account_token({"success": False, "result": None})

    def test_valid_test_database(self):
        self.assertEqual(audit.find_test_database(self.fixture()), TEST_UUID)

    def test_wrong_database_name_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.find_test_database(self.fixture(name="remura-tv-lab"))

    def test_wrong_jurisdiction_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.find_test_database(self.fixture(jurisdiction="us"))

    def test_multiple_matching_databases_rejected(self):
        p = self.fixture()
        p["result"].append(p["result"][0].copy())
        with self.assertRaises(audit.AuditError):
            audit.find_test_database(p)

    def test_cloudflare_error_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.find_test_database({"success": False, "result": []})

    def test_exact_synthetic_record(self):
        self.assertEqual(audit.inspect_test_record(self.record()), "record_verified")

    def test_missing_test_record_is_distinct(self):
        p = self.record()
        p["result"][0]["results"] = []
        self.assertEqual(audit.inspect_test_record(p), "record_missing")

    def test_market_record_must_not_pass(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_test_record(self.record(symbol="FXCM:EURUSD"))

    def test_wrong_synthetic_version_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_test_record(self.record(version="0.8.1-lab"))

    def test_invalid_account_id(self):
        with self.assertRaises(audit.AuditError):
            audit.require_account_id("")

    def test_correct_account_guard(self):
        self.assertEqual(audit.require_account_id("815b7a67ba41bf986b336978e6bcb5d9"),
                         "815b7a67ba41bf986b336978e6bcb5d9")

    def test_wrong_account_guard(self):
        with self.assertRaises(audit.AuditError):
            audit.require_account_id("00000000000000000000000000000000")

    def test_account_token_prefix_guard(self):
        self.assertEqual(audit.require_account_token("  cfat_" + "x" * 50 + "\\n"),
                         "cfat_" + "x" * 50)

    def test_wrong_account_token_prefix_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.require_account_token("cfut_" + "x" * 50)

    def test_sql_is_select_and_fixed_target(self):
        self.assertTrue(audit.SQL.startswith("SELECT "))
        self.assertNotIn("DELETE", audit.SQL.upper())
        self.assertEqual(audit.EXPECTED_NAME, "remura-tv-lab-test")


if __name__ == "__main__":
    unittest.main()
