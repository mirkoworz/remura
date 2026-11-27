#!/usr/bin/env python3
# REMURA v0.8.35 — 13/11/2026 CET — synthetic, offline only
import contextlib
import copy
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

import emergency_stop_test_guard_v1 as a
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
READ = "cfat_" + "x" * 48
EDITOR = "cfat_" + "y" * 48
TEST_UUID = "00000000-0000-4000-8000-000000000002"
MAIN_UUID = "00000000-0000-4000-8000-000000000001"
NS = "812345678901"
SECRET_SENTINEL = "SHOULD_NEVER_APPEAR_IN_LOGS"


def gateway(on=False, secret=False):
    bindings = [
        {"name": "TELEMETRY_DB", "type": "d1", "id": TEST_UUID},
        {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
         "namespace_id": NS, "simple": {"limit": 20, "period": 60}},
        {"name": "INGEST_ENABLED", "type": "plain_text",
         "text": "true" if on else "false"},
    ]
    if secret:
        bindings.append({"name": a.SECRET, "type": "secret_text",
                         "text": SECRET_SENTINEL})
    return {"success": True, "result": {"name": a.WORKER, "bindings": bindings}}


def empty():
    return {"success": True, "result": {"name": a.WORKER, "bindings": []}}


def inventory():
    return {"success": True, "result": [
        {"name": "remura-tv-lab", "uuid": MAIN_UUID, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": TEST_UUID, "jurisdiction": "eu"},
    ], "result_info": {"page": 1, "per_page": 100, "count": 2, "total_count": 2}}


class EmergencyStopGuardTests(unittest.TestCase):
    def inspect(self, obj):
        return a.inspect_before_stop(obj, test_uuid=TEST_UUID, namespace=NS)

    def test_accepts_empty_bootstrap(self):
        self.assertEqual(self.inspect(empty()), "ALREADY_EMPTY_BOOTSTRAP")

    def test_accepts_strict_gateway_off_and_on(self):
        for on in (False, True):
            for secret in (False, True):
                with self.subTest(on=on, secret=secret):
                    state = "ON" if on else "OFF"
                    suff = "WITH_HASH_SECRET" if secret else "NO_SECRET"
                    self.assertEqual(self.inspect(gateway(on, secret)),
                                     "TEST_GATEWAY_" + state + "_" + suff)

    def test_rejects_main_database_and_missing_identity(self):
        for change in ("main", "missing", "wrongtype"):
            obj = gateway(on=True, secret=True)
            db = obj["result"]["bindings"][0]
            if change == "main": db["id"] = MAIN_UUID
            elif change == "missing": del db["id"]
            else: db["type"] = "kv_namespace"
            with self.subTest(change=change), self.assertRaises(a.StopUnsafe):
                self.inspect(obj)

    def test_rejects_unknown_worker_even_if_valid(self):
        obj = gateway(True, True)
        obj["result"]["name"] = "remura-tv-ingest-lab"
        with self.assertRaises(a.StopUnsafe):
            self.inspect(obj)

    def test_rejects_unknown_or_weakened_limiter(self):
        for name, value in (("ns", "5"), ("limit", 200), ("period", 10)):
            obj = gateway(True, True)
            rl = obj["result"]["bindings"][1]
            if name == "ns": rl["namespace_id"] = value
            else: rl["simple"][name] = value
            with self.subTest(name=name), self.assertRaises(a.StopUnsafe):
                self.inspect(obj)

    def test_rejects_untrusted_flag_and_secret_type(self):
        for flag in ("TRUE", "1", None, True, ""):
            obj = gateway(True, True)
            obj["result"]["bindings"][2]["text"] = flag
            with self.subTest(flag=flag), self.assertRaises(a.StopUnsafe):
                self.inspect(obj)
        obj = gateway(True, True)
        obj["result"]["bindings"][3]["type"] = "plain_text"
        with self.assertRaises(a.StopUnsafe):
            self.inspect(obj)

    def test_rejects_extra_or_duplicate_bindings(self):
        for item in (
            {"name": "OTHER", "type": "secret_text"},
            {"name": "INGEST_ENABLED", "type": "plain_text", "text": "false"},
        ):
            obj = gateway(True, True)
            obj["result"]["bindings"].append(item)
            with self.subTest(item=item), self.assertRaises(a.StopUnsafe):
                self.inspect(obj)

    def test_rejects_malformed_or_untrusted_envelope(self):
        for obj in ({}, {"success": False}, {"success": True},
                    {"success": True, "result": {}},
                    {"success": True, "result": {"bindings": None}},
                    {"success": True, "result": {"bindings": {}}},
                    {"success": True, "result": {"bindings": ["bad"]}}):
            with self.subTest(obj=obj), self.assertRaises(a.StopUnsafe):
                self.inspect(obj)

    def test_secret_may_remain_after_inert_deploy_but_no_other_bindings(self):
        self.assertEqual(a.inspect_after_inert_deploy(empty()), "INERT_NO_BINDINGS")
        obj = empty()
        obj["result"]["bindings"].append(
            {"name": a.SECRET, "type": "secret_text", "text": SECRET_SENTINEL})
        self.assertEqual(a.inspect_after_inert_deploy(obj),
                         "INERT_SECRET_STILL_STORED")
        for bad in (gateway(on=False, secret=False), gateway(on=True, secret=True),
                    {"success": True, "result": {"name": a.WORKER, "bindings": [
                        {"name": "EXTRA", "type": "plain_text", "text": "true"}]}}):
            with self.assertRaises(a.StopUnsafe):
                a.inspect_after_inert_deploy(bad)

    def test_rejects_unverified_uuid_and_namespace(self):
        for invalid in ("", None, "not-uuid", MAIN_UUID[:20]):
            with self.assertRaises(a.StopUnsafe):
                a.inspect_before_stop(gateway(), test_uuid=invalid, namespace=NS)
        for invalid in ("0", None, "", "abc", "-1"):
            with self.assertRaises(a.StopUnsafe):
                a.inspect_before_stop(gateway(), test_uuid=TEST_UUID, namespace=invalid)

    def test_live_preflight_is_only_two_auth_gets(self):
        calls = []
        def d1(method, path, token):
            self.assertEqual(method, "GET")
            self.assertIn("/d1/database?", path)
            self.assertNotIn("/query", path)
            self.assertEqual(token, READ)
            calls.append("D1_GET")
            return inventory()
        def worker(account, token, path):
            self.assertEqual((account, token, path), (ACCOUNT, EDITOR, "/settings"))
            calls.append("TEST_SETTINGS_GET")
            return gateway(on=True, secret=True)
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=READ),
              patch.object(a, "api_request", side_effect=d1),
              patch.object(a, "api_get", side_effect=worker),
              patch.object(a, "choose_candidate_namespace", return_value=NS)):
            state = a.preflight(ACCOUNT, READ, EDITOR)
        self.assertEqual(state, "TEST_GATEWAY_ON_WITH_HASH_SECRET")
        self.assertEqual(calls, ["D1_GET", "TEST_SETTINGS_GET"])

    def test_editor_missing_fails_before_network(self):
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "api_request") as d1,
              patch.object(a, "api_get") as get):
            with self.assertRaises(a.StopUnsafe):
                a.preflight(ACCOUNT, READ, "")
        d1.assert_not_called()
        get.assert_not_called()

    def test_main_never_prints_sensitive_exception(self):
        with (patch.object(a, "preflight", side_effect=AuditError(SECRET_SENTINEL)),
              contextlib.redirect_stdout(StringIO()) as out):
            self.assertEqual(a.main(), 2)
        self.assertNotIn(SECRET_SENTINEL, out.getvalue())
        self.assertIn("BLOCKED_FAIL_CLOSED", out.getvalue())

    def test_after_main_reports_secret_without_disclosing_its_value(self):
        with (patch.object(a, "postdeploy", return_value="INERT_SECRET_STILL_STORED"),
              contextlib.redirect_stdout(StringIO()) as out):
            self.assertEqual(a.after_main(), 0)
        self.assertNotIn(SECRET_SENTINEL, out.getvalue())
        self.assertIn("SECRET_VALUE=NEVER_READ", out.getvalue())
        self.assertIn("EDGE_TRAFFIC_ALLOCATION=NOT_VERIFIED", out.getvalue())

    def test_sources_never_contact_production_or_write_db(self):
        source = Path(a.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/workers/scripts/remura-tv-ingest-lab", source)
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("wrangler deploy", source)


if __name__ == "__main__":
    unittest.main()
