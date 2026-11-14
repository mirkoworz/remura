#!/usr/bin/env python3
# REMURA v0.8.27 TEST — 13/11/2026, ore 18:34 CET — pure offline
import contextlib
from io import StringIO
import json
import unittest
from unittest.mock import patch, MagicMock
import bootstrap_settings_guard_v1 as guard

ACCOUNT = "a" * 32
TOKEN = "cfat_" + "x" * 55


class GuardTests(unittest.TestCase):
    def test_only_empty_existing_test_worker_allowed(self):
        self.assertEqual(guard.inspect_settings({
            "success": True,
            "result": {"name": "remura-tv-webhook-test", "bindings": []}
        }), "EXISTING_TEST_ONLY_NO_BINDINGS")

    def test_no_metadata_not_equal_no_bindings(self):
        for bad in (
            {}, {"success": False, "result": {}},
            {"success": True, "result": {}},
            {"success": True, "result": {"name": "remura-tv-webhook-test"}},
            {"success": True, "result": {"bindings": None}},
            {"success": True, "result": {"bindings": {}}},
            {"success": True, "result": []},
        ):
            with self.subTest(bad=bad), self.assertRaises(guard.UnsafeBootstrap):
                guard.inspect_settings(bad)

    def test_main_worker_name_rejected(self):
        with self.assertRaises(guard.UnsafeBootstrap):
            guard.inspect_settings({"success": True, "result": {
                "name": "remura-tv-ingest-lab", "bindings": [],
            }})

    def test_any_binding_rejected_no_matter_its_type(self):
        for kind in ("d1", "secret_text", "plain_text", "ratelimit"):
            with self.subTest(type=kind), self.assertRaises(guard.UnsafeBootstrap):
                guard.inspect_settings({"success": True, "result": {
                    "name": "remura-tv-webhook-test",
                    "bindings": [{"name": "UNEXPECTED", "type": kind}],
                }})

    def test_invalid_account_token_no_network(self):
        for account, token in (("", TOKEN), (ACCOUNT, ""), (ACCOUNT, "short"),
                               ("b" * 33, TOKEN), (ACCOUNT, TOKEN + "\n")):
            with self.subTest(account=account, token_length=len(token)):
                with patch.object(guard, "urlopen") as get:
                    with self.assertRaises(guard.UnsafeBootstrap):
                        guard.check_existing_worker(account, token)
                    get.assert_not_called()

    def test_allowed_get_targets_only_exact_test_settings(self):
        answer = json.dumps({"success": True, "result": {
            "name": "remura-tv-webhook-test", "bindings": [],
        }}).encode()
        conn = MagicMock()
        conn.status = 200
        conn.read.return_value = answer
        conn.__enter__.return_value = conn
        with patch.object(guard, "urlopen", return_value=conn) as call:
            self.assertEqual(guard.check_existing_worker(ACCOUNT, TOKEN),
                             "EXISTING_TEST_ONLY_NO_BINDINGS")
        req = call.call_args.args[0]
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.full_url, "https://api.cloudflare.com/client/v4/accounts/" +
                         ACCOUNT + "/workers/scripts/remura-tv-webhook-test/settings")
        self.assertNotIn("remura-tv-ingest-lab", req.full_url)
        self.assertNotIn(TOKEN, req.full_url)

    def test_http_denial_is_unknown_and_hidden(self):
        from urllib.error import HTTPError
        err = HTTPError("https://example.invalid", 403, "Sensitive", None, None)
        with patch.object(guard, "urlopen", side_effect=err):
            with self.assertRaisesRegex(guard.UnsafeBootstrap, "cloudflare_get_failed"):
                guard.check_existing_worker(ACCOUNT, TOKEN)

    def test_no_secret_logged_on_error(self):
        out = StringIO()
        with patch.object(guard, "check_existing_worker",
                          side_effect=guard.UnsafeBootstrap("secret-" + TOKEN)):
            with patch.dict(guard.os.environ, {
                "REMURA_CF_ACCOUNT_ID": ACCOUNT,
                "REMURA_CF_TEST_WORKER_EDITOR_TOKEN": TOKEN,
            }), contextlib.redirect_stdout(out):
                self.assertEqual(guard.main(), 2)
        self.assertIn("BLOCKED_UNKNOWN_OR_UNSAFE", out.getvalue())
        self.assertNotIn(TOKEN, out.getvalue())
        self.assertNotIn(ACCOUNT, out.getvalue())

    def test_success_does_not_claim_runtime_or_deployment(self):
        output = StringIO()
        with patch.object(guard, "check_existing_worker",
                          return_value="EXISTING_TEST_ONLY_NO_BINDINGS"):
            with contextlib.redirect_stdout(output):
                self.assertEqual(guard.main(), 0)
        self.assertIn("DEPLOY=NOT_YET", output.getvalue())
        self.assertNotIn("WEBHOOK=ACTIVE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
