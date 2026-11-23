"""Only NEW V20.2 ECB daily-price witness tests: no network nor credentials."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest

from ecb_daily_reference_witness_v202 import parse_rates, witness

OBSERVED = datetime(2026, 11, 23, 6, 44, tzinfo=timezone.utc)
VALUES = {"USD": "1.2", "JPY": "180", "GBP": "0.9",
          "CHF": "0.94", "CAD": "1.5", "AUD": "1.7", "NZD": "2.0"}


def xml(date_str="2026-11-20", values=None, duplicate=None):
    rates = VALUES if values is None else values
    cells = "".join(f'<Cube currency="{k}" rate="{v}"/>' for k,v in rates.items())
    if duplicate:
        cells += f'<Cube currency="{duplicate}" rate="{rates[duplicate]}"/>'
    return (f'<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" '
            f'xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">'
            f'<Cube><Cube time="{date_str}">{cells}</Cube></Cube></gesmes:Envelope>').encode()


class IndependentEcbWitness(unittest.TestCase):
    def test_complete_28_major_fx_pairs(self):
        r=witness(xml(), OBSERVED)
        self.assertEqual(len(r["derived_pairs"]), 28)
        self.assertEqual(len(set(r["derived_pairs"])), 28)
        self.assertEqual(r["derived_pairs"]["EURUSD"], "1.20000000")

    def test_usdjpy_inverse_base_and_cross_arithmetic(self):
        r=witness(xml(), OBSERVED)
        self.assertEqual(r["derived_pairs"]["USDJPY"], "150.00000000")
        self.assertEqual(r["derived_pairs"]["CADJPY"], "120.00000000")
        self.assertEqual(r["derived_pairs"]["GBPUSD"], "1.33333333")

    def test_publication_time_never_invented(self):
        r=witness(xml(), OBSERVED)
        self.assertTrue(r["reference_date_is_not_publication_timestamp"])
        self.assertFalse(r["first_seen_independently_attested"])
        self.assertEqual(r["eligible_for_future_decisions_only_after_utc"], "2026-11-23T06:44:00Z")
        self.assertFalse(r["intraday_candles_or_tradeable_price"])
        self.assertFalse(r["forward_60m_h4_24h_alpha_calculated"])

    def test_friday_reference_observed_monday_is_not_new_monday_price(self):
        r=witness(xml(), OBSERVED)
        self.assertEqual(r["days_behind_observation_date"],3)
        self.assertFalse(r["new_23_nov_reference_observed"])

    def test_reject_future_reference(self):
        with self.assertRaisesRegex(ValueError, "Future"):
            witness(xml(date_str="2026-11-24"), OBSERVED)

    def test_reject_stale_reference(self):
        with self.assertRaisesRegex(ValueError, "Stale"):
            witness(xml(date_str="2026-11-13"), OBSERVED)

    def test_reject_missing_major_currency(self):
        vals={k:v for k,v in VALUES.items() if k!="CAD"}
        with self.assertRaisesRegex(ValueError, "missing"):
            witness(xml(values=vals), OBSERVED)

    def test_reject_duplicate_currency(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            witness(xml(duplicate="USD"), OBSERVED)

    def test_reject_zero_and_nan(self):
        for bad in ("0", "-1", "NaN", "Infinity", "bogus"):
            with self.subTest(bad=bad):
                vals=dict(VALUES, USD=bad)
                with self.assertRaises(ValueError):
                    witness(xml(values=vals), OBSERVED)

    def test_reject_naive_observation_and_broken_payload(self):
        with self.assertRaisesRegex(ValueError, "timezone aware"):
            witness(xml(), datetime(2026,11,23))
        with self.assertRaisesRegex(ValueError, "parse failure"):
            parse_rates(b"<bad")
        with self.assertRaisesRegex(ValueError,"oversized"):
            parse_rates(b"x"*120001)

    def test_fingerprint_is_sha256_not_fake_first_seen(self):
        r=witness(xml(), OBSERVED)
        self.assertEqual(len(r["raw_xml_sha256"]),64)
        self.assertFalse(r["first_seen_independently_attested"])
        self.assertTrue(r["independent_daily_fx_context_only"])
        self.assertNotIn("secret",json.dumps(r).lower())


if __name__ == "__main__":
    unittest.main()
