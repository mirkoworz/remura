"""V30.7 LAB. One local science tick. Never called automatically by import.
Private input pipe from trusted local collector; no provider requests.
Run only under a separate owner-approved time-limited permit.
"""
import os,sys,time,json,sqlite3,fcntl,stat
from pathlib import Path
BASE=Path.home()/".remura-v296"
sys.path[:0]=[str(BASE/"v305"),str(BASE/"v301"),str(BASE)]
from v297_bounded_collector import check_private
from v307_science_queue import initialize,capture_tick,outcome_tick,summary
import v303_science_candidate as rule_module
def clock():return int(time.time()*1000)
def tick():
    os.umask(0o077)
    check_private(BASE,True)
    permit=BASE/"v307-science-permit.json"
    if not permit.exists() or (BASE/"v307-science-STOP").exists():return {"status":"DISABLED"}
    check_private(permit)
    p=json.loads(permit.read_text())
    if set(p)!={"enabled","start_ms","end_ms"} or p["enabled"] is not True or any(type(p[k]) is not int for k in ("start_ms","end_ms")) or not 0<p["end_ms"]-p["start_ms"]<=86400000 or not p["start_ms"]<=clock()<p["end_ms"]:raise ValueError("permit")
    buf=sys.stdin.buffer.read(4000001)
    if len(buf)>4000000:raise ValueError("size")
    item=json.loads(buf)
    captured=item["captured_ms"]
    if type(captured) is not int or not 0<=clock()-captured<=30000:raise ValueError("capture")
    price=json.dumps(item["price"],separators=(",",":"),allow_nan=False).encode()
    src=BASE/"tv-custody.sqlite3";cot=BASE/"v301"/"v303-public-cot.json"
    for x in (src,cot):check_private(x)
    with sqlite3.connect(src.as_uri()+"?mode=ro",uri=True,timeout=3) as c:
        c.execute("PRAGMA query_only=ON")
        rows=c.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
         WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)>?
         AND CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)<=?
         ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 289""",(captured-86400000,captured)).fetchall()
    if len(rows)>288:raise ValueError("window")
    records=[{"metadata":json.loads(m),"original":v,"sha256":h} for m,v,h in rows]
    raw={"price":price,"footprint":json.dumps(records,separators=(",",":"),allow_nan=False).encode(),"cot":cot.read_bytes()}
    rule=Path(rule_module.__file__).read_bytes()
    fd=os.open(BASE/"v307-science.lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"r+") as lock:
        check_private(BASE/"v307-science.lock")
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not p["start_ms"]<=clock()<p["end_ms"] or (BASE/"v307-science-STOP").exists():raise ValueError("expired")
        target=BASE/"v307-science.sqlite3"
        if not os.path.lexists(target):os.close(os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600))
        check_private(target)
        db=sqlite3.connect(target,timeout=3)
        try:
            initialize(db)
            out=capture_tick(db,raw,captured,clock,rule,enabled=True)
            outcomes=outcome_tick(db,price,captured,enabled=True)
            return {**summary(db),"capture_status":out["status"],**outcomes}
        finally:db.close()
if __name__=="__main__":
    try:print(json.dumps(tick(),sort_keys=True))
    except Exception as e:
        print("V307 SCIENCE STOP",type(e).__name__);sys.exit(2)
