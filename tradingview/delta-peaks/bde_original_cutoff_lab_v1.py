# REMURA v0.8.154 LAB — 18/11/2026, sessione successiva alle 11:13 CET
"""Actual B audit -> D/E coverage at original decision. Synthetic diagnostics only."""
from collections import Counter
from datetime import timedelta
import sqlite3
from fx_m15_decision_preview_v1 import utc,ms,HEX
from closed_de_custody_coverage_lab_v1 import coverage,E_PIN
from level_receipt_custody_lab_v1 import need
B_PIN="daaaa8f6c265d1501a0518940b3e9c9c68e6e3a3"
SCHEMA="remura-track-b-causal-local-cot-price-join-v1"
def summarize(b_db,d_db,*,as_of_utc,days=1,custody,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and type(days) is int and 1<=days<=7)
    need(isinstance(b_db,sqlite3.Connection) and not b_db.in_transaction)
    need(b_db.execute("PRAGMA query_only").fetchone()[0]==1)
    need([tuple(r) for r in b_db.execute("PRAGMA database_list")] in ([(0,"main","")],[(0,"main",""),(1,"temp","")]))
    need(b_db.execute("SELECT 1 FROM temp.sqlite_master LIMIT 1").fetchone() is None)
    keys={"d_witness","d_key","d_latest","e_binding","e_binding_pin","e_manifest","e_candidate","e_source_pin","e_journal_pin","e_old_generation","e_new_generation"}
    need(type(custody) is dict and set(custody)==keys)
    at=utc(as_of_utc)
    from scripts import shark_causal_pair_audit
    pairs=[]
    # Actual pinned B implementation, not arbitrary caller supplied pairs.
    b=shark_causal_pair_audit.audit(b_db,as_of=as_of_utc,days=days,_verified_pairs=pairs)
    need(b.get("schema")==SCHEMA)
    n=b.get("locallyJoinedCausalPairs")
    need((n is None and not pairs) or (type(n) is int and n==len(pairs)<=100))
    counts=Counter(); slots=Counter(); reviews=Counter(); reasons=Counter(); seen=set()
    for symbol,week,closed,observed,digest,side in pairs:
        close,decision=utc(closed),utc(observed)
        need(at-timedelta(days=days)<=decision<=at and close<=decision)
        need(type(side) is int and side in (-1,1) and type(digest) is str and HEX.fullmatch(digest))
        identity=(symbol,week,close,decision);need(identity not in seen);seen.add(identity)
        if symbol!="EURUSD":counts["OTHER_B_MARKET"]+=1;continue
        if close.minute%15 or close.second or close.microsecond or decision-close>timedelta(minutes=3):
            counts["B_DECISION_CLOCK_OUTSIDE_HANDOFF"]+=1;continue
        r=coverage(d_db,**custody,cutoff_ms=ms(decision),audit_ms=ms(at),synthetic=True,ingress_closed=True)
        need(r["schema"]=="remura.de.closed_custody_coverage.synthetic.v1" and r["cutoff_ms"]==ms(decision))
        need(all(r[k] is False for k in ("price_comparison_performed","scientific_admission","operational_signal","historical_population_unbiased","source_equivalence_attested")))
        counts["D_SNAPSHOT_ASOF_UNATTESTED" if r["d_eligible_fixture_snapshots"] else "D_NOT_AVAILABLE_ASOF"]+=1
        slots.update(r["d_latest_slot_counts"]);reviews.update(r["e_asof_review_diagnostics"]);reasons.update(r["blocked_reasons"])
    need(sum(counts.values())==len(pairs))
    return {"schema":"remura.bde.closed_custody_diagnostic.synthetic.v1","b_pin":B_PIN,"e_pin":E_PIN,
        "population":n,"status":"B_PROOFS_UNAVAILABLE" if n is None else "SYNTHETIC_DIAGNOSTICS_ONLY",
        "decision_counts":dict(sorted(counts.items())),"d_slot_counts":dict(sorted(slots.items())),
        "e_quarantine_review_counts":dict(sorted(reviews.items())),"blocked_reason_counts":dict(sorted(reasons.items())),
        "predictive_features_available":False,"price_comparison_performed":False,"scientific_admission":False,
        "source_equivalence_attested":False,"historical_population_unbiased":False,"operational_signal":False,
        "orders_enabled":False,"notifications_enabled":False,"edge":"NOT_ESTABLISHED"}
