#!/usr/bin/env python3
# REMURA v0.8.84 LAB — 14/11/2026 20:34 CET
"""Arithmetic envelope only; no account or device requests, no scheduler.
Observed read cap is a stop after each query, not a server hard cap.
"""
from cvd_runtime_private_state_v1 import PERIOD,MAX_BYTES
from cvd_private_runtime_preview_v1 import MAX_PAGES,MAX_OBSERVED_READS
def envelope():
    n=86400000//PERIOD
    return {"schema":"remura.tv.runtime.capacity.envelope.v1","daily_utc_buckets":n,
        "max_inventory_requests":n,"max_select_requests":n*MAX_PAGES,
        "max_d1_api_calls":n*(MAX_PAGES+1),
        "observed_read_threshold_times_buckets":n*MAX_OBSERVED_READS,
        "state_file_max_bytes":MAX_BYTES,"atomic_replace_two_files_bytes":2*MAX_BYTES,
        "excludes_crash_temp_files_and_filesystem_overhead":True,
        "read_threshold_is_hard_cap":False,"includes_other_account_usage":False,
        "counts_actual_billing":False,"scheduler_enabled":False,"oracle_capacity_verified":False}
