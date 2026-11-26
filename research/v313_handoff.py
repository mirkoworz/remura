"""V31.3 LAB: bounded successor scheduler; no installation or permit renewal.
Quota sample is a contract for a separately verified account reader, not billing proof.
"""
import os,sys,json,time,stat,subprocess,unittest
from pathlib import Path
from datetime import datetime,timezone
BASE=Path.home()/".remura-v296"
HOUR=3600000
def utc_day(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).date()
def quota_gate(sample,now):
    fields={"scope","plan","complete","checked_ms","rows_read","rows_written","storage_bytes","databases"}
    if set(sample)!=fields or sample["scope"]!="ACCOUNT_D1" or sample["plan"]!="FREE" or sample["complete"] is not True:
        return False
    for k in fields-{"scope","plan","complete"}:
        if type(sample[k]) is not int or sample[k]<0:return False
    t=sample["checked_ms"]
    return (0<=now-t<=HOUR and utc_day(now)==utc_day(t)
            and sample["rows_read"]+10000<=1000000
            and sample["rows_written"]<80000
            and sample["storage_bytes"]<4000000000 and sample["databases"]<=10)
def readiness(state,marker,now,end,permit_end,stop):
    if stop:return "STOP"
    if state in ("active","activating","deactivating","reloading"):return "WAIT_PREDECESSOR"
    if state!="inactive":return "REVIEW_PREDECESSOR"
    if not marker or now<end:return "WAIT_NATURAL_END"
    if now+90000>=permit_end:return "WAIT_AUTHORIZATION"
    return "READY"
def private_json(path):
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_size>65536:
        raise ValueError("private_file")
    return json.loads(path.read_bytes())
def state(unit):
    return subprocess.run(["systemctl","show","--no-pager",unit,"-p","ActiveState","--value"],check=True,capture_output=True,text=True,timeout=5).stdout.strip()
def run(kind):
    if os.getuid()==0:raise ValueError("not_root")
    now=int(time.time()*1000)
    if kind=="collector":
        unit="remura-v303-live.service";old=BASE/"v302-live-permit.json";mark=BASE/"v302-live-STOP"
        permit=BASE/"v312-collector-permit.json";stop=BASE/"v312-collector-STOP";entry="v312_collector_guard.py"
    elif kind=="science":
        unit="remura-v311-science.service";old=None;mark=BASE/"v311/STOP"
        permit=BASE/"v312/permit.json";stop=BASE/"v312/STOP";entry="v312_science_tick.py"
    else:raise ValueError("kind")
    if os.path.lexists(stop):return "STOP"
    s=state(unit)
    if s in ("active","activating","deactivating","reloading"):return "WAIT_PREDECESSOR"
    if s!="inactive":return "REVIEW_PREDECESSOR"
    if not permit.exists():return "WAIT_AUTHORIZATION"
    p=private_json(permit)
    if p.get("enabled") is not True:return "WAIT_AUTHORIZATION"
    end=private_json(old)["end_ms"] if old else 0
    ready=readiness(s,mark.is_file() and not mark.is_symlink(),now,end,p["end_ms"],False)
    if ready!="READY":return ready
    if now<p["start_ms"]:return "WAIT_AUTHORIZATION"
    if kind=="collector":
        sample=BASE/"v313-account-quota.json"
        if not sample.exists():return "WAIT_QUOTA"
        if not quota_gate(private_json(sample),now):return "WAIT_QUOTA"
        if utc_day(p["usage_checked_ms"])!=utc_day(now):return "WAIT_AUTHORIZATION"
    # Existing guard, lock, manifest, quota ledger and expiry remain authoritative.
    env=dict(os.environ,PYTHONPATH=os.pathsep.join(str(BASE/x) for x in ("v312","v301","v311")))
    subprocess.run([sys.executable,str(BASE/"v312"/entry)],env=env,check=True,timeout=100)
    return "TICK_RETURNED"
def units(kind):
    if kind not in ("collector","science"):raise ValueError("kind")
    service=("[Unit]\nDescription=REMURA V31.3 "+kind+" LAB\n"
      "[Service]\nType=oneshot\nUMask=0077\nNoNewPrivileges=yes\n"
      "TimeoutStartSec=120\nExecStart=/usr/bin/python3 %h/.remura-v296/v313/v313_handoff.py --run "+kind+"\n")
    timer=("[Unit]\nDescription=REMURA V31.3 "+kind+" LAB timer\n"
      "[Timer]\nOnCalendar=*:0/5\nPersistent=true\nAccuracySec=15s\n"
      "Unit=remura-v313-"+kind+".service\n[Install]\nWantedBy=timers.target\n")
    return service,timer
class Tests(unittest.TestCase):
    def test_wait(self):
        self.assertEqual(readiness("active",True,10,0,100000,False),"WAIT_PREDECESSOR")
        self.assertEqual(readiness("failed",True,10,0,100000,False),"REVIEW_PREDECESSOR")
    def test_expiry(self):
        self.assertEqual(readiness("inactive",True,100,0,1000,False),"WAIT_AUTHORIZATION")
        self.assertEqual(readiness("inactive",True,100,0,100000,False),"READY")
    def test_quota(self):
        n=1800000000000
        p=dict(scope="ACCOUNT_D1",plan="FREE",complete=True,checked_ms=n,rows_read=100,rows_written=20,storage_bytes=100,databases=5)
        self.assertTrue(quota_gate(p,n))
        self.assertFalse(quota_gate(dict(p,complete=False),n))
        self.assertFalse(quota_gate(p,n+HOUR+1))
        self.assertFalse(quota_gate(dict(p,rows_read=995000),n))
if __name__=="__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--run":print("V313",run(sys.argv[2]),flush=True)
    elif len(sys.argv)==3 and sys.argv[1]=="--units":print("\n---\n".join(units(sys.argv[2])))
    elif sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    else:raise SystemExit("LAB: use --selftest or --units; --run requires separate activation approval")
