"""REMURA V33.1: descriptive radar ledger and read-only historical coverage.
No network, no trading, no timer installation. Historical coverage is not prospective.
"""
import os,sys,json,time,sqlite3,hashlib,stat,fcntl,unittest
from pathlib import Path
from contextlib import closing
from decimal import Decimal
from collections import Counter
BASE=Path.home()/".remura-v296"
HERE=BASE/"v318"
M5=300000
CAP=32*1024*1024
FLAGS=("absorption_candidate","volume_anomaly_2x","price_delta_divergence_30m")
def clock():return time.time_ns()//1000000
def deps():
    sys.path[:0]=[str(HERE),str(BASE/"v311"),str(BASE/"v312"),str(BASE/"v301"),str(BASE)]
def canonical(p):return json.dumps(p,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def private(p,mode,kind):
    s=p.lstat()
    if s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=mode or not kind(s.st_mode):raise ValueError("permissions")
def read_rows(now):
    from v311_science import records
    from v310_multifeed import tv_bar
    from v294_footprint_cvd import derive
    p=BASE/"v312/science-tv.sqlite3"
    private(p,0o600,stat.S_ISREG)
    with closing(sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        src=records(db,now,now-86400000)
    if len(src)>288:raise ValueError("window")
    d=derive([{"metadata":a,"original":b,"sha256":h} for a,b,h in src],now)
    by={x["bar_close_ms"]:x for x in d}
    rows=[]
    for a,b,h in src:
        c=a["bar_close_ms"]
        if c not in by:continue
        bar=tv_bar(a,b,h,now)
        f=json.loads(b,parse_float=Decimal)["snapshot"]["footprint"]
        rows.append({**bar,"delta":Decimal(f["delta"]),"volume":Decimal(f["buy"])+Decimal(f["sell"]),
            "segment_bars":by[c]["segment_bars"],"digest":h})
    return rows,src[-1][0]["bar_close_ms"] if src else None
def history(rows,radar,absorption):
    counts={k:Counter() for k in FLAGS}
    for i,r in enumerate(rows):
        # Reconstruct from inputs available now; do not claim earlier availability.
        window=rows[max(0,i-24):i+1]
        p=radar(window,r["close_ms"],absorption)
        for k in FLAGS:
            v=p.get(k)
            counts[k]["true" if v is True else "false" if v is False else "unavailable"]+=1
    return {"status":"HISTORICAL_DESCRIPTIVE_ONLY","rows":len(rows),
        "counts":{k:{x:counts[k][x] for x in ("true","false","unavailable")} for k in FLAGS},
        "prospective_admitted":False,"persistent_write":False}
def initialize(db):
    tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables and tables!={"radar_observations"}:raise ValueError("ledger_scope")
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS radar_observations(close_ms INTEGER PRIMARY KEY, capture_ms INTEGER NOT NULL, digest TEXT UNIQUE NOT NULL, packet BLOB NOT NULL)")
        for op in ("UPDATE","DELETE"):
            db.execute("CREATE TRIGGER IF NOT EXISTS radar_no_"+op.lower()+" BEFORE "+op+" ON radar_observations BEGIN SELECT RAISE(ABORT,'append_only'); END")
def capture(rows,latest,now,radar,absorption,rule):
    if not rows or rows[-1]["close_ms"]!=latest:return None
    if any(r["available_ms"]>now for r in rows):raise ValueError("lookahead")
    result=radar(rows,now,absorption)
    if result["status"]!="DESCRIPTIVE_ONLY":return None
    last=rows[-1]
    window=rows[-min(last["segment_bars"],25):]
    return {"schema":"remura.v331.radar.local.v1","close_ms":latest,"capture_ms":now,
        "rules_sha256":rule,"sources":[[r["close_ms"],r["digest"]] for r in window],
        "features":result,"prospective_admitted":False}
def save(db,p,now):
    if p["prospective_admitted"] is not False or not 0<p["close_ms"]<=p["capture_ms"]<=now or now-p["close_ms"]>600000 or now-p["capture_ms"]>5000:raise ValueError("capture_clock")
    raw=canonical(p)
    with db:
        if db.execute("SELECT 1 FROM radar_observations WHERE close_ms=?",(p["close_ms"],)).fetchone():return "ALREADY_RECORDED"
        db.execute("INSERT INTO radar_observations VALUES(?,?,?,?)",(p["close_ms"],p["capture_ms"],sha(raw),raw))
    return "LOCAL_RADAR_RECORDED"
def run(mode):
    if os.getuid()==0:raise ValueError("not_root")
    os.umask(0o077)
    private(BASE,0o700,stat.S_ISDIR);private(HERE,0o700,stat.S_ISDIR)
    from v330_radar import radar
    from v313_intelligence import absorption
    import importlib.util
    pins={}
    for n in ("v331_radar_ledger","v330_radar","v313_intelligence","v311_science","v310_multifeed","v294_footprint_cvd"):
        p=Path(__file__) if n=="v331_radar_ledger" else Path(importlib.util.find_spec(n).origin)
        private(p,0o600,stat.S_ISREG)
        raw=p.read_bytes()
        if not 0<len(raw)<=1000000:raise ValueError("code_size")
        pins[n]=sha(raw)
    now=clock()
    if mode=="--history":
        rows,latest=read_rows(now)
        return history(rows,radar,absorption)
    permit=HERE/"radar-v331-permit.json"
    stop=HERE/"RADAR-STOP"
    if not permit.exists() or os.path.lexists(stop):return {"status":"DISABLED"}
    private(permit,0o600,stat.S_ISREG)
    raw=permit.read_bytes()
    if len(raw)>8192:raise ValueError("permit_size")
    auth=json.loads(raw)
    if set(auth)!={"enabled","start_ms","pins"} or auth["enabled"] is not True or type(auth["start_ms"]) is not int or not 0<auth["start_ms"]<=now or auth["pins"]!=pins:return {"status":"DISABLED"}
    lock=HERE/"radar-v331.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as guard:
        private(lock,0o600,stat.S_ISREG)
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {"status":"WAIT_LOCK"}
        if os.path.lexists(stop) or not permit.exists() or permit.read_bytes()!=raw:return {"status":"DISABLED"}
        import shutil
        if shutil.disk_usage(HERE).free<512*1024*1024:raise ValueError("disk")
        now=clock();rows,latest=read_rows(now)
        packet=capture(rows,latest,now,radar,absorption,sha(canonical(pins)))
        if packet is None:return {"status":"WAIT_FRESH_RADAR"}
        if os.path.lexists(stop) or not permit.exists() or permit.read_bytes()!=raw:return {"status":"DISABLED"}
        path=HERE/"radar-v331.sqlite3"
        if not os.path.lexists(path):os.close(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600))
        private(path,0o600,stat.S_ISREG)
        with closing(sqlite3.connect(path,timeout=3)) as db:
            cap=CAP//db.execute("PRAGMA page_size").fetchone()[0]
            if db.execute("PRAGMA max_page_count="+str(cap)).fetchone()[0]!=cap:raise ValueError("capacity")
            initialize(db)
            packet["rule_pins"]=pins
            status=save(db,packet,clock())
            return {"status":status,"observations":db.execute("SELECT COUNT(*) FROM radar_observations").fetchone()[0],"prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_ledger(self):
        db=sqlite3.connect(":memory:");initialize(db)
        p={"close_ms":M5,"capture_ms":M5+1,"prospective_admitted":False}
        self.assertEqual(save(db,p,M5+2),"LOCAL_RADAR_RECORDED")
        self.assertEqual(save(db,p,M5+2),"ALREADY_RECORDED")
        with self.assertRaises(sqlite3.IntegrityError):db.execute("DELETE FROM radar_observations")
        with self.assertRaises(ValueError):save(db,p,M5+600001)
        db.close()
    def test_history_counts_unavailable(self):
        rows=[{"close_ms":M5},{"close_ms":2*M5}]
        def radar(r,t,a):return {FLAGS[0]:False,FLAGS[1]:None,FLAGS[2]:len(r)==2}
        p=history(rows,radar,None)
        self.assertEqual(p["counts"][FLAGS[0]]["false"],2)
        self.assertEqual(p["counts"][FLAGS[1]]["unavailable"],2)
        self.assertEqual(p["counts"][FLAGS[2]]["true"],1)
        self.assertFalse(p["persistent_write"])
    def test_capture_asof(self):
        r={"close_ms":M5,"available_ms":M5+1,"segment_bars":1,"digest":"a"*64}
        radar=lambda *args:{"status":"DESCRIPTIVE_ONLY"}
        with self.assertRaises(ValueError):capture([r],M5,M5,radar,None,"b"*64)
        self.assertIsNone(capture([r],2*M5,M5+1,radar,None,"b"*64))
        self.assertEqual(capture([r],M5,M5+1,radar,None,"b"*64)["sources"],[[M5,"a"*64]])
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:] in (["--history"],["--tick"]):
        deps()
        try:print("V331 RADAR",json.dumps(run(sys.argv[1]),sort_keys=True))
        except Exception as e:print("V331 RADAR STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("--selftest | --history | separately authorized --tick")
