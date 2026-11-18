# REMURA v0.8.154 LAB — 18/11/2026, sessione successiva alle 11:13 CET
"""Closed D/E custody boundary: coverage only, no price/source equivalence."""
import sqlite3
from collections import Counter
from datetime import datetime,timezone,timedelta
from level_receipt_custody_lab_v1 import need,integer,hashobj
from level_receipt_witness_lab_v1 import verify_recovery
from level_transport_receiver_lab_v1 import decode
E_PIN="0612fe18265791d774845f5b83bde2e696495489"
MAX_MS=4102444800000
EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)
def utc_ms(s):
    need(type(s) is str)
    t=datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    need(t.strftime("%Y-%m-%dT%H:%M:%SZ")==s)
    return (t-EPOCH)//timedelta(milliseconds=1)
def coverage(db,*,d_witness,d_key,d_latest,e_binding,e_binding_pin,e_manifest,e_candidate,e_source_pin,e_journal_pin,e_old_generation,e_new_generation,cutoff_ms,audit_ms,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True)
    need(integer(cutoff_ms,1,MAX_MS-1) and integer(audit_ms,cutoff_ms,MAX_MS-1))
    need(type(d_latest) is dict and set(d_latest)=={"latest_anchor","latest_generation","latest_sequence"})
    need(isinstance(db,sqlite3.Connection) and not db.in_transaction)
    need(db.execute("PRAGMA query_only").fetchone()[0]==1)
    need([tuple(r) for r in db.execute("PRAGMA database_list")] in ([(0,"main","")],[(0,"main",""),(1,"temp","")]))
    need(db.execute("SELECT 1 FROM temp.sqlite_master LIMIT 1").fetchone() is None)
    # A private coherent clone prevents mixing verified logical state with later reads.
    clone=sqlite3.connect(":memory:")
    try:
        db.backup(clone);clone.execute("PRAGMA query_only=ON")
        verified=verify_recovery(clone,d_witness,d_key,**d_latest,synthetic=True,ingress_closed=True)
        rows=clone.execute("SELECT close_ms,received_ms,completed_ms,body FROM main.level_finalizations_v2 WHERE outcome='STORED_SYNTHETIC' ORDER BY close_ms LIMIT 13").fetchall()
        need(len(rows)==verified["receipts"]<=12)
    finally:clone.close()
    from closed_source_custody_lab_v1 import verify_bound
    e=verify_bound(e_binding,e_binding_pin,e_manifest,e_candidate,expected_source_pin=e_source_pin,
        latest_journal_pin=e_journal_pin,old_generation=e_old_generation,new_generation=e_new_generation,
        synthetic=True,ingress_closed=True)
    need(e["fixture_source_pin_matched"] is True and e["may_open"] is False and e["scientific_admission"] is False)
    # Audit-time archive may contain later claims. Do not expose their content in decision context.
    eligible=[];late=0;future=0
    for close,received,completed,raw in rows:
        if close>cutoff_ms:future+=1;continue
        if max(received,completed)>cutoff_ms:late+=1;continue
        eligible.append((close,raw))
    slots=Counter();reasons=Counter()
    if eligible:
        row,_,_=decode(eligible[-1][1])
        for level in row["levels"]:
            if level["price"] is None:slots["MISSING"]+=1
            elif not level["boundary_observed"]:slots["BOUNDARY_UNOBSERVED"]+=1
            elif level["period"]!="PREVIOUS_OBSERVED_MONTH" and cutoff_ms>level["period_end_ms"]:slots["PERIOD_EXPIRED"]+=1
            else:slots["PRESENT_UNATTESTED"]+=1
        reasons.update(("PRODUCT_UNATTESTED","CHART_CALENDAR_UNATTESTED","METHOD_EQUIVALENCE_UNATTESTED","RECEIPT_CLOCK_UNATTESTED","HISTORY_INCOMPLETE","SOURCE_INDEPENDENCE_UNATTESTED"))
    else:reasons["NO_D_SNAPSHOT_ASOF"]+=1
    # E candidates are current surviving records in quarantine, NOT an unbiased
    # historical population. Count timing for diagnostics only, never admit them.
    entries=e_candidate["entries"];reviews=e_candidate["historical_reviews"]
    need(type(entries) is list and type(reviews) is list and len(entries)<=200 and len(reviews)<=400)
    ecounts=Counter()
    states={}
    for r in reviews:
        if utc_ms(r["at_utc"])<=cutoff_ms:states[r["entry_id"]]=r["action"]
    for row in entries:
        if max(utc_ms(row[k]) for k in ("anchor_utc","observed_utc","received_utc"))>cutoff_ms:
            ecounts["NOT_AVAILABLE_ASOF"]+=1
        else:
            ecounts["REVIEW_"+states.get(row["entry_id"],"UNREVIEWED")]+=1
    reasons["E_QUARANTINE"]+=1
    return {"schema":"remura.de.closed_custody_coverage.synthetic.v1","origin":"SYNTHETIC","e_pin":E_PIN,
        "cutoff_ms":cutoff_ms,"d_eligible_fixture_snapshots":len(eligible),"d_late_archive_snapshots":late,
        "d_future_archive_snapshots":future,"d_latest_slot_counts":dict(sorted(slots.items())),
        "e_retained_quarantine_only":len(entries),"e_asof_review_diagnostics":dict(sorted(ecounts.items())),
        "blocked_reasons":sorted(reasons),"price_comparison_performed":False,
        "receipt_authenticated":False,"source_equivalence_attested":False,"source_independence_verified":False,
        "historical_population_unbiased":False,"scientific_admission":False,"operational_signal":False,
        "orders_enabled":False,"notifications_enabled":False}
