# REMURA Level Confluence v0.10 LAB — 14/11/2026 23:45 CET
"""Pure diagnostic comparison. Synthetic input only, no network or DB writes.
No price reactions, outcomes, institutional attribution or trading signals.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from archive_v1 import CatalogEntry, _catalog, ID
from ledger_v1 import PERIODS, KINDS, PRICE, _time

MAX_LEVELS=200
KEY_FIELDS=("market","provider","ticker","product","contract","period","anchor_utc","kind")

@dataclass(frozen=True)
class Rule:
    instrument: tuple  # exact market/provider/ticker/product/contract
    tick_size: str
    tolerance_ticks: int

def _positive(value):
    if type(value) is not str or not PRICE.fullmatch(value) or Decimal(value)<=0:
        raise ValueError("price")
    return Decimal(value)

def _id(value):
    if type(value) is not str or not ID.fullmatch(value):
        raise ValueError("identity")
    return value

def _key(p):
    if type(p) is not dict:
        raise ValueError("payload")
    key=tuple(p[k] for k in KEY_FIELDS)
    _catalog(CatalogEntry(*key[:5],source_group="synthetic"))
    if key[5] not in PERIODS or key[7] not in KINDS:
        raise ValueError("classification")
    _time(key[6])
    _positive(p["price"])
    return key

def _rules(rules):
    result={}
    for rule in rules:
        if type(rule) is not Rule or type(rule.instrument) is not tuple or len(rule.instrument)!=5:
            raise ValueError("rule")
        _catalog(CatalogEntry(*rule.instrument,source_group="synthetic"))
        if type(rule.tolerance_ticks) is not int or not 0<=rule.tolerance_ticks<=100000:
            raise ValueError("tolerance")
        if rule.instrument in result:
            raise ValueError("duplicate_rule")
        result[rule.instrument]=(_positive(rule.tick_size),rule.tolerance_ticks)
    return result

def _review_asof(row,cutoff):
    p=row["data"]
    anchor=_time(p["anchor_utc"]); observed=_time(p["observed_utc"])
    received=_time(row["received_utc"])
    if not anchor<=observed<=received:raise ValueError("manual_chronology")
    state="UNREVIEWED";prev=received;asof=state
    for n,h in enumerate(row["history"]):
        at=_time(h["at_utc"]);action=h["action"]
        if at<prev or (n and at==prev) or action not in {
            "UNREVIEWED":("APPROVED","REJECTED"),"APPROVED":("REVOKED",)
        }.get(state,()):
            raise ValueError("review_history")
        state=action;prev=at
        if at<=cutoff:asof=state
    if row["status"]!=state:raise ValueError("review_state")
    return received<=cutoff and asof=="APPROVED"

def compare(manual,automatic,rules,*,asof_utc,synthetic=False):
    if synthetic is not True:raise ValueError("synthetic_only")
    if type(manual) is not list or type(automatic) is not list or max(len(manual),len(automatic))>MAX_LEVELS:
        raise ValueError("capacity")
    cutoff=_time(asof_utc); thresholds=_rules(rules)
    seen=set();eligible=[];auto=[];excluded_manual=0;excluded_auto=0
    for row in manual:
        eid=row["id"]
        if type(eid) is not int or eid<=0 or eid in seen:raise ValueError("manual_id")
        seen.add(eid);p=row["data"];key=_key(p)
        group=_id(p["source_group"]);_id(row["subject"])
        if not _review_asof(row,cutoff):
            excluded_manual+=1;continue
        eligible.append((eid,key,_positive(p["price"]),group))
    seen=set()
    for row in automatic:
        aid=_id(row["id"])
        if aid in seen:raise ValueError("automatic_id")
        seen.add(aid);key=_key(row)
        observed=_time(row["observed_utc"]);available=_time(row["available_utc"])
        if not _time(row["anchor_utc"])<=observed<=available:raise ValueError("automatic_chronology")
        if available>cutoff:
            excluded_auto+=1;continue
        auto.append((aid,key,_positive(row["price"])))
    matches=[];used=set();used_manual=set();summary=[]
    with localcontext() as ctx:
        ctx.prec=40
        for aid,key,price in sorted(auto):
            candidates=[m for m in eligible if m[1]==key]
            rule=thresholds.get(key[:5])
            pairs=[];groups=set()
            for eid,_,mp,group in sorted(candidates):
                used_manual.add(eid)
                distance=abs(mp-price)
                ticks=None if rule is None else distance/rule[0]
                # compare exact price-distance to threshold, not rounded display ticks
                status=("NOT_COMPARABLE_NO_RULE" if rule is None else
                        "NEAR" if distance<=rule[0]*rule[1] else "DISTANT")
                pairs.append(dict(manual_id=eid,distance_price=format(distance,"f"),
                                  distance_ticks=None if ticks is None else format(ticks,".8f"),
                                  status=status))
                if status=="NEAR":
                    used.add(eid);groups.add(group)
            matches.append(dict(automatic_id=aid,
                status="NO_COMPARABLE_MANUAL" if not candidates else
                       "NOT_COMPARABLE_NO_RULE" if rule is None else
                       "NEAR" if groups else "DISTANT",
                pairs=pairs,near_count=sum(p["status"]=="NEAR" for p in pairs),
                declared_source_groups=len(groups)))
        for eid,key,_,_ in sorted(eligible):
            summary.append(dict(manual_id=eid,status="NEAR" if eid in used else
                "COMPARED_NO_NEAR" if eid in used_manual and key[:5] in thresholds else
                "NOT_COMPARABLE_NO_RULE" if eid in used_manual else "NO_COMPARABLE_AUTOMATIC"))
    return dict(asof_utc=asof_utc,automatic=matches,manual=summary,
                excluded_manual=excluded_manual,excluded_automatic=excluded_auto,
                scientific_admission=False,operational_signal=False,
                source_independence_verified=False,synthetic=True)
