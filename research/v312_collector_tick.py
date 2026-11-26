"""REMURA V31.2 LAB — continuation candidate, no activation on import.
Reuse existing D1 TEST custody, lock and quota ledger. Daily owner gate.
No calls unless explicitly permitted and old V303 has ended.
"""
import os,sys,time,sqlite3,fcntl,shutil,subprocess
from v302_backfill import BASE,old,clock,inventory
from v300_slot_custody import M5,key,plan_slots,plan_missing,ingest_slots
from v300_local_quota import Budget
from v300_slot_tick import utc_day
PERIOD=300000
MAX_LOOKBACK=7*86400000
def validate(p,now):
    keys={"enabled","free_confirmed","start_ms","end_ms","first_slot_ms","usage_checked_ms","account_rows_read"}
    if set(p)!=keys or p["enabled"] is not True or p["free_confirmed"] is not True:raise ValueError("permit")
    if any(type(p[k]) is not int for k in keys-{"enabled","free_confirmed"}):raise ValueError("permit_types")
    if not p["start_ms"]<=now or now+90000>=p["end_ms"] or not 0<p["end_ms"]-p["start_ms"]<=86400000:raise ValueError("permit_time")
    if not 0<=now-p["usage_checked_ms"]<=86400000 or utc_day(now)!=utc_day(p["usage_checked_ms"]):raise ValueError("daily_quota_attestation")
    if not 0<=p["account_rows_read"]<1000000:raise ValueError("account_headroom")
    key(p["first_slot_ms"])
    if not 0<=now-p["first_slot_ms"]<=MAX_LOOKBACK:raise ValueError("history_window")
def select_slots(db,first,last,now):
    if last<first:return []
    recent=plan_slots(db,max(first,last-3*M5),last,limit=2)
    older=plan_slots(db,first,last)
    repair=plan_missing(db,first,last,now-3600000)
    result=list(recent)
    # Reserve capacity for both unchecked history and previously missing slots.
    for stream in (older,repair,older,repair):
        for c in stream:
            if c not in result:
                result.append(c);break
        if len(result)==4:break
    return sorted(result)
def old_ended(now,first):
    p=old.read_private(BASE/"v302-live-permit.json")
    if type(p.get("first_slot_ms")) is not int or first>p["first_slot_ms"]:raise ValueError("handoff_first_slot")
    if type(p.get("end_ms")) is not int or now<p["end_ms"] or not (BASE/"v302-live-STOP").is_file():raise ValueError("old_permit")
    state=subprocess.run(["systemctl","show","remura-v303-live.service","-p","ActiveState","--value"],capture_output=True,text=True,timeout=5,check=True).stdout.strip()
    if state not in ("inactive","failed"):raise ValueError("old_service")
def tick():
    os.umask(0o077)
    old.check_private(BASE,True)
    permit=BASE/"v312-collector-permit.json";stop=BASE/"v312-collector-STOP"
    if not permit.exists() or os.path.lexists(stop):return "DISABLED"
    p=old.read_private(permit);now=clock();validate(p,now);old_ended(now,p["first_slot_ms"])
    if shutil.disk_usage(BASE).free<512*1024*1024:raise ValueError("disk")
    lock=BASE/"v297-tick.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as guard:
        old.check_private(lock);fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old_ended(clock(),p["first_slot_ms"])
        target=BASE/"tv-custody.sqlite3";qp=BASE/"v302-live-quota.sqlite3"
        for path in (target,qp):old.check_private(path)
        db=sqlite3.connect(target,timeout=3);qd=sqlite3.connect(qp,timeout=3)
        try:
            # Existing schema and quota ledger required. Never create a fresh quota DB.
            if "v300_slot_coverage" not in {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:raise ValueError("coverage")
            if "quota_requests" not in {x[0] for x in qd.execute("SELECT name FROM sqlite_master WHERE type='table'")}:raise ValueError("quota")
            pages=(256*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("archive_capacity")
            cutoff=clock()-120000;last=(cutoff-120000)//M5*M5
            slots=select_slots(db,p["first_slot_ms"],last,clock())
            if not slots:return "NO_PENDING"
            if old.read_private(permit)!=p or os.path.lexists(stop):raise ValueError("stop")
            validate(p,clock())
            day=utc_day(clock())
            budget=Budget(qd,300,1000000)
            rid=budget.reserve(day,10000)
            fetch=inventory(old.read_private(BASE/"v297-credentials.json"))
            validate(p,clock())
            if old.read_private(permit)!=p or utc_day(clock())!=day or os.path.lexists(stop):raise ValueError("stop_after_get")
            rows,n=fetch(slots,cutoff)
            budget.finish(rid,n)
            if n>10000:raise ValueError("scan_gate")
            result=ingest_slots(db,slots,cutoff,clock(),rows)
            return "OK new=%d missing=%d rows=%d"%(result["new"],result["missing_at_check"],n)
        finally:qd.close();db.close()
if __name__=="__main__":
    try:print("V312 COLLECTOR",tick(),flush=True)
    except Exception as e:print("V312 COLLECTOR STOP",type(e).__name__,flush=True);sys.exit(2)
