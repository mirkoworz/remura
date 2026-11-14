#!/usr/bin/env python3
# REMURA v0.8.53 LAB — 14/11/2026 11:39 CET — synthetic only.
import unittest
from configured_envelope_preview_v1 import validate_envelope,SCHEMA
from fx_pilot_config_v1 import REFERENCE
from test_telemetry_v1 import sample,T0

def envelope():
    p=sample()
    p["quality"].update(lower_tf="1",daily_anchor="HL2")
    return {"schema":SCHEMA,"snapshot":p,"configuration":dict(REFERENCE)}

class EnvelopeTests(unittest.TestCase):
    def test_valid_is_not_attestation(self):
        r=validate_envelope(envelope(),received_ms=T0+5000)
        self.assertEqual(r["status"],"CONFIG_DECLARATION_MATCH_ONLY")
        self.assertFalse(r["scientific_admission"])
        self.assertFalse(r["effective_alert_inputs_attested"])
        self.assertFalse(r["orders_enabled"])

    def test_config_changed_rejected(self):
        p=envelope()
        p["configuration"]["lookback"]=40
        with self.assertRaises(ValueError):
            validate_envelope(p,received_ms=T0+5000)

    def test_snapshot_config_conflict(self):
        p=envelope()
        p["snapshot"]["quality"]["daily_anchor"]="POC FOOTPRINT"
        with self.assertRaises(ValueError):
            validate_envelope(p,received_ms=T0+5000)

    def test_wrong_feed_or_late(self):
        p=envelope()
        p["snapshot"]["feed"]="OTHER"
        with self.assertRaises(ValueError):
            validate_envelope(p,received_ms=T0+5000)
        with self.assertRaises(ValueError):
            validate_envelope(envelope(),received_ms=T0+120001)

    def test_legacy_and_extra_fields_rejected(self):
        for p in (sample(),dict(envelope(),extra=True),dict(envelope(),schema="other")):
            with self.assertRaises(ValueError):
                validate_envelope(p,received_ms=T0+5000)

    def test_no_client_receiver_time(self):
        with self.assertRaises(ValueError):
            validate_envelope(envelope(),received_ms=None)
        p=dict(envelope(),received_ms=T0+5000)
        with self.assertRaises(ValueError):
            validate_envelope(p,received_ms=T0+5000)

if __name__=="__main__":
    unittest.main()
