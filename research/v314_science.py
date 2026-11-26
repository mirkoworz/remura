"""REMURA V31.4 LAB: continuous local science, explicitly authorized only.
No API, provider calls, external witnesses or automatic installation.
Preserve V311 observations in the V312 continuation ledger.
"""
import os,sys,time,sqlite3,json,stat,fcntl,shutil,subprocess,unittest
from pathlib import Path
BASE=Path.home()/".remura-v296"
OLD=BASE/"v311";LAB=BASE/"v312";HERE=BASE/"v314"
def clock():return time.time_ns()//1000000
def private(p,d=False):
    s=p.lstat()
    if not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600):raise ValueError("permissions")
def load(p):
    private(p)
    if p.stat().st_size>65536:raise ValueError("permit_size")
    return json.loads(p.read_bytes())
def gate(state,result,marker,old_end,now,permit,stop):
    if stop:return "STOP"
    if not isinstance(permit,dict) or set(permit)!={"mode","enabled","start_ms"} or permit["mode"]!="CONTINUOUS_LOCAL_SCIENCE" or permit["enabled"] is not True or type(permit["start_ms"]) is not int or not 0<permit["start_ms"]<=now:
        return "WAIT_AUTHORIZATION"
    if state in ("active","activating","deactivating","reloading"):return "WAIT_PREDECESSOR"
    if state!="inactive" or result!="success":return "REVIEW_PREDECESSOR"
    if type(old_end) is not int or old_end<=0 or now<old_end:return "WAIT_NATURAL_END"
    if marker!="CLOSED\n":return "REVIEW_PREDECESSOR"
    return "READY"
def service_state():
    raw=subprocess.run(["systemctl","show","--no-pager","remura-v311-science.service","-p","ActiveState","-p","Result"],capture_output=True,text=True,timeout=5,check=True).stdout
    fields=dict(line.split("=",1) for line in raw.splitlines() if "=" in line)
    return fields["ActiveState"],fields["Result"]
def ready(p):
    s,r=service_state()
    marker=OLD/"STOP"
    mark=None
    if os.path.lexists(marker):
        private(marker);mark=marker.read_text()
    old=load(OLD/"permit.json")
    return gate(s,r,mark,old["end_ms"],clock(),p,os.path.lexists(HERE/"STOP") or os.path.lexists(LAB/"STOP"))
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for path in (BASE,OLD,LAB,HERE,BASE/"v301"):private(path,True)
    permit=HERE/"permit.json"
    if not os.path.lexists(permit):return {"status":"WAIT_AUTHORIZATION"}
    p=load(permit);status=ready(p)
    if status!="READY":return {"status":status}
    # Original and successor share one lock and one continuation database.
    sys.path[:0]=[str(LAB),str(OLD)]
    from v312_science_tick import manifest,copy_completed
    from v311_science import ingest,observe_tick,digest,canonical
    from v312_science_continuation import evaluate_pending,summary
    lock=LAB/"tick.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as guard:
        private(lock)
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {"status":"WAIT_LOCK"}
        if load(permit)!=p or ready(p)!="READY":return {"status":"WAIT_AUTHORIZATION_OR_PREDECESSOR"}
        if os.path.lexists(LAB/"permit.json"):raise ValueError("legacy_permit_present")
        if shutil.disk_usage(LAB).free<512*1024*1024:raise ValueError("disk")
        code=Path(__file__).resolve();private(code)
        pin=load(HERE/"manifest.json")
        if pin!={code.name:digest(code.read_bytes())}:raise ValueError("code_pin")
        prior=manifest()
        man=canonical({"prior":json.loads(prior),"continuous":pin})
        target=LAB/"science-tv.sqlite3"
        if not os.path.lexists(target):copy_completed()
        private(target)
        marker=LAB/"copy-complete.lock";private(marker)
        if marker.read_text()!="VERIFIED\n":raise ValueError("copy_incomplete")
        db=sqlite3.connect(target,timeout=3)
        try:
            pages=(256*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("capacity")
            db.execute("PRAGMA foreign_keys=ON")
            srcpath=BASE/"tv-custody.sqlite3";private(srcpath)
            cotpath=BASE/"v301"/"v303-public-cot.json";private(cotpath)
            cot=cotpath.read_bytes()
            if not 0<len(cot)<=1000000:raise ValueError("cot")
            cutoff=clock()
            src=sqlite3.connect(srcpath.as_uri()+"?mode=ro",uri=True,timeout=3)
            try:
                src.execute("PRAGMA query_only=ON")
                rows=src.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
                    WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)>?
                    AND CAST(json_extract(metadata,'$.received_at_ms') AS INTEGER)<=?
                    ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 577""",(cutoff-172800000,cutoff)).fetchall()
            finally:src.close()
            if len(rows)>576:raise ValueError("window")
            def authorized():
                return load(permit)==p and not os.path.lexists(HERE/"STOP") and not os.path.lexists(LAB/"STOP")
            if not authorized():return {"status":"STOP"}
            new=ingest(db,[(json.loads(m),r,h) for m,r,h in rows],clock())
            if not authorized():return {"status":"STOP","new_m5":new}
            captured=observe_tick(db,cot,man,clock,p["start_ms"])
            if not authorized():return {"status":"STOP","capture_status":captured}
            return {**evaluate_pending(db,clock()),**summary(db),"new_m5":new,"capture_status":captured}
        finally:db.close()
def units():
    return ("[Unit]\nDescription=REMURA V31.4 continuous local science\n"
      "[Service]\nType=oneshot\nUMask=0077\nNoNewPrivileges=yes\n"
      "TimeoutStartSec=120\nExecStart=/usr/bin/python3 -B %h/.remura-v296/v314/v314_science.py --run\n",
      "[Unit]\nDescription=REMURA V31.4 science timer\n"
      "[Timer]\nOnCalendar=*:0/5\nPersistent=true\nAccuracySec=10s\n"
      "Unit=remura-v314-science.service\n[Install]\nWantedBy=timers.target\n")
class Tests(unittest.TestCase):
    def test_no_overlap(self):
        p=dict(mode="CONTINUOUS_LOCAL_SCIENCE",enabled=True,start_ms=1)
        self.assertEqual(gate("active","success",None,100,50,p,False),"WAIT_PREDECESSOR")
        self.assertEqual(gate("inactive","success","CLOSED\n",100,50,p,False),"WAIT_NATURAL_END")
    def test_no_failed_handoff(self):
        p=dict(mode="CONTINUOUS_LOCAL_SCIENCE",enabled=True,start_ms=1)
        self.assertEqual(gate("failed","exit-code","CLOSED\n",100,200,p,False),"REVIEW_PREDECESSOR")
        self.assertEqual(gate("inactive","success",None,100,200,p,False),"REVIEW_PREDECESSOR")
    def test_continuous_explicit(self):
        p=dict(mode="CONTINUOUS_LOCAL_SCIENCE",enabled=True,start_ms=1)
        self.assertEqual(gate("inactive","success","CLOSED\n",100,10**12,p,False),"READY")
        self.assertEqual(gate("inactive","success","CLOSED\n",100,200,p,True),"STOP")
        self.assertEqual(gate("inactive","success","CLOSED\n",100,200,{},False),"WAIT_AUTHORIZATION")
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--units"]:print("\n---\n".join(units()))
    elif sys.argv[1:]==["--run"]:
        try:print("V314 SCIENCE",json.dumps(run(),sort_keys=True),flush=True)
        except Exception as e:
            if HERE.is_dir() and not os.path.lexists(HERE/"STOP"):
                try:
                    with (HERE/"STOP").open("x") as f:f.write("MANUAL_REVIEW_REQUIRED\n");f.flush();os.fsync(f.fileno())
                except OSError:pass
            print("V314 SCIENCE STOP",type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("LAB: --selftest or --units; separate authorization required for --run")
