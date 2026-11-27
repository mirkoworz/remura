# REMURA v0.8.106 LAB — 16/11/2026 16:34 CET
"""E context evaluated at each original B cutoff. Synthetic only, no feed join."""
from collections import Counter
from fx_m15_decision_preview_v1 import utc, ms

E_PIN="9b4145e7b815dc04986eee5569bf009fc18fe535"
E_SCHEMA="remura.de.squalincome.confluence.synthetic.v1"
COHORT="LABFX_EXPLICIT_SYNTHETIC_V1"

def join(pairs, evidence, *, as_of_ms, origin):
    if origin!="SYNTHETIC" or type(evidence) is not dict or set(evidence) not in (
            {"manual","automatic"},{"manual","envelopes"}):
        raise ValueError("synthetic_level_context_only")
    wire="envelopes" in evidence
    transport="SYNTHETIC_WIRE_V1" if wire else "SYNTHETIC_EXPLICIT_ROWS"
    manual,automatic=evidence["manual"],evidence["envelopes" if wire else "automatic"]
    if type(manual) is not list or type(automatic) is not list or len(manual)>200 or len(automatic)>20:
        raise ValueError("level_context_scope")
    if pairs is None:
        return {"schema":"remura.tv.e.context.synthetic.v1","status":"B_PROOFS_UNAVAILABLE",
            "population":None,"decision_counts":{},"coverage_counts":{},"transport":transport,"e_pin":E_PIN,"cohort":COHORT,
            "source_equivalence_attested":False,"scientific_admission":False,"operational_signal":False}
    if type(pairs) is not list or len(pairs)>100:
        raise ValueError("level_context_decision_capacity")
    from explicit_level_contract_lab_v1 import evaluate
    if wire:
        from explicit_pine_wire_lab_v1 import handoff,CONFIG_ID,WIRE
    counts=Counter()
    coverage=Counter()
    for symbol,week,closed,observed,digest,side in pairs:
        if symbol!="EURUSD":
            counts["OTHER_B_MARKET"]+=1
            continue
        if not ms(utc(closed))<=ms(utc(observed))<=as_of_ms:
            raise ValueError("level_context_decision_clock")
        # E receives B's ORIGINAL observation timestamp, not the dossier audit time.
        data=(handoff(manual,automatic,asof_utc=observed,synthetic=True) if wire
              else evaluate(manual,automatic,asof_utc=observed,synthetic=True))
        if wire and (data.get("wire_schema")!=WIRE or data.get("config_id")!=CONFIG_ID
                or data.get("origin")!="SYNTHETIC" or data.get("config_attested") is not False
                or data.get("receipt_authenticated") is not False):
            raise ValueError("unexpected_wire_context")
        if (data.get("schema")!=E_SCHEMA or data.get("cohort")!=COHORT or data.get("asof_utc")!=observed
            or any(data.get(k) is not False for k in ("scientific_admission","operational_signal",
                "source_equivalence_attested","orders_enabled","notifications_enabled"))):
            raise ValueError("unexpected_e_context")
        status=data["automatic_status_counts"]
        # These are nonexclusive counts of B decisions, never counts of sources.
        for key,condition in (
            ("NEAR_PRESENT",status.get("NEAR",0)>0),
            ("DISTANT_PRESENT",status.get("DISTANT",0)>0),
            ("AUTOMATIC_LATE_PRESENT",data["automatic_late"]>0),
            ("MANUAL_REVIEW_EXCLUDED_PRESENT",data["manual_review_excluded"]>0),
            ("INCOMPATIBLE_METADATA_PRESENT",data["automatic_metadata_blocked"]>0 or data["manual_metadata_blocked"]>0),
            ("NO_AUTOMATIC_ELIGIBLE",not data["automatic_eligible"]),
            ("NO_MANUAL_ELIGIBLE",not data["manual_eligible"])):
            if condition:coverage[key]+=1
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
        "coverage_counts":dict(sorted(coverage.items())),"transport":transport,
        "e_pin":E_PIN,"cohort":COHORT,"source_equivalence_attested":False,
        "scientific_admission":False,"operational_signal":False}
