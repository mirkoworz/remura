"""REMURA V30.2 — 26/11/2026 Europe/Rome.
One authorized backfill, max 128 slots/32 SELECT/1 inventory GET.
No automatic scheduling, no credentials or RAW in logs.
"""
import os,sys,time,json,sqlite3,fcntl,shutil,getpass,warnings
from pathlib import Path
from urllib.parse import quote
from urllib.request import build_opener,HTTPRedirectHandler,ProxyHandler
BASE=Path.home()/".remura-v296"
sys.path.insert(0,str(BASE))
sys.path.insert(0,str(BASE/"v301"))
import v297_bounded_collector as old
import cloudflare_d1_readonly_audit as cf
from d1_test_target_preflight_v1 import inspect_verified_inventory,TEST_DB,MAIN_DB
from v300_slot_custody import initialize_coverage,request_slots,ingest_slots,key,M5
from v294_footprint_cvd import derive
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def clock():return int(time.time()*1000)
def inventory(credentials):
    account=quote(cf.require_account_id(credentials["account_id"]),safe="")
    token=cf.require_account_token(credentials["token"])
    cf.urlopen=build_opener(ProxyHandler({}),NoRedirect()).open
    root="/accounts/"+account+"/d1/database"
    ids=inspect_verified_inventory(cf.api_request("GET",root+"?page=1&per_page=100",token))
    if ids[TEST_DB]==ids[MAIN_DB]:raise ValueError("isolation")
    endpoint=root+"/"+quote(ids[TEST_DB],safe="")+"/query"
    def fetch(slots,cutoff):
        return old.query_rows(cf.api_request("POST",endpoint,token,request_slots(slots,cutoff)))
    return fetch
def recover():
    os.umask(0o077)
    warnings.simplefilter("error",getpass.GetPassWarning)
    old.check_private(BASE,True)
    old.check_private(BASE/"v301",True)
    target=BASE/"tv-custody.sqlite3"
    old.check_private(target)
    marker=BASE/"v302-backfill-attempt.lock"
    backup=BASE/"v302-before-backfill.sqlite3"
    if os.path.lexists(marker) or os.path.lexists(backup):
        raise ValueError("already_prepared")
    if shutil.disk_usage(BASE).free<100*1024*1024+2*target.stat().st_size:
        raise ValueError("disk")
    lock=BASE/"v297-tick.lock"
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"r+") as guard:
        old.check_private(lock)
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pilot=old.read_private(BASE/"v297-state.json")
        if pilot["inflight"] or pilot["ticks"]!=6 or pilot["selects"]!=8 or clock()<pilot["permit"]["end_ms"]:
            raise ValueError("pilot_state")
        db=sqlite3.connect(target,timeout=3)
        try:
            count,last=db.execute("SELECT COUNT(*),MAX(CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER)) FROM tv_test_custody").fetchone()
            key(last)
            cutoff=clock()-120000
            mature=(cutoff-120000)//M5*M5
            slots=list(range(last+M5,min(mature,last+128*M5)+1,M5))
            print("ARCHIVIO_PRIMA",count,"SLOT_DA_VERIFICARE",len(slots),flush=True)
            if not slots:return
            if getpass.getpass("Piano Free e letture sotto 1M verificati? SI: ").strip().upper()!="SI":
                raise ValueError("free_gate")
            if clock()-cutoff>600000:raise ValueError("confirmation_stale")
            credentials=old.read_private(BASE/"v297-credentials.json")
            with marker.open("x") as f:
                f.write("ONE_SHOT\n");f.flush();os.fsync(f.fileno())
            fd=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            os.close(fd)
            dest=sqlite3.connect(backup)
            try:
                db.backup(dest)
                if dest.execute("PRAGMA integrity_check").fetchone()!=("ok",):raise ValueError("backup_integrity")
                if dest.execute("SELECT COUNT(*) FROM tv_test_custody").fetchone()[0]!=count:raise ValueError("backup_count")
            finally:dest.close()
            old.check_private(backup)
            print("BACKUP_PRIVATO=OK",flush=True)
            initialize_coverage(db)
            print("GET_INVENTARIO_TENTATO=1",flush=True)
            fetch=inventory(credentials)
            print("D1_TEST_ISOLATO=OK",flush=True)
            total=new=missing=checked=0
            for i in range(0,len(slots),4):
                if clock()>cutoff+900000:raise ValueError("time_gate")
                page=slots[i:i+4]
                print("SELECT_TENTATA",i//4+1,flush=True)
                rows,read=fetch(page,cutoff)
                total+=read
                print("RIGHE_LETTE_CUMULATIVE",total,flush=True)
                if read>10000 or total>320000:raise ValueError("scan_gate")
                result=ingest_slots(db,page,cutoff,clock(),rows)
                new+=result["new"];missing+=result["missing_at_check"];checked+=len(page)
                print("SALVATI_NUOVI",new,"SLOT_VERIFICATI",checked,"MANCANTI",missing,flush=True)
            records=[{"metadata":json.loads(m),"original":v,"sha256":h} for m,v,h in db.execute("SELECT metadata,original,sha256 FROM tv_test_custody WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) BETWEEN ? AND ? ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 289",(last-127*M5,mature))]
            features=derive(records,clock())
            print(json.dumps({"archive_total":db.execute("SELECT COUNT(*) FROM tv_test_custody").fetchone()[0],"new":new,"checked":checked,"missing_at_check":missing,"rows_read":total,"valid_footprint_window":len(features),"longest_segment_window":max((f["segment_bars"] for f in features),default=0),"remaining_mature_slots_after_batch":max(0,(mature-slots[-1])//M5),"prospective_admitted":False},sort_keys=True),flush=True)
            print("BACKFILL_CONCLUSO",flush=True)
        finally:db.close()
if __name__=="__main__":
    try:recover()
    except Exception as e:
        print("V302 STOP",type(e).__name__,flush=True);sys.exit(2)
