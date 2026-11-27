# REMURA D1 Storage Guard tests v0.1 — aggiornamento 13/11/2026, ore 06:45 CET
# Solo dati sintetici, no network e no Cloudflare Secrets.
"""Offline tests for the EU TEST database free quota metadata guard."""
import unittest
from unittest.mock import patch

import cloudflare_d1_storage_guard as guard
from cloudflare_d1_readonly_audit import AuditError

UUID = "3bfe9fd1-d711-48cb-bce8-51f8c736a8bc"
TOKEN = "cfat_" + "x" * 50
ACCOUNT = "a" * 32


def metadata(size=4096, **overrides):
    item = {"name": guard.EXPECTED_NAME, "jurisdiction": "eu",
            "uuid": UUID, "file_size": size}
    item.update(overrides)
    return {"success": True, "result": item}


class D1StorageGuardTests(unittest.TestCase):
    def test_small_test_database_ok(self):
        self.assertEqual(guard.inspect_database_metadata(metadata(), UUID), 4096)
        self.assertEqual(guard.assess_storage(4096), "OK")

    def test_free_storage_warning_at_70_percent(self):
        self.assertEqual(guard.assess_storage(350_000_000), "WARNING")

    def test_free_storage_critical_at_90_percent(self):
        self.assertEqual(guard.assess_storage(450_000_000), "CRITICAL")

    def test_below_warning_ok(self):
        self.assertEqual(guard.assess_storage(349_999_999), "OK")

    def test_below_critical_warning(self):
        self.assertEqual(guard.assess_storage(449_999_999), "WARNING")

    def test_metadata_rejects_real_db_name(self):
        with self.assertRaises(AuditError):
            guard.inspect_database_metadata(metadata(name="remura-tv-lab"), UUID)

    def test_metadata_rejects_wrong_region(self):
        with self.assertRaises(AuditError):
            guard.inspect_database_metadata(metadata(jurisdiction="us"), UUID)

    def test_metadata_rejects_different_uuid(self):
        with self.assertRaises(AuditError):
            guard.inspect_database_metadata(metadata(), "00000000-0000-0000-0000-000000000000")

    def test_metadata_rejects_missing_size(self):
        p = metadata()
        del p["result"]["file_size"]
        with self.assertRaises(AuditError):
            guard.inspect_database_metadata(p, UUID)

    def test_metadata_rejects_float_boolean_negative_size(self):
        for size in [-1, True, 1.5, "1024", None]:
            with self.subTest(size=size), self.assertRaises(AuditError):
                guard.inspect_database_metadata(metadata(size), UUID)

    def test_rejects_invalid_size_in_assessment(self):
        for size in [-1, False, 1.5]:
            with self.subTest(size=size), self.assertRaises(AuditError):
                guard.assess_storage(size)

    def test_end_to_end_mocked_get_only(self):
        called = []
        def fake_request(method, path, token):
            called.append((method, path))
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("?name=" + guard.EXPECTED_NAME):
                return {"success": True, "result": [
                    {"name": guard.EXPECTED_NAME, "jurisdiction": "eu", "uuid": UUID}]}
            if path.endswith("/" + UUID):
                return metadata(12_345)
            raise AssertionError("unexpected url")
        with (patch.object(guard, "require_account_id", return_value=ACCOUNT),
              patch.object(guard, "require_account_token", return_value=TOKEN),
              patch.object(guard, "api_request", side_effect=fake_request)):
            size, status = guard.fetch_test_storage(ACCOUNT, TOKEN)
        self.assertEqual((size, status), (12_345, "OK"))
        self.assertEqual(len(called), 3)
        self.assertTrue(all(method == "GET" for method, _ in called))
        self.assertTrue(all("/d1/database" not in path or
                            path.endswith("?name=remura-tv-lab-test") or
                            path.endswith("/" + UUID) for _, path in called))

    def test_truncated_api_payload_fails_closed(self):
        with self.assertRaises(AuditError):
            guard.inspect_database_metadata({"success": False}, UUID)


if __name__ == "__main__":
    unittest.main()
