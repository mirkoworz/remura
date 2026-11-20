#!/usr/bin/env python3
# REMURA v0.8.51 LAB — 14/11/2026 10:55 CET, synthetic only.
import unittest
from fx_pilot_config_v1 import REFERENCE, inspect_declared_config, compare_v1_fields

class PilotConfigTests(unittest.TestCase):
    def test_reference_is_not_attestation(self):
        r=inspect_declared_config(dict(REFERENCE))
        self.assertTrue(r["reference_match"])
        self.assertFalse(r["effective_alert_inputs_attested"])
        self.assertFalse(r["scientific_admission"])

    def test_canonical_order_and_numeric(self):
        a=inspect_declared_config(dict(REFERENCE))
        b=inspect_declared_config(dict(reversed(list(REFERENCE.items()))))
        c=inspect_declared_config(dict(REFERENCE,fp_imbalance_pct=300))
        self.assertEqual(a["declared_config_sha256"],b["declared_config_sha256"])
        self.assertEqual(a["declared_config_sha256"],c["declared_config_sha256"])

    def test_changed_configuration_has_new_id(self):
        a=inspect_declared_config(dict(REFERENCE))
        b=inspect_declared_config(dict(REFERENCE,lookback=40,telemetry_heartbeat=False))
        self.assertNotEqual(a["declared_config_sha256"],b["declared_config_sha256"])
        self.assertEqual(b["different_fields"],["lookback","telemetry_heartbeat"])

    def test_bad_types_and_nonfinite(self):
        for p in (dict(REFERENCE,lookback=True),dict(REFERENCE,multiplier=float("nan")),
                  dict(REFERENCE,telemetry_enabled=1),dict(REFERENCE,extra=True)):
            with self.assertRaises(ValueError):
                inspect_declared_config(p)
        p=dict(REFERENCE)
        del p["lower_tf"]
        with self.assertRaises(ValueError):
            inspect_declared_config(p)

    def test_v1_only_five_observable(self):
        p={"symbol":"FXCM:EURUSD","timeframe":"5","version":"0.8.1-lab",
           "quality":{"lower_tf":"1","daily_anchor":"HL2"}}
        r=compare_v1_fields(p,dict(REFERENCE))
        self.assertTrue(r["v1_fields_match"])
        self.assertEqual(len(r["v1_observed_fields"]),5)
        self.assertIn("lookback",r["unobservable_from_v1"])
        self.assertFalse(r["effective_alert_inputs_attested"])

    def test_v1_conflict(self):
        p={"symbol":"BINANCE:BTCUSDT","timeframe":"5","version":"0.8.1-lab",
           "quality":{"lower_tf":"1","daily_anchor":"POC FOOTPRINT"}}
        r=compare_v1_fields(p,dict(REFERENCE))
        self.assertFalse(r["v1_fields_match"])
        self.assertEqual(r["v1_difference_fields"],["daily_anchor","symbol"])
if __name__ == "__main__":
    unittest.main()
