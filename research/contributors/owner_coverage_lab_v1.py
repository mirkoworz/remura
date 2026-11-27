"""REMURA Contributors v0.46 LAB — 18/11/2026 18:48 CET.
Owner-only aggregate diagnostic, no identities, prices, notes, instrument
labels or row IDs in return. Synthetic in-process use; no HTTP or export.
Counts may still disclose small cohort size; not an anonymization guarantee.
"""
from collections import Counter
from integrated_lab_v1 import IntegratedLab
from level_confluence_v1 import compare,MAX_LEVELS
from ledger_v1 import _time

AUTO=("NEAR","DISTANT","NO_COMPARABLE_MANUAL","NOT_COMPARABLE_NO_RULE")
MANUAL=("NEAR","COMPARED_NO_NEAR","NO_COMPARABLE_AUTOMATIC","NOT_COMPARABLE_NO_RULE")
MAX_AUTO=20

def owner_coverage(lab,token,automatic,rules,*,asof_utc=None,synthetic=False):
    if synthetic is not True or type(lab) is not IntegratedLab:
        raise ValueError("synthetic_integrated_lab_only")
    now=lab._now()
    actor=lab._access.principal(token,now=now)
    if actor.role!="OWNER":raise PermissionError("owner_required")
    current=lab._stamp(now)
    cutoff=current if asof_utc is None else asof_utc
    if _time(cutoff)>_time(current):raise ValueError("future_cutoff")
    if (type(automatic) is not list or len(automatic)>MAX_AUTO
            or type(rules) is not list or len(rules)>MAX_LEVELS):
        raise ValueError("coverage_capacity")
    manual=lab._archive.queue(actor)
    if len(manual)>MAX_LEVELS:raise ValueError("coverage_capacity")
    result=compare(manual,automatic,rules,asof_utc=cutoff,synthetic=True)
    def count(rows,statuses):
        counts=Counter(x["status"] for x in rows)
        if not set(counts)<=set(statuses):raise ValueError("unexpected_status")
        return {k:counts[k] for k in statuses}
    m,a=result["manual"],result["automatic"]
    if (len(m)+result["excluded_manual"]!=len(manual)
            or len(a)+result["excluded_automatic"]!=len(automatic)):
        raise ValueError("nonconserving_coverage")
    return {"schema":"remura.contributors.owner.coverage.lab.v1",
            "version":"0.46-lab","asof_utc":result["asof_utc"],
            "automatic_total":len(automatic),"automatic_admitted":len(a),
            "automatic_excluded":result["excluded_automatic"],
            "automatic_status_counts":count(a,AUTO),
            "manual_total":len(manual),"manual_admitted":len(m),
            "manual_excluded":result["excluded_manual"],
            "manual_status_counts":count(m,MANUAL),
            "synthetic":True,"public_export_authorized":False,
            "anonymization_attested":False,"source_independence_verified":False,
            "scientific_admission":False,"operational_signal":False,
            "orders_enabled":False,"notifications_enabled":False}
