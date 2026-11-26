"""V31.5 LAB read-only account telemetry refresh, not exact billing.
Requires separate explicit permit, confirmed Free plan, separately scoped read tokens.
No network on import/selftest; no automatic retries after an uncertain response.
"""
import os,sys,json,unittest,tempfile
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,HTTPRedirectHandler
BASE=Path.home()/".remura-v296";HERE=BASE/"v315"
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v315_collector import clock,load,private,permit_ok,readiness,day
from v313_account_quota import collect_sample
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def valid_scope(p):
    return p=={"mode":"ACCOUNT_D1_READ_ONLY","enabled":True}
def credentials(a,d,collector):
    if set(a)!={"account_id","token"} or set(d)!={"account_id","token"} or a["account_id"]!=d["account_id"] or a["account_id"]!=collector["account_id"]:raise ValueError("account_scope")
    return a["account_id"],a["token"],d["token"]
def save(path,data):
    if os.path.lexists(path):private(path)
    fd,tmp=tempfile.mkstemp(prefix=".quota-",dir=path.parent)
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(data,f,sort_keys=True);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fd=os.open(path.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.lexists(tmp):os.unlink(tmp)
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,HERE):private(p,True)
    if any(os.path.lexists(HERE/n) for n in ("STOP","QUOTA-STOP")):return "STOP"
    pp=HERE/"permit.json";qp=HERE/"quota-permit.json"
    if not pp.exists() or not qp.exists():return "WAIT_AUTHORIZATION"
    p=load(pp);q=load(qp)
    if not permit_ok(p,clock()) or not valid_scope(q):return "WAIT_AUTHORIZATION"
    if readiness(clock())[0]!="READY":return "WAIT_PREDECESSOR"
    planpath=HERE/"free-plan.json"
    ap=HERE/"analytics-read.json";dp=HERE/"d1-read.json"
    if not all(x.exists() for x in (planpath,ap,dp)):return "WAIT_READONLY_CREDENTIALS_OR_PLAN"
    plan=load(planpath)
    account,at,dt=credentials(load(ap),load(dp),load(BASE/"v297-credentials.json"))
    # Reuse the existing audited GraphQL and D1 metadata readers. No SQL.
    sys.path.extend([str(BASE/"v301"),str(BASE)])
    import cloudflare_account_quota_guard as analytics
    import cloudflare_d1_account_storage_guard as storage
    import cloudflare_d1_readonly_audit as cf
    opener=build_opener(ProxyHandler({}),NoRedirect()).open
    analytics.urlopen=opener;cf.urlopen=opener
    cachepath=HERE/"storage-cache.json";cache=None
    if cachepath.exists():
        c=load(cachepath);cache=(c["checked_ms"],c["storage"])
    def allowed():
        if any(os.path.lexists(HERE/n) for n in ("STOP","QUOTA-STOP")) or load(pp)!=p or load(qp)!=q or load(planpath)!=plan:raise ValueError("scope_changed")
    def ar(d):
        allowed()
        return analytics.query_account_analytics(account,at,d)
    def sr():
        allowed()
        return storage.fetch_account_storage(account,dt)
    # Invalidate previous sample before network; failures cannot leave stale green data.
    save(HERE/"account-quota.json",{"complete":False})
    sample,(stamp,st)=collect_sample(clock=clock,plan=plan,analytics_reader=ar,storage_reader=sr,storage_cache=cache,authorized=True)
    allowed()
    save(cachepath,{"checked_ms":stamp,"storage":st})
    save(HERE/"account-quota.json",sample)
    return "ACCOUNT_ESTIMATE_REFRESHED"
class Tests(unittest.TestCase):
    def test_scope(self):
        self.assertTrue(valid_scope({"mode":"ACCOUNT_D1_READ_ONLY","enabled":True}))
        self.assertFalse(valid_scope({"mode":"ACCOUNT_D1_READ_ONLY","enabled":False}))
    def test_credentials(self):
        a={"account_id":"a","token":"synthetic"}
        self.assertEqual(credentials(a,a,a)[0],"a")
        with self.assertRaises(ValueError):credentials(a,dict(a,account_id="b"),a)
    def test_atomic_sample(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample"
            save(p,{"complete":False});save(p,{"complete":True})
            self.assertTrue(load(p)["complete"])
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--run"]:
        try:print("V315 QUOTA",run(),flush=True)
        except Exception as e:
            if HERE.is_dir() and not os.path.lexists(HERE/"QUOTA-STOP"):
                try:
                    save(HERE/"account-quota.json",{"complete":False})
                    with (HERE/"QUOTA-STOP").open("x") as f:f.write("MANUAL_REVIEW_REQUIRED\n")
                except OSError:pass
            print("V315 QUOTA STOP",type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("LAB: --selftest or separately approved --run")
