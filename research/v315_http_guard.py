"""V31.5 LAB permanent HTTP boundary. No network on import or selftest.
Only the two authorized V315 entrypoints are callable. All attempted HTTP
requests are durably charged before transmission. No redirects or retries.
"""
import os,sys,json,time,sqlite3,stat,fcntl,re,hashlib,unittest
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
from urllib.request import OpenerDirector
BASE=Path.home()/".remura-v296";HERE=BASE/"v315"
sys.path.insert(0,str(HERE))
DAY=86400000;HALF=1800000
LIMITS={"quota_get":12,"graphql":48,"collector_get":300,"select":300}
def day(t):return datetime.fromtimestamp(t/1000,timezone.utc).date().isoformat()
def classify(kind,req,account):
    u=urlsplit(req.full_url);m=req.get_method()
    if u.scheme!="https" or u.netloc!="api.cloudflare.com" or u.fragment:raise ValueError("origin")
    root="/client/v4/accounts/"+account
    db=root+"/d1/database"
    if kind=="quota":
        if m=="POST" and u.path=="/client/v4/graphql" and not u.query:return "graphql"
        if m=="GET" and (u.path==root+"/tokens/verify" and not u.query or u.path==db and u.query=="page=1&per_page=100" or re.fullmatch(re.escape(db)+r"/[a-fA-F0-9-]{36}",u.path) and not u.query):return "quota_get"
    if kind=="collector":
        if m=="GET" and u.path==db and u.query=="page=1&per_page=100":return "collector_get"
        if m=="POST" and re.fullmatch(re.escape(db)+r"/[a-fA-F0-9-]{36}/query",u.path) and not u.query:return "select"
    raise ValueError("endpoint")
def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,day TEXT NOT NULL,ms INTEGER NOT NULL)")
    db.commit()
def eligible(db,k,now):
    if k not in LIMITS:raise ValueError("kind")
    last=db.execute("SELECT MAX(ms) FROM attempts").fetchone()[0]
    if last is not None and now<last:raise ValueError("clock_regressed")
    n=db.execute("SELECT COUNT(*) FROM attempts WHERE kind=? AND day=?",(k,day(now))).fetchone()[0]
    if n>=LIMITS[k]:return False
    if k=="graphql":
        t=db.execute("SELECT MAX(ms) FROM attempts WHERE kind=?",(k,)).fetchone()[0]
        if t is not None and now-t<HALF:return False
    return True
def reserve(db,k,now):
    db.execute("BEGIN IMMEDIATE")
    try:
        if not eligible(db,k,now):raise ValueError("http_budget")
        db.execute("INSERT INTO attempts(kind,day,ms) VALUES(?,?,?)",(k,day(now),now))
        db.commit()
    except BaseException:db.rollback();raise
def run(kind):
    if kind not in ("quota","collector"):raise ValueError("kind")
    os.umask(0o077)
    from v315_collector import private,load,clock,readiness,permit_ok
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,HERE):private(p,True)
    if os.path.lexists(HERE/"STOP") or os.path.lexists(HERE/"QUOTA-STOP"):return "STOP"
    pp=HERE/"permit.json";qp=HERE/"quota-permit.json"
    if not pp.exists() or not qp.exists():return "WAIT_AUTHORIZATION"
    p=load(pp);q=load(qp)
    if not permit_ok(p,clock()) or q!={"mode":"ACCOUNT_D1_READ_ONLY","enabled":True}:return "WAIT_AUTHORIZATION"
    status,_=readiness(clock())
    if status!="READY":return status
    # Verify the pinned six staged files and this boundary before importing readers.
    pins=load(HERE/"http-manifest.json")
    expected={"v315_http_guard.py","v315_collector.py","v315_quota_refresh.py","v313_handoff.py","v313_account_quota.py","cloudflare_account_quota_guard.py","cloudflare_d1_account_storage_guard.py"}
    if set(pins)!=expected:raise ValueError("manifest_scope")
    for name,h in pins.items():
        f=HERE/name;private(f)
        if hashlib.sha256(f.read_bytes()).hexdigest()!=h:raise ValueError("code_pin")
    lock=HERE/"http.lock"
    with os.fdopen(os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600),"r+") as guard:
        private(lock)
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return "WAIT_HTTP_LOCK"
        if load(pp)!=p or load(qp)!=q:return "WAIT_AUTHORIZATION"
        status,_=readiness(clock())
        if status!="READY":return status
        if os.path.lexists(HERE/"http-cycle-inflight.lock"):raise ValueError("unfinished_cycle")
        ledger=HERE/"http-attempts.sqlite3";private(ledger)
        db=sqlite3.connect(ledger,timeout=3)
        original=OpenerDirector.open
        try:
            if kind=="quota" and not eligible(db,"graphql",clock()):return "WAIT_GRAPHQL_INTERVAL"
            if kind=="collector" and (not eligible(db,"select",clock()) or not eligible(db,"collector_get",clock())):return "WAIT_HTTP_BUDGET"
            c=load(BASE/"v297-credentials.json");a=load(HERE/"analytics-read.json");d=load(HERE/"d1-read.json")
            account=c["account_id"]
            if a["account_id"]!=account or d["account_id"]!=account:raise ValueError("account")
            sys.path.extend([str(BASE/"v301"),str(BASE)])
            import cloudflare_account_quota_guard as analytics
            from v300_slot_custody import request_slots
            start_day=day(clock())
            seen=set()
            def bounded(self,req,*args,**kwargs):
                now=clock()
                if day(now)!=start_day or os.path.lexists(HERE/"STOP") or os.path.lexists(HERE/"QUOTA-STOP") or load(pp)!=p or load(qp)!=q:raise ValueError("stop_gate")
                k=classify(kind,req,account)
                token={"graphql":a["token"],"quota_get":d["token"],"collector_get":c["token"],"select":c["token"]}[k]
                if req.get_header("Authorization")!="Bearer "+token:raise ValueError("token_scope")
                if k=="graphql":
                    body=json.loads(req.data)
                    if body!={"query":analytics.QUERY,"variables":{"accountTag":account,"day":start_day}} or k in seen:raise ValueError("graphql_scope")
                elif k=="select":
                    body=json.loads(req.data)
                    params=body["params"]
                    slots=[int(v.split("|")[2]) for v in params[:-1]]
                    if body!=request_slots(slots,params[-1]) or k in seen or "collector_get" not in seen:raise ValueError("select_scope")
                elif k=="collector_get" and k in seen:raise ValueError("inventory_scope")
                if k=="quota_get":
                    key=req.full_url
                    if key in seen:raise ValueError("duplicate_get")
                    seen.add(key)
                reserve(db,k,now);seen.add(k)
                return original(self,req,*args,**kwargs)
            OpenerDirector.open=bounded
            if kind=="quota":
                from v315_quota_refresh import run as tick
            else:
                from v315_collector import run as tick
            inflight=HERE/"http-cycle-inflight.lock"
            with inflight.open("x") as marker:
                marker.write(kind+"\n");marker.flush();os.fsync(marker.fileno())
            fd=os.open(HERE,os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
            result=tick()
            inflight.unlink()
            fd=os.open(HERE,os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
            return result
        finally:
            OpenerDirector.open=original;db.close()
class Tests(unittest.TestCase):
    def test_limits(self):
        db=sqlite3.connect(":memory:");initialize(db);t=1800000000000
        for _ in range(12):reserve(db,"quota_get",t)
        with self.assertRaises(ValueError):reserve(db,"quota_get",t)
        reserve(db,"quota_get",t+DAY)
        db.close()
    def test_interval(self):
        db=sqlite3.connect(":memory:");initialize(db);t=1800000000000
        reserve(db,"graphql",t)
        self.assertFalse(eligible(db,"graphql",t+HALF-1))
        self.assertTrue(eligible(db,"graphql",t+HALF))
        db.close()
    def test_endpoints(self):
        from urllib.request import Request
        a="a"*32;root="https://api.cloudflare.com/client/v4/accounts/"+a
        self.assertEqual(classify("quota",Request(root+"/tokens/verify"),a),"quota_get")
        with self.assertRaises(ValueError):classify("quota",Request(root+"/d1/database/"+"a"*36+"/query",data=b"{}"),a)
        with self.assertRaises(ValueError):classify("collector",Request("https://example.com"),a)
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif len(sys.argv)==3 and sys.argv[1]=="--run":
        kind=sys.argv[2]
        try:print("V315 GUARDED",kind,run(kind),flush=True)
        except Exception as e:
            # Latch uncertain attempts; never retry automatically.
            try:
                path=HERE/("QUOTA-STOP" if kind=="quota" else "STOP")
                with path.open("x") as f:f.write("MANUAL_REVIEW_REQUIRED\n");f.flush();os.fsync(f.fileno())
            except OSError:pass
            print("V315 GUARDED STOP",kind,type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("LAB --selftest or separately authorized --run quota|collector")
