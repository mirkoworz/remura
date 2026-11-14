# REMURA Account Quota Guard tests v0.1 — aggiornamento 13/11/2026 ore 06:54 CET
# Solo fixture GraphQL offline, nessuna rete e nessun token reale.
"""Unit tests for account-wide D1 daily-usage analytics safety gates."""
import os
import unittest
from unittest.mock import patch
import cloudflare_account_quota_guard as guard
from cloudflare_d1_readonly_audit import AuditError

DAY = "2026-11-13"
UUID = "12345678-1234-1234-1234-123456789abc"


def payload(reads=50, writes=10, day=DAY, db=UUID):
    return {"data": {"viewer": {"accounts": [
        {"d1AnalyticsAdaptiveGroups": [
            {"dimensions": {"date": day, "databaseId": db},
             "sum": {"rowsRead": reads, "rowsWritten": writes}}
        ]}
    ]}}}


class AccountQuotaGuardTests(unittest.TestCase):
    def test_single_database_usage(self):
        self.assertEqual(guard.parse_analytics(payload(), DAY), (50, 10))

    def test_aggregate_two_databases(self):
        p = payload()
        p["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"].append({
            "dimensions": {"date": DAY, "databaseId": "other-database"},
            "sum": {"rowsRead": 75, "rowsWritten": 3}})
        self.assertEqual(guard.parse_analytics(p, DAY), (125, 13))

    def test_missing_data_is_unknown_not_zero(self):
        p = payload()
        p["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"] = []
        self.assertIsNone(guard.parse_analytics(p, DAY))

    def test_zero_usage_from_explicit_group_is_ok(self):
        self.assertEqual(guard.parse_analytics(payload(0, 0), DAY), (0, 0))
        self.assertEqual(guard.assessment(0, 0), "OK")

    def test_read_warning(self):
        self.assertEqual(guard.assessment(3_500_000, 0), "WARNING")

    def test_write_warning(self):
        self.assertEqual(guard.assessment(0, 70_000), "WARNING")

    def test_read_critical(self):
        self.assertEqual(guard.assessment(4_500_000, 0), "CRITICAL")

    def test_write_critical(self):
        self.assertEqual(guard.assessment(0, 90_000), "CRITICAL")

    def test_just_below_warning(self):
        self.assertEqual(guard.assessment(3_499_999, 69_999), "OK")

    def test_just_below_critical(self):
        self.assertEqual(guard.assessment(4_499_999, 89_999), "WARNING")

    def test_invalid_usage_counter_rejected(self):
        for bad in (True, -1, 1.5, "10", None):
            with self.subTest(bad=bad), self.assertRaises(AuditError):
                guard.assessment(bad, 0)

    def test_graphql_api_errors_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_analytics({"errors": [{"message": "no authorization"}]}, DAY)

    def test_graphql_no_data_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_analytics({"data": None}, DAY)

    def test_duplicate_database_rejected(self):
        p = payload()
        group = p["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"][0]
        p["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"].append(group.copy())
        with self.assertRaises(AuditError):
            guard.parse_analytics(p, DAY)

    def test_wrong_date_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_analytics(payload(day="2026-11-12"), DAY)

    def test_missing_accounts_rejected(self):
        with self.assertRaises(AuditError):
            guard.parse_analytics({"data": {"viewer": {"accounts": []}}}, DAY)

    def test_bad_numeric_metrics_rejected(self):
        for bad in (True, "100", -1, -1.0, 0.5, float("nan"), float("inf")):
            with self.subTest(bad=bad), self.assertRaises(AuditError):
                guard.parse_analytics(payload(reads=bad), DAY)

    def test_account_with_more_than_10_groups_rejected(self):
        p = payload()
        p["data"]["viewer"]["accounts"][0]["d1AnalyticsAdaptiveGroups"] *= 11
        with self.assertRaises(AuditError):
            guard.parse_analytics(p, DAY)

    def test_query_does_not_reference_main_database(self):
        self.assertIn("d1AnalyticsAdaptiveGroups", guard.QUERY)
        self.assertIn("rowsRead rowsWritten", guard.QUERY)
        self.assertIn("date_geq:", guard.QUERY)
        self.assertNotIn("DELETE", guard.QUERY.upper())
        self.assertNotIn("mutation ", guard.QUERY)

    def test_missing_token_skips_without_network(self):
        with (patch.dict(os.environ, {"REMURA_CF_ANALYTICS_READ_TOKEN": ""}),
              patch.object(guard, "urlopen", side_effect=AssertionError("no network"))):
            self.assertEqual(guard.main(), 0)


if __name__ == "__main__":
    unittest.main()
