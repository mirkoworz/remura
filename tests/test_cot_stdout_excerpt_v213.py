"""REMURA B V21.3: new checks for audited partial REAL stdout evidence.

No CFTC HTTP, broker queries, secrets, new synthetic price outcomes, or writes.
This is ONLY an excerpt from an earlier successfully completed public API audit.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "real-proofs" / "REMURA-B-CFTC-20261123-STDOUT-PARTIAL-EXCERPT.json"
sys.path.insert(0, str(ROOT / "scripts"))
from cot_intelligence_parity import validate, PUBLIC_SOURCE

# This independent transcription pins EVERY value printed in job 137804869184.
EXPECTED = {
    "GBPAUD": ("tff", "synthetic_fx_relative", 7.6571, 1.8347),
    "GBPNZD": ("tff", "synthetic_fx_relative", 6.9413, -39.6856),
    "GBPCAD": ("tff", "synthetic_fx_relative", 6.1169, -78.7651),
    "AUDCHF": ("tff", "synthetic_fx_relative", -5.8250, -65.7386),
    "EURGBP": ("tff", "synthetic_fx_relative", -5.7489, 82.9774),
    "US30": ("tff", "futures_reference", -11.7403, -13.3727),
    "NAS100": ("tff", "futures_reference", 2.757, 31.6534),
    "US500": ("tff", "futures_reference", -2.6226, 53.8889),
    "DXY": ("tff", "futures_reference", 1.7897, 36.0),
    "XAUUSD": ("disagg", "futures_reference", -2.5162, 26.3669),
    "XAGUSD": ("disagg", "futures_reference", -2.0846, 11.5149),
    "USOIL": ("disagg", "futures_reference", -0.4953, -19.7569),
}


def proof():
    return json.loads(PATH.read_text("utf-8"))


class TestRealCftcStdoutExcerpt(unittest.TestCase):
    def test_all_twelve_numbers_match_the_preexisting_successful_job_printout(self):
        rows = proof()["observations"]
        self.assertEqual(len(rows), 12)
        self.assertEqual(set(x["symbol"] for x in rows), set(EXPECTED))
        for row in rows:
            source, typ, weekly, gap = EXPECTED[row["symbol"]]
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["dataset"], source)
                self.assertEqual(row["calculationType"], typ)
                self.assertEqual(row["weeklyCategoryANetChangePp"], weekly)
                self.assertEqual(row["categoryGapPp"], gap)
                self.assertEqual(row["reportDate"], "2026-11-17")

    def test_prior_audit_metadata_not_a_new_api_call_or_raw_dataset(self):
        p = proof()
        source = p["evidence"]
        self.assertEqual(p["schema"], "remura-b-cftc-stdout-excerpt-v1")
        self.assertEqual(source["githubRunId"], 45206837974)
        self.assertEqual(source["githubJobId"], 137804869184)
        self.assertEqual(source["sourceStdoutProofMarker"], "REMURA_B_PUBLIC_CFTC_PROOF")
        self.assertEqual(source["sourceSnapshotRowsReported"], 980)
        self.assertEqual(source["sourceSnapshotReadAtUtc"], "2026-11-23T15:35:17.664069Z")
        self.assertEqual(source["fullSnapshotRowsSha256ReportedByRun"],
            "a2d58c5a3347c121b491c5f495f7ee01ed83b6a282cc11fb2e5f49b1688ffb23")
        self.assertFalse(source["fullSourceSnapshotRecoverableFromThisExcerpt"])
        self.assertFalse(source["excerptEquivalentToOriginalFullSnapshot"])
        self.assertFalse(source["sourceLogIndependentSignatureVerified"])
        self.assertEqual(p["scientificControls"]["incrementalCftcApiRequests"], 0)

    def test_five_selected_crosses_not_28_independent_pairs_and_seven_direct(self):
        p = proof()
        g = p["groupSummary"]
        self.assertEqual([g["crossesPrintedInRun"], g["totalCrossesComputedInPastRun"]],
                         [5, 28])
        self.assertEqual([g["tffDirectPrintedInRun"], g["disaggDirectPrintedInRun"]], [4, 3])
        self.assertFalse(g["crossesStatisticallyIndependent"])
        self.assertEqual(sum(x["underlyingPositioningNotDirectForex"]
                             for x in p["observations"]), 5)
        self.assertEqual(p["fieldDefinitions"]["tffCategoryA"],
                         "Asset Manager/Institutional")
        self.assertEqual(p["fieldDefinitions"]["disaggCategoryA"], "Managed Money")

    def test_real_historical_printout_never_claims_prepublication_or_forward_alpha(self):
        p = proof()
        self.assertEqual(p["period"]["latestReportDate"], "2026-11-17")
        self.assertEqual(p["period"]["previousReportDate"], "2026-11-10")
        self.assertFalse(p["period"]["officialPublicationTimestampAttestedByThisExcerpt"])
        control = p["scientificControls"]
        for key in ("verifiedActualSevenCurrencyFactorVector",
                    "authenticatedPrivateCftcParity",
                    "independentHistoricalDataAvailabilityVerified",
                    "futurePriceOutcomesVerified", "tradeRecommendationsGenerated",
                    "statisticalAlphaEstablished"):
            self.assertFalse(control[key], key)

    def test_partial_audit_excerpt_must_not_pass_full_public_snapshot_validator(self):
        with self.assertRaisesRegex(ValueError, "INVALID_SNAPSHOT_SOURCE"):
            validate(proof(), PUBLIC_SOURCE,
                     __import__("datetime").datetime(2026,11,23,21,0,
                      tzinfo=__import__("datetime").timezone.utc))


if __name__ == "__main__":
    unittest.main()
