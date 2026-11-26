"""REMURA V31.2 LAB — private continuation entry; NOT installed.
The V31.1 pilot must be closed before copying. No network.
"""
import os,sys,time,sqlite3,shutil,json,fcntl,stat,subprocess
from pathlib import Path
BASE=Path.home()/".remura-v296";OLD=BASE/"v311";LAB=BASE/"v312"
sys.path.insert(0,str(OLD))
from v311_science import ingest,observe_tick,digest
from v312_science_continuation import prepare,evaluate_pending,summary
def clock():return int(time.time()*1000)
def private(p,d=False):
    s=p.lstat()
    if not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600):raise ValueError("permissions")
def closed():
    private(OLD/"STOP")
    state=subprocess.run(["systemctl","show","remura-v311-science.service","-p","ActiveState","--value"],capture_output=True,text=True,timeout=5,check=True).stdout.strip()
    if state!="inactive":raise ValueError("pilot_not_closed")
def manifest():
    p=LAB/"manifest.json";private(p);raw=p.read_bytes()
    doc=json.loads(raw)
    if set(doc)!={"previous","continuation"}:raise ValueError("manifest")
    prior=OLD/"manifest.json";private(prior)
    if doc["previous"]!=json.loads(prior.read_bytes()):raise ValueError("prior_manifest")
    for directory,items in ((OLD,doc["previous"]),(LAB,doc["continuation"])):
        for n,h in items.items():
            if Path(n).name!=n or not n.endswith(".py"):raise ValueError("name")
            p=directory/n;private(p)
            if digest(p.read_bytes())!=h:raise ValueError("pin")
    if set(doc["continuation"])!={"v312_science_continuation.py","v312_science_tick.py"}:raise ValueError("manifest_scope")
    return raw
def copy_completed():
    os.umask(0o077)
    closed()
    source=OLD/"science-tv.sqlite3";private(source)
    target=LAB/"science-tv.sqlite3"
    if shutil.disk_usage(LAB).free<512*1024*1024+2*source.stat().st_size:raise ValueError("disk")
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
    src=sqlite3.connect(source.as_uri()+"?mode=ro",uri=True,timeout=3)
    dest=sqlite3.connect(target,timeout=3)
    try:
        src.execute("PRAGMA query_only=ON")
        src.backup(dest)
        if dest.execute("PRAGMA integrity_check").fetchone()!=("ok",):raise ValueError("integrity")
        for t in ("events","observations","outcomes"):
            if src.execute("SELECT COUNT(*) FROM "+t).fetchone()!=dest.execute("SELECT COUNT(*) FROM "+t).fetchone():raise ValueError("copy_count")
        if dest.execute("PRAGMA foreign_key_check").fetchone() is not None:raise ValueError("foreign_keys")
        prepare(dest)
        return summary(dest)
    finally:src.close();dest.close()
def tick():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,OLD,LAB,BASE/"v301"):private(p,True)
    closed()
    stop=LAB/"STOP";permit=LAB/"permit.json"
    if not permit.exists() or os.path.lexists(stop):return {"status":"DISABLED"}
    private(permit);p=json.loads(permit.read_bytes());now=clock()
    if set(p)!={"start_ms","end_ms","enabled"} or p["enabled"] is not True or any(type(p[k]) is not int for k in ("start_ms","end_ms")) or not p["start_ms"]<=now< p["end_ms"]-30000 or not 0<p["end_ms"]-p["start_ms"]<=86400000:raise ValueError("permit")
    man=manifest()
    lock=LAB/"tick.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as f:
        private(lock);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if shutil.disk_usage(LAB).free<512*1024*1024:raise ValueError("disk")
        target=LAB/"science-tv.sqlite3"
        if not target.exists():copy_completed()
        private(target)
        db=sqlite3.connect(target,timeout=3)
        try:
            pages=(256*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("capacity")
            db.execute("PRAGMA foreign_keys=ON")
            srcpath=BASE/"tv-custody.sqlite3";private(srcpath)
            cotpath=BASE/"v301"/"v303-public-cot.json";private(cotpath)
            cot=cotpath.read_bytes()
            if not 0<len(cot)<=1000000:raise ValueError("cot")
            src=sqlite3.connect(srcpath.as_uri()+"?mode=ro",uri=True,timeout=3)
            try:
                src.execute("PRAGMA query_only=ON")
                # Reconcile the last 48h; keep older evidence and observed times untouched.
                cutoff=clock()
                rows=src.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
                  WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)>?
                  AND CAST(json_extract(metadata,'$.received_at_ms') AS INTEGER)<=?
                  ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 577""",(cutoff-172800000,cutoff)).fetchall()
            finally:src.close()
            if len(rows)>576:raise ValueError("window")
            if clock()+10000>=p["end_ms"] or os.path.lexists(stop) or json.loads(permit.read_bytes())!=p:raise ValueError("stop")
            new=ingest(db,[(json.loads(m),r,h) for m,r,h in rows],clock())
            result=observe_tick(db,cot,man,clock,p["start_ms"])
            return {**evaluate_pending(db,clock()),**summary(db),"new_m5":new,"capture_status":result}
        finally:db.close()
if __name__=="__main__":
    try:print("V312 SCIENCE",json.dumps(tick(),sort_keys=True),flush=True)
    except Exception as e:
        print("V312 SCIENCE STOP",type(e).__name__,flush=True);sys.exit(2)
