"""REMURA V30.2 LAB — 26/11/2026 Europe/Rome.
Persistent scheduler candidate: one bounded tick, disabled by default.
Requires separate operator authorization and private permit. No install action.
"""
import os,sys,sqlite3,fcntl,shutil,time
from pathlib import Path
from v302_backfill import BASE,old,clock,inventory
from v300_slot_custody import plan_slots,plan_missing,ingest_slots,initialize_coverage,M5,key
from v300_local_quota import Budget
from v300_slot_tick import utc_day

def tick():
    os.umask(0o077)
    old.check_private(BASE,True)
    permit=BASE/"v302-live-permit.json"
    if not permit.exists() or (BASE/"v302-live-STOP").exists():
        print("V302 LIVE DISABLED");return
    p=old.read_private(permit)
    now=clock()
    if (set(p)!={"enabled","free_confirmed","start_ms","end_ms","first_slot_ms"} or
        p["enabled"] is not True or p["free_confirmed"] is not True or
        any(type(p[k]) is not int for k in ("start_ms","end_ms","first_slot_ms")) or
        not p["start_ms"]<=now<p["end_ms"] or p["end_ms"]-p["start_ms"]>86400000):
        raise ValueError("permit")
    first=p["first_slot_ms"];key(first)
    if shutil.disk_usage(BASE).free<100*1024*1024:raise ValueError("disk")
    lock=BASE/"v297-tick.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as guard:
        old.check_private(lock)
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        target=BASE/"tv-custody.sqlite3"
        old.check_private(target)
        qp=BASE/"v302-live-quota.sqlite3"
        if not os.path.lexists(qp):
            os.close(os.open(qp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600))
        old.check_private(qp)
        db=sqlite3.connect(target,timeout=3);qd=sqlite3.connect(qp,timeout=3)
        try:
            # Explicitly separate backfill from permanent collection.
            cutoff=clock()-120000
            last=(cutoff-120000)//M5*M5
            if last<first or last-first>7*86400000:raise ValueError("window")
            initialize_coverage(db)
            recent=max(first,last-3*M5)
            slots=plan_slots(db,recent,last)
            if not slots:
                slots=plan_slots(db,first,last)
            if not slots:
                slots=plan_missing(db,first,last,clock()-3600000)
            if not slots:
                print("V302 NO_PENDING_SLOTS");return
            if clock()+90000>=p["end_ms"] or (BASE/"v302-live-STOP").exists():return
            # Reserve before GET: at most one GET + SELECT per reservation.
            # Pending reservation blocks automatic attempts across UTC dates.
            budget=Budget(qd,300,1000000)
            day=utc_day(clock())
            rid=budget.reserve(day,10000)
            fetch=inventory(old.read_private(BASE/"v297-credentials.json"))
            if clock()+30000>=p["end_ms"] or utc_day(clock())!=day or (BASE/"v302-live-STOP").exists():raise ValueError("stop_gate")
            rows,n=fetch(slots,cutoff)
            if n>10000:raise ValueError("scan_gate")
            out=ingest_slots(db,slots,cutoff,clock(),rows)
            budget.finish(rid,n)
            print("V302 TICK",out["new"],out["missing_at_check"],n,flush=True)
        finally:qd.close();db.close()

if __name__=="__main__":
    try:tick()
    except Exception as e:
        print("V302 LIVE STOP",type(e).__name__,flush=True);sys.exit(2)
