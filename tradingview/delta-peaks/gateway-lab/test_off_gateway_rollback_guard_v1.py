#!/usr/bin/env python3
# REMURA v0.8.31 TEST — 13/11/2026, ore 21:09 CET — OFFLINE
import copy
import unittest
from off_gateway_rollback_guard_v1 import inspect_worker_bindings, RollbackUnsafe

TEST_UUID = "00000000-0000-4000-8000-000000000002"
MAIN_UUID = "00000000-0000-4000-8000-000000000001"
NAMESPACE = "812345678901"


def body(bindings=None):
    if bindings is None:
        bindings = [
            {"name": "TELEMETRY_DB", "type": "d1", "id": TEST_UUID},
            {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
             "namespace_id": NAMESPACE,
             "simple": {"limit": 20, "period": 60}},
            {"name": "INGEST_ENABLED", "type": "plain_text", "text": "false"},
        ]
    return {"success": True, "result": {
        "name": "remura-tv-webhook-test", "bindings": bindings}}


def inspect(payload, test_uuid=TEST_UUID, ns=NAMESPACE):
    return inspect_worker_bindings(payload, verified_test_uuid=test_uuid,
                                   expected_namespace=ns)


class RollbackGuardTests(unittest.TestCase):
    def test_empty_bootstrap_allowed(self):
        self.assertEqual(inspect(body([])), "BOOTSTRAP_ALREADY_EMPTY")

    def test_strict_gateway_off_allowed(self):
        self.assertEqual(inspect(body()), "TEST_GATEWAY_OFF_STRICT_NO_SECRET")

    def test_database_main_binding_rejected(self):
        data = body()
        data["result"]["bindings"][0]["id"] = MAIN_UUID
        with self.assertRaises(RollbackUnsafe):
            inspect(data)

    def test_missing_d1_id_not_passed(self):
        data = body()
        del data["result"]["bindings"][0]["id"]
        with self.assertRaises(RollbackUnsafe):
            inspect(data)

    def test_limiting_namespace_differs(self):
        data = body()
        data["result"]["bindings"][1]["namespace_id"] = "99999999"
        with self.assertRaises(RollbackUnsafe):
            inspect(data)

    def test_missing_or_weakened_rate_limiter(self):
        for bad in ({"limit": 999, "period": 60},
                    {"limit": 20, "period": 10}, None, {}):
            data = body()
            data["result"]["bindings"][1]["simple"] = bad
            with self.subTest(bad=bad), self.assertRaises(RollbackUnsafe):
                inspect(data)

    def test_ingest_true_and_missing_value(self):
        for value in ("true", True, None, ""):
            data = body()
            data["result"]["bindings"][2]["text"] = value
            with self.subTest(value=value), self.assertRaises(RollbackUnsafe):
                inspect(data)

    def test_any_extra_secret_or_binding_rejected(self):
        data = body()
        data["result"]["bindings"].append(
            {"name": "WEBHOOK_TOKEN_SHA256", "type": "secret_text"})
        with self.assertRaises(RollbackUnsafe):
            inspect(data)

    def test_wrong_worker_name_rejected(self):
        data = body()
        data["result"]["name"] = "remura-tv-ingest-lab"
        with self.assertRaises(RollbackUnsafe):
            inspect(data)

    def test_ambiguous_metadata_fail_closed(self):
        for val in ({}, {"success": False}, {"success": True, "result": {}},
                    {"success": True, "result": {"bindings": None}},
                    {"success": True, "result": {"bindings": {}}}):
            with self.subTest(val=val), self.assertRaises(RollbackUnsafe):
                inspect(val)

    def test_invalid_d1_uuid_and_namespace_rejected(self):
        for candidate in (None, "", "unknown", MAIN_UUID[:8]):
            with self.subTest(candidate=candidate), self.assertRaises(RollbackUnsafe):
                inspect(body(), test_uuid=candidate)
        for ns in ("", "0", "-1", "12hello", None):
            with self.subTest(ns=ns), self.assertRaises(RollbackUnsafe):
                inspect(body(), ns=ns)

    def test_duplicate_binding_names_rejected(self):
        data = body()
        data["result"]["bindings"][1] = copy.deepcopy(data["result"]["bindings"][0])
        with self.assertRaises(RollbackUnsafe):
            inspect(data)


if __name__ == "__main__":
    unittest.main()
