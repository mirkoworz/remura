#!/usr/bin/env python3
"""Track B P0b: one-shot PASSIVE observation of ONE natural cTrader batch.

Stand-alone, stdlib-only; NO CVD, cTrader APIs, database file access, signals,
orders, credentials, filesystem writes, service changes or cron installation.
Reads cgroup v2 + /proc counters and TWO existing *localhost* metadata
summaries, before and after the natural M15 scheduled batch. No raw JSON
is printed, stored, or forwarded.

Only --self-check is used by GitHub CI; --observe requires explicit operator
execution on the authorized Oracle host. The E2.1.Micro CPU entitlement is
NOT measured by cgroup CPU usage; results never authorize a CVD deployment.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import urllib.request

SCHEMA = "remura-track-b-p0b-passive-natural-batch-v2"
SERVICE = "remura-private.service"
CGROUP_BASE = Path("/sys/fs/cgroup/system.slice/remura-private.service")
SIGNALS_URL = "http://127.0.0.1:8765/private-api/signals/status"
QUARTER_SECONDS = 900
CLOSE_GRACE_SECONDS = 90
BEFORE_SECONDS = 10
AFTER_SECONDS = 75
SAMPLE_STEP_SECONDS = 5
SAMPLE_COUNT = (BEFORE_SECONDS + AFTER_SECONDS) // SAMPLE_STEP_SECONDS + 1
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_READ_BYTES = 4096
MiB = 1024 * 1024


def planned_window(now_seconds):
    """Next *complete* natural M15 observation interval, in UTC seconds."""
    if (type(now_seconds) not in (int, float) or
            not math.isfinite(now_seconds) or now_seconds <= 0):
        raise ValueError("invalid_clock")
    target = ((int(now_seconds - CLOSE_GRACE_SECONDS) // QUARTER_SECONDS)
              + 1) * QUARTER_SECONDS + CLOSE_GRACE_SECONDS
    if target - BEFORE_SECONDS <= now_seconds:
        target += QUARTER_SECONDS
    if not 0 < target - BEFORE_SECONDS - now_seconds <= QUARTER_SECONDS:
        raise ValueError("invalid_window")
    return target, target - BEFORE_SECONDS, target + AFTER_SECONDS


def _small_text(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ValueError("untrusted_kernel_counter")
    with path.open("r", encoding="ascii") as stream:
        data = stream.read(MAX_READ_BYTES + 1)
    if len(data) > MAX_READ_BYTES:
        raise ValueError("oversized_kernel_counter")
    return data


def _counter_rows(contents):
    values = {}
    for line in contents.splitlines():
        bits = line.split()
        if len(bits) == 2 and re.fullmatch(r"[a-z_]+", bits[0]) and bits[1].isdigit():
            values[bits[0]] = int(bits[1])
    return values


def _psi_some_total(path):
    for line in _small_text(path).splitlines():
        bits = line.split()
        if bits and bits[0] == "some":
            fields = dict(x.split("=", 1) for x in bits[1:] if "=" in x)
            value = fields.get("total", "")
            if value.isdecimal():
                return int(value)
    raise ValueError("psi_some_total_unavailable")


def _available_kib():
    for line in _small_text("/proc/meminfo").splitlines():
        if line.startswith("MemAvailable:"):
            fields = line.split()
            if len(fields) == 3 and fields[1].isdigit() and fields[2] == "kB":
                return int(fields[1])
    raise ValueError("mem_available_unavailable")


def service_identity():
    """One bounded systemctl metadata query, not systemd control or restart."""
    output = subprocess.run(
        ["systemctl", "show", SERVICE,
         "-p", "ActiveState", "-p", "MainPID", "-p", "ControlGroup",
         "--no-pager"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if output.returncode or len(output.stdout) > 4096:
        raise ValueError("service_metadata_unavailable")
    fields = dict(row.split("=", 1) for row in output.stdout.splitlines()
                  if "=" in row)
    if (fields.get("ActiveState") != "active" or
            not (fields.get("MainPID", "").isdigit() and
                 int(fields["MainPID"]) > 0) or
            fields.get("ControlGroup") != "/system.slice/remura-private.service"):
        raise ValueError("service_not_in_expected_cgroup")
    # If the service is moved to another slice, fail closed rather than
    # read unrelated processes or assume a different collector topology.
    return int(fields["MainPID"])


def read_host_counters():
    """Reads small world-readable Linux cgroup v2 and procfs counters."""
    for directory in (Path("/sys/fs/cgroup"),
                      Path("/sys/fs/cgroup/system.slice"), CGROUP_BASE):
        mode = directory.lstat().st_mode
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            raise ValueError("cgroup_path_untrusted")
    cpu = _counter_rows(_small_text(CGROUP_BASE / "cpu.stat"))
    if "usage_usec" not in cpu:
        raise ValueError("cgroup_v2_cpu_unavailable")
    memory = _small_text(CGROUP_BASE / "memory.current").strip()
    if not memory.isdecimal():
        raise ValueError("cgroup_memory_unavailable")
    throttle_fields = ("nr_throttled", "throttled_usec")
    present = [key in cpu for key in throttle_fields]
    if any(present) and not all(present):
        raise ValueError("partial_kernel_throttle_counters")
    throttle = dict(zip(throttle_fields,
                        (cpu[k] for k in throttle_fields))) if all(present) else {}
    return {
        "cpuUsec":cpu["usage_usec"],
        "cgroupThrottlePeriods":throttle.get("nr_throttled"),
        "cgroupThrottleUsec":throttle.get("throttled_usec"),
        "serviceMemBytes":int(memory),
        "hostMemAvailableKiB":_available_kib(),
        "cpuPsiSomeUsec":_psi_some_total("/proc/pressure/cpu"),
        "ioPsiSomeUsec":_psi_some_total("/proc/pressure/io"),
        "memoryPsiSomeUsec":_psi_some_total("/proc/pressure/memory"),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("localhost_redirect_forbidden")


def local_batch_status():
    """Exactly one GET to the already-running REMURA localhost service."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        SIGNALS_URL, headers={"Accept":"application/json"}, method="GET")
    with opener.open(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError("localhost_status_not_200")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("localhost_status_too_large")
    doc = json.loads(raw)
    if not isinstance(doc, dict) or doc.get("schema") != "remura-squalincome-monitor-v1":
        raise ValueError("localhost_status_schema_unexpected")
    timing = doc.get("collectorTiming")
    if (not isinstance(timing, dict) or
            timing.get("schema") != "remura-collector-batch-timing-v1" or
            timing.get("state") != "ready"):
        raise ValueError("collector_timing_not_ready")
    stamp = timing.get("lastIngestReturnedUtc")
    if not isinstance(stamp, str):
        raise ValueError("ingest_stamp_absent")
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("unzonified_ingest_stamp")
    samples = timing.get("samples")
    if type(samples) is not int or not 1 <= samples <= 256:
        raise ValueError("invalid_collector_samples")
    return {
        "ingestUtcSeconds":when.astimezone(timezone.utc).timestamp(),
        "samples":samples,
    }


def _utc_seconds(seconds):
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def aggregate(samples, *, target, window_start, window_end,
              before, after, pid_before, pid_after):
    """Pure fail-closed aggregation; no fabricated measurements or trading OK."""
    if (len(samples) != SAMPLE_COUNT or
            type(pid_before) is not int or pid_before <= 0 or
            type(pid_after) is not int or pid_after <= 0):
        raise ValueError("incomplete_observation")
    names=("cpuUsec","serviceMemBytes","hostMemAvailableKiB",
           "cpuPsiSomeUsec","ioPsiSomeUsec","memoryPsiSomeUsec")
    if any(type(sample) is not dict or any(
            type(sample.get(k)) is not int or sample[k] < 0 for k in names)
           for sample in samples):
        raise ValueError("invalid_observation")
    sample_times = [sample.get("sampleMonotonicSeconds") for sample in samples]
    if any(type(t) not in (int,float) or not math.isfinite(t) or t < 0
           for t in sample_times):
        raise ValueError("invalid_sample_clock")
    elapsed_intervals = [sample_times[i+1]-sample_times[i]
                         for i in range(len(samples)-1)]
    if any(not 3 <= seconds <= 7 for seconds in elapsed_intervals):
        raise ValueError("invalid_five_second_interval")
    throttle_keys=("cgroupThrottlePeriods", "cgroupThrottleUsec")
    throttle_missing = all(
        sample.get("cgroupThrottlePeriods") is None and
        sample.get("cgroupThrottleUsec") is None for sample in samples)
    throttle_present = all(
        all(type(sample.get(k)) is int and sample[k] >= 0
            for k in throttle_keys) for sample in samples)
    if not (throttle_missing or throttle_present):
        raise ValueError("partial_or_invalid_kernel_throttle_counters")
    monotonic=("cpuUsec","cpuPsiSomeUsec","ioPsiSomeUsec",
               "memoryPsiSomeUsec")
    if throttle_present:
        monotonic += throttle_keys
    if any(samples[i][k] > samples[i+1][k]
           for k in monotonic for i in range(len(samples)-1)):
        raise ValueError("counter_reset_or_restart")
    if (not isinstance(before, dict) or not isinstance(after, dict) or
            any(type(info.get("samples")) is not int or
                type(info.get("ingestUtcSeconds")) not in (int,float)
                for info in (before,after))):
        raise ValueError("invalid_ingest_timestamps")
    newest = after["ingestUtcSeconds"]
    advanced = (newest > before["ingestUtcSeconds"] and
                window_start <= newest <= window_end+8 and
                (after["samples"] > before["samples"] or
                 (before["samples"] == after["samples"] == 256)))
    stable = pid_before == pid_after
    delta = samples[-1]["cpuUsec"]-samples[0]["cpuUsec"]
    cpu_intervals = [samples[i+1]["cpuUsec"]-samples[i]["cpuUsec"]
                     for i in range(len(samples)-1)]
    burst = max(cpu_intervals)
    burst_core_pct = max(100*usec/(seconds*1_000_000)
                         for usec,seconds in zip(cpu_intervals,
                                                 elapsed_intervals))
    duration = BEFORE_SECONDS+AFTER_SECONDS
    return {
        "schema":SCHEMA,
        "status":("NATURAL_INGEST_BASELINE_OBSERVED" if advanced and stable
                  else "NO_GO_INGEST_OR_SERVICE_NOT_CONFIRMED"),
        "targetUtc":_utc_seconds(target),
        "windowSeconds":duration,
        "samples":len(samples),
        "sampleIntervalSeconds":SAMPLE_STEP_SECONDS,
        "collectorRecordAdvancedInWindow":advanced,
        "servicePidUnchanged":stable,
        "serviceCpuDuringWindowMs":round(delta/1000, 3),
        "serviceCpuPctOfOneFullCore":round(
            100*delta/(duration*1_000_000), 4),
        "maxSampledFiveSecondCpuMs":round(burst/1000, 3),
        "maxSampledFiveSecondCpuPctOfOneFullCore":round(burst_core_pct, 4),
        "minObservedSampleIntervalSeconds":round(min(elapsed_intervals),4),
        "maxObservedSampleIntervalSeconds":round(max(elapsed_intervals),4),
        "cgroupCpuThrottleObservable":throttle_present,
        "cgroupCpuThrottlePeriodDelta":(
            samples[-1]["cgroupThrottlePeriods"]-
            samples[0]["cgroupThrottlePeriods"] if throttle_present else None),
        "cgroupCpuThrottledMsDelta":(
            round((samples[-1]["cgroupThrottleUsec"]-
                   samples[0]["cgroupThrottleUsec"])/1000, 3)
            if throttle_present else None),
        "maxSampledServiceMemMiB":round(
            max(v["serviceMemBytes"] for v in samples)/MiB, 2),
        "minSampledHostAvailableMiB":round(
            min(v["hostMemAvailableKiB"] for v in samples)/1024, 2),
        "cpuPsiSomeTotalDeltaMs":round(
            (samples[-1]["cpuPsiSomeUsec"]-samples[0]["cpuPsiSomeUsec"])/1000, 3),
        "ioPsiSomeTotalDeltaMs":round(
            (samples[-1]["ioPsiSomeUsec"]-samples[0]["ioPsiSomeUsec"])/1000, 3),
        "memoryPsiSomeTotalDeltaMs":round(
            (samples[-1]["memoryPsiSomeUsec"]-
             samples[0]["memoryPsiSomeUsec"])/1000, 3),
        "onlySampledMaximaNotActualPeaks":True,
        "oracleCpuEntitlementMeasured":False,
        "providerHypervisorThrottleMeasured":False,
        "realCvdCollectorCoLoadTested":False,
        "oracleBillingVerified":False,
        "cvdResearchMayBeEnabled":False,
        "additionalBrokerCalls":0,
        "localReadOnlyStatusGets":2,
        "writesOrServiceChanges":False,
    }


def observe(*, clock=time.time, sleeper=time.sleep,
            monotonic=time.monotonic,
            sampler=read_host_counters, status=local_batch_status,
            identity=service_identity):
    """One observation, no loop over batches and no daemon installation."""
    initial = clock()
    target, window_start, window_end = planned_window(initial)
    pid_before = identity()
    prior = status()
    delay = window_start-clock()
    if not 0 <= delay <= QUARTER_SECONDS:
        raise ValueError("window_not_available")
    sleeper(delay)
    samples=[]
    for index in range(SAMPLE_COUNT):
        due = window_start+index*SAMPLE_STEP_SECONDS
        rest = due-clock()
        if rest > 0:
            sleeper(rest)
        # Very late wakeup indicates unstable VM; do NOT claim overlap.
        if abs(clock()-due) > 2.5:
            raise ValueError("passive_sampling_deadline_missed")
        reading=sampler()
        if type(reading) is not dict:
            raise ValueError("invalid_counter_snapshot")
        # Monotonic timestamps give the ACTUAL interval, not the nominal
        # five seconds when a micro VM is briefly delayed by scheduling.
        samples.append({**reading, "sampleMonotonicSeconds":monotonic()})
    if clock() > window_end+3:
        raise ValueError("passive_sampling_overran")
    after = status()
    pid_after = identity()
    return aggregate(samples, target=target, window_start=window_start,
                     window_end=window_end, before=prior, after=after,
                     pid_before=pid_before, pid_after=pid_after)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ["--self-check"]:
        start=3600*20+120
        target, begin, end=planned_window(start)
        if not (begin < target < end and
                end-begin == BEFORE_SECONDS+AFTER_SECONDS):
            print("REMURA_P0B_PASSIVE_SELF_CHECK=FAIL")
            return 2
        print("REMURA_P0B_PASSIVE_SELF_CHECK=PASS")
        return 0
    if args != ["--observe"]:
        print("usage: python3 -B scripts/shark_p0b_passive_observer.py --self-check|--observe")
        return 2
    try:
        report=observe()
    except (OSError, ValueError, RuntimeError, TypeError,
            subprocess.SubprocessError, KeyError, OverflowError,
            json.JSONDecodeError, urllib.error.URLError):
        # Do not reveal paths, response payloads, access tokens or host details.
        print("REMURA_P0B_PASSIVE=NO_GO_READ_ONLY_OBSERVATION_FAILED")
        return 2
    print("REMURA_P0B_PASSIVE="+json.dumps(
        report,sort_keys=True,separators=(",",":")))
    return 0 if report["status"]=="NATURAL_INGEST_BASELINE_OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
