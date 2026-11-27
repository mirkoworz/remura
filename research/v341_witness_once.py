"""REMURA V34.1 — one-shot independent timestamp pilot.
No automatic activation. Only --once with explicit local permit may POST.
No change to observations, outcomes, or admission status.
"""
import os,sys,time,json,hashlib,sqlite3,stat,subprocess,re,ssl,http.client,unittest
from pathlib import Path
from datetime import datetime,timezone
from contextlib import closing
BASE=Path.home()/".remura-v296"
HERE=BASE/"v318"
ROOT=HERE/"witness-v341"
CERT=BASE/"v306-tsa-synthetic"
PINS={"cacert.pem":"2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438","tsa.crt":"8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467"}
PREP_BLOB="7a02c0692b01934b2d299523ba811984a05b92ae"
M15=900000
def clock():return time.time_ns()//1000000
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def read(p,cap=1000000):
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:raise ValueError("private_file")
    with p.open("rb") as f:b=f.read(cap+1)
    if not 0<len(b)<=cap:raise ValueError("size")
    return b
def directory(p):
    s=p.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise ValueError("private_dir")
def write(p,b):
    with p.open("xb") as f:
        f.write(b);f.flush();os.fsync(f.fileno())
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def eligible(p,start,now):
    return (p.get("schema")=="remura.v318.multifactor.local.v1" and p.get("prospective_admitted") is False and
        all(type(p.get(k)) is int for k in ("capture_ms","frozen_ms","entry_ms")) and
        0<start<=p["capture_ms"]<=p["frozen_ms"]<=now and
        p["entry_ms"]==(p["frozen_ms"]//M15+1)*M15 and now+45000<p["entry_ms"])
def witness_time(text):
    matches=re.findall(r"^Time stamp: (.+) GMT$",text,re.M)
    if len(matches)!=1:raise ValueError("signed_time")
    x=matches[0];m=re.fullmatch(r"([A-Za-z]{3})\s+(\d{1,2})\s+(\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?\s+(\d{4})",x)
    if not m:raise ValueError("signed_time")
    mon,day,hms,frac,yr=m.groups()
    t=datetime.strptime(f"{mon} {day} {hms} {yr}","%b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
    low=int(t.timestamp())*1000+int(((frac or "")+"000")[:3])
    # Conservative millisecond bounds; second-only timestamps may not be precise.
    width=1000 if not frac else (100 if len(frac)==1 else 10 if len(frac)==2 else 1)
    return low,low+width
def time_ok(p,lo,hi,received):
    return p["frozen_ms"]<=lo<hi<=received+1 and hi<=p["entry_ms"] and received<p["entry_ms"]
def ro(p):
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:raise ValueError("ledger")
    db=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=3);db.execute("PRAGMA query_only=ON");return db
def proof(p,ident,raw):
    if sha(raw)!=ident:raise ValueError("packet")
    e=p["evidence"];root=HERE/"evidence-v324";directory(root)
    def check(h):
        if not re.fullmatch("[a-f0-9]{64}",h):raise ValueError("digest")
        x=read(root/h)
        if sha(x)!=h:raise ValueError("evidence")
        return x
    check(e["cot_sha256"]);manifest=json.loads(check(e["rules_sha256"]))
    for h in manifest.values():check(h)
    with closing(ro(BASE/"v312/science-tv.sqlite3")) as db:
        for t,h in e["source_records"]:
            r=db.execute("SELECT raw,digest,received_ms,seen_ms FROM events WHERE close_ms=?",(t,)).fetchone()
            if not r or r[1]!=h or sha(r[0])!=h or max(r[2],r[3])>p["capture_ms"]:raise ValueError("source")
def openssl(d,*args,stdin=None):
    env=dict(os.environ,LC_ALL="C",TZ="UTC")
    return subprocess.run(["/usr/bin/openssl",*args],cwd=d,input=stdin,capture_output=True,timeout=10,check=True,env=env).stdout
def certs():
    directory(CERT)
    out={n:read(CERT/n,65536) for n in PINS}
    if any(sha(out[n])!=h for n,h in PINS.items()):raise ValueError("cert_pin")
    out["v307-root-ca.pem"]=read(CERT/"v307-root-ca.pem")
    openssl(CERT,"verify","-CAfile","cacert.pem","-CRLfile","v307-root-ca.pem","-crl_check","-purpose","timestampsign","tsa.crt")
    return out
def prepare(ident):
    raw=read(HERE/"v305_witness_prepare.py")
    blob=b"blob "+str(len(raw)).encode()+b"\0"+raw
    if hashlib.sha1(blob).hexdigest()!=PREP_BLOB:raise ValueError("prep_pin")
    ns={};exec(compile(raw,"v305_witness_prepare.py","exec"),ns)
    return ns["prepare"](ident,enabled=True)
def permit():
    p=json.loads(read(HERE/"witness-v341-permit.json",8192))
    if set(p)!={"enabled","start_ms","end_ms","max_post"} or p["enabled"] is not True or type(p["max_post"]) is not int or p["max_post"]!=1 or any(type(p[k]) is not int for k in ("start_ms","end_ms")) or not 0<p["end_ms"]-p["start_ms"]<=3600000 or not p["start_ms"]<=clock()<p["end_ms"]:raise ValueError("permit")
    return p
def once():
    if os.getuid()==0:raise ValueError("not_root")
    os.umask(0o077);directory(BASE);directory(HERE)
    p0=permit()
    if os.path.lexists(HERE/"WITNESS-STOP") or os.path.lexists(ROOT):return {"status":"DISABLED_OR_ALREADY_ATTEMPTED","post":0}
    cert=certs()
    with closing(ro(HERE/"multifactor.sqlite3")) as db:
        row=db.execute("SELECT id,packet FROM v318_observations ORDER BY entry_ms DESC LIMIT 1").fetchone()
    if not row:return {"status":"WAIT_NEW_OBSERVATION","post":0}
    ident,raw=row;p=json.loads(raw)
    if not eligible(p,p0["start_ms"],clock()):return {"status":"WAIT_NEW_OBSERVATION","post":0}
    proof(p,ident,raw);env,q=prepare(ident)
    if permit()!=p0 or os.path.lexists(HERE/"WITNESS-STOP") or not eligible(p,p0["start_ms"],clock()):return {"status":"WAIT_BOUNDARY","post":0}
    # Exclusive persistent directory is the one-shot attempt gate, even after failure.
    ROOT.mkdir(mode=0o700)
    syncdir(HERE)
    for n,b in {**cert,"packet.json":raw,"envelope.json":env,"request.tsq":q,"permit.json":canonical(p0)}.items():write(ROOT/n,b)
    syncdir(ROOT)
    if permit()!=p0 or os.path.lexists(HERE/"WITNESS-STOP") or not eligible(p,p0["start_ms"],clock()):return {"status":"STOP_BEFORE_POST","post":0}
    write(ROOT/"attempt.json",canonical({"attempt_ms":clock(),"endpoint":"https://freetsa.org/tsr","max_post":1}));syncdir(ROOT)
    print("V341_TSA_POST_ATTEMPT=1",flush=True)
    # Direct TLS, no proxy, no redirect or retry. Send only the RFC3161 query.
    conn=http.client.HTTPSConnection("freetsa.org",timeout=10,context=ssl.create_default_context())
    try:
        conn.request("POST","/tsr",body=q,headers={"Content-Type":"application/timestamp-query","Accept":"application/timestamp-reply"})
        response=conn.getresponse();b=response.read(65537);received=clock()
        if response.status!=200 or response.getheader("Content-Type","").split(";")[0].strip().lower()!="application/timestamp-reply" or not 0<len(b)<=65536:raise ValueError("response")
    finally:conn.close()
    write(ROOT/"response.tsr",b);write(ROOT/"receipt.json",canonical({"received_ms":received}));syncdir(ROOT)
    openssl(ROOT,"verify","-CAfile","cacert.pem","-CRLfile","v307-root-ca.pem","-crl_check","-purpose","timestampsign","tsa.crt")
    openssl(ROOT,"ts","-verify","-queryfile","request.tsq","-in","response.tsr","-CAfile","cacert.pem","-untrusted","tsa.crt")
    openssl(ROOT,"ts","-verify","-digest",sha(env),"-in","response.tsr","-CAfile","cacert.pem","-untrusted","tsa.crt")
    token=openssl(ROOT,"ts","-reply","-in","response.tsr","-token_out")
    openssl(ROOT,"cms","-verify","-inform","DER","-nointern","-certfile","tsa.crt","-noverify","-out","/dev/null",stdin=token)
    lo,hi=witness_time(openssl(ROOT,"ts","-reply","-in","response.tsr","-text").decode("ascii"))
    ok=time_ok(p,lo,hi,received)
    status="WITNESSED_BEFORE_ENTRY" if ok else "WITNESS_TIME_NOT_ADMITTED"
    write(ROOT/"result.json",canonical({"status":status,"signed_time_lower_ms":lo,"signed_time_upper_ms":hi,"received_ms":received,"entry_ms":p["entry_ms"],"prospective_admitted":False}));syncdir(ROOT)
    return {"status":status,"post":1,"prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_boundary(self):
        p={"schema":"remura.v318.multifactor.local.v1","prospective_admitted":False,"capture_ms":910000,"frozen_ms":910001,"entry_ms":1800000}
        self.assertTrue(eligible(p,900000,1000000))
        self.assertFalse(eligible(p,910001,1000000))
        self.assertFalse(eligible(p,900000,1755000))
        self.assertTrue(time_ok(p,920000,921000,930000))
        self.assertFalse(time_ok(p,910000,911000,930000))
        self.assertFalse(time_ok(p,1799000,1800000,1800000))
    def test_signed_time(self):
        t=datetime(2026,11,27,12,0,0,tzinfo=timezone.utc)
        n=int(t.timestamp())*1000
        self.assertEqual(witness_time("Time stamp: Nov 27 12:00:00.123 2026 GMT"),(n+123,n+124))
        self.assertEqual(witness_time("Time stamp: Nov 27 12:00:00 2026 GMT"),(n,n+1000))
        with self.assertRaises(ValueError):witness_time("Time stamp: Nov 27 12:00:00 2026 UTC")
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--once"]:
        try:print("V341 WITNESS",json.dumps(once(),sort_keys=True),flush=True)
        except Exception as e:print("V341 WITNESS STOP",type(e).__name__,flush=True);sys.exit(2)
    else:raise SystemExit("--selftest | separately authorized --once")
