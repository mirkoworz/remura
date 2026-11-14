#!/usr/bin/env python3
# REMURA v0.8.69 LAB — 14/11/2026 CET
"""Read-only causal research adapter; B original event clock, FX:EURUSD only.
A match is a local temporal association, not price equivalence or proof of venue.
No future data, fallback, execution, score, or private identifiers in aggregates.
"""
from collections import Counter,defaultdict
import json
from cvd_telemetry_preview_v1 import validate,SYMBOL,VERSION,M5
from cvd_archive_preview_v1 import MIN_CLOSE_MS
from cvd_outcome_readiness_v1 import MAX_ROWS
from cvd_radar_preview_v1 import describe
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS
from fx_m15_decision_preview_v1 import utc,ms,HEX

def index_rows(rows):
    if type(rows) is not list or len(rows)>MAX_ROWS:
        raise ValueError("cvd_export_scope")
    groups=defaultdict(list)
    for r in rows:
        if type(r) is not dict or r.get("symbol")!=SYMBOL or r.get("timeframe")!="5":
            raise ValueError("cvd_export_wrong_cohort")
        t,received=r.get("bar_close_ms"),r.get("received_at_ms")
        if type(t) is not int or type(received) is not int or t%M5:
            raise ValueError("cvd_export_bad_clock")
        groups[t].append(r)
    return groups

def at_decision(groups,*,close_ms,decision_ms):
    if (type(close_ms) is not int or type(decision_ms) is not int or
        close_ms%(3*M5) or not close_ms<=decision_ms<=close_ms+180000):
        raise ValueError("cvd_decision_clock")
    if close_ms<MIN_CLOSE_MS:
        return "BEFORE_CVD_DEPLOYMENT",None
    current=[r for r in groups.get(close_ms,[]) if r["received_at_ms"]<=decision_ms]
    if not current:
        return ("NOT_KNOWN_AT_DECISION" if groups.get(close_ms) else "NO_EXACT_CLOSE"),None
    first=current[0]
    if any(r!=first for r in current[1:]):
        return "BLOCKED_CONFLICT",None
    try:
        if (set(first)!=EXPECTED_COLUMNS or first["version"]!=VERSION or
            type(first["is_timely"]) is not int or first["is_timely"]!=0 or
            type(first["raw_json"]) is not str or len(first["raw_json"].encode())>20000):
            raise ValueError("cvd_row_scope")
        e=json.loads(first["raw_json"])
        v=validate(e,received_ms=first["received_at_ms"])
        if (v["event_key"]!=first["event_key"] or v["bar_close_ms"]!=close_ms or
            e["snapshot"]["event_type"]!=first["event_type"]):
            raise ValueError("cvd_row_identity")
        # No negative receive lag, even if a lower-level validator has clock tolerance.
        if not close_ms<=first["received_at_ms"]<=close_ms+120000:
            raise ValueError("cvd_receipt_clock")
        radar=describe(e,received_ms=first["received_at_ms"],as_of_ms=decision_ms)
    except (ValueError,TypeError,KeyError,OverflowError):
        return "BLOCKED_INVALID",None
    if radar["status"]=="BLOCKED_REVIEW":
        return "BLOCKED_DIAGNOSTIC_REVIEW",None
    if radar["status"]=="AMBIGUOUS":
        return "BLOCKED_AMBIGUOUS",None
    if not radar["observed"]["cvd_eligible"]:
        return "CVD_NOT_ELIGIBLE",None
    return "DESCRIPTIVE_MATCH",radar

def join_local_pairs(pairs,rows,*,as_of_ms):
    """pairs must originate from pinned B audit private sink, not from signals API."""
    groups=index_rows(rows)
    if type(as_of_ms) is not int or type(pairs) is not list or len(pairs)>5000:
        raise ValueError("cvd_pair_scope")
    statuses=Counter(); reasons=Counter(); cot_relation=Counter(); seen=set()
    for symbol,week,closed_s,observed_s,digest,side in pairs:
        if symbol!="EURUSD":
            statuses["OTHER_B_MARKET"]+=1
            continue
        close,obs=ms(utc(closed_s)),ms(utc(observed_s))
        key=(symbol,week,close,obs)
        if (key in seen or type(side) is not int or side not in (-1,1) or
            type(digest) is not str or not HEX.fullmatch(digest) or obs>as_of_ms or close>obs):
            raise ValueError("cvd_b_pair_invalid")
        seen.add(key)
        if close%(3*M5) or obs-close>180000:
            statuses["B_DECISION_CLOCK_OUTSIDE_HANDOFF"]+=1
            continue
        state,r=at_decision(groups,close_ms=close,decision_ms=obs)
        statuses[state]+=1
        if r is None:
            continue
        o=r["observed"]
        reasons["ER_"+o["er"]]+=1
        reasons["DELTA_FP_"+o["delta_footprint_relation"]]+=1
        reasons["CVD_"+("SELECTED" if r["cvd_selected"] is True else
                      "PRICE_ONLY" if r["cvd_selected"] is False else "NO_PRICE_CANDIDATE")]+=1
        if any(l["range_touch"] is True for l in o["levels"]):
            reasons["PRIOR_LEVEL_TOUCH"]+=1
        if any(l["sender_retest"] is True and l["range_touch"] is True for l in o["levels"]):
            reasons["SENDER_RETEST_ON_PRIOR_LEVEL"]+=1
        # COT side versus CVD-selected candidate only, not ER or volume magnitude.
        if r["cvd_selected"] is True:
            cot_relation["ALIGNED" if (r["candidate"]=="BULL")== (side==1) else "OPPOSED"]+=1
        else:
            cot_relation["NO_SELECTED_DIRECTION"]+=1
    if sum(statuses.values())!=len(pairs):
        raise ValueError("cvd_pair_denominator")
    return {"schema":"remura.tv.cvd.b.asof.preview.v1",
            "status":"DESCRIPTIVE_MATCHES_PRESENT" if statuses["DESCRIPTIVE_MATCH"] else "NO_DESCRIPTIVE_MATCH",
            "symbol":SYMBOL,"denominator":"B_LOCAL_COT_PRICE_PAIRS",
            "pair_counts":dict(sorted(statuses.items())),
            "observed_reason_counts":dict(sorted(reasons.items())),
            "cot_vs_cvd_selected":dict(sorted(cot_relation.items())),
            "source_mapping":"B_EURUSD_M15_TO_FX_EURUSD_M5_EXACT_CLOSE",
            "cross_feed_price_equivalence_assumed":False,"provenance_attested":False,
            "ct_cvd_same_decision_proven":False,"sentiment_same_decision_proven":False,
            "conflict_ledger_available":False,"scientific_admission":False,
            "verdict":"NO_OPERATIONAL_SIGNAL","orders_enabled":False,"notifications_enabled":False}
