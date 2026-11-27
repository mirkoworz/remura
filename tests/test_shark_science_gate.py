"""Track B no-look-ahead / lineage / H1 quality tests. Synthetic only."""
import copy
import json
import unittest

from scripts import shark_science_gate as gate

ASOF = "2026-11-04T12:00:00Z"


def valid():
    return {
        "cot": {"dataset": "tff", "publicationVerified": True,
                "marketMappingVerified": True, "mappingType": "derived_fx_cross",
                "reportDate": "2026-10-27", "publishedAt": "2026-10-30T19:30:00Z",
                "availableAt": "2026-10-30T19:35:00Z", "side": 1},
        "retail": {"provider": "myfxbook", "sampledAt": "2026-11-04T11:00:00Z",
                   "availableAt": "2026-11-04T11:02:00Z", "side": -1},
        "price": {"provider": "ctrader", "qualityVerified": True,
                  "frameStatus": {"M15": "ready", "H1": "ready", "H4": "ready"},
                  "closedAt": {"M15": "2026-11-04T11:45:00Z",
                               "H1": "2026-11-04T11:00:00Z",
                               "H4": "2026-11-04T08:00:00Z"},
                  "availableAt": "2026-11-04T11:48:00Z", "side": 1},
        "cvdProxy": {"algorithm": gate.CVD_VERSION,
                     "state": "confirmed_technical_not_trade_signal",
                     "side": "bullish", "dataQualityVerified": True,
                     "confirmedAt": "2026-11-04T11:30:00Z",
                     "collectedAt": "2026-11-04T11:47:00Z",
                     "detectedAt": "2026-11-04T11:49:00Z"},
    }


class SharkGateTests(unittest.TestCase):
    def test_all_sources_valid_are_still_not_trading_signal(self):
        sample = valid()
        unchanged = copy.deepcopy(sample)
        out = gate.evaluate(sample, as_of=ASOF)
        self.assertEqual(out["verdict"], "CONFERMA PARZIALE")
        self.assertEqual(out["qualityGate"], "PASS")
        self.assertEqual(out["excluded"], [])
        self.assertIsNone(out["probability"])
        self.assertEqual(out["empiricalEdge"], "NOT_ESTABLISHED")
        self.assertFalse(out["orderEnabled"])
        self.assertFalse(out["notificationEnabled"])
        self.assertEqual(out["institutionalAttribution"], "NOT_PROVEN")
        self.assertEqual(sample, unchanged)

    def test_future_cot_publication_is_never_backdated_to_report_date(self):
        sample = valid()
        sample["cot"]["publishedAt"] = "2026-11-06T19:30:00Z"
        sample["cot"]["availableAt"] = "2026-11-06T19:35:00Z"
        out = gate.evaluate(sample, as_of=ASOF)
        self.assertEqual(out["channels"]["cot"]["reason"], "cot_not_known_asof")
        self.assertNotEqual(out["verdict"], "CONFERMA PARZIALE")

    def test_cot_requires_verified_release_and_contract_mapping(self):
        for key in ("publicationVerified", "marketMappingVerified"):
            sample = valid()
            sample["cot"][key] = False
            result = gate.evaluate(sample, as_of=ASOF)
            self.assertEqual(result["channels"]["cot"]["reason"],
                             "cot_lineage_unverified")

    def test_stale_h1_blocks_price_even_when_m15_is_fresh(self):
        sample = valid()
        sample["price"]["closedAt"]["H1"] = "2026-11-04T09:00:00Z"
        out = gate.evaluate(sample, as_of=ASOF)
        self.assertEqual(out["qualityGate"], "BLOCK")
        self.assertIn("price", out["excluded"])
        self.assertNotEqual(out["verdict"], "CONFERMA PARZIALE")
        sample = valid()
        sample["price"]["frameStatus"]["H1"] = "stale"
        self.assertEqual(gate.evaluate(sample, as_of=ASOF)["qualityGate"], "BLOCK")

    def test_future_price_or_cvd_ingest_is_not_known_at_confirmation(self):
        sample = valid()
        sample["price"]["availableAt"] = "2026-11-04T12:01:00Z"
        self.assertEqual(gate.evaluate(sample, as_of=ASOF)["qualityGate"], "BLOCK")
        sample = valid()
        sample["cvdProxy"]["collectedAt"] = "2026-11-04T11:29:00Z"
        self.assertEqual(gate.evaluate(sample, as_of=ASOF)["channels"]["cvdProxy"]["reason"],
                         "cvd_unavailable_at_decision")
        sample = valid()
        sample["cvdProxy"]["detectedAt"] = "2026-11-04T12:01:00Z"
        self.assertIn("cvdProxy", gate.evaluate(sample, as_of=ASOF)["excluded"])

    def test_retail_future_sample_and_stale_sample_both_excluded(self):
        sample = valid()
        sample["retail"]["sampledAt"] = "2026-11-04T12:01:00Z"
        self.assertIn("retail", gate.evaluate(sample, as_of=ASOF)["excluded"])
        sample = valid()
        sample["retail"]["sampledAt"] = "2026-11-04T08:00:00Z"
        sample["retail"]["availableAt"] = "2026-11-04T08:01:00Z"
        self.assertEqual(gate.evaluate(sample, as_of=ASOF)["channels"]["retail"]["reason"],
                         "retail_stale")

    def test_conflicting_price_cot_and_partial_sources_do_not_vote(self):
        sample = valid()
        sample["price"]["side"] = -1
        out = gate.evaluate(sample, as_of=ASOF)
        self.assertTrue(out["contextPriceConflict"])
        self.assertEqual(out["verdict"], "DA OSSERVARE")
        sample = valid()
        sample["cot"] = None
        self.assertNotEqual(gate.evaluate(sample, as_of=ASOF)["verdict"], "CONFERMA PARZIALE")

    def test_missing_all_sources_is_explicit_not_zero_probability(self):
        out = gate.evaluate({}, as_of=ASOF)
        self.assertEqual(out["verdict"], "NESSUN SEGNALE VALIDATO")
        self.assertEqual(len(out["excluded"]), 4)
        self.assertIsNone(out["probability"])
        self.assertEqual(out["qualityGate"], "BLOCK")

    def test_invalid_type_timestamps_and_privacy_fail_closed(self):
        sample = valid()
        sample["cot"]["side"] = True
        self.assertIn("cot", gate.evaluate(sample, as_of=ASOF)["excluded"])
        sample = valid()
        sample["price"]["availableAt"] = "2026-11-04T13:48:00+02:00"
        self.assertIn("price", gate.evaluate(sample, as_of=ASOF)["excluded"])
        with self.assertRaises(ValueError):
            gate.evaluate(sample, as_of="2026-11-04T12:00:00")
        sample = valid()
        sample["retail"]["token"] = "NEVER_PRINT_PRIVATE_SECRET"
        sample["price"]["account"] = "NEVER_PRINT_BROKER_ACCOUNT"
        out = gate.evaluate(sample, as_of=ASOF)
        self.assertNotIn("NEVER_PRINT", json.dumps(out))


if __name__ == "__main__":
    unittest.main()
