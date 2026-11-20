#!/usr/bin/env python3
# REMURA v0.8.67 LAB — 14/11/2026 CET
"""CVD prospective readiness, descriptive only, on already validated CVD envelopes.
No mixing FX/FXCM, no future-fill, no retrospective pivot entry, no orders.
Primary 1h, secondary 4h/24h, consistent with D0.8 research horizons.
The caller must actually provide a contiguous validated export; 72-slot reader
cannot independently produce a 24h outcome. No statistical significance claimed.
"""
from collections import Counter,defaultdict
from statistics import mean,median
from math import isfinite
from outcome_audit_v1 import _evaluate,session_id
from volume_quality_v1 import diagnose
from cvd_telemetry_preview_v1 import SYMBOL,VERSION,M5

HORIZONS=(12,48,288)
MAX_ROWS=10000
def summarize(valid,*,as_of_ms):
    """Triples (row, validated envelope, validation result) from dedicated reader."""
    if type(as_of_ms) is not int or as_of_ms<=1000000000000 or len(valid)>MAX_ROWS:
        raise ValueError("invalid_scope")
    bars={}; envelopes={}; quality={}
    for row,e,v in valid:
        t=row["bar_close_ms"]
        if row["received_at_ms"]>as_of_ms or t>as_of_ms:
            continue
        if t in bars or row["symbol"]!=SYMBOL or row["version"]!=VERSION or v["event_key"]!=row["event_key"]:
            raise ValueError("invalid_cohort")
        p=e["snapshot"]
        bars[t]={"payload":p,"timely":True,"conflicted":False}
        envelopes[t]=e
        quality[t]=not any(x=="REVIEW" for x in diagnose(p).values())
    counts=Counter()
    candidates=[]
    for t,e in sorted(envelopes.items()):
        c=e["cvd"]; p=e["snapshot"]; ev=p["events"]
        # Each direction is a separate candidate. Simultaneous candidates
        # are excluded from directional benchmarking rather than double-counted.
        if c["price_bull"] and c["price_bear"]:
            counts["AMBIGUOUS_DUAL_DIRECTION"]+=1
            continue
        if not(c["price_bull"] or c["price_bear"]):
            continue
        side=1 if c["price_bull"] else -1
        selected=c["cvd_bull"] if side==1 else c["cvd_bear"]
        # ER is effort/result, not an established direction; co-occurrence only.
        tags={"ANY_CVD_CANDIDATE":selected,"ER_PRESENT":ev["er_positive"] or ev["er_negative"],
              "RETEST_PRESENT":any(ev[x] for x in ("retest_day1","retest_day2","retest_day3","retest_previous_day")),
              "FOOTPRINT_PRESENT":p["footprint"]["available"]}
        for k,value in tags.items():
            counts[k]+=int(value)
        counts["PRICE_CANDIDATES"]+=1
        candidates.append((t,side,selected,tags))
    report={"schema":"remura.tv.cvd.outcomes.preview.v1","version":"0.8.67-lab",
            "status":"DESCRIPTIVE_ONLY" if bars else "NO_OBSERVATIONS",
            "as_of_ms":as_of_ms,"bars":len(bars),"candidate_counts":dict(counts),
            "primary_minutes":60,"secondary_minutes":[240,1440],"horizons":{},
            "source":"FX_EURUSD_CVD_ONLY","entry_basis":"CONFIRMATION_CLOSE_NOT_PIVOT_NOT_EXECUTION",
            "scientific_admission":False,"trading_edge_established":False,"orders_enabled":False}
    for h in HORIZONS:
        attempts=defaultdict(Counter); returns=defaultdict(list); controls=defaultdict(list); treated=[]
        for t,side,selected,tags in candidates:
            group="CVD_SELECTED" if selected else "PRICE_ONLY_NOT_SELECTED"
            names=[group]
            if selected:
                names.extend(k for k in ("ER_PRESENT","RETEST_PRESENT","FOOTPRINT_PRESENT") if tags[k])
            err=None; result=None
            if t+h*M5+120000>as_of_ms:
                err="PENDING_MATURITY"
            elif any(not quality.get(t+i*M5,True) for i in range(h+1)):
                err="DIAGNOSTIC_REVIEW"
            else:
                result,err=_evaluate(bars,t,h)
                if result is not None and not all(isfinite(x) for x in result.values()):
                    err="NONFINITE_OUTCOME"
            for name in names:
                attempts[name]["attempted"]+=1
                attempts[name][err or "COMPLETE"]+=1
            if err:
                continue
            value=side*result["return_atr"]
            for name in names:
                returns[name].append(value)
            key=(session_id(t),side)
            if selected:
                treated.append((key,value))
            else:
                controls[key].append(value)
        matched=[(v,mean(controls[k])) for k,v in treated if controls.get(k)]
        report["horizons"][str(h*5)]={
            "counts":{k:dict(v) for k,v in sorted(attempts.items())},
            "median_direction_adjusted_return_atr":{k:round(median(v),6) for k,v in sorted(returns.items())},
            "matched_selected":len(matched),"unmatched_selected":len(treated)-len(matched),
            "matched_selected_mean_atr":round(mean(v for v,b in matched),6) if matched else None,
            "matched_control_mean_atr":round(mean(b for v,b in matched),6) if matched else None,
            "paired_descriptive_difference_atr":round(mean(v-b for v,b in matched),6) if matched else None,
            "matching":"SAME_UTC_DAY_8H_SESSION_AND_DIRECTION; NONSELECTED_PRICE_CANDIDATES",
            "limitations":"OVERLAPPING_HORIZONS_CONTROL_REUSE_COSTS_UNRESOLVED"}
    return report
