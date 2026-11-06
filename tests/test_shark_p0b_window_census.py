"""Offline-only checks for multi-window passive REMURA collector baseline census.

All observations synthesized unless stated otherwise; no OCI, SSH, broker,
SQLite, data sources, file output, trading or wall-clock sleeps.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import shark_p0b_window_census as census


def observation(target="2026-11-06T08:31:30Z", **changes):
    # Numbers below mirror the first OPERATOR-OBSERVED 2026-11-06
    # aggregate already recorded in ROADMAP-B, but this test does NOT
    # independently verify provenance, OCI billing or CVD co-load.
    report={
        "schema":"remura-track-b-p0b-passive-natural-batch-v1",
        "status":"NATURAL_INGEST_BASELINE_OBSERVED",
        "targetUtc":target,
        "windowSeconds":85,
        "samples":18,
        "sampleIntervalSeconds":5,
        "collectorRecordAdvancedInWindow":True,
        "servicePidUnchanged":True,
        "onlySampledMaximaNotActualPeaks":True,
        "oracleCpuEntitlementMeasured":False,
        "realCvdCollectorCoLoadTested":False,
        "oracleBillingVerified":False,
        "cvdResearchMayBeEnabled":False,
        "additionalBrokerCalls":0,
        "localReadOnlyStatusGets":2,
        "writesOrServiceChanges":False,
        "serviceCpuPctOfOneFullCore":2.048,
        "serviceCpuDuringWindowMs":1740.784,
        "maxSampledServiceMemMiB":113.33,
        "minSampledHostAvailableMiB":621.24,
        "cpuPsiSomeTotalDeltaMs":42.604,
        "ioPsiSomeTotalDeltaMs":88.052,
        "memoryPsiSomeTotalDeltaMs":0.0,
    }
    report.update(changes)
    return report


def observation_v2(target="2026-11-06T08:46:30Z", **changes):
    record=observation(target=target)
    record.update({
        "schema":"remura-track-b-p0b-passive-natural-batch-v2",
        "maxSampledFiveSecondCpuMs":800.0,
        "maxSampledFiveSecondCpuPctOfOneFullCore":16.0,
        "cgroupCpuThrottleObservable":True,
        "cgroupCpuThrottlePeriodDelta":2,
        "cgroupCpuThrottledMsDelta":12.2,
        "providerHypervisorThrottleMeasured":False,
    })
    record.update(changes)
    return record


def diversified_records():
    ts=[
        "2026-11-05T07:01:30Z",
        "2026-11-05T08:31:30Z",
        "2026-11-05T14:16:30Z",
        "2026-11-05T19:46:30Z",
        "2026-11-06T07:16:30Z",
        "2026-11-06T08:31:30Z",
        "2026-11-06T14:01:30Z",
        "2026-11-06T19:16:30Z",
    ]
    # Times represent test labels, NOT eight actual collected observations.
    return [observation(t) for t in ts]


class CensusTests(unittest.TestCase):
    def test_actual_first_operator_observation_is_only_one_window(self):
        result=census.summarize([observation()])
        self.assertEqual(result["status"],"BASELINE_COVERAGE_INCOMPLETE")
        self.assertEqual(result["windows"],1)
        self.assertEqual(result["windowsWithFiveSecondBurstData"],0)
        self.assertIsNone(result["maxSampledFiveSecondCpuPctOfOneCore"])
        self.assertEqual(result["windowsWithKernelThrottleCounters"],0)
        self.assertIsNone(result["maxCgroupCpuThrottledMsDelta"])
        self.assertFalse(result["providerHypervisorThrottleMeasured"])
        self.assertEqual(result["engineeringTargetWindows"],8)
        self.assertEqual(result["maxMeanServiceCpuPctOfOneCore"],2.048)
        self.assertEqual(result["maxServiceCpuWindowMs"],1740.784)
        self.assertEqual(result["maxSampledServiceMemMiB"],113.33)
        self.assertEqual(result["minSampledHostAvailableMiB"],621.24)
        self.assertFalse(result["realCvdCollectorCoLoadTested"])
        self.assertFalse(result["priceIngestLatencyRegressionMeasured"])
        self.assertFalse(result["sourceProvenanceVerified"])
        self.assertFalse(result["cvdResearchMayBeEnabled"])
        self.assertFalse(result["statisticalTradingEdgeEstablished"])

    def test_eight_distinct_windows_meet_only_descriptive_coverage(self):
        records=diversified_records()
        records.reverse()
        out=census.summarize(records)
        self.assertEqual(out["windows"],8)
        self.assertEqual(out["differentUtcDates"],2)
        self.assertGreaterEqual(out["differentUtcHours"],3)
        self.assertGreaterEqual(out["differentSixHourUtcBands"],2)
        self.assertEqual(out["firstTargetUtc"],"2026-11-05T07:01:30Z")
        self.assertEqual(out["lastTargetUtc"],"2026-11-06T19:16:30Z")
        self.assertEqual(out["status"],
                         "MULTI_WINDOW_BASELINE_COVERAGE_OBSERVED_NOT_CVD_GO")
        self.assertFalse(out["cvdResearchMayBeEnabled"])
        self.assertFalse(out["peakCpuQuotaUtilizationMeasured"])
        self.assertFalse(out["oracleFreeTierBillingVerified"])

    def test_v1_and_v2_are_comparable_but_v1_bursts_remain_unknown(self):
        out=census.summarize([observation(),observation_v2()])
        self.assertEqual(out["status"],"BASELINE_COVERAGE_INCOMPLETE")
        self.assertEqual(out["windows"],2)
        self.assertEqual(out["windowsWithFiveSecondBurstData"],1)
        self.assertEqual(out["maxSampledFiveSecondCpuPctOfOneCore"],16.0)
        self.assertEqual(out["windowsWithKernelThrottleCounters"],1)
        self.assertEqual(out["maxCgroupCpuThrottlePeriodDelta"],2)
        self.assertEqual(out["maxCgroupCpuThrottledMsDelta"],12.2)
        self.assertTrue(out["kernelThrottlingNotHypervisorThrottle"])
        self.assertFalse(out["peakCpuQuotaUtilizationMeasured"])
        self.assertFalse(out["cvdResearchMayBeEnabled"])

    def test_missing_linux_throttle_counters_are_unknown_not_zero(self):
        out=census.summarize([observation_v2(
            cgroupCpuThrottleObservable=False,
            cgroupCpuThrottlePeriodDelta=None,
            cgroupCpuThrottledMsDelta=None)])
        self.assertEqual(out["windowsWithFiveSecondBurstData"],1)
        self.assertEqual(out["windowsWithKernelThrottleCounters"],0)
        self.assertIsNone(out["maxCgroupCpuThrottledMsDelta"])
        self.assertIsNone(out["maxCgroupCpuThrottlePeriodDelta"])
        self.assertFalse(out["oracleFreeTierBillingVerified"])

    def test_forged_v2_burst_and_quota_metrics_fail_closed(self):
        cases=[
            {"maxSampledFiveSecondCpuMs":1600},
            {"maxSampledFiveSecondCpuPctOfOneFullCore":99},
            {"maxSampledFiveSecondCpuMs":1741},
            {"maxSampledFiveSecondCpuPctOfOneFullCore":1},
            {"cgroupCpuThrottleObservable":"true"},
            {"cgroupCpuThrottleObservable":True,
             "cgroupCpuThrottlePeriodDelta":None},
            {"cgroupCpuThrottledMsDelta":-1},
            {"cgroupCpuThrottleObservable":False},
            {"providerHypervisorThrottleMeasured":True},
        ]
        for updates in cases:
            with self.subTest(update=repr(updates)):
                with self.assertRaises(ValueError):
                    census.summarize([observation_v2(**updates)])

    def test_eight_in_one_date_are_not_diversified(self):
        stamps=[
            "2026-11-06T08:01:30Z",
            "2026-11-06T08:16:30Z",
            "2026-11-06T08:31:30Z",
            "2026-11-06T08:46:30Z",
            "2026-11-06T09:01:30Z",
            "2026-11-06T09:16:30Z",
            "2026-11-06T09:31:30Z",
            "2026-11-06T09:46:30Z",
        ]
        report=census.summarize([observation(t) for t in stamps])
        self.assertEqual(report["status"],"BASELINE_COVERAGE_INCOMPLETE")

    def test_duplicated_or_fake_m15_clock_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate_natural_batch"):
            census.summarize([observation(),observation()])
        for bad in (
            "2026-11-06T08:30:00Z",
            "2026-11-06T08:31:29Z",
            "2026-11-06T08:31:30+00:00",
            "2026-11-06T08:31:30",
            "2026-02-30T08:31:30Z",
            "PRIVATE-ACCOUNT-ID",
            None,
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    census.summarize([observation(target=bad)])

    def test_missing_type_changing_and_forged_safety_flags_rejected(self):
        pairs=[
            ("status","CVD_GO"),
            ("collectorRecordAdvancedInWindow",False),
            ("servicePidUnchanged",False),
            ("onlySampledMaximaNotActualPeaks",False),
            ("oracleCpuEntitlementMeasured",True),
            ("realCvdCollectorCoLoadTested",True),
            ("oracleBillingVerified",True),
            ("cvdResearchMayBeEnabled",True),
            ("additionalBrokerCalls",1),
            ("writesOrServiceChanges",True),
            ("localReadOnlyStatusGets",3),
            ("windowSeconds",90),
            ("samples",17),
            ("sampleIntervalSeconds",2),
            ("samples",True),
            ("serviceCpuPctOfOneFullCore",float("nan")),
            ("serviceCpuPctOfOneFullCore",float("inf")),
            ("serviceCpuDuringWindowMs",-0.01),
            ("minSampledHostAvailableMiB",True),
            ("ioPsiSomeTotalDeltaMs",-1),
        ]
        for key,val in pairs:
            with self.subTest(key=key,val=repr(val)):
                with self.assertRaises(ValueError):
                    census.summarize([observation(**{key:val})])

    def test_unhashable_or_wrong_schema_fails_closed(self):
        for shape in ({}, [], None, 123, False):
            with self.subTest(shape=repr(shape)):
                with self.assertRaisesRegex(ValueError,"invalid_input_schema"):
                    census.summarize([observation(schema=shape)])

    def test_cpu_units_must_match(self):
        with self.assertRaisesRegex(ValueError,"inconsistent_cpu_units"):
            census.summarize([observation(serviceCpuDuringWindowMs=1800)])

    def test_census_does_not_echo_extra_secrets(self):
        private="NEVER_EXPOSE_BROKER_PASSWORD_OR_PRIVATE_OHLC"
        out=census.summarize([observation(
            accountSecret=private, symbols=["EURUSD"], rawTokens=[private])])
        blob=json.dumps(out)
        self.assertNotIn(private,blob)
        self.assertNotIn("EURUSD",blob)
        self.assertNotIn("symbols",blob)

    def test_input_limit_and_nonlist_fail_closed(self):
        for bad in ([],{},[observation()]*33,None,True,"private"):
            with self.subTest(kind=str(type(bad))):
                with self.assertRaises(ValueError):
                    census.summarize(bad)

    def test_empirical_min_max_without_fake_p95_or_roi(self):
        records=diversified_records()
        records[0]["maxSampledServiceMemMiB"]=301.25
        records[1]["minSampledHostAvailableMiB"]=301.1
        records[2]["cpuPsiSomeTotalDeltaMs"]=501.2
        records[3]["ioPsiSomeTotalDeltaMs"]=1001.0
        records[4]["memoryPsiSomeTotalDeltaMs"]=30.0
        records[5]["serviceCpuDuringWindowMs"]=8500.0
        records[5]["serviceCpuPctOfOneFullCore"]=10.0
        out=census.summarize(records)
        self.assertEqual(out["maxSampledServiceMemMiB"],301.25)
        self.assertEqual(out["minSampledHostAvailableMiB"],301.1)
        self.assertEqual(out["maxWindowHostCpuPsiSomeDeltaMs"],501.2)
        self.assertEqual(out["maxWindowHostIoPsiSomeDeltaMs"],1001.0)
        self.assertEqual(out["maxWindowHostMemoryPsiSomeDeltaMs"],30.0)
        self.assertEqual(out["maxMeanServiceCpuPctOfOneCore"],10)
        self.assertNotIn("p95",str(out))
        self.assertNotIn("profit",str(out).lower())
        self.assertFalse(out["statisticalTradingEdgeEstablished"])

    def test_standalone_stdin_audit_no_write_no_network(self):
        script=Path(census.__file__).resolve()
        with tempfile.TemporaryDirectory(prefix="remura-census-check-") as wd:
            cmd=[sys.executable,"-B",str(script),"--audit-stdin"]
            proc=subprocess.run(cmd,cwd=wd,env={**os.environ,"PYTHONPATH":""},
                                input=json.dumps([observation()]),text=True,
                                capture_output=True,timeout=10)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertTrue(proc.stdout.startswith("REMURA_P0B_CENSUS="))
            payload=json.loads(proc.stdout.split("=",1)[1])
            self.assertEqual(payload["windows"],1)
            self.assertFalse(payload["cvdResearchMayBeEnabled"])
            self.assertEqual(list(Path(wd).iterdir()),[])
            proc2=subprocess.run(cmd,cwd=wd,env={**os.environ,"PYTHONPATH":""},
                                input='{"rawToken":"PRIVATE"}',text=True,
                                capture_output=True,timeout=10)
            self.assertEqual(proc2.returncode,2)
            self.assertEqual(proc2.stdout.strip(),
                "REMURA_P0B_CENSUS=NO_GO_INVALID_OR_UNVERIFIED_INPUT")
            self.assertNotIn("PRIVATE",proc2.stdout)
            check=subprocess.run([sys.executable,"-B",str(script),"--self-check"],
                                 cwd=wd,env={**os.environ,"PYTHONPATH":""},
                                 capture_output=True,text=True,timeout=10)
            self.assertEqual(check.returncode,0)
            self.assertEqual(check.stdout.strip(),
                             "REMURA_P0B_CENSUS_SELF_CHECK=PASS")
            self.assertEqual(list(Path(wd).iterdir()),[])


if __name__=="__main__":
    unittest.main()
