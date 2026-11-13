# REMURA Workers Analytics Guard tests v0.1 — aggiornamento 13/11/2026, ore 10:06 CET
# Solo sintesi GraphQL offline, nessun token o chiamata internet.
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import cloudflare_workers_usage_guard as guard
from cloudflare_d1_readonly_audit import AuditError


def sample_rows(requests=5, errors=0, subrequests=1, cpu=800.0,
                name="remura-tv-ingest-lab"):
    return {"data": {"viewer": {"accounts": [{
        "workersInvocationsAdaptive": [{
            "dimensions": {"scriptName": name, "status": "success"},
            "sum": {"requests": requests, "errors": errors, "subrequests": subrequests},
            "quantiles": {"cpuTimeP99": cpu},
        }]
    }]}}}


class WorkerMetricsTests(unittest.TestCase):
    def test_parse_worker_metrics(self):
        got = guard.parse_workers(sample_rows())
        self.assertEqual(got["requests_estimate"], 5)
        self.assertEqual(got["errors_estimate"], 0)
        self.assertEqual(got["script_count"], 1)
        self.assertEqual(got["max_reported_cpu_p99_us"], 800.0)

    def test_aggregate_distinct_scripts(self):
        p = sample_rows()
        p["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"].append({
            "dimensions": {"scriptName": "telegram-mirko-bridge", "status": "success"},
            "sum": {"requests": 8, "errors": 1, "subrequests": 1},
            "quantiles": {"cpuTimeP99": 1200.0}})
        got = guard.parse_workers(p)
        self.assertEqual(got["requests_estimate"], 13)
        self.assertEqual(got["script_count"], 2)
        self.assertEqual(got["max_reported_cpu_p99_us"], 1200.0)

    def test_empty_response_is_unknown_not_zero(self):
        p = sample_rows()
        p["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"] = []
        self.assertIsNone(guard.parse_workers(p))

    def test_full_page_is_truncated_not_safe(self):
        p = sample_rows()
        p["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"] *= guard.MAX_GROUPS
        with self.assertRaises(AuditError):
            guard.parse_workers(p)

    def test_unexpected_account_rejected(self):
        p = sample_rows()
        p["data"]["viewer"]["accounts"] = []
        with self.assertRaises(AuditError):
            guard.parse_workers(p)

    def test_graphql_errors_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_workers({"errors": [{"message": "Access denied"}]})

    def test_no_graphql_data_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_workers({"data": None})

    def test_wrong_missing_dimensions_rejected(self):
        p = sample_rows()
        p["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"][0]["dimensions"] = {}
        with self.assertRaises(AuditError):
            guard.parse_workers(p)

    def test_negative_noninteger_boolean_nan_inf_rejected(self):
        for bad in (-1, True, 1.5, float("nan"), float("inf"), None, "10"):
            with self.subTest(bad=bad):
                p = sample_rows(requests=bad)
                with self.assertRaises(AuditError):
                    guard.parse_workers(p)

    def test_negative_or_nan_cpu_rejected(self):
        for bad in (-1, float("nan"), "10"):
            p = sample_rows(cpu=bad)
            with self.assertRaises(AuditError):
                guard.parse_workers(p)

    def test_null_cpu_is_allowed_when_unavailable(self):
        self.assertEqual(
            guard.parse_workers(sample_rows(cpu=None))["max_reported_cpu_p99_us"],
            0.0)

    def test_inconsistent_errors_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_workers(sample_rows(requests=1, errors=2))

    def test_requests_ok_warning_critical(self):
        self.assertEqual(guard.assess_requests(0), "OK")
        self.assertEqual(guard.assess_requests(69_999), "OK")
        self.assertEqual(guard.assess_requests(70_000), "WARNING")
        self.assertEqual(guard.assess_requests(89_999), "WARNING")
        self.assertEqual(guard.assess_requests(90_000), "CRITICAL")

    def test_missing_token_causes_no_network(self):
        with (patch.dict(os.environ, {"REMURA_CF_ANALYTICS_READ_TOKEN": ""}),
              patch.object(guard, "urlopen", side_effect=AssertionError("network"))):
            self.assertEqual(guard.main(), 0)

    def test_no_query_mutation_and_bounded_rows(self):
        self.assertIn("workersInvocationsAdaptive", guard.QUERY)
        self.assertIn("limit: 1000", guard.QUERY)
        self.assertNotIn("mutation", guard.QUERY.lower())
        self.assertNotIn("DELETE ", guard.QUERY)
        self.assertNotIn("INSERT ", guard.QUERY)
        self.assertNotIn("scriptName:", guard.QUERY)  # Account-wide, not a single Worker.

    def test_naive_clock_rejected(self):
        with patch.object(guard, "require_account_id", return_value="a"*32):
            with self.assertRaises(AuditError):
                guard.fetch_workers_analytics("a"*32,"cfat_"+"x"*60,
                                             datetime(2026,11,13))

    def test_cpu_quantile_is_not_interpreted_as_total_cpu(self):
        got = guard.parse_workers(sample_rows(cpu=321.25))
        self.assertEqual(got["max_reported_cpu_p99_us"], 321.25)
        self.assertNotIn("cpu_total_us", got)


if __name__ == "__main__":
    unittest.main()
