# REMURA v0.8.105 LAB — 16/11/2026 16:27 CET
"""E context evaluated at each original B cutoff. Synthetic only, no feed join."""
from collections import Counter
from fx_m15_decision_preview_v1 import utc, ms

E_PIN="4fa2fffe0d66d8c6fa4fe4aa996e8bd839e28ad2"
E_SCHEMA="remura.de.squalincome.confluence.synthetic.v1"
COHORT="LABFX_EXPLICIT_SYNTHETIC_V1"

def join(pairs, evidence, *, as_of_ms, origin):
    if origin!="SYNTHETIC" or type(evidence) is not dict or set(evidence)!={"manual","automatic"}:
        raise ValueError("synthetic_level_context_only")
    manual,automatic=evidence["manual"],evidence["automatic"]
    if type(manual) is not list or type(automatic) is not list or len(manual)>200 or len(automatic)>20:
        raise ValueError("level_context_scope")
    if pairs is None:
        return {"schema":"remura.tv.e.context.synthetic.v1","status":"B_PROOFS_UNAVAILABLE",
            "population":None,"decision_counts":{},"e_pin":E_PIN,"cohort":COHORT,
            "source_equivalence_attested":False,"scientific_admission":False,"operational_signal":False}
    if type(pairs) is not list or len(pairs)>100:
        raise ValueError("level_context_decision_capacity")
    from explicit_level_contract_lab_v1 import evaluate
    counts=Counter()
    for symbol,week,closed,observed,digest,side in pairs:
        if symbol!="EURUSD":
            counts["OTHER_B_MARKET"]+=1
            continue
        if not ms(utc(closed))<=ms(utc(observed))<=as_of_ms:
            raise ValueError("level_context_decision_clock")
        # E receives B's ORIGINAL observation timestamp, not the dossier audit time.
        data=evaluate(manual,automatic,asof_utc=observed,synthetic=True)
        if (data.get("schema")!=E_SCHEMA or data.get("cohort")!=COHORT or data.get("asof_utc")!=observed
            or any(data.get(k) is not False for k in ("scientific_admission","operational_signal",
                "source_equivalence_attested","orders_enabled","notifications_enabled"))):
            raise ValueError("unexpected_e_context")
        status=data["automatic_status_counts"]
        if data["automatic_metadata_blocked"] or data["manual_metadata_blocked"]:
            state="INCOMPATIBLE_METADATA_PRESENT"
        elif data["automatic_compared"]:
            state="CANDIDATE_NEAR_CONTEXT" if status.get("NEAR",0) else "DISTANT_CONTEXT"
        elif data["automatic_late"] and not data["automatic_eligible"]:
            state="AUTOMATIC_LATE"
        elif not data["automatic_eligible"]:
            state="AUTOMATIC_MISSING"
        elif not data["manual_eligible"]:
            state="MANUAL_NOT_AVAILABLE_ASOF"
        else:
            state="NO_COMPARABLE_LEVEL"
        counts[state]+=1
    if sum(counts.values())!=len(pairs):
        raise ValueError("level_context_denominator")
    return {"schema":"remura.tv.e.context.synthetic.v1","status":"SYNTHETIC_CONTEXT_ONLY",
        "population":len(pairs),"decision_counts":dict(sorted(counts.items())),
        "e_pin":E_PIN,"cohort":COHORT,"source_equivalence_attested":False,
        "scientific_admission":False,"operational_signal":False}
