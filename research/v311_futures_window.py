"""V31.1 LAB — offline futures trade-window statistics. No provider connection.
A window is not proof of complete exchange coverage. No trading signals.
"""
from decimal import Decimal
from v310_cme_contract import normalize_trade
def summarize(contract,events,start_ms,end_ms,asof_ms,*,approved=False,license_ref=None):
    if approved is not True or not isinstance(license_ref,str) or not license_ref.strip():raise PermissionError("disabled")
    if any(type(x) is not int for x in (start_ms,end_ms,asof_ms)) or not 0<start_ms<end_ms<=asof_ms or end_ms-start_ms>3600000:raise ValueError("window")
    if len(events)>100000:raise ValueError("capacity")
    seen={};volume=0
    groups={"EXCHANGE_REPORTED":{"buy":0,"sell":0},"VENDOR_CLASSIFIED":{"buy":0,"sell":0}}
    unknown=0
    for event in events:
        e=normalize_trade(contract,event,approved=approved,license_ref=license_ref)
        if not start_ms<=e["exchange_ms"]<end_ms or e["received_ms"]>asof_ms:raise ValueError("clock_scope")
        key=e["trade_id"]
        if key in seen:
            if seen[key]!=e:raise ValueError("conflicting_trade")
            continue
        seen[key]=e;q=e["quantity"];volume+=q
        if e["aggressor"]=="UNKNOWN":unknown+=q
        else:groups[e["side_provenance"]][e["aggressor"].lower()]+=q
    for g in groups.values():g["delta"]=g["buy"]-g["sell"]
    return {"provider":contract.provider,"instrument_id":contract.instrument_id,"expiry":contract.expiration.isoformat(),
        "start_ms":start_ms,"end_ms":end_ms,"unique_trades":len(seen),"observed_volume":volume,
        "unknown_side_volume":unknown,"by_provenance":groups,"complete_coverage_verified":False,
        "cvd_available":False,"prospective_admitted":False}
