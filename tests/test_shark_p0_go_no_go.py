"""Synthetic-only fail-closed P0 screening. Never a LIVE release test."""
from __future__ import annotations

from copy import deepcopy
import unittest

from scripts import shark_p0_go_no_go as gate

NOW="2026-11-05T12:00:00.000000Z"


def prospective_synthetic():
    # Values here are CONTRIVED to exercise the conditional, not a
    # claim that the user's billing or ingest impact was ever measured.
    return {
        "liveDiagnostic":{
            "observedAt":"2026-11-05T11:45:00.000000Z",
            "liveVersion":"TEST_ONLY",
            "marketCount":34,
            "m15Stale":0,"h1Stale":0,"h4Stale":0,
            "collectorBatches":128,"collectorBatchFailures":0,
            "squalincomeScans":128,"squalincomeFailures":0,
            "researchOffOnLive":True,
            "ramUsedPercent":33.1,"diskUsedPercent":8.0,
        },
        "controlledLiveOverlap":{
            "observedUnderRealIngest":True,
            "measuredAt":"2026-11-05T11:40:00.000000Z",
            "independentOverlapWindows":12,
            "newBrokerCalls":0,
            "scannerBusyErrors":0,
            "baselinePostIngestMedianMs":250,
            "pilotPostIngestMedianMs":260,
            "unmodifiedPriceCollectionCadence":True,
        },
        "accountConsoleUsage":{
            "checkedAt":"2026-11-05T11:50:00.000000Z",
            "oracle":{
                "alwaysFreeEligibleResourcesConfirmed":True,
                "actualMonthlyCharges":0,
            },
            "githubPrivateActions":{
                "minutesUsed":200,"minutesIncluded":2000,
                "actualCharges":0,
            },
            "firestoreStandard":{
                "onlyFreeEligibleDatabase":True,
                "readsDaily":100,"writesDaily":500,
                "storedBytes":100000,"outboundBytesMonthly":100000,
                "billingCharge":0,
            },
        },
    }


class P0GateTests(unittest.TestCase):
    def test_no_evidence_never_claims_cost_or_safety(self):
        for empty in ({},None,[],{"liveDiagnostic":{}}):
            with self.subTest(shape=type(empty).__name__):
                report=gate.evaluate(empty,as_of=NOW)
                self.assertEqual(report["status"],"NO_GO")
                self.assertIn("REAL_INGEST_OVERLAP_UNMEASURED_OR_UNSAFE",
                              report["unresolvedChecks"])
                self.assertIn("ORACLE_ACCOUNT_BILL_OR_ELIGIBILITY_UNKNOWN",
                              report["unresolvedChecks"])
                self.assertIn("FIRESTORE_READ_WRITE_STORAGE_OR_EGRESS_UNKNOWN",
                              report["unresolvedChecks"])
                self.assertFalse(report["liveResearchAutomaticallyEnabled"])
                self.assertFalse(report["releaseOrDeploymentAuthorized"])

    def test_old_realistic_diagnostic_baseline_with_7_stale_blocks(self):
        d=prospective_synthetic()
        l=d["liveDiagnostic"]
        l["observedAt"]="2026-11-04T17:24:53.000000Z"
        l["h1Stale"]=7
        l["h4Stale"]=7
        d.pop("controlledLiveOverlap")
        d.pop("accountConsoleUsage")
        report=gate.evaluate(d,as_of=NOW)
        self.assertEqual(report["status"],"NO_GO")
        self.assertIn("TIMEFRAME_COVERAGE_NOT_34_OF_34_FRESH",
                      report["unresolvedChecks"])
        self.assertIn("REAL_INGEST_OVERLAP_UNMEASURED_OR_UNSAFE",
                      report["unresolvedChecks"])
        self.assertFalse(report["tradingEdgeEstablished"])

    def test_explicit_synthetic_happy_path_still_requires_human_review(self):
        out=gate.evaluate(prospective_synthetic(),as_of=NOW)
        self.assertEqual(out["status"],"PRECHECK_REVIEW_ONLY")
        self.assertEqual(out["unresolvedChecks"],[])
        for key in ("releaseOrDeploymentAuthorized",
                    "liveResearchAutomaticallyEnabled",
                    "accountMetricsVerifiedIndependentlyByThisCode",
                    "realIngestOverlapValidatedByThisCode"):
            self.assertFalse(out[key])
        self.assertFalse(out["tradingEdgeEstablished"])
        self.assertEqual(out["additionalBrokerCalls"],0)

    def test_missing_real_traffic_and_bill_cannot_use_ci_as_proof(self):
        d=prospective_synthetic()
        d["controlledLiveOverlap"]["observedUnderRealIngest"]=False
        d["controlledLiveOverlap"]["independentOverlapWindows"]=3
        d["controlledLiveOverlap"]["pilotPostIngestMedianMs"]=470
        d["accountConsoleUsage"]["checkedAt"]="2026-10-01T12:00:00Z"
        d["accountConsoleUsage"]["oracle"]["alwaysFreeEligibleResourcesConfirmed"]=False
        d["accountConsoleUsage"]["githubPrivateActions"]["minutesUsed"]=1900
        d["accountConsoleUsage"]["firestoreStandard"]["readsDaily"]=50000
        out=gate.evaluate(d,as_of=NOW)
        self.assertEqual(out["status"],"NO_GO")
        for code in ("REAL_INGEST_OVERLAP_UNMEASURED_OR_UNSAFE",
                     "POST_INGEST_LATENCY_REGRESSION_UNVERIFIED",
                     "ACCOUNT_CONSOLE_EVIDENCE_MISSING_OR_STALE",
                     "ORACLE_ACCOUNT_BILL_OR_ELIGIBILITY_UNKNOWN",
                     "GITHUB_PRIVATE_BILLED_MINUTES_OR_COST_UNKNOWN",
                     "FIRESTORE_READ_WRITE_STORAGE_OR_EGRESS_UNKNOWN"):
            self.assertIn(code,out["unresolvedChecks"])

    def test_numeric_bool_nan_and_stale_diagnostic_fail_closed(self):
        d=prospective_synthetic()
        d["liveDiagnostic"]["collectorBatches"]=True
        d["liveDiagnostic"]["ramUsedPercent"]=float("nan")
        d["liveDiagnostic"]["observedAt"]="2026-11-02T11:00:00Z"
        d["controlledLiveOverlap"]["newBrokerCalls"]=1
        d["accountConsoleUsage"]["firestoreStandard"]["writesDaily"]=True
        d["accountConsoleUsage"]["githubPrivateActions"]["minutesUsed"]=-1
        out=gate.evaluate(d,as_of=NOW)
        for reason in ("LIVE_DIAGNOSTIC_ABSENT_OR_STALE",
                       "BASELINE_COLLECTOR_AND_SQUALINCOME_NOT_CERTIFIED",
                       "VPS_RESOURCE_HEADROOM_NOT_CERTIFIED",
                       "REAL_INGEST_OVERLAP_UNMEASURED_OR_UNSAFE",
                       "FIRESTORE_READ_WRITE_STORAGE_OR_EGRESS_UNKNOWN",
                       "GITHUB_PRIVATE_BILLED_MINUTES_OR_COST_UNKNOWN"):
            self.assertIn(reason,out["unresolvedChecks"])

    def test_unbounded_or_unzoned_clock_cannot_qualify(self):
        d=prospective_synthetic()
        with self.assertRaises(ValueError):
            gate.evaluate(d,as_of="2026-11-05T12:00:00")
        d["accountConsoleUsage"]["checkedAt"]="tomorrow unknown"
        self.assertEqual(gate.evaluate(d,as_of=NOW)["status"],"NO_GO")


if __name__=="__main__":
    unittest.main()
