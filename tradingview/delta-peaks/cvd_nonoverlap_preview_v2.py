#!/usr/bin/env python3
# REMURA v0.8.79 LAB — 14/11/2026 18:22 CET
"""Frozen, descriptive sensitivity analysis; not execution or OOS validation.
Candidate at confirmation, entry proxy NEXT M5 close only after receipt.
Chronological non-overlap before outcome evaluation; one control per comparison.
No future-aware selection, market-calendar approximation, or invented real costs.
"""
from collections import Counter,defaultdict,deque
from math import isfinite
from statistics import mean
from hashlib import sha256
import json
from cvd_telemetry_preview_v1 import SYMBOL,VERSION,M5
from cvd_outcome_readiness_v1 import HORIZONS,MAX_ROWS
from outcome_audit_v1 import _evaluate,session_id
from volume_quality_v1 import diagnose
from volume_features_v1 import sign

COST_PIPS=(0,1,2) # illustrative round-trip costs, NOT measured spreads
FILTERS=("CVD","ER","RETEST","FP_SIGN")
def compare(valid,*,as_of_ms):
    if type(as_of_ms) is not int or len(valid)>MAX_ROWS:
        raise ValueError("benchmark_scope")
    bars={}; quality={}; candidates=[]; late_candidates=0
    for row,e,v in sorted(valid,key=lambda x:x[0]["bar_close_ms"]):
        t=row["bar_close_ms"]; receipt=row["received_at_ms"]
        if t>as_of_ms or receipt>as_of_ms:
            continue
        if t in bars or row["symbol"]!=SYMBOL or row["version"]!=VERSION or v["event_key"]!=row["event_key"]:
            raise ValueError("benchmark_identity")
        p=e["snapshot"]; c=e["cvd"]; ev=p["events"];fp=p["footprint"]
        bars[t]={"payload":p,"timely":t<=receipt<=t+120000,"conflicted":False}
        quality[t]="REVIEW" not in diagnose(p).values()
        if c["price_bull"]==c["price_bear"]:
            continue
        # Late arrivals cannot reserve a slot retroactively: eligibility known before next M5 close.
        if not bars[t]["timely"]:
            late_candidates+=1
            continue
        side=1 if c["price_bull"] else -1
        selected=c["cvd_bull"] if side==1 else c["cvd_bear"]
        d,f=sign(p["delta_intrabar"]),sign(fp["delta"]) if fp["available"] else None
        tags={"CVD":selected,"ER":ev["er_positive"] or ev["er_negative"],
              "RETEST":any(ev[k] for k in ("retest_day1","retest_day2","retest_day3","retest_previous_day")),
              "FP_SIGN":None if d in (None,0) or f in (None,0) else d==f}
        candidates.append((t,side,selected,tags))
    report={"schema":"remura.tv.cvd.nonoverlap.preview.v2","version":"0.8.79-lab",
            "status":"DESCRIPTIVE_ONLY" if bars else "NO_OBSERVATIONS","horizons":{},
            "primary_minutes":60,"entry_basis":"NEXT_M5_CLOSE_PROXY_AFTER_RECEIPT_NOT_EXECUTION",
            "cost_roundtrip_pips_hypothetical":list(COST_PIPS),"actual_execution_costs_available":False,
            "assignment_method":"FIFO_PRE_OUTCOME_NO_REPLACEMENT","conflict_ledger_attested":False,
            "independent_out_of_sample":False,"edge":"NOT_ESTABLISHED","orders_enabled":False}
    for h in HORIZONS:
        reserved=[]; end_prior=None; counts=Counter({"LATE_CANDIDATE_EXCLUDED":late_candidates})
        # Phase 1: reserve and assign from decision metadata only.
        for t,side,selected,tags in candidates:
            counts["PRICE_CANDIDATES"]+=1
            if end_prior is not None and t<=end_prior:
                counts["OVERLAP_EXCLUDED"]+=1
                continue
            end_prior=t+M5+h*M5
            counts["NONOVERLAP_RETAINED"]+=1
            date,session=session_id(t)
            key=(date,session,side) if h==12 else (session,side)
            reserved.append((t,side,key,selected,tags))
        assignments={}
        for name in FILTERS:
            by=defaultdict(lambda:{True:deque(),False:deque()})
            exposed=Counter({"POSITIVE":0,"NEGATIVE":0,"UNKNOWN_EXCLUDED":0})
            pairs=[]
            for t,side,key,selected,tags in reserved:
                if name!="CVD" and not selected:
                    continue
                flag=tags[name]
                if flag is None:
                    exposed["UNKNOWN_EXCLUDED"]+=1
                    continue
                exposed["POSITIVE" if flag else "NEGATIVE"]+=1
                group=by[key]
                group[flag].append(t)
                if group[True] and group[False]:
                    pairs.append((group[True].popleft(),group[False].popleft()))
            assignments[name]=(exposed,tuple(pairs))
        # Phase 2: outcomes cannot alter the immutable assignment tuples.
        outcomes={}
        for t,side,key,selected,tags in reserved:
            entry=t+M5; end=entry+h*M5
            if end+120000>as_of_ms:
                counts["PENDING_MATURITY"]+=1
                outcomes[t]=(None,"PENDING_MATURITY")
                continue
            if any(t+i*M5 not in bars for i in range(h+2)):
                counts["MISSING_BAR"]+=1
                outcomes[t]=(None,"MISSING_BAR")
                continue
            if any(not quality[t+i*M5] or not bars[t+i*M5]["timely"] for i in range(h+2)):
                counts["QUALITY_OR_CLOCK_BLOCKED"]+=1
                outcomes[t]=(None,"QUALITY_OR_CLOCK_BLOCKED")
                continue
            result,err=_evaluate(bars,entry,h)
            if err:
                counts[err]+=1
                outcomes[t]=(None,err)
                continue
            pips=side*(result["close_h"]-bars[entry]["payload"]["ohlc"]["close"])*10000
            if not isfinite(pips):
                counts["NONFINITE"]+=1
                outcomes[t]=(None,"NONFINITE")
                continue
            counts["COMPLETE"]+=1
            outcomes[t]=(pips,"COMPLETE")
        comparisons={}
        for name,(exposed,assigned) in assignments.items():
            complete=[]; incomplete_reasons=Counter(); pending=0
            for a,b in assigned:
                pa,sa=outcomes[a]; pb,sb=outcomes[b]
                if sa==sb=="COMPLETE":
                    complete.append((pa,pb))
                else:
                    reasons={sa,sb}-{"COMPLETE"}
                    for reason in reasons:
                        incomplete_reasons[reason]+=1
                    if "PENDING_MATURITY" in reasons:
                        pending+=1
            n=len(assigned)
            comparisons[name]={"eligible":dict(exposed),"assigned_pairs":n,
                "complete_pairs":len(complete),"incomplete_pairs":n-len(complete),
                "pending_pairs":pending,"incomplete_reason_pair_counts_nonexclusive":dict(incomplete_reasons),
                "assignment_sha256":sha256(json.dumps(assigned,separators=(",",":")).encode()).hexdigest(),
                "unmatched_positive":exposed["POSITIVE"]-n,
                "unmatched_negative":exposed["NEGATIVE"]-n,
                "mean_difference_pips":round(mean(a-b for a,b in complete),6) if complete else None,
                "hypothetical_net_means_pips":{str(cost):{
                    "positive":round(mean(a-cost for a,b in complete),6) if complete else None,
                    "negative":round(mean(b-cost for a,b in complete),6) if complete else None} for cost in COST_PIPS}}
        report["horizons"][str(h*5)]={"counts":dict(counts),"comparisons":comparisons,
            "matching":"SAME_UTC_DATE_8H_BAND_DIRECTION" if h==12 else "SAME_UTC_8H_BAND_DIRECTION_ACROSS_DATES",
            "selection":"EARLIEST_TIMELY_PRICE_CANDIDATE_RESERVE_FULL_INTERVAL_BEFORE_OUTCOMES",
            "control_reuse_within_comparison":False,"comparisons_not_independent":True}
    return report
