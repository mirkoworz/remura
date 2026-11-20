#!/usr/bin/env python3
# REMURA v0.8.82 LAB — 14/11/2026 20:28 CET
"""Explicit one-shot private LAB orchestration. No CLI, scheduler, output
files, broker, notification transport or live activation. Caller provides
trusted detached exports, local lock and genuine quota reports.
"""
from copy import deepcopy
from contextlib import ExitStack
import time
from cvd_runtime_singleflight_v1 import single_flight
from cvd_staged_runtime_preflight_v1 import prepared
from cvd_linux_host_evidence_v1 import sample_host
from cvd_runtime_resource_gate_v1 import assess
from cvd_guarded_collection_v2 import collect_guarded
MAX_RUN_MS=120000
MAX_CLOCK_DRIFT_MS=5000

def run_once(root,digests,lock_root,account_id,token,*,budget,explicit=False,
             secret=None,origin="LOCAL_SNAPSHOT"):
    if explicit is not True:raise ValueError("explicit_one_shot_required")
    if origin not in ("LOCAL_SNAPSHOT","SYNTHETIC"):raise ValueError("runtime_origin")
    # Freeze caller metadata; secret never returned. Retail activation remains excluded.
    budget=deepcopy(budget);digests=deepcopy(digests)
    start_wall=time.time_ns()//1000000; start_mono=time.monotonic_ns()//1000000
    with single_flight(lock_root) as still_held:
        def guard():
            still_held()
            host=sample_host()
            now=time.time_ns()//1000000
            elapsed=time.monotonic_ns()//1000000-start_mono
            if (not 0<=elapsed<=MAX_RUN_MS or now<start_wall or
                abs((now-start_wall)-elapsed)>MAX_CLOCK_DRIFT_MS):
                raise ValueError("runtime_clock_or_deadline")
            gate=assess(now=now,host=host,budget=budget)
            if gate["status"]!="ONE_SHOT_TEST_PREVIEW_PLAUSIBLE":
                raise ValueError("runtime_resource_blocked")
            return now
        guard()
        with prepared(root,digests,budget=budget,explicit=True) as (core,private,_):
            cutoff=guard()
            if (private is None)!=(secret is None):raise ValueError("runtime_private_secret_scope")
            result=collect_guarded(core,account_id,token,now=cutoff,explicit=True,
                                   private=private,secret=secret,guard=guard,origin=origin)
            guard()
            return {"schema":"remura.tv.one.shot.preview.v1","version":"0.8.82-lab",
                    "status":"LOCAL_PREVIEW_ONLY","cutoff_ms":cutoff,"preview":result,
                    "cooperating_host_lock":True,"cross_host_exclusion":False,
                    "hard_deadline_enforced":False,"account_quota_reserved_atomically":False,
                    "retail_enabled":False,"live_authorized":False,"notifications_enabled":False,
                    "orders_enabled":False}
