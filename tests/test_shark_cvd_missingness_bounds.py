"""Adversarial offline synthetic controls for logical CVD coverage bounds.

Every observation in this suite is SYNTHETIC, NEVER a true market outcome.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_cvd_missingness_bounds as bounds

AS_OF = "2026-11-10T00:00:00Z"


def candidate(symbol="EURUSD", *, result="BULLISH_CONFIRMED",
              coverage="FULL_PROSPECTIVE", **changes):
    legs = protocol.expected_cot_legs(symbol)
    row = {
        "schema": protocol.INPUT_SCHEMA,
        "symbol": symbol,
        "direction": 1,
        "observedAtUtc": "2026-11-09T10:01:00Z",
        "firstRecordedAtUtc": "2026-11-09T10:00:59Z",
        "cotFirstSeenAtUtc": "2026-11-06T20:00:00Z",
        "cotReportDate": "2026-11-03",
        "cotFirstSeenVerified": True,
        "cotDataset": legs[0][0],
        "cotMappedLegWitnesses": [
            {"dataset": ds, "code": code, "reportDate": "2026-11-03",
             "firstSeenAtUtc": "2026-11-06T20:00:00Z"}
            for ds, code in legs
        ],
        "priceWitnessAtUtc": "2026-11-09T10:00:08Z",
        "m15ClosedAtUtc": "2026-11-09T10:00:00Z",
        "priceQualityVerified": True,
        "provider": "ctrader",
        "priceFrame": "M15",
        "retailFirstSeenAtUtc": "2026-11-09T09:59:00Z",
        "retailQualityVerified": True,
        "cvdScanCoverage": coverage,
        "cvdScanWitnessAtUtc": "2026-11-09T10:00:45Z",
        "cvdAlgorithm": protocol.CVD_VERSION,
        "cvdQualityVerified": True,
        "cvdOriginalClosedBarsVerified": True,
        "cvdSourceWitnessSha256": "a" * 64,
        "cvdFullMarketUniverseAtObservation": True,
        "cvdResult": result,
        "cvdConfirmedAtUtc": "2026-11-09T10:00:40Z",
        "privateBrokerSecret": "DO_NOT_LEAK",
    }
    row.update(changes)
    return row


def run(rows):
    return bounds.audit(
        rows, as_of=AS_OF,
        expected_protocol_sha256=protocol.FROZEN_PROTOCOL_SHA256,
    )


class CvdMissingnessBoundsTests(unittest.TestCase):
    def test_only_two_labeled_out_of_34_extremely_wide_bounds(self):
        # 34 market/clock candidates, NOT 34 independent profit samples.
        rows = [
            candidate(symbol, result=("BULLISH_CONFIRMED"
                       if symbol == "EURUSD" else
                       "NO_CONFIRMED_DIVERGENCE"),
                      coverage=("FULL_PROSPECTIVE" if symbol in
                                ("EURUSD", "XAUUSD") else "UNKNOWN"))
            for symbol in protocol.FROZEN_UNIVERSE
        ]
        output = run(rows)
        self.assertEqual(output["coreAdmitted"], 34)
        self.assertEqual(output["cvdLabeledBySubmittedMetadata"], 2)
        self.assertEqual(output["cvdUnknownCoverage"], 32)
        self.assertEqual(output["labeledCoveragePct"], 5.88)
        self.assertEqual(
            output["logicalCandidateShareBoundsPct"]["aligned"],
            {"observedCandidateCount": 1,
             "lowerPct": 2.94, "upperPct": 97.06})
        self.assertEqual(
            output["logicalCandidateShareBoundsPct"]["fullScanNegative"],
            {"observedCandidateCount": 1,
             "lowerPct": 2.94, "upperPct": 97.06})
        self.assertFalse(output["profitabilityOrCausalEffectEstimated"])
        self.assertFalse(output["independentSourceAttestation"])
        self.assertFalse(output["cvdResearchMayBeEnabled"])
        self.assertNotIn("EURUSD", json.dumps(output))
        self.assertNotIn("DO_NOT_LEAK", json.dumps(output))
        self.assertEqual(protocol.protocol_sha256(),
                         "09d833dafdd426254bc8fedccc367e41fa451ac8f2e6c99a9dac27f7387e2905")

    def test_unknown_is_never_silently_negative_even_if_result_says_none(self):
        rows = [candidate("EURUSD", result="NO_CONFIRMED_DIVERGENCE",
                          coverage="PARTIAL"),
                candidate("GBPUSD", result="NO_CONFIRMED_DIVERGENCE",
                          cvdScanWitnessAtUtc="2026-11-09T10:05:00Z")]
        output = run(rows)
        self.assertEqual(output["cvdUnknownCoverage"], 2)
        self.assertEqual(output["cvdLabeledBySubmittedMetadata"], 0)
        self.assertEqual(output["logicalCandidateShareBoundsPct"]
                         ["fullScanNegative"]["lowerPct"], 0)
        self.assertEqual(output["logicalCandidateShareBoundsPct"]
                         ["fullScanNegative"]["upperPct"], 100)

    def test_reclassifying_unknown_only_tightens_bounds_no_mnar_assumption(self):
        rows = [candidate("EURUSD"), candidate("GBPUSD", coverage="UNKNOWN"),
                candidate("XAUUSD", result="NO_CONFIRMED_DIVERGENCE")]
        a = run(rows)
        rows[1]["cvdScanCoverage"] = "FULL_PROSPECTIVE"
        b = run(rows)
        self.assertEqual(a["cvdUnknownCoverage"], 1)
        self.assertEqual(b["cvdUnknownCoverage"], 0)
        self.assertEqual(a["logicalCandidateShareBoundsPct"]["aligned"],
                         {"observedCandidateCount": 1,
                          "lowerPct": 33.33, "upperPct": 66.67})
        self.assertEqual(b["logicalCandidateShareBoundsPct"]["aligned"],
                         {"observedCandidateCount": 2,
                          "lowerPct": 66.67, "upperPct": 66.67})
        self.assertFalse(b["missingAtRandomAssumed"])

    def test_duplicate_ambiguous_rows_both_excluded_irrespective_of_order(self):
        rows = [candidate("EURUSD"),
                candidate("EURUSD", result="NO_CONFIRMED_DIVERGENCE"),
                candidate("GBPUSD", coverage="UNKNOWN")]
        a = run(rows)
        b = run(list(reversed(rows)))
        self.assertEqual(a, b)
        self.assertEqual(a["coreAdmitted"], 1)
        self.assertEqual(a["excluded"], 2)
        self.assertEqual(a["exclusionReasons"]
                         ["ambiguous_duplicate_observation"], 2)
        self.assertEqual(a["logicalCandidateShareBoundsPct"]
                         ["aligned"]["upperPct"], 100)

    def test_temporal_leakage_and_forged_outcomes_do_not_enter(self):
        future = candidate("EURUSD", firstRecordedAtUtc="2026-11-09T10:10:00Z")
        past = candidate("GBPUSD", observedAtUtc="2026-11-08T10:01:00Z")
        forged = candidate("XAUUSD", winningTrade=True, profit=123456789,
                           cvdConfirmedAtUtc="2026-11-09T10:02:00Z")
        out = run([future, past, forged])
        self.assertEqual(out["excluded"], 2)
        self.assertEqual(out["coreAdmitted"], 1)
        self.assertEqual(out["cvdUnknownCoverage"], 1)
        self.assertFalse(out["independentlyRecordedOutcomes"])
        self.assertNotIn("123456789", json.dumps(out))
        self.assertNotIn("profit", json.dumps(out).lower().replace("profitability", ""))

    def test_empty_cohort_is_unknown_not_zero_percent(self):
        out = run([])
        self.assertEqual(out["coreAdmitted"], 0)
        self.assertIsNone(out["labeledCoveragePct"])
        for share in out["logicalCandidateShareBoundsPct"].values():
            self.assertIsNone(share["lowerPct"])
            self.assertIsNone(share["upperPct"])

    def test_wrong_frozen_fingerprint_and_tampering_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "research_protocol_digest_changed"):
            bounds.audit([candidate()], as_of=AS_OF,
                         expected_protocol_sha256="0"*64)
        self.assertEqual(bounds.main(["--self-check"]), 0)
        self.assertFalse(run([candidate()])["liveSignalsOrOrdersAuthorized"])

    def test_stdin_cli_requires_explicit_opt_in_and_writes_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = {
                "asOfUtc": AS_OF,
                "protocolSha256": protocol.FROZEN_PROTOCOL_SHA256,
                "records": [candidate()],
            }
            args = [sys.executable, "-B", "-m",
                    "scripts.shark_cvd_missingness_bounds", "--audit-stdin"]
            repo_root = str(Path(bounds.__file__).resolve().parents[1])
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            completed = subprocess.run(args, input=json.dumps(payload),
                                       text=True, cwd=repo_root, env=env,
                                       capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(completed.stdout.startswith("REMURA_CVD_MISSINGNESS="))
            self.assertEqual(json.loads(completed.stdout.split("=",1)[1])
                             ["coreAdmitted"],1)
            payload["protocolSha256"] = "bad"
            failed = subprocess.run(args, input=json.dumps(payload), text=True,
                                    cwd=repo_root, env=env, capture_output=True,
                                    timeout=10)
            self.assertEqual(failed.returncode, 2)
            self.assertIn("NO_GO_INVALID_INPUT", failed.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
