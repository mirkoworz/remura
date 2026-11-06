"""Offline-only tests for the P0b passive one-natural-batch observer.

No Oracle, cTrader, SQLite, secrets, network, real systemd, sleeps or LIVE.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_p0b_passive_observer as p


def samples():
    result=[]
    for i in range(p.SAMPLE_COUNT):
        result.append({
            "cpuUsec":12_000_000+i*5_000,
            "sampleMonotonicSeconds":float(i*5),
            "cgroupThrottlePeriods":3+i//6,
            "cgroupThrottleUsec":100+i*25,
            "serviceMemBytes":60*1024*1024+i*1024,
            "hostMemAvailableKiB":655360-i*8,
            "cpuPsiSomeUsec":20000+i,
            "ioPsiSomeUsec":10000+2*i,
            "memoryPsiSomeUsec":5000+i,
        })
    return result


class FakeClock:
    def __init__(self,t):
        self.t=float(t)
        self.sleeps=[]
    def now(self):
        return self.t
    def sleep(self,value):
        if value < 0 or value > p.QUARTER_SECONDS:
            raise AssertionError("sleep outside bounded one-shot window")
        self.t += value
        self.sleeps.append(value)


class ObserverTests(unittest.TestCase):
    def test_next_complete_natural_quarter_and_near_deadline(self):
        # In a local arbitrary day 20:03:00 -> 20:16:30.
        target,begin,end=p.planned_window(20*3600+3*60)
        self.assertEqual(target,20*3600+16*60+30)
        self.assertEqual(begin,target-10)
        self.assertEqual(end,target+75)
        # When called only 9 seconds before start, skip to NEXT quarter.
        t2,b2,e2=p.planned_window(target-9)
        self.assertEqual(t2,target+p.QUARTER_SECONDS)
        self.assertEqual(e2-b2,85)
        # Exactly at deadline is also too late.
        self.assertEqual(p.planned_window(begin)[0],target+900)
        for bad in (True,0,-1,float("nan"),float("inf"),"12:30"):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    p.planned_window(bad)

    def test_pure_aggregate_only_baseline_never_authorizes_cvd(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        out=p.aggregate(samples(),target=target,window_start=begin,
                        window_end=end,
                        before={"samples":12,"ingestUtcSeconds":target-900+17},
                        after={"samples":13,"ingestUtcSeconds":target+17},
                        pid_before=100,pid_after=100)
        self.assertEqual(out["status"],"NATURAL_INGEST_BASELINE_OBSERVED")
        self.assertEqual(out["samples"],p.SAMPLE_COUNT)
        self.assertEqual(out["windowSeconds"],85)
        self.assertEqual(out["serviceCpuDuringWindowMs"],85)
        self.assertEqual(out["serviceCpuPctOfOneFullCore"],0.1)
        self.assertEqual(out["cpuPsiSomeTotalDeltaMs"],0.017)
        self.assertEqual(out["schema"],
                         "remura-track-b-p0b-passive-natural-batch-v2")
        self.assertEqual(out["maxSampledFiveSecondCpuMs"],5.0)
        self.assertEqual(out["maxSampledFiveSecondCpuPctOfOneFullCore"],0.1)
        self.assertEqual(out["minObservedSampleIntervalSeconds"],5)
        self.assertEqual(out["maxObservedSampleIntervalSeconds"],5)
        self.assertEqual(out["observedSamplingSpanSeconds"],85)
        self.assertTrue(out["cgroupCpuThrottleObservable"])
        self.assertEqual(out["cgroupCpuThrottlePeriodDelta"],2)
        self.assertEqual(out["cgroupCpuThrottledMsDelta"],0.425)
        self.assertFalse(out["providerHypervisorThrottleMeasured"])
        self.assertEqual(out["ioPsiSomeTotalDeltaMs"],0.034)
        self.assertFalse(out["realCvdCollectorCoLoadTested"])
        self.assertFalse(out["cvdResearchMayBeEnabled"])
        self.assertFalse(out["oracleBillingVerified"])
        self.assertFalse(out["oracleCpuEntitlementMeasured"])
        self.assertEqual(out["additionalBrokerCalls"],0)
        self.assertEqual(out["localReadOnlyStatusGets"],2)
        self.assertFalse(out["writesOrServiceChanges"])
        self.assertNotIn("EURUSD",str(out))
        self.assertNotIn("access_token",str(out))

    def test_one_shot_observe_without_real_clock_or_network(self):
        testclock=FakeClock(20*3600+3*60)
        target,_,_=p.planned_window(testclock.now())
        values=iter(samples())
        responses=iter([
            {"samples":218,"ingestUtcSeconds":target-900+17},
            {"samples":219,"ingestUtcSeconds":target+17},
        ])
        counts={"read":0,"status":0,"service":0}
        def read():
            counts["read"]+=1
            return next(values)
        def status():
            counts["status"]+=1
            return next(responses)
        def identity():
            counts["service"]+=1
            return 44
        with patch.object(p.urllib.request,"build_opener",
                          side_effect=AssertionError("no real HTTP")), \
             patch.object(p.subprocess,"run",
                          side_effect=AssertionError("no real systemctl")):
            out=p.observe(clock=testclock.now,sleeper=testclock.sleep,
                          monotonic=testclock.now,
                          sampler=read,status=status,identity=identity)
        self.assertEqual(out["status"],"NATURAL_INGEST_BASELINE_OBSERVED")
        self.assertEqual(counts,{"read":p.SAMPLE_COUNT,"status":2,"service":2})
        self.assertEqual(testclock.now(),target+p.AFTER_SECONDS)
        self.assertLessEqual(max(testclock.sleeps),p.QUARTER_SECONDS)

    def test_missing_or_stale_natural_ingest_is_never_success(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        good={"samples":218,"ingestUtcSeconds":target-900+17}
        for newer in (
            {"samples":218,"ingestUtcSeconds":good["ingestUtcSeconds"]},
            {"samples":219,"ingestUtcSeconds":target+200},
            {"samples":219,"ingestUtcSeconds":target-30},
            {"samples":217,"ingestUtcSeconds":target+17},
        ):
            with self.subTest(after=newer):
                out=p.aggregate(samples(),target=target,window_start=begin,
                                window_end=end,before=good,after=newer,
                                pid_before=100,pid_after=100)
                self.assertEqual(out["status"],
                                 "NO_GO_INGEST_OR_SERVICE_NOT_CONFIRMED")
                self.assertFalse(out["cvdResearchMayBeEnabled"])

    def test_bounded_256_record_rollover_requires_newer_timestamp(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        before={"samples":256,"ingestUtcSeconds":target-900+17}
        after={"samples":256,"ingestUtcSeconds":target+17}
        out=p.aggregate(samples(),target=target,window_start=begin,
                        window_end=end,before=before,after=after,
                        pid_before=100,pid_after=100)
        self.assertTrue(out["collectorRecordAdvancedInWindow"])
        out=p.aggregate(samples(),target=target,window_start=begin,
                        window_end=end,before=before,after=after,
                        pid_before=100,pid_after=101)
        self.assertEqual(out["status"],
                         "NO_GO_INGEST_OR_SERVICE_NOT_CONFIRMED")

    def test_counter_regression_and_missing_sample_fail_closed(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        before={"samples":1,"ingestUtcSeconds":target-900}
        after={"samples":2,"ingestUtcSeconds":target+10}
        def call(values):
            return p.aggregate(values,target=target,window_start=begin,
                               window_end=end,before=before,after=after,
                               pid_before=100,pid_after=100)
        with self.assertRaisesRegex(ValueError,"incomplete_observation"):
            call(samples()[:-1])
        bad=samples();bad[8]["cpuUsec"]=0
        with self.assertRaisesRegex(ValueError,"counter_reset"):
            call(bad)
        bad=samples();bad[10]["ioPsiSomeUsec"]=-1
        with self.assertRaisesRegex(ValueError,"invalid_observation"):
            call(bad)
        bad=samples();bad[0]["serviceMemBytes"]=True
        with self.assertRaisesRegex(ValueError,"invalid_observation"):
            call(bad)

    def test_true_five_second_cpu_burst_not_hidden_by_85_second_mean(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        arr=samples()
        for i, item in enumerate(arr):
            item["cpuUsec"]=12_000_000+(0 if i < 7 else 2_000_000)
        out=p.aggregate(arr,target=target,window_start=begin,window_end=end,
                        before={"samples":1,"ingestUtcSeconds":target-900},
                        after={"samples":2,"ingestUtcSeconds":target+10},
                        pid_before=100,pid_after=100)
        self.assertEqual(out["serviceCpuDuringWindowMs"],2000.0)
        self.assertAlmostEqual(out["serviceCpuPctOfOneFullCore"],2.3529,places=4)
        self.assertEqual(out["maxSampledFiveSecondCpuMs"],2000.0)
        self.assertEqual(out["maxSampledFiveSecondCpuPctOfOneFullCore"],40.0)
        self.assertFalse(out["cvdResearchMayBeEnabled"])

    def test_measured_monotonic_intervals_prevent_false_peak_cpu_rates(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        arr=samples()
        for i,record in enumerate(arr):
            record["sampleMonotonicSeconds"]=i*5.05
            record["cpuUsec"]=12_000_000+i*5_000
        out=p.aggregate(arr,target=target,window_start=begin,window_end=end,
                        before={"samples":1,"ingestUtcSeconds":target-900},
                        after={"samples":2,"ingestUtcSeconds":target+10},
                        pid_before=100,pid_after=100)
        # A 5.05s interval with 5ms CPU is below 0.1% of one core.
        self.assertEqual(out["maxSampledFiveSecondCpuMs"],5)
        self.assertAlmostEqual(out["maxSampledFiveSecondCpuPctOfOneFullCore"],
                               0.099,places=3)
        self.assertEqual(out["minObservedSampleIntervalSeconds"],5.05)
        self.assertEqual(out["maxObservedSampleIntervalSeconds"],5.05)
        self.assertEqual(out["observedSamplingSpanSeconds"],85.85)
        arr[8]["sampleMonotonicSeconds"]=arr[7]["sampleMonotonicSeconds"]
        with self.assertRaisesRegex(ValueError,"invalid_five_second_interval"):
            p.aggregate(arr,target=target,window_start=begin,window_end=end,
                        before={"samples":1,"ingestUtcSeconds":target-900},
                        after={"samples":2,"ingestUtcSeconds":target+10},
                        pid_before=100,pid_after=100)

    def test_missing_linux_throttling_fields_are_unknown_not_zero(self):
        target,begin,end=p.planned_window(20*3600+3*60)
        arr=samples()
        for item in arr:
            item["cgroupThrottlePeriods"]=None
            item["cgroupThrottleUsec"]=None
        kw=dict(target=target,window_start=begin,window_end=end,
                before={"samples":1,"ingestUtcSeconds":target-900},
                after={"samples":2,"ingestUtcSeconds":target+10},
                pid_before=100,pid_after=100)
        out=p.aggregate(arr,**kw)
        self.assertFalse(out["cgroupCpuThrottleObservable"])
        self.assertIsNone(out["cgroupCpuThrottlePeriodDelta"])
        self.assertIsNone(out["cgroupCpuThrottledMsDelta"])
        self.assertFalse(out["oracleCpuEntitlementMeasured"])
        arr[9]["cgroupThrottlePeriods"]=12
        with self.assertRaisesRegex(ValueError,"partial_or_invalid"):
            p.aggregate(arr,**kw)
        arr=samples()
        arr[9]["cgroupThrottleUsec"]=0
        with self.assertRaisesRegex(ValueError,"counter_reset"):
            p.aggregate(arr,**kw)

    def test_deadline_miss_fails_before_falsely_reporting_overlap(self):
        t=FakeClock(20*3600+3*60)
        def slow_sleep(secs):
            t.t+=secs+3
        with self.assertRaisesRegex(ValueError,"deadline_missed"):
            p.observe(clock=t.now,sleeper=slow_sleep,
                      sampler=lambda:None,
                      status=lambda:{"samples":218,"ingestUtcSeconds":1},
                      identity=lambda:12)

    def test_linux_kernel_counter_parser_and_symlink_rejection(self):
        self.assertEqual(p._counter_rows("usage_usec 123\nuser_usec 56\n"),
                         {"usage_usec":123,"user_usec":56})
        with tempfile.TemporaryDirectory(prefix="remura-p0b-test-") as folder:
            base=Path(folder)
            good=base/"psi"
            good.write_text("some avg10=0.00 avg60=0.00 avg300=0.00 total=72\n")
            self.assertEqual(p._psi_some_total(good),72)
            link=base/"link"
            link.symlink_to(good)
            with self.assertRaisesRegex(ValueError,"untrusted_kernel_counter"):
                p._small_text(link)
            bad=base/"bad"
            bad.write_text("some avg10=0.00\n")
            with self.assertRaisesRegex(ValueError,"psi_some_total"):
                p._psi_some_total(bad)
            huge=base/"huge"
            huge.write_text("x"*(p.MAX_READ_BYTES+1))
            with self.assertRaisesRegex(ValueError,"oversized_kernel_counter"):
                p._small_text(huge)

    def test_service_identity_fails_on_other_service_or_restart(self):
        class Result:
            returncode=0
            stdout="ActiveState=active\nMainPID=123\nControlGroup=/system.slice/remura-private.service\n"
        with patch.object(p.subprocess,"run",return_value=Result()) as stub:
            self.assertEqual(p.service_identity(),123)
            self.assertEqual(stub.call_args.args[0][:3],
                             ["systemctl","show","remura-private.service"])
        class Bad:
            returncode=0
            stdout="ActiveState=active\nMainPID=1\nControlGroup=/system.slice/other.service\n"
        with patch.object(p.subprocess,"run",return_value=Bad()):
            with self.assertRaisesRegex(ValueError,"expected_cgroup"):
                p.service_identity()

    def test_only_two_localhost_reads_and_no_proxy_or_redirect(self):
        payload={
            "schema":"remura-squalincome-monitor-v1",
            "collectorTiming":{
                "schema":"remura-collector-batch-timing-v1",
                "state":"ready",
                "lastIngestReturnedUtc":"2026-11-05T20:01:47Z",
                "samples":219,
                "untrustedProviderToken":"PRIVATE_TOKEN_NEVER_EXPOSE",
            },
        }
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return json.dumps(payload).encode("utf-8")
        class Opener:
            def open(self,request,timeout):
                self.request=request
                return Response()
        op=Opener()
        with patch.object(p.urllib.request,"build_opener",return_value=op) as construct:
            report=p.local_batch_status()
        self.assertEqual(report["samples"],219)
        self.assertEqual(op.request.full_url,p.SIGNALS_URL)
        self.assertEqual(op.request.get_method(),"GET")
        self.assertNotIn("PRIVATE_TOKEN_NEVER_EXPOSE",str(report))
        self.assertTrue(any(isinstance(x,p.NoRedirect)
                            for x in construct.call_args.args))
        payload["collectorTiming"]["state"]="disabled"
        with patch.object(p.urllib.request,"build_opener",return_value=op):
            with self.assertRaisesRegex(ValueError,"collector_timing_not_ready"):
                p.local_batch_status()

    def test_main_offline_self_check_and_opaque_error_handling(self):
        output=io.StringIO()
        with patch.object(p,"observe",
                          side_effect=AssertionError("must not execute observe")), \
             redirect_stdout(output):
            self.assertEqual(p.main(["--self-check"]),0)
        self.assertEqual(output.getvalue().strip(),
                         "REMURA_P0B_PASSIVE_SELF_CHECK=PASS")
        output=io.StringIO()
        with patch.object(p,"observe",side_effect=OSError(
                "PRIVATE_LOCAL_PATH_AND_CREDENTIALS")),redirect_stdout(output):
            self.assertEqual(p.main(["--observe"]),2)
        self.assertEqual(output.getvalue().strip(),
                         "REMURA_P0B_PASSIVE=NO_GO_READ_ONLY_OBSERVATION_FAILED")

    def test_executable_outside_checkout_without_import_install_or_files(self):
        target=Path(p.__file__).resolve()
        with tempfile.TemporaryDirectory(prefix="remura-p0b-standalone-") as folder:
            completed=subprocess.run(
                [sys.executable,"-B",str(target),"--self-check"],
                cwd=folder,env={**os.environ,"PYTHONPATH":""},
                capture_output=True,text=True,timeout=10,check=False)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(completed.stdout.strip(),
                             "REMURA_P0B_PASSIVE_SELF_CHECK=PASS")
            self.assertEqual(list(Path(folder).iterdir()),[])


if __name__=="__main__":
    unittest.main()
