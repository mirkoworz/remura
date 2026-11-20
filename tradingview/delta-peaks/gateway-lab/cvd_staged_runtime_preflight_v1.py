#!/usr/bin/env python3
# REMURA v0.8.81 LAB — 14/11/2026 19:58 CET
"""One-shot staged preview preparation; no scheduler or live activation.
Budget evidence must come from the existing privately obtained monitor reports.
Never refresh quota by relabeling a report timestamp.
"""
from contextlib import contextmanager
import time
from cvd_runtime_resource_gate_v1 import assess
from cvd_detached_snapshots_v1 import open_snapshots
from cvd_linux_host_evidence_v1 import sample_host

@contextmanager
def prepared(root,digests,*,budget,explicit=False):
    if explicit is not True:raise ValueError("explicit_preparation_required")
    def gate():
        host=sample_host()
        return assess(now=time.time_ns()//1000000,host=host,budget=budget)
    before=gate()
    if before["status"]=="BLOCKED":
        raise ValueError("snapshot_preflight_blocked")
    with open_snapshots(root,digests,explicit=True) as (core,private):
        after=gate()
        if after["status"]=="BLOCKED":
            raise ValueError("snapshot_postflight_blocked")
        yield core,private,after
