# REMURA Worker PUBLIC FAIL-CLOSED AUDIT tests v0.2 — 13/11/2026 ore 06:57 CET
# Prove esclusivamente offline: non fare richieste HTTP reali.
"""Unit tests for strict GET-only Cloudflare Worker public health auditing."""
import unittest
from unittest.mock import patch

import worker_public_failclosed_audit as audit


class FakeResponse:
    def __init__(self, status, raw):
        self.status = status
        self.raw = raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, length):
        return self.raw[:length]


class FakeOpener:
    def __init__(self):
        self.calls = []
    def open(self, req, timeout):
        self.calls.append((req.full_url, req.get_method(), timeout))
        return FakeResponse(200, b'{"status":"lab_only","accepting":false}')


class PublicFailclosedAuditTests(unittest.TestCase):
    def test_two_edge_denials_are_inconclusive_not_verified(self):
        self.assertEqual(audit.classify_public_state(
            (403, {"status": "forbidden"}), (403, {"status": "forbidden"})),
            "INCONCLUSIVE_EDGE_403")

    def test_mixed_403_and_health_200_is_not_verified(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.classify_public_state(
                (403, {"status": "forbidden"}), (503, {"status": "disabled"}))

    def test_true_ingest_in_403_body_is_never_classed_as_safe(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.classify_public_state(
                (403, {"accepting": True}), (403, {"status": "forbidden"}))

    def test_valid_public_health_is_verified(self):
        self.assertEqual(audit.classify_public_state(
            (200, {"status": "lab_only", "accepting": False}),
            (503, {"status": "disabled"})), "VERIFIED_DISABLED")

    def test_valid_failclosed_response(self):
        audit.validate_failclosed(
            (200, {"status": "lab_only", "accepting": False}),
            (503, {"status": "disabled"}))

    def test_health_says_accepting_true_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (200, {"status": "lab_only", "accepting": True}),
                (503, {"status": "disabled"}))

    def test_health_missing_accepting_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (200, {"status": "lab_only"}), (503, {"status": "disabled"}))

    def test_health_false_as_string_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (200, {"status": "lab_only", "accepting": "false"}),
                (503, {"status": "disabled"}))

    def test_health_not_200_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (503, {"status": "lab_only", "accepting": False}),
                (503, {"status": "disabled"}))

    def test_root_not_503_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (200, {"status": "lab_only", "accepting": False}),
                (200, {"status": "disabled"}))

    def test_root_unexpected_status_rejected(self):
        with self.assertRaises(audit.GatewayNotSafe):
            audit.validate_failclosed(
                (200, {"status": "lab_only", "accepting": False}),
                (503, {"status": "active"}))

    def test_exact_https_get_no_credentials(self):
        opener = FakeOpener()
        status, body = audit.fetch_public("/health", opener)
        self.assertEqual(status, 200)
        self.assertIs(body["accepting"], False)
        self.assertEqual(opener.calls, [
            (audit.BASE + "/health", "GET", 10)])

    def test_unsafe_url_path_rejected_before_network(self):
        opener = FakeOpener()
        for path in ("/ingest/fake", "//evil.tld", "https://evil.invalid", "/health?key=secret"):
            with self.subTest(path=path), self.assertRaises(audit.GatewayNotSafe):
                audit.fetch_public(path, opener)
        self.assertEqual(opener.calls, [])

    def test_non_json_rejected(self):
        class InvalidOpener:
            def open(self, req, timeout):
                return FakeResponse(200, b"<html>Not JSON</html>")
        with self.assertRaises(audit.GatewayNotSafe):
            audit.fetch_public("/health", InvalidOpener())

    def test_large_response_rejected(self):
        class LargeOpener:
            def open(self, req, timeout):
                return FakeResponse(200, b"x" * 2200)
        with self.assertRaises(audit.GatewayNotSafe):
            audit.fetch_public("/health", LargeOpener())

    def test_unreachable_rejected(self):
        from urllib.error import URLError
        class Offline:
            def open(self, req, timeout):
                raise URLError("simulated outage")
        with self.assertRaises(audit.GatewayNotSafe):
            audit.fetch_public("/health", Offline())

    def test_client_only_requests_static_expected_base(self):
        self.assertEqual(audit.BASE, "https://remura-tv-ingest-lab.mirkoworz.workers.dev")
        self.assertEqual(audit.ALLOWED_PATHS, {"/", "/health"})


if __name__ == "__main__":
    unittest.main()
