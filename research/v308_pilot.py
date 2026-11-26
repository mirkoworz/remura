"""V30.8 controlled local pilot: 6 polls at 5-minute cadence, no network.
Runs as unprivileged owner. Only the fixed inline SQLite read runs via sudo.
No automatic restart, no external timestamp, no prospective admission.
"""
import os,sys,json,sqlite3,time,subprocess,shutil,stat,fcntl
from pathlib import Path
BASE=Path.home()/".remura-v296"
LAB=BASE/"v308"
sys.path[:0]=[str(LAB),str(BASE/"v305"),str(BASE/"v301"),str(BASE)]
from v297_bounded_collector import check_private
from v308_queue import capture_tick
from v308_history import initialize,archive,evaluate_pending,totals
import v303_science_candidate as rule_module
READ="""import sqlite3,json,time,sys
try:
    with sqlite3.connect('file:/opt/remura/private/remura-prices.sqlite3?mode=ro',uri=True,timeout=3) as db:
        db.execute('PRAGMA query_only=ON')
        row=db.execute('SELECT symbol,source,broker_symbol,updated_at,payload FROM prices WHERE symbol=?',('EURUSD',)).fetchone()
    data=json.dumps({'price':row,'captured_ms':int(time.time()*1000)},allow_nan=False).encode()
    if len(data)>4000000:raise ValueError('size')
    sys.stdout.buffer.write(data)
except Exception:
    sys.exit(2)
"""
def clock():return int(time.time()*1000)
def tick(db,deadline):
    if clock()+30000>=deadline:raise ValueError("deadline")
    result=subprocess.run(["sudo","-n","/usr/bin/python3","-I","-B","-c",READ],capture_output=True,timeout=10,check=True)
    if len(result.stdout)>4000000:raise ValueError("size")
    item=json.loads(result.stdout);captured=item["captured_ms"]
    if not 0<=clock()-captured<=30000:raise ValueError("capture")
    if item["price"] is None:return {"status":"WAIT_PRICE_MISSING"}
    price=json.dumps(item["price"],separators=(",",":"),allow_nan=False).encode()
    src=BASE/"tv-custody.sqlite3";cot=BASE/"v301"/"v303-public-cot.json"
    for x in (src,cot):check_private(x)
    c=sqlite3.connect(src.as_uri()+"?mode=ro",uri=True,timeout=3)
    try:
        c.execute("PRAGMA query_only=ON")
        rows=c.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
        WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)>?
        AND CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)<=?
        AND CAST(json_extract(metadata,'$.received_at_ms') AS INTEGER)<=?
        ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 289""",(captured-86400000,captured,captured)).fetchall()
    finally:c.close()
    if len(rows)>288:raise ValueError("window")
    records=[{"metadata":json.loads(m),"original_hex":bytes(v).hex(),"sha256":h} for m,v,h in rows]
    raw={"price":price,"footprint":json.dumps(records,separators=(",",":"),allow_nan=False).encode(),"cot":cot.read_bytes()}
    rule=Path(rule_module.__file__).read_bytes()
    if clock()+5000>=deadline:raise ValueError("deadline")
    archive(db,price,captured)
    out=capture_tick(db,raw,captured,clock,rule,enabled=True)
    outcomes=evaluate_pending(db,clock())
    return {**totals(db),"capture_status":out["status"],**outcomes}
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for d in (BASE,LAB):check_private(d,True)
    permit=LAB/"permit.json";check_private(permit)
    p=json.loads(permit.read_text())
    if set(p)!={"start_ms","end_ms","enabled"} or p["enabled"] is not True or any(type(p[k]) is not int for k in ("start_ms","end_ms")) or p["end_ms"]-p["start_ms"]!=1800000 or not p["start_ms"]<=clock()<p["end_ms"]:raise ValueError("permit")
    stop=LAB/"STOP"
    if os.path.lexists(stop):raise ValueError("stop")
    if shutil.disk_usage(LAB).free<512*1024*1024:raise ValueError("disk")
    target=LAB/"science.sqlite3"
    # Exclusive creation also prevents any accidental restart with old data.
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    os.close(fd);check_private(target)
    db=sqlite3.connect(target,timeout=3)
    done=0
    try:
        pages=(128*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
        if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("db_limit")
        db.execute("PRAGMA foreign_keys=ON")
        initialize(db)
        for i in range(6):
            if os.path.lexists(stop) or clock()+30000>=p["end_ms"]:break
            if json.loads(permit.read_text())!=p:raise ValueError("permit_changed")
            if shutil.disk_usage(LAB).free<384*1024*1024:raise ValueError("disk")
            started=time.monotonic()
            print("V308 TICK",i+1,json.dumps(tick(db,p["end_ms"]),sort_keys=True),flush=True)
            done+=1
            if i<5:time.sleep(max(0,min(300-(time.monotonic()-started),(p["end_ms"]-clock()-30000)/1000)))
        print("V308 FINE",done,json.dumps(totals(db),sort_keys=True),flush=True)
    finally:
        db.close()
        if not os.path.lexists(stop):
            with stop.open("x") as f:f.write("CLOSED\n")
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("V308 STOP",type(e).__name__,flush=True);sys.exit(2)
