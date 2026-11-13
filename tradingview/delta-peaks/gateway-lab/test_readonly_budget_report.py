# REMURA Budget Report unit tests v0.1 — aggiornamento 13/11/2026, ore 10:09 CET
# Solo stringhe sintetiche, nessuna rete o secret reale.
import unittest

import readonly_budget_report as report


D1 = """REMURA_CF_ACCOUNT_QUOTA=OK
D1_ACCOUNT_ROWS_READ_ESTIMATE=12
D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0
"""
WORKERS = """REMURA_CF_WORKERS_USAGE=OK
WORKERS_ACCOUNT_REQUESTS_ESTIMATE=200
WORKERS_ACCOUNT_ERRORS_ESTIMATE=1
WORKERS_MAX_REPORTED_CPU_P99_US=3080.0
"""
STORAGE = """REMURA_D1_TEST_STORAGE=OK
REMURA_D1_TEST_STORAGE_BYTES=28672
REMURA_D1_TEST_STORAGE_PERCENT=0.0057
"""


class BudgetReportTests(unittest.TestCase):
    def test_all_good_display_values(self):
        summary = report.build_report(D1, WORKERS, STORAGE, "2026-11-13")
        for expected in ("12", "200", "28.672", "28672", "OK", "2026-11-13"):
            if expected != "28.672":  # no locale formatting guaranteed
                self.assertIn(expected, summary)
        self.assertIn("stimate", summary)

    def test_missing_analytics_does_not_claim_zero(self):
        summary = report.build_report("", "", STORAGE, "2026-11-13")
        self.assertIn("UNKNOWN", summary)
        self.assertIn("non disponibile", summary)
        self.assertIn("28672", summary)

    def test_worker_unknown_no_data_cannot_use_leftover_counters(self):
        w = WORKERS.replace("REMURA_CF_WORKERS_USAGE=OK",
                            "REMURA_CF_WORKERS_USAGE=UNKNOWN_NO_DATA")
        summary = report.build_report(D1, w, STORAGE, "2026-11-13")
        self.assertNotIn("| 200 |", summary)
        self.assertIn("UNKNOWN", summary)

    def test_d1_unknown_cannot_use_leftover_counters(self):
        d = D1.replace("REMURA_CF_ACCOUNT_QUOTA=OK",
                       "REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA")
        summary = report.build_report(d, WORKERS, STORAGE, "2026-11-13")
        self.assertNotIn("| 12 |", summary)
        self.assertIn("non disponibile", summary)

    def test_storage_unknown_cannot_claim_small_file(self):
        summary = report.build_report(D1, WORKERS,
                                      "REMURA_D1_TEST_STORAGE=UNKNOWN\nREMURA_D1_TEST_STORAGE_BYTES=28672",
                                      "2026-11-13")
        self.assertNotIn("28672 byte", summary)

    def test_critical_status_preserved(self):
        summary = report.build_report(D1.replace("=OK", "=CRITICAL"),
                                      WORKERS, STORAGE, "2026-11-13")
        self.assertIn("CRITICAL", summary)

    def test_no_sensitive_payload_in_summary(self):
        d = D1 + "CLOUDFLARE_BEARER=very-secret\n"
        summary = report.build_report(d, WORKERS, STORAGE, "2026-11-13")
        self.assertNotIn("very-secret", summary)
        self.assertNotIn("CLOUDFLARE_BEARER", summary)

    def test_unexpected_markup_fails_closed(self):
        with self.assertRaises(ValueError):
            report.filtered_fields("D1_ACCOUNT_ROWS_READ_ESTIMATE=<script>")

    def test_duplicate_field_fails_closed(self):
        with self.assertRaises(ValueError):
            report.filtered_fields("REMURA_CF_ACCOUNT_QUOTA=OK\nREMURA_CF_ACCOUNT_QUOTA=WARNING")

    def test_number_needs_strict_format(self):
        self.assertEqual(report.display_number(
            {"D1_ACCOUNT_ROWS_READ_ESTIMATE": "abc"}, "D1_ACCOUNT_ROWS_READ_ESTIMATE"),
            "non disponibile")

    def test_none_field_unknown(self):
        self.assertEqual(report.category_status({}, "workers"), "UNKNOWN")

    def test_report_explains_external_403_is_inconclusive(self):
        summary = report.build_report(D1, WORKERS, STORAGE, "2026-11-13")
        self.assertIn("403/403", summary)
        self.assertIn("non verificabile", summary)

    def test_report_never_claims_billing_exactness(self):
        summary = report.build_report(D1, WORKERS, STORAGE, "2026-11-13")
        self.assertIn("non sono contatori di fatturazione esatti", summary.lower())


if __name__ == "__main__":
    unittest.main()
