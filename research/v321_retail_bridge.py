"""REMURA V32.1: local EURUSD bridge. No network or production writes.
Install only as root-owned code outside the user's writable home.
--stdout: manual preview; --publish: atomic root-owned /run transport.
"""
import os,json,time,hashlib,stat,math,sys,grp,tempfile
from datetime import datetime
SOURCE="/opt/remura/private/myfxbook/data/myfxbook/latest.json"
DIR="/run/remura-v321"
GROUP="ubuntu"
def collect():
    with os.fdopen(os.open(SOURCE,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),"rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError("file")
        raw=f.read(4194305)
    read_ms=time.time_ns()//1000000
    if not 0<len(raw)<=4194304:raise ValueError("size")
    d=json.loads(raw)
    if d["status"]!="ok":raise ValueError("status")
    e=d["symbols"]["EURUSD"]
    t=datetime.fromisoformat(d["updatedAt"].replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone")
    c=int(t.timestamp()*1000)
    l,s=e["lPct"],e["sPct"]
    if not all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=100 for x in (l,s)):raise ValueError("percent")
    if abs(l+s-100)>.2 or not 0<c<=read_ms:raise ValueError("clock")
    return json.dumps({"source":"Myfxbook Community Outlook","symbol":"EURUSD",
        "collection_ms":c,"read_ms":read_ms,"long_pct":l,"short_pct":s,
        "source_sha256":hashlib.sha256(raw).hexdigest()},allow_nan=False).encode()
def publish(data):
    gid=grp.getgrnam(GROUP).gr_gid
    s=os.lstat(DIR)
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=0 or s.st_gid!=gid or stat.S_IMODE(s.st_mode)!=0o750:
        raise ValueError("runtime_directory")
    fd,p=tempfile.mkstemp(prefix=".retail-",dir=DIR)
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchown(f.fileno(),0,gid)
            os.fchmod(f.fileno(),0o640)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(p,DIR+"/retail.json")
    finally:
        if os.path.lexists(p):os.unlink(p)
def main():
    if os.getuid()!=0:raise ValueError("root_helper_only")
    if sys.argv[1:] not in (["--stdout"],["--publish"]):raise ValueError("mode")
    os.umask(0o077)
    try:data=collect()
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError) as e:
        data=b""
        print("V321_BRIDGE_INPUT_UNAVAILABLE "+type(e).__name__,file=sys.stderr)
    if sys.argv[1]=="--stdout":
        sys.stdout.buffer.write(data)
        return 0 if data else 2
    publish(data)
    print("V321_BRIDGE_PUBLISHED" if data else "V321_BRIDGE_EMPTY")
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("V321_BRIDGE_STOP "+type(e).__name__,file=sys.stderr)
        sys.exit(2)
