"""REMURA V30.0 LAB — 26/11/2026 Europe/Rome.
Exact event-key lookup and transactional slot coverage. No network or scheduler
on import. Caller supplies authenticated TEST-only SELECT transport and budget.
Never reuse this coverage ledger as prospective admission.
"""
import json
from v292_d1_oracle_page_contract import COLUMNS, inspect_page, SYMBOL, VERSION
M5=300000
MAX_PAGE=4

def key(close):
    if type(close) is not int or close<=0 or close%M5:
        raise ValueError("slot")
    return "|".join((SYMBOL,"5",str(close),VERSION))

def request_slots(slots,cutoff):
    if (type(slots) is not list or not 1<=len(slots)<=MAX_PAGE
        or type(cutoff) is not int or slots!=sorted(set(slots))):
        raise ValueError("slots")
    keys=[key(c) for c in slots]
    if slots[-1]+120000>cutoff:
        raise ValueError("immature_slot")
    return {"sql":"SELECT "+", ".join(COLUMNS)+" FROM tv_flow_events WHERE event_key IN ("+",".join("?" for _ in keys)+") AND received_at_ms<=? ORDER BY received_at_ms,event_key LIMIT 4",
            "params":keys+[cutoff]}

def initialize_coverage(db):
    if db.in_transaction:
        raise ValueError("transaction")
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"tv_test_custody","tv_test_cursor"}<=names or names-{"tv_test_custody","tv_test_cursor","v300_slot_coverage"}:
        raise ValueError("not_dedicated_custody")
    db.execute("""CREATE TABLE IF NOT EXISTS v300_slot_coverage(
        close_ms INTEGER PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('PRESENT','MISSING_AT_CHECK')),
        checked_ms INTEGER NOT NULL, first_local_seen_ms INTEGER,
        attempts INTEGER NOT NULL CHECK(attempts>0))""")
    db.commit()

def plan_slots(db,first,last,limit=4):
    # Explicit interval, no receipt cursor jump; oldest unchecked slots first.
    key(first);key(last)
    if first>last or last-first>7*86400000 or type(limit) is not int or not 1<=limit<=4:
        raise ValueError("interval")
    existing={r[0] for r in db.execute("SELECT close_ms FROM v300_slot_coverage WHERE close_ms BETWEEN ? AND ?",(first,last))}
    result=[]
    for c in range(first,last+1,M5):
        if c not in existing:
            result.append(c)
            if len(result)==limit:break
    return result

def plan_missing(db,first,last,checked_before):
    key(first);key(last)
    if first>last or last-first>7*86400000 or type(checked_before) is not int:
        raise ValueError("interval")
    return sorted(r[0] for r in db.execute("""SELECT close_ms FROM v300_slot_coverage
      WHERE status='MISSING_AT_CHECK' AND close_ms BETWEEN ? AND ? AND checked_ms<=?
      ORDER BY checked_ms,close_ms LIMIT 4""",(first,last,checked_before)))

def ingest_slots(db,slots,cutoff,observed_ms,rows):
    request_slots(slots,cutoff)
    if type(observed_ms) is not int or observed_ms<cutoff or db.in_transaction:
        raise ValueError("observation_clock")
    if type(rows) is not list or len(rows)>len(slots):
        raise ValueError("page")
    records,_,_=inspect_page(rows,1,cutoff)
    seen={}
    for rec in records:
        m=rec["metadata"]; c=m["bar_close_ms"]
        if c not in slots or c in seen or m["received_at_ms"]<c:
            raise ValueError("receipt_scope")
        seen[c]=rec
    added=0
    db.execute("BEGIN IMMEDIATE")
    try:
        for c in slots:
            old=db.execute("SELECT metadata,original,sha256 FROM tv_test_custody WHERE event_key=?",(key(c),)).fetchone()
            prior=db.execute("SELECT status,checked_ms,first_local_seen_ms,attempts FROM v300_slot_coverage WHERE close_ms=?",(c,)).fetchone()
            if prior and observed_ms<prior[1]:
                raise ValueError("clock_regressed")
            if prior and prior[0]=="PRESENT" and old is None:
                raise ValueError("custody_missing")
            first_seen=prior[2] if prior else None
            if c in seen:
                r=seen[c]
                value=(json.dumps(r["metadata"],sort_keys=True,separators=(",",":")),r["original"],r["sha256"])
                if old is not None:
                    if tuple(old)!=value:
                        raise ValueError("custody_conflict")
                else:
                    db.execute("INSERT INTO tv_test_custody VALUES (?,?,?,?)",(key(c),*value))
                    added+=1
                    first_seen=observed_ms
                status="PRESENT"
            elif old is not None:
                # A missing upstream response must never erase local data.
                raise ValueError("upstream_missing_existing")
            else:
                status="MISSING_AT_CHECK"
            db.execute("""INSERT INTO v300_slot_coverage VALUES (?,?,?,?,?)
                ON CONFLICT(close_ms) DO UPDATE SET status=excluded.status,
                checked_ms=excluded.checked_ms,first_local_seen_ms=excluded.first_local_seen_ms,
                attempts=excluded.attempts""",(c,status,observed_ms,first_seen,1+(prior[3] if prior else 0)))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"new":added,"returned":len(seen),"missing_at_check":len(slots)-len(seen),
            "prospective_admitted":False}
