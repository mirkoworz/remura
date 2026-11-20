# REMURA D1 ACCOUNT STORAGE TESTS v0.8.14 — 13/11/2026, ore 12:05 CET
# Solo fixture sintetiche; nessuna rete, credenziali o D1 reale.
import unittest
from unittest.mock import patch

import cloudflare_d1_account_storage_guard as guard
from cloudflare_d1_readonly_audit import AuditError

ID1 = "3bfe9fd1-d711-48cb-bce8-51f8c736a8bc"
ID2 = "8cd1fbea-282a-42cd-b2ba-83ef3159f785"
ID3 = "a1fd4433-d2de-4ac2-8377-0f5f0d3e59f1"
ACCOUNT = "a" * 32
TOKEN = "cfat_" + "x" * 48

def entries():
    return [
        {"name": "remura-tv-lab", "uuid": ID1, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": ID2, "jurisdiction": "eu"},
    ]

def inventory(rows=None, **info_overrides):
    rows = entries() if rows is None else rows
    info = {"page": 1, "per_page": 100, "count": len(rows),
            "total_count": len(rows)}
    info.update(info_overrides)
    return {"success": True, "result": rows, "result_info": info}

def metadata(row, size):
    return {"success": True, "result": {
        "uuid": row["uuid"], "name": row["name"],
        "jurisdiction": row.get("jurisdiction"), "file_size": size,
    }}

class AccountStorageTests(unittest.TestCase):
    def test_complete_inventory(self):
        self.assertEqual(len(guard.parse_inventory(inventory())), 2)

    def test_missing_pagination_is_unknown(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory({"success": True, "result": entries()})

    def test_partial_page_is_unknown_not_zero(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory(total_count=3))

    def test_page_other_than_one_is_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory(page=2))

    def test_missing_required_database_is_unknown(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory(entries()[:1]))

    def test_unexpected_jurisdiction_is_rejected(self):
        rows = entries()
        rows[0]["jurisdiction"] = "us"
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory(rows))

    def test_duplicate_ids_or_names_are_rejected(self):
        for idx in ("name", "uuid"):
            rows = entries()
            rows[1][idx] = rows[0][idx]
            with self.subTest(field=idx), self.assertRaises(AuditError):
                guard.parse_inventory(inventory(rows))

    def test_noninteger_total_is_unknown(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory(total_count="2"))

    def test_empty_inventory_is_unknown(self):
        with self.assertRaises(AuditError):
            guard.parse_inventory(inventory([]))

    def test_metadata_identity_mismatch_rejected(self):
        row = entries()[0]
        with self.assertRaises(AuditError):
            guard.read_db_size(metadata(row, 300), row["name"], ID2, "eu")

    def test_optional_jurisdiction_for_unrelated_database(self):
        row = {"name": "unrelated-db", "uuid": ID3}
        meta = {"success": True, "result": {
            "name": row["name"], "uuid": ID3,
            "jurisdiction": "us", "file_size": 2048}}
        self.assertEqual(guard.read_db_size(meta, row["name"], ID3, None), 2048)
        with self.assertRaises(AuditError):
            guard.read_db_size(meta, row["name"], ID3, "eu")

    def test_missing_or_noninteger_size_rejected(self):
        row = entries()[0]
        for size in (None, True, -10, 1.2, "100"):
            with self.subTest(size=size), self.assertRaises(AuditError):
                guard.read_db_size(metadata(row, size), row["name"], row["uuid"], "eu")

    def test_thresholds_for_aggregate_space(self):
        self.assertEqual(guard.assessment(2, 3_499_999_999, 300_000_000), "OK")
        self.assertEqual(guard.assessment(2, 3_500_000_000, 300_000_000), "WARNING")
        self.assertEqual(guard.assessment(2, 4_500_000_000, 300_000_000), "CRITICAL")

    def test_thresholds_for_largest_database(self):
        self.assertEqual(guard.assessment(2, 350_000_000, 350_000_000), "WARNING")
        self.assertEqual(guard.assessment(2, 450_000_000, 450_000_000), "CRITICAL")

    def test_thresholds_for_database_count(self):
        self.assertEqual(guard.assessment(6, 40_000, 20_000), "OK")
        self.assertEqual(guard.assessment(7, 40_000, 20_000), "WARNING")
        self.assertEqual(guard.assessment(9, 40_000, 20_000), "CRITICAL")

    def test_invalid_assessment_is_rejected(self):
        for values in ((0, 0, 0), (2, -1, 0), (True, 1, 1)):
            with self.subTest(values=values), self.assertRaises(AuditError):
                guard.assessment(*values)

    def test_get_only_full_account_inventory_without_names_in_log(self):
        calls = []
        rows = entries() + [{"name": "unrelated-db", "uuid": ID3, "jurisdiction": None}]
        sizes = {ID1: 28_672, ID2: 16_384, ID3: 100_000}
        def fake_api(method, path, token):
            calls.append((method, path))
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("?page=1&per_page=100"):
                return inventory(rows)
            for row in rows:
                if path.endswith("/" + row["uuid"]):
                    return metadata(row, sizes[row["uuid"]])
            raise AssertionError("unexpected remote request")
        with (patch.object(guard, "require_account_id", return_value=ACCOUNT),
              patch.object(guard, "require_account_token", return_value=TOKEN),
              patch.object(guard, "api_request", side_effect=fake_api)):
            stats = guard.fetch_account_storage(ACCOUNT, TOKEN)
        self.assertEqual(stats, {"count": 3, "bytes": 145_056,
                                 "largest": 100_000, "status": "OK"})
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(method == "GET" for method, _ in calls))
        self.assertTrue(all("/query" not in path and "/raw" not in path
                            for _, path in calls))

    def test_metadata_read_failure_is_unknown_not_partial(self):
        rows = entries()
        def fake_api(method, path, token):
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("per_page=100"):
                return inventory(rows)
            return {"success": False, "result": None}
        with (patch.object(guard, "require_account_id", return_value=ACCOUNT),
              patch.object(guard, "require_account_token", return_value=TOKEN),
              patch.object(guard, "api_request", side_effect=fake_api)):
            with self.assertRaises(AuditError):
                guard.fetch_account_storage(ACCOUNT, TOKEN)


if __name__ == "__main__":
    unittest.main()
