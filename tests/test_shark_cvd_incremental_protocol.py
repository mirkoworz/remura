"""Offline-only regression tests for prospective CVD incremental study protocol.

Synthetic cases are NOT measured market signals or authenticated COT releases.
No broker/API/VPS, SQLite, file writes, trade execution or real source dates
are used as evidence of predictive performance.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from scripts import shark_cvd_incremental_protocol as p

OBSERVED="2026-11-09T10:01:00Z"
ASOF="2026-11-10T00:00:00Z"


def event(**changes):
    payload={
        "schema":p.INPUT_SCHEMA,
        "symbol":"EURUSD",
        "direction":1,
        "observedAtUtc":OBSERVED,
        "firstRecordedAtUtc":"2026-11-09T10:00:59Z",
        "cotFirstSeenAtUtc":"2026-11-06T20:00:00Z",
        "cotReportDate":"2026-11-03",
        "cotFirstSeenVerified":True,
        "cotDataset":"tff",
        "priceWitnessAtUtc":"2026-11-09T10:00:08Z",
        "m15ClosedAtUtc":"2026-11-09T10:00:00Z",
        "priceQualityVerified":True,
        "provider":"ctrader",
        "priceFrame":"M15",
        "retailFirstSeenAtUtc":"2026-11-09T09:59:00Z",
        "retailQualityVerified":True,
        "cvdScanCoverage":"FULL_PROSPECTIVE",
        "cvdScanWitnessAtUtc":"2026-11-09T10:00:45Z",
        "cvdAlgorithm":p.CVD_VERSION,
        "cvdQualityVerified":True,
        "cvdOriginalClosedBarsVerified":True,
        "cvdSourceWitnessSha256":"a"*64,
        "cvdFullMarketUniverseAtObservation":True,
        "cvdResult":"BULLISH_CONFIRMED",
        "cvdConfirmedAtUtc":"2026-11-09T10:00:40Z",
        "privateBrokerToken":"DONT_EXPOSE_THIS_SECRET"
    }
    payload.update(changes)
    return payload


def check(rows, asof=ASOF, digest=None):
    return p.assess(rows,as_of=asof,expected_protocol_sha256=(
        p.protocol_sha256() if digest is None else digest))


class ProspectiveCvdProtocolTests(unittest.TestCase):

    def test_protocol_is_fixed_future_only_and_no_trade(self):
        a=p.protocol_sha256()
        self.assertEqual(len(a),64)
        self.assertEqual(p.PROTOCOL["effectiveStartUtc"],"2026-11-09T00:00:00Z")
        self.assertEqual(p.PROTOCOL["outcomeHorizonsHours"],[1,4,24])
        self.assertEqual(p.PROTOCOL["purgeEmbargoM15"],8)
        self.assertEqual(p.PROTOCOL["minimumDistinctCotWeeks"],8)
        self.assertEqual(p.PROTOCOL["stopAtr"],1.0)
        self.assertEqual(p.PROTOCOL["targetAtr"],1.5)
        self.assertFalse(p.PROTOCOL["tradingAuthorization"])
        self.assertEqual(check([])["protocolSha256"],a)
        with self.assertRaisesRegex(ValueError,"research_protocol_digest_changed"):
            check([event()],digest="0"*64)

    def test_real_history_not_made_future_evidence(self):
        before=event(observedAtUtc="2026-11-08T10:01:00Z",
                     firstRecordedAtUtc="2026-11-08T10:00:59Z")
        after=event(firstRecordedAtUtc="2026-11-09T10:03:00Z")
        out=check([before,after,event()])
        self.assertEqual(out["rowsReceived"],3)
        self.assertEqual(out["rowsCoreAdmitted"],1)
        self.assertEqual(out["exclusionReasons"]["not_prospectively_recorded"],2)
        self.assertFalse(out["causalIncrementalCvdEffectEstimated"])
        self.assertFalse(out["profitProbabilityEstimated"])

    def test_complete_cvd_positive_negative_opposite_placebo_and_unknown(self):
        inputs=[
            event(symbol="EURUSD",cvdResult="BULLISH_CONFIRMED"),
            event(symbol="GBPUSD",cvdResult="NO_CONFIRMED_DIVERGENCE"),
            event(symbol="USDJPY",cvdResult="BEARISH_CONFIRMED"),
            event(symbol="USDCHF",cvdScanCoverage="PARTIAL",
                  cvdResult="NO_CONFIRMED_DIVERGENCE"),
        ]
        out=check(inputs)
        self.assertEqual(out["rowsCoreAdmitted"],4)
        self.assertEqual(out["sameCohortCvdAlignedCandidates"],1)
        self.assertEqual(out["sameCohortCvdFullScanNegativeCandidates"],1)
        self.assertEqual(out["sameCohortInvertedDirectionPlaceboCandidates"],1)
        self.assertEqual(out["sameCohortCvdUnknownCoverage"],1)
        self.assertTrue(out["unobservedCvdNeverTreatedAsNegative"])
        self.assertFalse(out["eligibleCvdScanProvenanceVerifiedIndependently"])
        self.assertFalse(out["priceSourceIntegrityVerifiedIndependently"])
        self.assertFalse(out["cotOriginalFirstSeenVerifiedIndependently"])
        self.assertFalse(out["independentlyRecordedOutcomes"])
        self.assertFalse(out["costsAndSlippageMeasured"])
        self.assertFalse(out["liveSignalsOrOrdersAuthorized"])
        self.assertFalse(out["cvdResearchMayBeEnabled"])
        self.assertEqual(out["brokerCallsMade"],0)
        self.assertFalse(out["writesMade"])
        self.assertNotIn("DONT_EXPOSE_THIS_SECRET",json.dumps(out))
        self.assertNotIn("EURUSD",json.dumps(out))

    def test_future_pivot_confirmation_and_late_scan_never_retroactive(self):
        cases=[
            dict(cvdConfirmedAtUtc="2026-11-09T10:02:00Z"),
            dict(cvdScanWitnessAtUtc="2026-11-09T10:02:00Z"),
            dict(cvdScanWitnessAtUtc="2026-11-09T06:01:00Z"),
            dict(cvdScanWitnessAtUtc="2026-11-08T23:59:59Z"),
            dict(cvdConfirmedAtUtc="2026-11-08T23:59:59Z"),
            dict(cvdConfirmedAtUtc="2026-11-09T10:00:55Z"),
            dict(cvdAlgorithm="impostor_real_aggressor_flow"),
            dict(cvdSourceWitnessSha256="123"),
            dict(cvdSourceWitnessSha256="A"*64),
            dict(cvdQualityVerified=False),
            dict(cvdFullMarketUniverseAtObservation=False),
            dict(cvdOriginalClosedBarsVerified=False),
            dict(cvdScanCoverage="UNKNOWN",cvdResult="NO_CONFIRMED_DIVERGENCE"),
        ]
        for update in cases:
            with self.subTest(update=update):
                report=check([event(**update)])
                self.assertEqual(report["rowsCoreAdmitted"],1)
                self.assertEqual(report["sameCohortCvdUnknownCoverage"],1)
                self.assertEqual(report["sameCohortCvdFullScanNegativeCandidates"],0)
                self.assertEqual(report["sameCohortCvdAlignedCandidates"],0)

    def test_core_future_sources_are_not_valid_historically(self):
        cases=[
            dict(cotFirstSeenAtUtc="2026-11-09T10:02:00Z"),
            dict(priceWitnessAtUtc="2026-11-09T10:05:00Z"),
            dict(retailFirstSeenAtUtc="2026-11-09T10:05:00Z"),
            dict(m15ClosedAtUtc="2026-11-09T10:15:00Z"),
        ]
        for update in cases:
            with self.subTest(update=update):
                result=check([event(**update)])
                self.assertEqual(result["rowsCoreAdmitted"],0)
                self.assertEqual(result["exclusionReasons"]["future_core_source"],1)

    def test_stale_bad_frame_and_backdated_report_are_excluded(self):
        bad=[
            event(retailFirstSeenAtUtc="2026-11-09T06:00:00Z"),
            event(priceWitnessAtUtc="2026-11-09T08:00:00Z"),
            event(m15ClosedAtUtc="2026-11-09T09:59:00Z"),
            event(cotReportDate="2026-10-01"),
            event(cotReportDate="2026-11-10"),
            event(cotReportDate="malformed"),
            event(cotDataset="made_up"),
            event(priceQualityVerified=False),
            event(provider="not_ctrader"),
        ]
        for data in bad:
            with self.subTest(data=data):
                result=check([data])
                self.assertEqual(result["rowsCoreAdmitted"],0)

    def test_two_cot_versions_or_duplicate_signal_at_same_instant_not_independent(self):
        duplicate=event(cotReportDate="2026-10-28",cvdResult="NO_CONFIRMED_DIVERGENCE")
        r=check([event(),duplicate])
        self.assertEqual(r["rowsCoreAdmitted"],0)
        self.assertEqual(r["exclusionReasons"]["ambiguous_duplicate_observation"],2)
        self.assertEqual(r["coreDistinctObservationDates"],0)
        self.assertEqual(r["coreDistinctCotReportDates"],0)
        r_reverse=check([duplicate,event()])
        self.assertEqual(r_reverse["rowsCoreAdmitted"],0)
        self.assertEqual(r_reverse["exclusionReasons"]["ambiguous_duplicate_observation"],2)

    def test_invalid_clock_dst_ambiguity_and_nonutc_are_not_assumed(self):
        cases=[
            dict(observedAtUtc="2026-11-09T10:01:00+01:00"),
            dict(observedAtUtc="2026-11-09T10:01:00"),
            dict(observedAtUtc="2026-13-09T10:01:00Z"),
            dict(m15ClosedAtUtc="2026-11-09T10:00:00+00:00"),
            dict(firstRecordedAtUtc="2026-11-09T10:01:01Z"),
        ]
        for update in cases:
            with self.subTest(update=update):
                r=check([event(**update)])
                self.assertEqual(r["rowsCoreAdmitted"],0)

    def test_invalid_or_unrelated_inputs_never_leak_secrets(self):
        cases=[
            None,False,{},[],123,
            {"schema":p.INPUT_SCHEMA,"symbol":"MY_PRIVATE_PASSWORD"},
            event(direction=True),
            event(direction="LONG"),
            event(symbol="private/secret"),
            event(schema="fake"),
        ]
        out=check(cases)
        self.assertEqual(out["rowsCoreAdmitted"],0)
        self.assertEqual(out["rowsExcluded"],len(cases))
        self.assertNotIn("private",json.dumps(out).lower())
        with self.assertRaises(ValueError):
            check("not a list")
        with self.assertRaises(ValueError):
            check([event()]*(p.MAX_RECORDS+1))

    def test_fabricated_profitable_outcomes_not_accepted_or_reported(self):
        forged=event(
            winningTrade=True,roiPercent=99999.0,
            nominalProbability=99.99,netPnl=1e9,
            cbPositionIsInstitutional=True)
        report=check([forged])
        self.assertEqual(report["rowsCoreAdmitted"],1)
        self.assertFalse(report["causalIncrementalCvdEffectEstimated"])
        self.assertFalse(report["profitProbabilityEstimated"])
        self.assertFalse(report["liveSignalsOrOrdersAuthorized"])
        self.assertNotIn("netPnl",json.dumps(report))
        self.assertNotIn("winningTrade",json.dumps(report))

    def test_standalone_explicit_stdin_only_with_no_files_written(self):
        script=Path(p.__file__).resolve()
        with tempfile.TemporaryDirectory(prefix="remura-cvd-study-") as folder:
            env={**os.environ,"PYTHONPATH":""}
            good={
                "asOfUtc":ASOF,
                "protocolSha256":p.protocol_sha256(),
                "records":[event()],
            }
            args=[sys.executable,"-B",str(script),"--audit-stdin"]
            run=subprocess.run(args,cwd=folder,env=env,
                               input=json.dumps(good),text=True,
                               capture_output=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertTrue(run.stdout.startswith("REMURA_CVD_PREREGISTRATION="))
            data=json.loads(run.stdout.split("=",1)[1])
            self.assertEqual(data["rowsCoreAdmitted"],1)
            self.assertFalse(data["cvdResearchMayBeEnabled"])
            self.assertEqual(list(Path(folder).iterdir()),[])
            bad=copy.deepcopy(good)
            bad["protocolSha256"]="bad_digest"
            run=subprocess.run(args,cwd=folder,env=env,
                               input=json.dumps(bad),text=True,
                               capture_output=True,timeout=10)
            self.assertEqual(run.returncode,2)
            self.assertIn("NO_GO_INVALID_INPUT",run.stdout)
            self.assertEqual(list(Path(folder).iterdir()),[])
            run=subprocess.run([sys.executable,"-B",str(script),"--self-check"],
                               cwd=folder,env=env,text=True,
                               capture_output=True,timeout=10)
            self.assertEqual(run.returncode,0)
            self.assertEqual(run.stdout.strip(),
                             "REMURA_CVD_PREREGISTRATION="+p.protocol_sha256())
            self.assertEqual(list(Path(folder).iterdir()),[])


if __name__=="__main__":
    unittest.main()
