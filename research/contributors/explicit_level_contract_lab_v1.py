# REMURA Contributors v0.35 LAB — 16/11/2026 16:17 CET
"""Separate synthetic level cohort, never relabel real FX telemetry."""
from datetime import timedelta
from level_confluence_v1 import compare,Rule,KEY_FIELDS,_key,_id
from ledger_v1 import _time
SCHEMA="remura.de.explicit-level.synthetic.v1"
METHOD="SYNTHETIC_DELTA_PEAK_V1"
POLICY="UTC_CALENDAR_V1"
INSTRUMENT=("EURUSD","LABFX","EURUSD","SPOT","")
RULE=Rule(INSTRUMENT,"0.00001",10)
BASE=set(KEY_FIELDS)|{"price","observed_utc"}
def need(ok):
    if not ok:raise ValueError("explicit_level_denied")
def anchor(period,observed):
    day=_time(observed).replace(hour=0,minute=0,second=0,microsecond=0)
    if period=="DAY":return day
    if period=="WEEK":return day-timedelta(days=day.weekday())
    month=day.replace(day=1)
    if period=="CURRENT_MONTH":return month
    if period=="PREVIOUS_MONTH":return (month-timedelta(days=1)).replace(day=1)
    raise ValueError("period")
def semantics(row,meta):
    key=_key(row)
    need(type(meta) is dict and set(meta)=={"method","period_policy","known_utc"})
    known=_time(meta["known_utc"])
    need(known>=_time(row["observed_utc"]))
    return (key[:5]==INSTRUMENT and key[-1]=="DELTA_PEAK" and
            meta["method"]==METHOD and meta["period_policy"]==POLICY and
            _time(row["anchor_utc"])==anchor(row["period"],row["observed_utc"])),known
def evaluate(manual,automatic,*,asof_utc,synthetic=False):
    need(synthetic is True and type(manual) is list and type(automatic) is list and len(manual)<=200 and len(automatic)<=20)
    cutoff=_time(asof_utc)
    rows=[];metadata={}
    for item in manual:
        need(type(item) is dict and set(item)=={"entry","metadata"})
        row=item["entry"];rows.append(row);metadata[row["id"]]=item["metadata"]
    pre=compare(rows,[],[],asof_utc=asof_utc,synthetic=True)
    eligible={x["manual_id"] for x in pre["manual"]}
    accepted=[];manual_blocked=0
    for row in rows:
        ok,known=semantics(row["data"],metadata[row["id"]])
        if row["id"] not in eligible:continue
        if not ok or known>cutoff:manual_blocked+=1;continue
        accepted.append(row)
    auto=[];seen=set();blocked=late=0
    for row in automatic:
        need(type(row) is dict and set(row)==BASE|{"schema","id","available_utc","metadata"})
        need(row["schema"]==SCHEMA)
        aid=_id(row["id"]);need(aid not in seen);seen.add(aid)
        available=_time(row["available_utc"])
        ok,known=semantics(row,row["metadata"])
        need(_time(row["observed_utc"])<=available)
        if max(available,known)>cutoff:late+=1;continue
        if not ok:blocked+=1;continue
        auto.append({k:row[k] for k in BASE|{"id","available_utc"}})
    res=compare(accepted,auto,[RULE],asof_utc=asof_utc,synthetic=True)
    counts={}
    for x in res["automatic"]:counts[x["status"]]=counts.get(x["status"],0)+1
    compared=sum(x["status"] in ("NEAR","DISTANT") for x in res["automatic"])
    return {"schema":"remura.de.squalincome.confluence.synthetic.v1","asof_utc":asof_utc,
        "cohort":"LABFX_EXPLICIT_SYNTHETIC_V1","automatic_eligible":len(auto),"manual_eligible":len(accepted),
        "manual_review_excluded":pre["excluded_manual"],"manual_metadata_blocked":manual_blocked,
        "automatic_late":late,"automatic_metadata_blocked":blocked,
        "automatic_compared":compared,"automatic_status_counts":counts,
        "near_pair_count":sum(x["near_count"] for x in res["automatic"]),
        "price_comparison_performed":compared>0,"source_equivalence_attested":False,
        "source_independence_verified":False,"scientific_admission":False,"operational_signal":False,
        "orders_enabled":False,"notifications_enabled":False}
