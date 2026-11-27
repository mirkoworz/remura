"""REMURA V31.8 LAB: live local six-arm preview and gated tick.
No network. Existing V312 database is read only. No historical capture.
Persistent mode requires separate owner approval and local permit.
"""
import os,sys,json,time,sqlite3,stat,fcntl,shutil,hashlib,unittest
from pathlib import Path
from contextlib import closing
BASE=Path.home()/".remura-v296"
HERE=BASE/"v318"
DAY=86400000
def clock():return time.time_ns()//1000000
def private(p,d=False):
    s=p.lstat()
    if s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600) or not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)):raise ValueError("permissions")
def read(p,cap):
    private(p)
    with p.open("rb") as f:b=f.read(cap+1)
    if not 0<len(b)<=cap:raise ValueError("size")
    return b
def permit_ok(p,now):
    return type(p) is dict and set(p)=={"mode","enabled","start_ms"} and p["mode"]=="V318_LOCAL_MULTIFACTOR" and p["enabled"] is True and type(p["start_ms"]) is int and 0<p["start_ms"]<=now
def deps():
    sys.path[:0]=[str(HERE),str(BASE/"v311"),str(BASE/"v312"),str(BASE/"v301"),str(BASE)]
def source():
    p=BASE/"v312/science-tv.sqlite3";private(p)
    db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)
    db.execute("PRAGMA query_only=ON")
    return db
def candidate(src,retail_input,rule_hash):
    import v318_multifactor as m
    from v317_source_join import packet,retail
    from v311_science import records
    from v310_multifeed import tv_bar,m15
    from v294_footprint_cvd import derive
    from v299_source_correlation import cot_context
    from v310_science_adapter import prepare
    if retail_input is None:return "WAIT_RETAIL",None
    cot=read(BASE/"v301/v303-public-cot.json",1000000)
    now=clock()
    r=retail(retail_input,now)
    if r["status"]!="LOCAL_COLLECTION_FRESH_ORIGIN_UNKNOWN":return "WAIT_RETAIL",None
    rows=records(src,now,now-DAY)
    if not rows:return "WAIT_TV",None
    if len(rows)>288:raise ValueError("window")
    if now-rows[-1][0]["bar_close_ms"]>600000:return "WAIT_TV_FRESH",None
    bars=m15([tv_bar(*x,now) for x in rows],now)
    if not bars:return "WAIT_M15",None
    f=derive([{"metadata":a,"original":b,"sha256":c} for a,b,c in rows],now)
    if not f:return "WAIT_FOOTPRINT",None
    if f[-1]["bar_close_ms"]!=rows[-1][0]["bar_close_ms"]:return "WAIT_LATEST_FOOTPRINT",None
    c=cot_context(json.loads(cot),now)
    b=prepare(rows,now,{"status":"DESCRIPTIVE_ONLY",**f[-1]},c)
    if b["status"]!="TV_LOCAL_CANDIDATE_ONLY":return b["status"],None
    a,raw,h=rows[-1]
    ctx=packet(a,raw,h,tv_bar(a,raw,h,now),retail_input,now)
    if m.sides(b["sides"],ctx) is None:return "WAIT_MATCHED_CONTEXT",None
    e={"input_close_ms":bars[-1]["close_ms"],"tv_latest_sha256":h,"cot_sha256":m.sha(cot),
       "rules_sha256":rule_hash,"source_records":[[a["bar_close_ms"],h] for a,raw,h in rows]}
    if clock()-now>4500:return "WAIT_CAPTURE_TIMEOUT",None
    p=m.freeze(b,ctx,e,clock)
    if p is None:return "WAIT_FREEZE_BOUNDARY",None
    # Keep public COT context and exact rule manifest hash in the local packet.
    p["cot_context"]=c
    return "READY_LOCAL_UNWITNESSED",p
def missing_jobs(db,now):
    # Every mature missing outcome is retained. No old gap is silently discarded.
    return db.execute("""WITH h(hours) AS (VALUES(1),(4),(24)), c(cost) AS (VALUES(0),(1),(2))
      SELECT o.id,o.entry_ms,h.hours,c.cost FROM v318_observations o CROSS JOIN h CROSS JOIN c
      LEFT JOIN v318_outcomes x ON x.id=o.id AND x.hours=h.hours AND x.cost=c.cost
      WHERE x.id IS NULL AND o.entry_ms+h.hours*3600000<=?
      AND o.entry_ms+h.hours*3600000>? ORDER BY o.entry_ms,h.hours,c.cost LIMIT 96""",(now,now-2*DAY)).fetchall()
def evaluate_pending(db,src,now,allowed):
    import v318_multifactor as m
    from v311_science import records
    from v310_multifeed import tv_bar,m15
    saved=waiting=0;cache={}
    for identity,entry,h,c in missing_jobs(db,now):
        if not allowed():break
        key=(entry,h)
        if key not in cache:
            end=entry+h*3600000
            rows=[r for r in records(src,now,entry) if r[0]["bar_close_ms"]<=end]
            cache[key]=m15([tv_bar(*r,now) for r in rows],now)
        r=m.save_outcome(db,identity,cache[key],now,h,c)
        if r=="EVALUATED":saved+=1
        elif r=="MISSING_CONTIGUOUS_BARS":waiting+=1
    overdue=db.execute("""WITH h(hours) AS (VALUES(1),(4),(24)), c(cost) AS (VALUES(0),(1),(2))
      SELECT COUNT(*) FROM v318_observations o CROSS JOIN h CROSS JOIN c
      LEFT JOIN v318_outcomes x ON x.id=o.id AND x.hours=h.hours AND x.cost=c.cost
      WHERE x.id IS NULL AND o.entry_ms+h.hours*3600000<=?""",(now-2*DAY,)).fetchone()[0]
    return {"new_outcome_rows":saved,"waiting_batch_rows":waiting,"overdue_unresolved_cost_horizons":overdue}
def main(mode):
    if os.getuid()==0:raise ValueError("not_root")
    os.umask(0o077);private(BASE,True);private(HERE,True);deps()
    import v318_multifactor as m
    # The staged manifest pins the runner, join, and existing scientific dependencies.
    manifest=read(HERE/"manifest.json",65536)
    pins=json.loads(manifest)
    if not isinstance(pins,dict) or not pins:raise ValueError("manifest")
    import importlib.util
    required={"v318_runner","v318_multifactor","v317_source_join","v311_science","v310_multifeed","v294_footprint_cvd","v299_source_correlation","v310_science_adapter","v303_science_candidate","v300_paired_outcomes"}
    if set(pins)!=required:raise ValueError("manifest_scope")
    for name,h in pins.items():
        p=Path(__file__) if name=="v318_runner" else Path(importlib.util.find_spec(name).origin)
        if hashlib.sha256(read(p,1000000)).hexdigest()!=h:raise ValueError("pin")
    if mode=="--tick":
        pp=HERE/"permit.json"
        if not pp.exists() or os.path.lexists(HERE/"STOP"):return {"status":"DISABLED"}
        p=json.loads(read(pp,8192))
        if not permit_ok(p,clock()):return {"status":"DISABLED"}
        def allowed():
            return not os.path.lexists(HERE/"STOP") and pp.exists() and json.loads(read(pp,8192))==p and permit_ok(p,clock())
    data=sys.stdin.buffer.read(8193)
    if len(data)>8192:raise ValueError("input")
    # Empty bridge input still permits outcome evaluation.
    retail_input=json.loads(data) if data.strip() else None
    if mode=="--preview":
        with closing(source()) as src:
            status,packet=candidate(src,retail_input,m.sha(manifest))
        return {"status":status,"matched_arms":len(packet["sides"]) if packet else 0,"prospective_admitted":False,"persistent_write":False}
    with os.fdopen(os.open(HERE/"tick.lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as lock:
        private(HERE/"tick.lock")
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {"status":"WAIT_LOCK"}
        if not allowed():return {"status":"DISABLED"}
        if shutil.disk_usage(HERE).free<512*1024*1024:raise ValueError("disk")
        path=HERE/"multifactor.sqlite3"
        if not os.path.lexists(path):os.close(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600))
        private(path)
        with closing(sqlite3.connect(path,timeout=3)) as db,closing(source()) as src:
            cap=(128*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(cap)).fetchone()[0]!=cap:raise ValueError("capacity")
            m.initialize(db)
            status,packet=candidate(src,retail_input,m.sha(manifest))
            if packet and allowed():status=m.append(db,packet,clock)
            stats=evaluate_pending(db,src,clock(),allowed)
            return {"status":status,**stats,"observations":db.execute("SELECT COUNT(*) FROM v318_observations").fetchone()[0],"outcome_rows":db.execute("SELECT COUNT(*) FROM v318_outcomes").fetchone()[0],"prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_permit(self):
        p={"mode":"V318_LOCAL_MULTIFACTOR","enabled":True,"start_ms":100}
        self.assertTrue(permit_ok(p,100));self.assertFalse(permit_ok(p,99));self.assertFalse(permit_ok(dict(p,enabled=False),100))
    def test_jobs(self):
        import v318_multifactor as m
        db=sqlite3.connect(":memory:");m.initialize(db)
        db.execute("INSERT INTO v318_observations VALUES(?,?,?,?)",("a",DAY,DAY-900000,b"{}"))
        self.assertEqual(len(missing_jobs(db,DAY+3600000)),3)
        self.assertEqual(len(missing_jobs(db,DAY+4*3600000)),6)
        self.assertEqual(len(missing_jobs(db,DAY+DAY)),9)
        self.assertEqual(len(missing_jobs(db,4*DAY)),0)
        db.close()
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:
        deps();unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:] in (["--preview"],["--tick"]):
        try:print("V318 RUNNER",json.dumps(main(sys.argv[1]),sort_keys=True),flush=True)
        except Exception as e:print("V318 RUNNER STOP",type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("LAB --selftest | --preview | separately authorized --tick")
