#!/usr/bin/env python3
# REMURA v0.8.4 Quota Guard — aggiornamento 11/11/2026 18:04 CET.
# Solo simulazioni, non quote account effettive.
import unittest
from quota_budget_v1 import budget


class QuotaGuardTests(unittest.TestCase):
    def test_single_eurusd_pilot_with_30_day_retention_fits_model(self):
        r = budget()
        self.assertTrue(r["fits_internal_guardrails"])
        self.assertFalse(r["cloudflare_account_usage_checked"])
        self.assertFalse(r["cost_verified_zero"])
        self.assertEqual(r["estimated_max"]["daily_bars"], 288)

    def test_two_symbols_max_payload_30_days_exceed_storage_guard(self):
        r = budget(symbols=2)
        self.assertFalse(r["fits_internal_guardrails"])
        self.assertGreater(
            r["estimated_max"]["storage_bytes_one_database"],
            r["internal_guardrails"]["d1_database_storage_bytes"])

    def test_two_symbols_14_days_fit_model(self):
        r = budget(symbols=2, retention_days=14)
        self.assertTrue(r["fits_internal_guardrails"])

    def test_missing_heartbeat_cannot_approve_prospective_model(self):
        r = budget(heartbeat_enabled=False)
        self.assertFalse(r["fits_internal_guardrails"])

    def test_oversized_payload_rejected(self):
        with self.assertRaises(ValueError):
            budget(max_payload_bytes=20_001)

    def test_zero_or_negative_accounting_inputs_rejected(self):
        for kwargs in (
            {"symbols": 0}, {"retention_days": 0},
            {"active_hours": 0}, {"active_hours": -1},
            {"retries_multiplier": 0.9},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                budget(**kwargs)

    def test_large_pilot_does_not_claim_free_status(self):
        r = budget(symbols=25)
        self.assertFalse(r["fits_internal_guardrails"])
        self.assertFalse(r["cost_verified_zero"])


if __name__ == "__main__":
    unittest.main()
