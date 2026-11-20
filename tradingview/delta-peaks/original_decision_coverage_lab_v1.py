"""REMURA v0.8.172 LAB — 18/11/2026, sessione successiva alle 17:48 CET.
Synthetic original-decision coverage matrix for separate FXCM and FX cohorts.
No price equivalence, directional relation, outcome, network, or private export.
Use only frozen B-pair fixtures; never pass an unverified live population.
"""
from collections import Counter,defaultdict
from cvd_squalincome_asof_preview_v1 import index_rows,at_decision
from fx_asof_handoff_v1 import handoff
from fx_m15_decision_preview_v1 import utc,ms,HEX
from fx_pilot_config_v1 import REFERENCE,compare_v1_fields
from volume_features_v1 import decode,MAX_EXPORT_ROWS

FXCM="FXCM:EURUSD"
M5=300000

def coverage(pairs,legacy_rows,cvd_rows,*,as_of_ms,synthetic=False):
    if (synthetic is not True or type(as_of_ms) is not int or type(pairs) is not list
        or len(pairs)>5000 or type(legacy_rows) is not list or len(legacy_rows)>MAX_EXPORT_ROWS):
        raise ValueError("COVERAGE_LAB_SCOPE")
    indexed=index_rows(cvd_rows)
    # Audit cutoff limits retrospective diagnosis; later arrivals never enter it.
    groups={t:[row for row in rows if row["received_at_ms"]<=as_of_ms]
            for t,rows in indexed.items()}
    old=defaultdict(list)
    for row in legacy_rows:
        if (type(row) is not dict or row.get("symbol")!=FXCM or row.get("timeframe")!="5"
            or type(row.get("bar_close_ms")) is not int or type(row.get("received_at_ms")) is not int
            or row["bar_close_ms"]%M5):
            raise ValueError("LEGACY_COHORT_SCOPE")
        if row["received_at_ms"]<=as_of_ms:
            old[row["bar_close_ms"]].append(row)
    counts=Counter()
    legacy_reasons=Counter()
    cvd_reasons=Counter()
    seen=set()
    eligible=0
    for symbol,week,closed,observed,digest,side in pairs:
        t,d=ms(utc(closed)),ms(utc(observed))
        identity=(symbol,week,t,d)
        if (identity in seen or not t<=d<=as_of_ms or type(digest) is not str
            or not HEX.fullmatch(digest) or type(side) is not int or side not in (-1,1)):
            raise ValueError("B_PAIR_SCOPE")
        seen.add(identity)
        if symbol!="EURUSD":
            counts["OTHER_B_MARKET"]+=1
            continue
        if t%(3*M5) or d-t>180000:
            counts["B_CLOCK_OUTSIDE_HANDOFF"]+=1
            continue
        eligible+=1
        h=handoff(old.get(t,[]),decision_ms=d,bar_close_ms=t)
        candidate=h["candidate"]
        fxcm="UNKNOWN"
        legacy_reason=h["status"]
        if legacy_reason=="NO_CURRENT_ASOF_OBSERVATION":
            legacy_reason=("NOT_KNOWN_AT_DECISION" if old.get(t) else "NO_EXACT_CLOSE")
        if candidate is not None:
            matches=[row for row in old[t] if row["received_at_ms"]==candidate["received_at_ms"]]
            if matches and all(compare_v1_fields(decode(row)[0],REFERENCE)["v1_fields_match"] for row in matches):
                fxcm="PARTIAL" if h["status"]=="PARTIAL_DESCRIPTIVE_ONLY" else "PRESENT"
            else:
                legacy_reason="BLOCKED_CONFIG_METADATA_MISMATCH"
        state,_=at_decision(groups,close_ms=t,decision_ms=d)
        fx="PRESENT" if state=="DESCRIPTIVE_MATCH" else "UNKNOWN"
        legacy_reasons[legacy_reason]+=1
        cvd_reasons[state]+=1
        counts["FXCM_"+fxcm+"|FX_"+fx]+=1
    if (sum(counts.values())!=len(pairs) or sum(legacy_reasons.values())!=eligible
        or sum(cvd_reasons.values())!=eligible):
        raise ValueError("NONCONSERVING_POPULATION")
    return {"schema":"remura.tv.original.decision.coverage.lab.v1",
            "population":len(pairs),"eligible_clock_population":eligible,
            "counts":dict(sorted(counts.items())),
            "legacy_reason_counts":dict(sorted(legacy_reasons.items())),
            "cvd_reason_counts":dict(sorted(cvd_reasons.items())),
            "reason_denominator":"ELIGIBLE_ORIGINAL_CLOCK_POPULATION",
            "late_diagnostic_scope":"RECEIPTS_UP_TO_AUDIT_CUTOFF_ONLY",
            "both_descriptive_present":counts["FXCM_PRESENT|FX_PRESENT"],
            "source_price_equivalence":False,"source_independence_verified":False,
            "outcomes_evaluated":False,"scientific_admission":False,
            "orders_enabled":False,"notifications_enabled":False}
