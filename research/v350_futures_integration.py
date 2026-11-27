"""V35.0 — offline 6E session integration. No network or entitlement assumption.
Observed volume is NOT independent exchange total. Coverage stays unverified.
"""
from v310_cme_contract import validate
from v311_futures_window import summarize
from v312_futures_segments import segments
from v313_futures_coverage import coverage
M5=300000
def session_report(contract,events,session,asof_ms,provenance,*,approved=False,license_ref=None):
    if approved is not True or not isinstance(license_ref,str) or not license_ref.strip():raise PermissionError("license_gate")
    validate(contract)
    if contract.root!="6E":raise ValueError("pilot_root")
    if provenance not in ("EXCHANGE_REPORTED","VENDOR_CLASSIFIED"):raise ValueError("provenance")
    start,end=session["start_ms"],session["end_ms"]
    if any(type(t) is not int for t in (start,end,asof_ms)) or not 0<start<end<=asof_ms or start%M5 or end%M5 or end-start>86400000:raise ValueError("session")
    if len(events)>100000:raise ValueError("capacity")
    ident={"provider":contract.provider,"instrument_id":contract.instrument_id,"expiry":contract.expiration.isoformat()}
    if any(session.get(k)!=v for k,v in ident.items()):raise ValueError("session_identity")
    # Never accept upstream calendar or transport completeness as independently verified.
    session={**session,"calendar_verified":False}
    buckets={};seen={}
    for e in events:
        t=e["exchange_ms"]
        if type(t) is not int or not start<=t<end:raise ValueError("session_trade")
        key=e["trade_id"]
        if key in seen:
            if seen[key]!=e:raise ValueError("conflict")
            continue
        seen[key]=e
        buckets.setdefault(t//M5*M5,[]).append(e)
    windows=[]
    for t,ev in sorted(buckets.items()):
        w=summarize(contract,ev,t,t+M5,asof_ms,approved=approved,license_ref=license_ref)
        # Field adapter for coverage arithmetic only, never verified exchange volume.
        windows.append({**w,"total_trade_volume":w["observed_volume"],"transport_continuity_verified":False})
    return {"status":"OFFLINE_OBSERVED_ONLY","spot_reference":"EURUSD","windows":len(windows),
        "coverage":coverage(windows,session,provenance),"segments":segments(windows,provenance),
        "exchange_total_verified":False,"futures_lead_lag":"NOT_MEASURED",
        "order_book":"UNAVAILABLE","prospective_admitted":False}
