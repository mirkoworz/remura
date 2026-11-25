"""REMURA V29.7 LAB — 25/11/2026 Europe/Rome.
Bounded pilot; disabled unless owner creates a time-limited permit.
No broker, no production DB, no prospective decisions, no RAW logs.
"""
import os, sys, stat, time, json, sqlite3, fcntl, shutil
from pathlib import Path
from urllib.parse import quote
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler

sys.dont_write_bytecode=True
import cloudflare_d1_readonly_audit as cf
from d1_test_target_preflight_v1 import inspect_verified_inventory, TEST_DB, MAIN_DB
from v292_d1_oracle_page_contract import request_page
from v294_d1_oracle_custody import cursor, pull_once
from v295_bridge_observation import summarize

BASE=Path.home()/".remura-v296"
MAX_TICKS=6
MAX_SELECT=8
MAX_READ_PER_QUERY=10000
MAX_LAG=3600000
M5=300000

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def check_private(path, directory=False):
    s=path.lstat()
    kind=stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if directory else 0o600):
        raise ValueError("private_permissions")

def read_private(path):
    check_private(path)
    if path.stat().st_size>8192:
        raise ValueError("file_size")
    return json.loads(path.read_text())

def save_state(path,state):
    tmp=path.with_name(path.name+".tmp")
    with tmp.open("x") as f:
        json.dump(state,f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def permit_ok(p,now):
    return (type(p) is dict and set(p)=={"start_ms","end_ms","free_confirmed"}
            and p["free_confirmed"] is True
            and type(p["start_ms"]) is int and type(p["end_ms"]) is int
            and p["start_ms"]<=now<p["end_ms"]
            and 0<p["end_ms"]-p["start_ms"]<=2400000)

def forward_window(cur,now):
    if cur is None or type(cur[0]) is not int:
        raise ValueError("missing_seed_cursor")
    cutoff=now-120000
    if not 0<=cutoff-cur[0]<=MAX_LAG:
        raise ValueError("history_or_clock_gate")
    return cur[0],cutoff

def query_rows(response):
    if response.get("success") is not True:
        raise ValueError("api_failure")
    batch=response.get("result")
    if type(batch) is not list or len(batch)!=1 or batch[0].get("success") is not True:
        raise ValueError("query_failure")
    q=batch[0]
    m=q.get("meta",{})
    n,w=m.get("rows_read"),m.get("rows_written")
    if type(n) is not int or type(w) is not int or n<0 or w!=0:
        raise ValueError("quota_metadata")
    rows=q.get("results")
    if type(rows) is not list or len(rows)>4:
        raise ValueError("page_shape")
    return rows,n

def tick():
    os.umask(0o077)
    check_private(BASE,True)
    permit=BASE/"v297-permit.json"
    if not permit.exists():
        print("V297 DISABLED")
        return
    p=read_private(permit)
    now=int(time.time()*1000)
    if not permit_ok(p,now):
        print("V297 PERMIT_EXPIRED_OR_INVALID")
        return
    lock=BASE/"v297-tick.lock"
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"r+") as guard:
        check_private(lock)
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (BASE/"v297-STOP").exists():
            print("V297 STOPPED")
            return
        path=BASE/"v297-state.json"
        state=read_private(path) if path.exists() else {"ticks":0,"selects":0,"rows_read":0,"inflight":False,"permit":p}
        if state["permit"]!=p or state["inflight"]:
            raise ValueError("previous_attempt_or_permit_changed")
        if state["ticks"]>=MAX_TICKS or state["selects"]>=MAX_SELECT:
            print("V297 PILOT_LIMIT")
            return
        if shutil.disk_usage(BASE).free<100*1024*1024:
            raise ValueError("disk_gate")
        dbpath=BASE/"tv-custody.sqlite3"
        check_private(dbpath)
        credentials=read_private(BASE/"v297-credentials.json")
        account=quote(cf.require_account_id(credentials["account_id"]),safe="")
        token=cf.require_account_token(credentials["token"])
        cf.urlopen=build_opener(ProxyHandler({}),NoRedirect()).open
        db=sqlite3.connect(dbpath,timeout=3)
        try:
            start,cutoff=forward_window(cursor(db),int(time.time()*1000))
            state["ticks"]+=1
            state["inflight"]=True
            save_state(path,state)
            base="/accounts/"+account+"/d1/database"
            ids=inspect_verified_inventory(cf.api_request("GET",base+"?page=1&per_page=100",token))
            if ids[TEST_DB]==ids[MAIN_DB]:
                raise ValueError("not_test")
            def fetch(query):
                if not permit_ok(p,int(time.time()*1000)) or (BASE/"v297-STOP").exists():
                    raise ValueError("stop_gate")
                params=query.get("params")
                if type(params) is not list or len(params)!=9 or query!=request_page(params[3],params[4],(params[5],params[7])):
                    raise ValueError("select_only")
                if state["selects"]>=MAX_SELECT or state["rows_read"]>=MAX_SELECT*MAX_READ_PER_QUERY:
                    raise ValueError("budget")
                state["selects"]+=1
                save_state(path,state)
                rows,n=query_rows(cf.api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,query))
                state["rows_read"]+=n
                save_state(path,state)
                if n>MAX_READ_PER_QUERY:
                    raise ValueError("scan_budget_exceeded")
                return rows
            a=pull_once(db,fetch,start,cutoff,enabled=True)
            replayed=0
            # Bounded overlap only, never a claim of full historical reconciliation.
            if state["ticks"]%3==0:
                overlap=max(1,cutoff-900000)
                z=pull_once(db,fetch,overlap,cutoff,enabled=True,reconciliation=True)
                replayed=z["inserted"]
                if z["more_possible"]:
                    print("V297 RECONCILIATION_PARTIAL")
            report=summarize(db,max(1,cutoff-7200000),cutoff)
            state["inflight"]=False
            save_state(path,state)
            print(json.dumps({"ticks":state["ticks"],"selects":state["selects"],"rows_read":state["rows_read"],"new":a["inserted"],"reconciled":replayed,"summary":report},sort_keys=True))
        finally:
            db.close()

if __name__=="__main__":
    try:
        tick()
    except Exception as e:
        # Never print exception text, credentials, row contents or traceback.
        print("V297 STOP",type(e).__name__)
        sys.exit(2)
