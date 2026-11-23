"""REMURA B V21.7 — offline transport safety for at-most-two CFTC GETs.
No network access: all responses are local in-memory objects or mocks.
"""
from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cot_public_two_date_archive_v216 import (
    _DenyRedirects, read_once, official_query,
)


class DummyResponse:
    def __init__(self, url, status=200, raw=b"[]"):
        self._url = url
        self.status = status
        self._io = io.BytesIO(raw)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        self._io.close()
        return False
    def geturl(self):
        return self._url
    def read(self, n=-1):
        return self._io.read(n)


class TransportNoRetryTests(unittest.TestCase):
    def test_redirect_handler_rejects_301_302_307_and_308_without_new_request(self):
        handler = _DenyRedirects()
        for status in (301, 302, 307, 308):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "REDIRECT_REJECTED"):
                    handler.redirect_request(None, None, status, "redirect",
                                             {}, "https://untrusted.example")

    def test_default_transport_installs_no_redirects_and_no_proxy(self):
        url = official_query("tff")
        calls = []
        class Opener:
            def open(self, req, timeout):
                calls.append((req.full_url, timeout))
                return DummyResponse(url)
        with patch("cot_public_two_date_archive_v216.urllib.request.build_opener",
                   return_value=Opener()) as build:
            self.assertEqual(read_once("tff"), [])
        self.assertEqual(calls, [(url, 20)])
        handlers = build.call_args.args
        self.assertIn(_DenyRedirects, handlers)
        self.assertTrue(any(type(handler).__name__ == "ProxyHandler"
                            and handler.proxies == {} for handler in handlers))

    def test_changed_response_url_rejected_even_if_injected_opener_returns_body(self):
        url = official_query("tff")
        counter = []
        def changed(req, timeout):
            counter.append(req.full_url)
            return DummyResponse("https://untrusted.example/other.json")
        with self.assertRaisesRegex(ValueError, "RESPONSE_URL_CHANGED"):
            read_once("tff", opener=changed)
        self.assertEqual(counter, [url])

    def test_non_200_status_and_oversize_rejected_without_fallback(self):
        url = official_query("disagg")
        for response, expected in ((DummyResponse(url, status=206), "NOT_HTTP_200"),
                                   (DummyResponse(url, raw=b""), "EMPTY_OR_TOO_LARGE")):
            with self.subTest(reason=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    read_once("disagg", opener=lambda req, timeout, response=response: response)


if __name__ == "__main__":
    unittest.main()
