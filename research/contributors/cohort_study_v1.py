# REMURA Level Confluence v0.13 LAB — 14/11/2026 23:50 CET
"""Synthetic cohort freeze and descriptive aggregation. No real study admission.
Digest detects a changed manifest only if the original digest is held separately
by a trusted caller before outcomes. Not a timestamp, signature or immutable log.
"""
from collections import Counter
from decimal import Decimal,localcontext
from hashlib import sha256
import json
from level_confluence_v1 import compare,KEY_FIELDS,_positive,_key
from reaction_study_v1 import reaction
from ledger_v1 import _time

COHORTS=("A_NEAR","B_DISTANT","C_NO_MANUAL","D_MANUAL_ISOLATED","N_D_RULE")
VERSION="E-R1-LAB-v0.13"
MAX_UNITS=400
def _canonical(data):
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
def _digest(data):
    return sha256(_canonical(data).encode("ascii")).hexdigest()

def freeze(manual,automatic,rules,*,cutoff_utc,synthetic=False):
    if synthetic is not True:raise ValueError("synthetic_only")
    cutoff=_time(cutoff_utc)
    if cutoff.minute%5 or cutoff.second:raise ValueError("cutoff_alignment")
    if type(rules) not in (list,tuple):raise ValueError("rules_sequence")
    result=compare(manual,automatic,rules,asof_utc=cutoff_utc,synthetic=True)
    m={row["id"]:row["data"] for row in manual}
    a={row["id"]:row for row in automatic}
    groups={}
    def add(p,cohort,label):
        key=_key(p)
        price=format(_positive(p["price"]).normalize(),"f")
        # One exact instrument/period/anchor/kind/price/cutoff unit, not one pair.
        uid=_digest([list(key),price,cutoff_utc])
        if uid in groups:
            if groups[uid]["cohort"]!=cohort:raise ValueError("cohort_conflict")
            groups[uid]["labels"].append(label)
        else:
            groups[uid]=dict(unit_id=uid,key=list(key),price=price,cohort=cohort,labels=[label])
    auto_status={"NEAR":"A_NEAR","DISTANT":"B_DISTANT","NO_COMPARABLE_MANUAL":"C_NO_MANUAL",
                 "NOT_COMPARABLE_NO_RULE":"N_D_RULE"}
    for row in result["automatic"]:
        add(a[row["automatic_id"]],auto_status[row["status"]],"auto:"+row["automatic_id"])
    # Isolated means no automatic with identical comparison key, not merely distant.
    # Other manual levels are not a second independent copy of the auto cohort.
    for row in result["manual"]:
        if row["status"]=="NO_COMPARABLE_AUTOMATIC":
            add(m[row["manual_id"]],"D_MANUAL_ISOLATED","manual:"+str(row["manual_id"]))
    units=sorted(groups.values(),key=lambda u:u["unit_id"])
    for u in units:u["labels"].sort()
    manifest=dict(version=VERSION,cutoff_utc=cutoff_utc,synthetic=True,
                  units=units,excluded_manual=result["excluded_manual"],
                  excluded_automatic=result["excluded_automatic"],
                  manual_not_separate=sum(x["status"]!="NO_COMPARABLE_AUTOMATIC" for x in result["manual"]),
                  rules=sorted([dict(instrument=list(r.instrument),tick_size=r.tick_size,
                                     tolerance_ticks=r.tolerance_ticks) for r in rules],
                               key=lambda r:r["instrument"]))
    return {"manifest":manifest,"digest":_digest(manifest)}

def evaluate(manifest,expected_digest,windows,*,evaluated_utc,synthetic=False):
    if synthetic is not True or manifest.get("synthetic") is not True or manifest.get("version")!=VERSION:
        raise ValueError("synthetic_only")
    if _digest(manifest)!=expected_digest:raise ValueError("manifest_changed")
    units=manifest["units"]
    if len(units)>MAX_UNITS:raise ValueError("capacity")
    ids={u["unit_id"] for u in units}
    if len(ids)!=len(units) or type(windows) is not dict or not set(windows)<=ids:
        raise ValueError("unit_ids")
    cutoff=manifest["cutoff_utc"]
    if _time(evaluated_utc)<_time(cutoff):raise ValueError("evaluation_before_cutoff")
    out=[];metrics={k:dict(total=0,touched=0,no_touch=0,n_d=0,closed_across=0,reasons=Counter()) for k in COHORTS}
    shared={}
    for u in units:
        cohort=u["cohort"];s=metrics[cohort];s["total"]+=1
        if cohort=="N_D_RULE":
            rr=dict(status="N_D",reason="COMPARISON_RULE_ABSENT")
        elif u["unit_id"] not in windows:
            rr=dict(status="N_D",reason="WINDOW_ABSENT")
        else:
            w=windows[u["unit_id"]]
            if type(w) is not dict or set(w)!={"instrument","previous_close","bars"}:
                raise ValueError("window_fields")
            if w["instrument"]!=u["key"][:5]:
                rr=dict(status="N_D",reason="FEED_MISMATCH")
            else:
                identity=tuple(w["instrument"])
                raw=_canonical(w)
                if identity in shared and shared[identity]!=raw:raise ValueError("inconsistent_feed_window")
                shared[identity]=raw
                rr=reaction(level=u["price"],cutoff_utc=cutoff,evaluated_utc=evaluated_utc,
                            previous_close=w["previous_close"],bars=w["bars"],synthetic=True)
        if rr["status"]=="TOUCHED":
            s["touched"]+=1
            s["closed_across"]+=int(rr["closed_across"])
        elif rr["status"]=="NO_TOUCH":s["no_touch"]+=1
        else:s["n_d"]+=1;s["reasons"][rr["reason"]]+=1
        out.append(dict(unit_id=u["unit_id"],cohort=cohort,result=rr))
    with localcontext() as ctx:
        ctx.prec=40
        for s in metrics.values():
            valid=s["touched"]+s["no_touch"]
            s["valid"]=valid
            s["contact_rate"]=format(Decimal(s["touched"])/valid,".6f") if valid else None
            s["crossing_rate_given_contact"]=format(Decimal(s["closed_across"])/s["touched"],".6f") if s["touched"] else None
            s["reasons"]=dict(s["reasons"])
    return dict(manifest_digest=expected_digest,metrics=metrics,results=out,synthetic=True,
                scientific_admission=False,operational_signal=False,
                independent_observations_verified=False)
