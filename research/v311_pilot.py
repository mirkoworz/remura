"""REMURA V31.1 LAB. Bounded 3-hour pilot, local input only."""
import os,sys,time,json,sqlite3,stat,shutil,subprocess
from pathlib import Path
from v311_science import initialize,ingest,observe_tick,evaluate_tick,totals,records,canonical,digest
from v310_multifeed import tv_bar,m15,compare,CT,M15
from v299_source_correlation import ms
BASE=Path.home()/".remura-v296";LAB=BASE/"v311"
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
def private(p,d=False):
    s=p.lstat()
    if not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600):raise ValueError("permissions")
def compare_local(db):
    v=subprocess.run(["sudo","-n","/usr/bin/python3","-I","-B","-c",READ],capture_output=True,timeout=10,check=True)
    if not 0<len(v.stdout)<=4000000:raise ValueError("price_size")
    inp=json.loads(v.stdout);now=clock();capture=inp["captured_ms"]
    symbol,source,broker,updated,payload=inp["price"]
    p=json.loads(payload);u=ms(updated)
    if symbol!="EURUSD" or source!="ctrader" or not broker or p.get("provider")!="ctrader" or p.get("providerSymbol")!=broker or not 0<u<=capture<=now or now-capture>30000:raise ValueError("price_identity_clock")
    a=m15([tv_bar(*r,now) for r in records(db,now,now-86400000)],now)
    ct=[]
    if a:
        for v in p["timeframes"]["M15"]:
            t=ms(v["t"])
            if a[0]["open_ms"]<=t and t+M15<=min(a[-1]["close_ms"],u):
                ct.append({"source":CT,"open_ms":t,"close_ms":t+M15,"available_ms":capture,**{k:v[k] for k in ("o","h","l","c")}})
    return {**compare(a,ct,now),"ctrader_snapshot_age_seconds":(capture-u)//1000}
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,BASE/"v301",LAB):private(p,True)
    for p in (LAB/"permit.json",LAB/"manifest.json",BASE/"tv-custody.sqlite3",BASE/"v301"/"v303-public-cot.json"):private(p)
    permit=json.loads((LAB/"permit.json").read_bytes());start,end=permit["start_ms"],permit["end_ms"]
    if permit!={"start_ms":start,"end_ms":end,"enabled":True} or type(start) is not int or type(end) is not int or end-start!=10800000 or not start<=clock()<end:raise ValueError("permit")
    manifest=(LAB/"manifest.json").read_bytes()
    for n,h in json.loads(manifest).items():
        if "/" in n or not n.endswith(".py"):raise ValueError("manifest")
        private(LAB/n)
        if digest((LAB/n).read_bytes())!=h:raise ValueError("pin")
    cot=(BASE/"v301"/"v303-public-cot.json").read_bytes()
    if not 0<len(cot)<=1000000:raise ValueError("cot_size")
    stop=LAB/"STOP";target=LAB/"science-tv.sqlite3"
    if os.path.lexists(stop) or shutil.disk_usage(LAB).free<512*1024*1024:raise ValueError("stop_disk")
    os.close(os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600))
    db=sqlite3.connect(target,timeout=3);done=0
    try:
        pages=(128*1024*1024)//db.execute("PRAGMA page_size").fetchone()[0]
        if db.execute("PRAGMA max_page_count="+str(pages)).fetchone()[0]!=pages:raise ValueError("db_limit")
        db.execute("PRAGMA foreign_keys=ON")
        initialize(db)
        for i in range(36):
            if os.path.lexists(stop) or clock()+30000>=end:break
            if json.loads((LAB/"permit.json").read_bytes())!=permit or shutil.disk_usage(LAB).free<384*1024*1024:raise ValueError("permit_disk")
            began=time.monotonic();cutoff=clock()
            src=sqlite3.connect((BASE/"tv-custody.sqlite3").as_uri()+"?mode=ro",uri=True,timeout=3)
            try:
                src.execute("PRAGMA query_only=ON")
                rows=src.execute("""SELECT metadata,original,sha256 FROM tv_test_custody WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)>? AND CAST(json_extract(metadata,'$.received_at_ms') AS INTEGER)<=? ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 577""",(cutoff-172800000,cutoff)).fetchall()
            finally:src.close()
            new=ingest(db,[(json.loads(m),raw,h) for m,raw,h in rows],clock())
            status=observe_tick(db,cot,manifest,clock,start)
            out=evaluate_tick(db,clock())
            print("V311 TICK",i+1,json.dumps({**totals(db,clock()),**out,"new_m5":new,"capture_status":status},sort_keys=True),flush=True)
            done+=1
            if i in (0,35):
                try:print("V311 COMPARE",json.dumps(compare_local(db),sort_keys=True),flush=True)
                except Exception as e:print("V311 COMPARE_UNAVAILABLE",type(e).__name__,flush=True)
            if i<35:time.sleep(max(0,min(300-(time.monotonic()-began),(end-clock()-30000)/1000)))
        print("V311 FINE",done,json.dumps(totals(db,clock()),sort_keys=True),flush=True)
    finally:
        db.close()
        if not os.path.lexists(stop):
            with stop.open("x") as f:f.write("CLOSED\n")
if __name__=="__main__":
    try:run()
    except Exception as e:print("V311 STOP",type(e).__name__,flush=True);sys.exit(2)
