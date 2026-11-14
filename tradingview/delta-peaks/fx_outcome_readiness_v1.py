#!/usr/bin/env python3
# REMURA v0.8.54 LAB — 14/11/2026 CET
"""Offline FX outcome readiness. No network, DB writes, prices in output or trades.
Reuse the preregistered v0.8.3 outcome functions only after strict D1 row checks.
Explicit observation cutoff; distinguish not-yet-due horizons from missing data.
No authentic configuration/provenance, costs or out-of-sample proof is implied.
"""
from collections import Counter
from math import isfinite

from volume_features_v1 import analyze_export, decode, M5, MAX_EXPORT_ROWS
from fx_pilot_config_v1 import compare_v1_fields, REFERENCE
from outcome_audit_v1 import HORIZONS, cohorts_for, _evaluate, _retest_label, _contrarian_label, session_id

VERSION = "0.8.54-lab"

def readiness(rows, *, as_of_ms):
    if type(as_of_ms) is not int or as_of_ms <= 1_000_000_000_000:
        raise ValueError("asof_required")
    if not isinstance(rows,list) or len(rows)>MAX_EXPORT_ROWS:
        raise ValueError("row_limit")
    selected=[]
    excluded=Counter()
    for row in rows:
        if not isinstance(row,dict):
            excluded["INVALID_METADATA"]+=1
            continue
        if row.get("symbol")!="FXCM:EURUSD" or row.get("timeframe")!="5":
            excluded["OTHER_COHORT"]+=1
            continue
        received,close=row.get("received_at_ms"),row.get("bar_close_ms")
        if type(received) is not int or type(close) is not int:
            excluded["INVALID_METADATA"]+=1
            continue
        if received>as_of_ms or close>as_of_ms:
            excluded["NOT_KNOWN_AS_OF"]+=1
            continue
        selected.append(row)
    parsed=analyze_export(selected)
    observations=parsed["observations"]
    report={
        "schema":"remura.tv.fx.outcome.readiness.v1","version":VERSION,
        "as_of_ms":as_of_ms,"excluded_counts":dict(excluded),
        "source_counts":parsed["counts"],"selected_rows":len(selected),
        "quarantined_bars":parsed["quarantined_bars"],"valid_bars":len(observations),
        "configuration_status":"ALERT_INPUTS_NOT_ATTESTED",
        "provenance_status":"CALLER_EXPORT_NOT_INDEPENDENTLY_ATTESTED",
        "trading_edge_established":False,"scientific_admission":False,
        "orders_enabled":False,"notifications_enabled":False,"horizons":{},
    }
    if excluded["INVALID_METADATA"] or parsed["counts"].get("INVALID_ROW") or parsed["quarantined_bars"]:
        return dict(report,status="BLOCKED_INVALID_OR_CONFLICT")
    if not observations:
        return dict(report,status="NO_FX_OBSERVATIONS")
    # Use validated, deduplicated actual snapshots, not reconstructed prices.
    bars={}
    for row in selected:
        close=row["bar_close_ms"]
        if close in bars:
            continue
        p,check=decode(row)
        if not compare_v1_fields(p,REFERENCE)["v1_fields_match"]:
            return dict(report,status="BLOCKED_CONFIG_METADATA_MISMATCH")
        bars[close]={"payload":p,"timely":check["timely_for_prospective"],"conflicted":False}
    quality={v["bar_close_ms"]:not any(x=="REVIEW" for x in v["diagnostic_checks"].values())
             for v in observations}
    # A horizon becomes due only after the last expected bar's 120-second receipt allowance.
    def result_at(t,h):
        if t+h*M5+120000>as_of_ms:
            return None,"PENDING_MATURITY"
        if any(not quality.get(t+i*M5,True) for i in range(h+1)):
            return None,"DIAGNOSTIC_REVIEW"
        out,err=_evaluate(bars,t,h)
        if out is not None and not all(isfinite(v) for v in out.values()):
            return None,"NONFINITE_OUTCOME"
        return out,err
    for h in HORIZONS:
        baseline=Counter()
        totals=Counter()
        by_cohort={}
        for t,b in sorted(bars.items()):
            p=b["payload"]
            if p["event_type"]=="HEARTBEAT":
                out,err=result_at(t,h)
                totals["baseline_" + (err or "COMPLETE")]+=1
                if err is None:
                    baseline[session_id(t)]+=1
        for t,b in sorted(bars.items()):
            p=b["payload"]
            cohorts=cohorts_for(p)
            if not cohorts:
                continue
            out,err=result_at(t,h)
            for name,field in [("ANY_EVENT",None),*cohorts]:
                c=by_cohort.setdefault(name,Counter())
                c["attempted"]+=1
                if err:
                    c[err]+=1
                    continue
                c["COMPLETE"]+=1
                c["MATCHED_BASELINE" if baseline[session_id(t)] else "NO_MATCHED_BASELINE"]+=1
                label=(_retest_label(p,out["close_h"],field) if field is not None else
                       _contrarian_label(name,out["return_atr"]))
                if label is not None:
                    c[label]+=1
        report["horizons"][str(h*5)]={"baseline_counts":dict(totals),
                                      "event_counts":{k:dict(v) for k,v in sorted(by_cohort.items())}}
    return dict(report,status="DESCRIPTIVE_READINESS_ONLY")
