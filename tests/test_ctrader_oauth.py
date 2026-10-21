"""Offline checks for the private, read-only cTrader OAuth bootstrap."""
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ctrader_oauth as oauth
import private_server

CONFIG = {
    "CTRADER_CLIENT_ID": "dummy-test-app",
    "CTRADER_CLIENT_SECRET": "dummy-test-secret",
    "CTRADER_REDIRECT_URI": "https://remura-server.example.ts.net/ctrader/callback",
}


class OAuthTests(unittest.TestCase):
    def test_read_only_url_and_strict_redirect(self):
        url = oauth.authorization_url(CONFIG)
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["scope"], ["accounts"])
        self.assertEqual(query["redirect_uri"], [CONFIG["CTRADER_REDIRECT_URI"]])
        self.assertNotIn("trading", url)
        self.assertNotIn(CONFIG["CTRADER_CLIENT_SECRET"], url)
        with self.assertRaises(ValueError):
            oauth.authorization_url({**CONFIG,
                "CTRADER_REDIRECT_URI": "https://public.example.com/ctrader/callback"})

    def test_exchange_keeps_tokens_private(self):
        with tempfile.TemporaryDirectory() as d:
            destination = Path(d) / "private" / "db.sqlite"
            recorded = []
            def requester(req):
                recorded.append(req)
                return {"accessToken": "test_access", "refreshToken": "test_refresh",
                        "expiresIn": 2628000, "errorCode": None}
            self.assertTrue(oauth.exchange_code("test-code_123", CONFIG, destination, requester))
            token_file = destination.parent / "ctrader-tokens.json"
            self.assertEqual(token_file.stat().st_mode & 0o777, 0o600)
            saved = json.loads(token_file.read_text())
            self.assertEqual(saved["refreshToken"], "test_refresh")
            self.assertEqual(len(recorded), 1)
            self.assertIn("grant_type=authorization_code", recorded[0].full_url)

    def test_provider_error_details_are_reduced_to_safe_labels(self):
        descriptions = {
            "Client Secret is invalid, test-token-DO-NOT-LOG": "CLIENT_SECRET",
            "The redirect URI is incorrect: https://unsafe.invalid/callback?code=SECRET": "REDIRECT_URI",
            "This code has expired": "EXPIRED_CODE",
            "The authorization code has already been used": "REUSED_CODE",
            "Wrong authorization code": "AUTH_CODE",
            "A required request parameter is missing": "PARAMETERS",
        }
        for description, expected in descriptions.items():
            with self.subTest(description=expected):
                self.assertEqual(oauth._safe_error_detail(description), expected)
        self.assertEqual(oauth._safe_error_detail("secret-value-with-no-info"), "OTHER")

    def test_provider_denial_is_logged_without_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "private" / "db.sqlite"
            def denied(req):
                return {
                    "errorCode": "ACCESS_DENIED",
                    "description": "Secret value must never be logged",
                }
            with self.assertRaises(RuntimeError):
                oauth.exchange_code("test-code_123", CONFIG, dest, denied)
            status_file = dest.parent / "ctrader-oauth-status.json"
            self.assertEqual(status_file.stat().st_mode & 0o777, 0o600)
            raw = status_file.read_text()
            self.assertEqual(json.loads(raw)["result"], "API_ACCESS_DENIED_DETAIL_OTHER")
            self.assertNotIn("Secret value", raw)
            self.assertNotIn(CONFIG["CTRADER_CLIENT_SECRET"], raw)
            self.assertNotIn("test-code_123", raw)
            self.assertFalse((dest.parent / "ctrader-tokens.json").exists())

    def test_failed_exchange_does_not_disclose_or_store_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "private" / "db.sqlite"
            def bad_request(req):
                raise ValueError("TOP SECRET: DO NOT PRINT")
            with self.assertRaisesRegex(RuntimeError, "OAuth non riuscito") as failure:
                oauth.exchange_code("test-code_123", CONFIG, dest, bad_request)
            self.assertNotIn("TOP SECRET", str(failure.exception))
            self.assertFalse((dest.parent / "ctrader-tokens.json").exists())


class BrowserCallbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, CONFIG)
        self.env.start()
        self.folder = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0),
            private_server.http_handler(Path(self.folder.name) / "db.sqlite"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.folder.cleanup()
        self.env.stop()

    def request(self, path, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        headers = {"Cookie": cookie} if cookie else {}
        conn.request("GET", path, headers=headers)
        r = conn.getresponse()
        data = (r.status, dict(r.getheaders()), r.read())
        conn.close()
        return data

    def test_browser_bound_and_one_time(self):
        status, headers, body = self.request("/ctrader/start")
        self.assertEqual(status, 303)
        self.assertIn("scope=accounts", headers["Location"])
        self.assertNotIn("dummy-test-secret", headers["Location"])
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.assertIn("Secure", headers["Set-Cookie"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", headers["Set-Cookie"])
        code = "test-code_123"
        with patch.object(private_server, "exchange_code", return_value=True) as exchange:
            status, headers, body = self.request("/ctrader/callback?code=" + code)
            self.assertEqual(status, 303)
            self.assertEqual(headers["Location"], "/ctrader/result?result=denied")
            exchange.assert_not_called()
            status, headers, body = self.request("/ctrader/callback?code=" + code, cookie)
            self.assertEqual(status, 303)
            self.assertEqual(headers["Location"], "/ctrader/result?result=ok")
            self.assertNotIn(code, str(headers) + str(body))
            self.assertEqual(exchange.call_count, 1)
            status, headers, body = self.request("/ctrader/callback?code=" + code, cookie)
            self.assertEqual(status, 303)
            self.assertEqual(headers["Location"], "/ctrader/result?result=denied")
            self.assertEqual(exchange.call_count, 1)


if __name__ == "__main__":
    unittest.main()
