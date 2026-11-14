#!/usr/bin/env python3
# REMURA v0.8.75 LAB — 14/11/2026 17:07 CET
"""Validate only bounded aggregate labels, derive diagnostic categories.
No scores, no direction from sentiment, no confidence or signal admission."""
from collections import Counter
TV=("ALIGNED","OPPOSED","UNKNOWN")
CT=(*TV,"MIXED")
RETAIL=("UNKNOWN","LOCAL_ORIGINAL_PIN_VERIFIED")
MATRIX={f"TV_{t}|CT_{c}|RETAIL_{r}":(t,c,r) for t in TV for c in CT for r in RETAIL}
TV_STATES=("DESCRIPTIVE_MATCH","BEFORE_CVD_DEPLOYMENT","NOT_KNOWN_AT_DECISION","NO_EXACT_CLOSE",
           "BLOCKED_CONFLICT","BLOCKED_INVALID","BLOCKED_DIAGNOSTIC_REVIEW","BLOCKED_AMBIGUOUS",
           "CVD_NOT_ELIGIBLE","B_CLOCK_OUTSIDE_TV_HANDOFF")
TV_KEYS={"TV_"+s for s in TV_STATES}
CT_KEYS={"CT_EXACT_"+s for s in CT}
RETAIL_KEYS={"RETAIL_"+s for s in RETAIL}
BOTH="TV_AND_CT_EXACT_LOCAL_SAME_B_DECISION"
ALL="ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION"
ALLOWED=TV_KEYS|CT_KEYS|RETAIL_KEYS|{BOTH,ALL}
def _counts(x,keys,n):
    if type(x) is not dict or any(k not in keys or type(v) is not int or not 0<=v<=n for k,v in x.items()):
        raise ValueError("invalid_auxiliary_aggregate")
    return x
def summarize(aux,*,b_pairs,expected_eurusd):
    if aux is None:
        return None
    if (type(aux) is not dict or aux.get("schema")!="remura.tv.auxiliary.same.decision.preview.v1" or
        aux.get("b_local_pairs")!=b_pairs or aux.get("eurusd_pairs")!=expected_eurusd or
        aux.get("edge")!="NOT_ESTABLISHED" or any(aux.get(k) is not False for k in
        ("orders_enabled","notifications_enabled","scientific_admission","retail_direction_used",
         "missing_is_negative","cross_database_atomic","independent_provenance",
         "retail_actually_used_by_original_signal","earlier_ct_prefix_tier_included"))):
        raise ValueError("invalid_auxiliary_report")
    if b_pairs is None:
        if expected_eurusd is not None or aux.get("status")!="B_PROOFS_UNAVAILABLE":
            raise ValueError("invalid_unknown_b_population")
        n=0
    else:
        n=expected_eurusd
        if type(b_pairs) is not int or type(n) is not int or not 0<=n<=min(b_pairs,20) or aux.get("status")!="LOCAL_ASSOCIATIONS_ONLY":
            raise ValueError("invalid_auxiliary_population")
    counts=_counts(aux.get("counts"),ALLOWED,n)
    matrix=_counts(aux.get("matrix"),MATRIX,n)
    if sum(matrix.values())!=n or any(sum(counts.get(k,0) for k in keys)!=n for keys in (TV_KEYS,CT_KEYS,RETAIL_KEYS)):
        raise ValueError("nonconserving_auxiliary_counts")
    outcomes=Counter(); ct_actual=Counter(); retail_actual=Counter()
    directional=0; all_directional=0; ct_retail=0; tv_ct=0; all_possible=0
    for key,v in matrix.items():
        t,c,r=MATRIX[key]
        ct_actual["CT_EXACT_"+c]+=v; retail_actual["RETAIL_"+r]+=v
        if t!="UNKNOWN": directional+=v
        if c!="UNKNOWN": tv_ct+=v
        if c!="UNKNOWN" and r==RETAIL[1]: all_possible+=v
        if t!="UNKNOWN" and c!="UNKNOWN":
            outcomes[("BOTH_ALIGNED_WITH_COT" if t==c=="ALIGNED" else
                      "BOTH_OPPOSED_TO_COT" if t==c=="OPPOSED" else
                      "MIXED_CT" if c=="MIXED" else "TV_CT_DIRECTION_DISAGREEMENT")]+=v
            ct_retail+=v
            if r==RETAIL[1]: all_directional+=v
        else:
            outcomes["DIRECTION_UNKNOWN_OR_NOT_SELECTED"]+=v
    if any(counts.get(k,0)!=ct_actual[k] for k in CT_KEYS) or any(counts.get(k,0)!=retail_actual[k] for k in RETAIL_KEYS):
        raise ValueError("auxiliary_marginal_mismatch")
    matched=counts.get("TV_DESCRIPTIVE_MATCH",0)
    both=counts.get(BOTH,0); all_=counts.get(ALL,0)
    if not (directional<=matched and ct_retail<=both<=min(matched,tv_ct)
            and all_directional<=all_<=min(both,all_possible)):
        raise ValueError("auxiliary_intersection_mismatch")
    return {"population":expected_eurusd,"status":aux["status"],"tv_matches":matched,
            "ct_exact_known":tv_ct,"retail_pin_verified":counts.get("RETAIL_"+RETAIL[1],0),
            "all_local_proof_types":all_,"both_directional_and_retail_pin":all_directional,
            "direction_categories":dict(sorted(outcomes.items())),
            "source_counts":dict(sorted(counts.items())),"matrix":dict(sorted(matrix.items())),
            "edge":"NOT_ESTABLISHED","orders_enabled":False}
