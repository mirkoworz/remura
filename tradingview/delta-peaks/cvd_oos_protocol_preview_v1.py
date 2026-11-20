#!/usr/bin/env python3
# REMURA v0.8.71 LAB — 14/11/2026 16:56 CET
"""Fixed prospective calendar cohorts, not a claim of independent edge.
No cross-fold matching, no interim fold outcome, no moving date endpoints.
Requested windows certify scope only; market schedule and source authenticity unknown.
"""
from datetime import datetime,timezone
from hashlib import sha256
import json
from cvd_nonoverlap_preview_v1 import compare
from cvd_telemetry_preview_v1 import M5
def clock(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*1000
FOLDS=(
    ("DEVELOPMENT","2026-11-16","2026-11-23"),
    ("HOLDOUT_1","2026-11-23","2026-11-30"),
    ("HOLDOUT_2","2026-11-30","2026-12-07"),
)
PROTOCOL={"id":"CVD_D_PROSPECTIVE_20261114_V1","created_utc":"2026-11-14T15:56:00Z",
          "primary":"CVD_vs_price_only_60m","secondary":["240m","1440m","ER","RETEST","FP_SIGN"],
          "folds":FOLDS,"entry":"NEXT_M5_CLOSE_PROXY","benchmark_version":"0.8.70-lab",
          "cost_scenarios_pips":[0,1,2],"data":"FX:EURUSD_0.9.1-cvd-lab",
          "matching":"NO_CROSS_FOLD;_CHRONOLOGICAL_NONOVERLAP",
          "last_mature_close":"LAST_CLOSE_BEFORE_FOLD_END",
          "stopping":"FIXED_CALENDAR_NO_EARLY_OUTCOME",
          "prior_D08_1h_difference_pips":-0.6680}
def digest():
    return sha256(json.dumps(PROTOCOL,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def covered(windows,start,end):
    # End is exclusive, window ends are inclusive M5 timestamps.
    cursor=start
    for a,b in windows:
        if b<cursor:
            continue
        if a>cursor:
            return False
        cursor=b+M5
        if cursor>=end:
            return True
    return False

def evaluate_folds(valid,windows,*,as_of_ms):
    """Already validated triples and ordered validated window boundaries."""
    result={}
    for name,start_s,end_s in FOLDS:
        start,end=clock(start_s),clock(end_s)
        status=("PENDING_FIXED_END" if as_of_ms<end else
                "INCOMPLETE_REQUEST_SCOPE" if not covered(windows,start,end) else
                "DESCRIPTIVE_FOLD_ONLY")
        entry={"status":status,"start_utc":start_s,"end_exclusive_utc":end_s,
               "requested_scope_complete":covered(windows,start,end),"benchmark":None}
        if status=="DESCRIPTIVE_FOLD_ONLY":
            # Do not use a bar at or after the next fold or later receipts.
            # The existing benchmark applies maturity and interval reservation.
            subset=[x for x in valid if start<=x[0]["bar_close_ms"]<end and x[0]["received_at_ms"]<end]
            if not subset:
                entry["status"]="NO_OBSERVATIONS"
            else:
                entry["benchmark"]=compare(subset,as_of_ms=end-1)
        result[name]=entry
    return {"schema":"remura.tv.cvd.prospective.folds.preview.v1","protocol_sha256":digest(),
            "protocol":PROTOCOL,"folds":result,"market_coverage_attested":False,
            "independent_blinding_attested":False,"edge":"NOT_ESTABLISHED",
            "scientific_admission":False,"orders_enabled":False}
