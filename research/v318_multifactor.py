"""REMURA V31.8 LAB — 27/11/2026 Europe/Rome.
Separate experimental ledger; no scheduler, network, orders or V312 writes.
The caller must verify source bytes and real capture clock. No certification.
"""
import hashlib,json,math,sqlite3,re,unittest
from decimal import Decimal
M15=900000
TV="TRADINGVIEW:FX:EURUSD"
BASE=("price_only","footprint_only","footprint_plus_cot")
EXTRA=("footprint_cot_levels","footprint_cot_retail","footprint_cot_levels_retail")
ARMS=BASE+EXTRA
LEVELS=("week","current_month","previous_month")
def canonical(p):return json.dumps(p,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def digest_ok(h):return isinstance(h,str) and re.fullmatch("[a-f0-9]{64}",h) is not None
def numeric(x):return type(x) in (int,float) and math.isfinite(x)
def sides(base,ctx):
    if set(base)!=set(BASE) or any(type(v) is not int or v not in (-1,0,1) for v in base.values()):raise ValueError("sides")
    side=base["footprint_plus_cot"]
    if side not in (0,base["footprint_only"]):raise ValueError("base")
    if ctx.get("symbol")!="EURUSD" or ctx.get("tv_fresh") is not True or ctx.get("prospective_admitted") is not False:return None
    lv=ctx["levels"];r=ctx["retail"]
    if any(lv.get(k,{}).get("status")!="AVAILABLE_DESCRIPTIVE" for k in LEVELS):return None
    ds=[lv[k]["distance_pips"] for k in LEVELS]
    if not all(numeric(x) for x in ds):raise ValueError("distance")
    if r.get("status")!="LOCAL_COLLECTION_FRESH_ORIGIN_UNKNOWN" or r.get("origin_verified") is not False or r.get("predictive_admitted") is not False:return None
    l,s=r["long_pct"],r["short_pct"]
    if not all(numeric(v) and 0<=v<=100 for v in (l,s)) or abs(l+s-100)>.2:raise ValueError("retail")
    # Fixed hypotheses only, not tuned on past outcomes. Levels are proximity
    # filters, not asserted support/resistance. Retail is a contrarian filter.
    level_ok=all(abs(d)>=5 for d in ds)
    retail_ok=(side==1 and s>=60) or (side==-1 and l>=60)
    return {**base,EXTRA[0]:side if level_ok else 0,
            EXTRA[1]:side if retail_ok else 0,
            EXTRA[2]:side if level_ok and retail_ok else 0}
def freeze(b,ctx,e,clock):
    if b.get("status")!="TV_LOCAL_CANDIDATE_ONLY" or b.get("price_source")!=TV or b.get("symbol")!="EURUSD" or b.get("prospective_admitted") is not False:raise ValueError("baseline")
    a=b["frozen_ms"];n=clock()
    if type(a) is not int or type(n) is not int or not 0<a<=n or n-a>5000 or ctx.get("asof_ms")!=a:raise ValueError("clock")
    entry=(n//M15+1)*M15
    if b["entry_ms"]!=entry or entry-n<5000:return None
    if set(e)!={"input_close_ms","tv_latest_sha256","cot_sha256","rules_sha256","source_records"} or not all(digest_ok(e[k]) for k in ("tv_latest_sha256","cot_sha256","rules_sha256")):raise ValueError("evidence")
    rows=e["source_records"]
    if not isinstance(rows,list) or not 1<=len(rows)<=288:raise ValueError("records")
    prior=0
    for t,h in rows:
        if type(t) is not int or not prior<t<=a or not digest_ok(h):raise ValueError("record")
        prior=t
    if rows[-1][1]!=e["tv_latest_sha256"] or ctx["tv_sha256"]!=rows[-1][1]:raise ValueError("join")
    c=e["input_close_ms"]
    if type(c) is not int or c%M15 or not 0<c<=prior or not b["input_evidence"] or not set(b["input_evidence"])<=set(h for t,h in rows):raise ValueError("baseline_evidence")
    r=ctx["retail"]
    if not 0<r["collection_ms"]<=r["read_ms"]<=a or a-r["collection_ms"]>3600000 or not digest_ok(r["source_sha256"]):raise ValueError("retail_clock")
    if not 0<=a-prior<=600000:raise ValueError("tv_age")
    ss=sides(b["sides"],ctx)
    if ss is None:return None
    return {"schema":"remura.v318.multifactor.local.v1","symbol":"EURUSD","price_source":TV,
        "capture_ms":a,"frozen_ms":n,"entry_ms":entry,"evidence":e,"context":ctx,"sides":ss,
        "hypothesis":"V318_LEVEL_DISTANCE_5PIP_RETAIL_CONTRARIAN_60PCT","prospective_admitted":False}
def initialize(db):
    if db.in_transaction:raise ValueError("transaction")
    tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables and tables!={"v318_observations","v318_outcomes"}:raise ValueError("not_dedicated_ledger")
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS v318_observations(id TEXT PRIMARY KEY,entry_ms INTEGER UNIQUE NOT NULL,input_close_ms INTEGER UNIQUE NOT NULL,packet BLOB NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS v318_outcomes(id TEXT NOT NULL,hours INTEGER NOT NULL,cost INTEGER NOT NULL,result BLOB NOT NULL,evidence BLOB NOT NULL,asof_ms INTEGER NOT NULL,PRIMARY KEY(id,hours,cost),FOREIGN KEY(id) REFERENCES v318_observations(id))")
        for t in ("v318_observations","v318_outcomes"):
            for op in ("UPDATE","DELETE"):
                db.execute("CREATE TRIGGER IF NOT EXISTS "+t+"_no_"+op.lower()+" BEFORE "+op+" ON "+t+" BEGIN SELECT RAISE(ABORT,'append_only'); END")
def append(db,p,clock):
    now=clock()
    if p["schema"]!="remura.v318.multifactor.local.v1" or p["prospective_admitted"] is not False or not p["capture_ms"]<=p["frozen_ms"]<=now<p["entry_ms"] or now-p["frozen_ms"]>5000 or p["entry_ms"]!=(p["frozen_ms"]//M15+1)*M15:raise ValueError("freeze")
    raw=canonical(p)
    with db:
        if db.execute("SELECT 1 FROM v318_observations WHERE entry_ms=? OR input_close_ms=?",(p["entry_ms"],p["evidence"]["input_close_ms"])).fetchone():return "ALREADY_OBSERVED"
        db.execute("INSERT INTO v318_observations VALUES(?,?,?,?)",(sha(raw),p["entry_ms"],p["evidence"]["input_close_ms"],raw))
    return "LOCAL_RECORDED_UNWITNESSED"
def evaluate_six(p,bars,asof,hours,cost):
    from v300_paired_outcomes import evaluate
    if p.get("schema")!="remura.v318.multifactor.local.v1" or p.get("price_source")!=TV or p.get("prospective_admitted") is not False or p["entry_ms"]!=(p["frozen_ms"]//M15+1)*M15 or set(p["sides"])!=set(ARMS) or type(cost) is not int or cost not in (0,1,2):raise ValueError("packet")
    if any(b.get("source")!=TV or type(b.get("available_ms")) is not int or not b["open_ms"]+M15<=b["available_ms"]<=asof for b in bars):raise ValueError("same_feed")
    net={}
    for group in (BASE,EXTRA):
        d={"symbol":"EURUSD","mode":"TEST_DESCRIPTIVE_ONLY","frozen_ms":p["frozen_ms"],"sides":{k:p["sides"][a] for k,a in zip(BASE,group)}}
        r=evaluate(d,bars,asof,cost,hours)
        if r["status"]!="RETROSPECTIVE_ONLY":return r
        net.update({a:r["net_pips"][k] for k,a in zip(BASE,group)})
    return {**r,"net_pips":net,"price_source":TV,"execution_price_verified":False}
def save_outcome(db,identity,bars,asof,hours,cost):
    row=db.execute("SELECT packet FROM v318_observations WHERE id=?",(identity,)).fetchone()
    if row is None or sha(row[0])!=identity:raise ValueError("packet_integrity")
    p=json.loads(row[0])
    r=evaluate_six(p,bars,asof,hours,cost)
    if r["status"]!="RETROSPECTIVE_ONLY":return r["status"]
    ev=[]
    for b in sorted(bars,key=lambda b:b["open_ms"]):
        if r["entry_ms"]<=b["open_ms"]<r["end_ms"]:
            h=b.get("evidence")
            if not isinstance(h,(tuple,list)) or len(h)!=3 or not all(digest_ok(x) for x in h):raise ValueError("outcome_evidence")
            ev.append([b["open_ms"],list(h)])
    result,proof=canonical(r),canonical(ev)
    with db:
        old=db.execute("SELECT result,evidence FROM v318_outcomes WHERE id=? AND hours=? AND cost=?",(identity,hours,cost)).fetchone()
        if old:
            if old!=(result,proof):raise ValueError("outcome_conflict")
            return "ALREADY_EVALUATED"
        db.execute("INSERT INTO v318_outcomes VALUES(?,?,?,?,?,?)",(identity,hours,cost,result,proof,asof))
    return "EVALUATED"
class Tests(unittest.TestCase):
    def setup(self):
        a=1000000;h="a"*64
        c={"symbol":"EURUSD","tv_fresh":True,"prospective_admitted":False,"asof_ms":a,"tv_sha256":h,
            "levels":{k:{"status":"AVAILABLE_DESCRIPTIVE","distance_pips":10} for k in LEVELS},
            "retail":{"status":"LOCAL_COLLECTION_FRESH_ORIGIN_UNKNOWN","origin_verified":False,"predictive_admitted":False,"long_pct":30,"short_pct":70,"collection_ms":a-1000,"read_ms":a-1,"source_sha256":"d"*64}}
        b=dict(status="TV_LOCAL_CANDIDATE_ONLY",price_source=TV,symbol="EURUSD",prospective_admitted=False,frozen_ms=a,entry_ms=1800000,sides=dict(price_only=-1,footprint_only=1,footprint_plus_cot=1),input_evidence=[h])
        e=dict(input_close_ms=900000,tv_latest_sha256=h,cot_sha256="b"*64,rules_sha256="c"*64,source_records=[[900000,h]])
        return b,c,e
    def test_arms(self):
        b,c,e=self.setup()
        self.assertEqual(set(sides(b["sides"],c)),set(ARMS))
        self.assertEqual(sides(b["sides"],c)[EXTRA[2]],1)
        c["levels"]["week"]["distance_pips"]=2
        self.assertEqual(sides(b["sides"],c)[EXTRA[2]],0)
        self.assertEqual(sides(b["sides"],c)[EXTRA[1]],1)
        c["retail"]["status"]="STALE_LOCAL_COLLECTION"
        self.assertIsNone(sides(b["sides"],c))
    def test_clock(self):
        b,c,e=self.setup()
        self.assertIsNotNone(freeze(b,c,e,lambda:1000001))
        c["retail"]["read_ms"]=1000001
        with self.assertRaises(ValueError):freeze(b,c,e,lambda:1000001)
    def test_ledger(self):
        b,c,e=self.setup();p=freeze(b,c,e,lambda:1000001)
        db=sqlite3.connect(":memory:");initialize(db)
        self.assertEqual(append(db,p,lambda:1000002),"LOCAL_RECORDED_UNWITNESSED")
        self.assertEqual(append(db,p,lambda:1000002),"ALREADY_OBSERVED")
        with self.assertRaises(ValueError):append(db,p,lambda:1800000)
        with self.assertRaises(sqlite3.IntegrityError):db.execute("DELETE FROM v318_observations")
        db.close()
    def test_evaluate(self):
        b,c,e=self.setup();p=freeze(b,c,e,lambda:1000001)
        bars=[dict(source=TV,open_ms=t,available_ms=t+M15,o="1.1000",h="1.1010",l="1.1000",c="1.1010",evidence=["f"*64]*3) for t in range(1800000,5400000,M15)]
        db=sqlite3.connect(":memory:");initialize(db);append(db,p,lambda:1000002)
        identity=sha(canonical(p))
        self.assertEqual(save_outcome(db,identity,bars[:-1],5400000,1,1),"MISSING_CONTIGUOUS_BARS")
        self.assertEqual(save_outcome(db,identity,bars,5400000,1,1),"EVALUATED")
        self.assertEqual(save_outcome(db,identity,bars,5400000,1,1),"ALREADY_EVALUATED")
        self.assertEqual(Decimal(evaluate_six(p,bars,5400000,1,1)["net_pips"][EXTRA[1]]),9)
        db.close()
if __name__=="__main__":unittest.main()
