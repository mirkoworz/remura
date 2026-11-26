"""REMURA V30.0 LAB — bounded tick for future persistent scheduler.
No activation, no private input in repository. Owner permit and quota gate
must be wired before use. No retries; an uncertain debit stays charged.
"""
from v300_slot_custody import request_slots,ingest_slots,plan_slots,plan_missing
from v297_bounded_collector import query_rows
from datetime import datetime,timezone

def utc_day(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).date().isoformat()

def run_page(db,slots,cutoff,clock,transport,quota,*,enabled=False):
    """quota.reserve persists before network; finish persists actual usage.
    transport must verify TEST identity and allow exact generated SELECT only.
    An external hard stop on free account remains necessary.
    """
    if enabled is not True:
        raise ValueError("disabled")
    query=request_slots(slots,cutoff)
    t=clock()
    if type(t) is not int or t<cutoff:
        raise ValueError("clock")
    # Reservation includes worst-case policy allowance; actual scan is post-query.
    reservation=quota.reserve(utc_day(t),10000)
    response=transport(query)
    rows,read=query_rows(response)
    quota.finish(reservation,read)
    if read>10000:
        raise ValueError("scan_gate")
    observed=clock()
    if observed<t:
        raise ValueError("clock_regressed")
    return ingest_slots(db,slots,cutoff,observed,rows)

def plan_tick(db,first,last,now,*,reconcile=False):
    cutoff=now-120000
    mature=(cutoff-120000)//300000*300000
    last=min(last,mature)
    if last<first:
        return [],cutoff
    if reconcile:
        return plan_missing(db,first,last,now-3600000),cutoff
    return plan_slots(db,first,last),cutoff
