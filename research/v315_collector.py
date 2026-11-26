"""REMURA V31.5 LAB. Continuous TEST custody, explicit activation required.
No calls on import or selftest. Existing quota ledger and shared lock mandatory.
Account telemetry is adaptive, not billing proof. Missing/stale data pauses collection.
"""
import os,sys,sqlite3,time,json,stat,fcntl,shutil,subprocess,unittest
from pathlib import Path
from datetime import datetime,timezone
BASE=Path.home()/".remura-v296";HERE=BASE/"v315"
M5=300000;DAY=86400000;WINDOW=7*DAY
def clock():return time.time_ns()//1000000
def day(t):return datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat()
def private(p,d=False):
    s=p.lstat()
    if s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600) or not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)):raise ValueError("permissions")
def load(p):
    private(p)
    if p.stat().st_size>65536:raise ValueError("size")
    return json.loads(p.read_bytes())
def permit_ok(p,now):
    return (isinstance(p,dict) and set(p)=={"mode","enabled","start_ms"} and p["mode"]=="CONTINUOUS_TEST_COLLECTOR" and p["enabled"] is True and type(p["start_ms"]) is int and 0<p["start_ms"]<=now)
def handoff(state,result,marker,end,now):
    if state in ("active","activating","deactivating","reloading"):return "WAIT_PREDECESSOR"
    if state!="inactive" or result!="success":return "REVIEW_PREDECESSOR"
    if type(end) is not int or end<=0 or now<end:return "WAIT_NATURAL_END"
    if marker!="V303_CLOSED\n":return "REVIEW_PREDECESSOR"
    return "READY"
def readiness(now):
    raw=subprocess.run(["systemctl","show","--no-pager","remura-v303-live.service","-p","ActiveState","-p","Result"],capture_output=True,text=True,check=True,timeout=5).stdout
    fields=dict(line.split("=",1) for line in raw.splitlines() if "=" in line)
    mark=BASE/"v302-live-STOP";marker=None
    if os.path.lexists(mark):private(mark);marker=mark.read_text()
    p=load(BASE/"v302-live-permit.json")
    return handoff(fields["ActiveState"],fields["Result"],marker,p["end_ms"],now),p["first_slot_ms"]
def select_slots(db,first,last,now):
    """Recent unchecked slots first, one older hole and one recent missing repair.
    Historical unchecked slots remain discoverable forever; missing older than
    seven days remain explicitly recorded for manual recovery, never marked present.
    """
    if type(first) is not int or type(last) is not int or first<=0 or first%M5 or last%M5:raise ValueError("slot")
    if last<first:return []
    recent=max(first,last-3*M5)
    present={r[0] for r in db.execute("SELECT close_ms FROM v300_slot_coverage WHERE close_ms BETWEEN ? AND ?",(recent,last))}
    out=[t for t in range(recent,last+1,M5) if t not in present][:2]
    # Index-backed ordered walk; no fixed first-slot expiry. No state mutation before ingest.
    expected=first
    for (t,) in db.execute("SELECT close_ms FROM v300_slot_coverage WHERE close_ms BETWEEN ? AND ? ORDER BY close_ms",(first,last)):
        if t>expected:break
        if t==expected:expected+=M5
    while expected<=last and expected in out:expected+=M5
    if expected<=last and db.execute("SELECT 1 FROM v300_slot_coverage WHERE close_ms=?",(expected,)).fetchone() is None:out.append(expected)
    for (t,) in db.execute("SELECT close_ms FROM v300_slot_coverage WHERE status='MISSING_AT_CHECK' AND close_ms BETWEEN ? AND ? AND checked_ms<=? ORDER BY checked_ms,close_ms LIMIT 4",(max(first,last-WINDOW),last,now-3600000)):
        if t not in out:out.append(t)
        if len(out)>=4:break
    return sorted(out[:4])
def budget_state(db,now):
    if db.execute("SELECT 1 FROM quota_requests WHERE finished=0 LIMIT 1").fetchone():return "REVIEW_UNRESOLVED"
    n,total=db.execute("SELECT COUNT(*),COALESCE(SUM(COALESCE(actual,reserved)),0) FROM quota_requests WHERE day=?",(day(now),)).fetchone()
    return "WAIT_DAILY_BUDGET" if n>=300 or total+10000>1000000 else "READY"
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,HERE,BASE/"v301"):private(p,True)
    permit=HERE/"permit.json";stop=HERE/"STOP"
    if os.path.lexists(stop):return "STOP"
    if not os.path.lexists(permit):return "WAIT_AUTHORIZATION"
    p=load(permit);now=clock()
    if not permit_ok(p,now):return "WAIT_AUTHORIZATION"
    state,first=readiness(now)
    if state!="READY":return state
    if now%DAY>DAY-120000:return "WAIT_UTC_RESET"
    sys.path[:0]=[str(HERE),str(BASE/"v301"),str(BASE)]
    from v313_handoff import quota_gate
    from v302_backfill import inventory
    from v300_slot_custody import ingest_slots,key
    from v300_local_quota import Budget
    key(first)
    if shutil.disk_usage(BASE).free<512*1024*1024:raise ValueError("disk")
    lock=BASE/"v297-tick.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as f:
        private(lock)
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return "WAIT_LOCK"
        def allowed():
            return not os.path.lexists(stop) and load(permit)==p and permit_ok(p,clock()) and day(clock())==day(now)
        if not allowed() or readiness(clock())!=("READY",first):return "WAIT_GATE"
        target=BASE/"tv-custody.sqlite3";qp=BASE/"v302-live-quota.sqlite3"
        for q in (target,qp):private(q)
        db=sqlite3.connect(target,timeout=3);qd=sqlite3.connect(qp,timeout=3)
        try:
            if budget_state(qd,clock())!="READY":return budget_state(qd,clock())
            pages=(256*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("capacity")
            cutoff=clock()-120000;last=(cutoff-120000)//M5*M5
            slots=select_slots(db,first,last,clock())
            if not slots:return "NO_PENDING"
            sample=HERE/"account-quota.json"
            if not os.path.lexists(sample) or not quota_gate(load(sample),clock()):return "WAIT_QUOTA"
            if not allowed():return "WAIT_GATE"
            b=Budget(qd,300,1000000)
            rid=b.reserve(day(now),10000)
            fetch=inventory(load(BASE/"v297-credentials.json"))
            if not allowed() or not quota_gate(load(sample),clock()):raise ValueError("gate_after_reservation")
            rows,n=fetch(slots,cutoff)
            b.finish(rid,n)
            if n>10000:raise ValueError("scan_gate")
            result=ingest_slots(db,slots,cutoff,clock(),rows)
            return "OK new=%d missing=%d rows=%d"%(result["new"],result["missing_at_check"],n)
        finally:db.close();qd.close()
class Tests(unittest.TestCase):
    def test_handoff(self):
        self.assertEqual(handoff("active","success",None,100,200),"WAIT_PREDECESSOR")
        self.assertEqual(handoff("failed","exit-code","V303_CLOSED\n",100,200),"REVIEW_PREDECESSOR")
        self.assertEqual(handoff("inactive","success","V303_CLOSED\n",100,200),"READY")
    def test_old_gap(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE v300_slot_coverage(close_ms INTEGER PRIMARY KEY,status TEXT,checked_ms INTEGER)")
        first=M5;last=first+8*DAY
        db.execute("INSERT INTO v300_slot_coverage VALUES(?,?,?)",(first,"PRESENT",last))
        out=select_slots(db,first,last,last+M5)
        self.assertIn(first+M5,out);self.assertLessEqual(len(out),4)
        db.close()
    def test_budget(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE quota_requests(day TEXT,reserved INTEGER,actual INTEGER,finished INTEGER)")
        now=1800000000000
        self.assertEqual(budget_state(db,now),"READY")
        db.execute("INSERT INTO quota_requests VALUES(?,?,?,?)",(day(now),10000,None,0))
        self.assertEqual(budget_state(db,now),"REVIEW_UNRESOLVED")
        db.close()
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--run"]:
        try:print("V315 COLLECTOR",run(),flush=True)
        except Exception as e:
            if HERE.is_dir() and not os.path.lexists(HERE/"STOP"):
                try:
                    with (HERE/"STOP").open("x") as f:f.write("MANUAL_REVIEW_REQUIRED\n");f.flush();os.fsync(f.fileno())
                except OSError:pass
            print("V315 STOP",type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("LAB: --selftest; --run only after separate authorization")
