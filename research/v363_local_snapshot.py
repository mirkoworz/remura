"""REMURA V36.3 — bounded local recovery snapshot, 27/11/2026.
Manual only. No network, no rotation, no source writes or deletion.
Each SQLite image is consistent individually, not a cross-database transaction.
"""
import os,sys,stat,time,json,sqlite3,hashlib,shutil,re,unittest,tempfile
from pathlib import Path
from contextlib import closing
BASE=Path.home()/".remura-v296"
MIB=2**20
CAP=1024*MIB
DBS={"tv-custody.sqlite3":256,"v312/science-tv.sqlite3":256,
     "v318/multifactor.sqlite3":128,"v318/radar-v331.sqlite3":32}
AUX={"v318/radar-v331-rules":7*MIB,"v318/witness-v341":8*MIB}
WITNESS={"cacert.pem","tsa.crt","v307-root-ca.pem","packet.json","envelope.json",
         "request.tsq","permit.json","attempt.json","response.tsr","receipt.json","result.json"}
RULES={"v331_radar_ledger.py","v330_radar.py","v313_intelligence.py",
       "v311_science.py","v310_multifeed.py","v294_footprint_cvd.py","pins.json"}
def clock():return time.time_ns()//1000000
def private(p,kind,mode):
    s=p.lstat()
    if not kind(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=mode:
        raise ValueError("private_path")
    return s
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(MIB),b""):h.update(b)
    return h.hexdigest()
def write(p,b):
    with p.open("xb") as f:
        f.write(b);f.flush();os.fsync(f.fileno())
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def backup_db(src,dst,cap,deadline):
    private(src,stat.S_ISREG,0o600)
    if src.stat().st_size>cap:raise ValueError("source_capacity")
    start=clock()
    fd=os.open(dst,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
    with closing(sqlite3.connect(src.as_uri()+"?mode=ro",uri=True,timeout=2)) as a, closing(sqlite3.connect(dst,timeout=2)) as b:
        a.execute("PRAGMA query_only=ON")
        ps=a.execute("PRAGMA page_size").fetchone()[0]
        def progress(status,remaining,total):
            if time.monotonic()>deadline or total*ps>cap:raise ValueError("backup_bound")
        a.backup(b,pages=128,progress=progress,sleep=.1)
        b.execute("PRAGMA query_only=ON")
        if b.execute("PRAGMA integrity_check").fetchall()!=[("ok",)]:raise ValueError("integrity")
    if dst.stat().st_size>cap:raise ValueError("snapshot_capacity")
    with dst.open("rb") as f:os.fsync(f.fileno())
    return {"bytes":dst.stat().st_size,"sha256":digest(dst),"start_ms":start,"end_ms":clock(),"integrity_check":"ok"}
def copy_private(src,dst,cap,expected=None):
    s=private(src,stat.S_ISREG,0o600)
    if not 0<s.st_size<=cap:raise ValueError("aux_capacity")
    with src.open("rb") as f:raw=f.read(cap+1)
    if len(raw)!=s.st_size or src.stat().st_mtime_ns!=s.st_mtime_ns:raise ValueError("aux_changed")
    h=hashlib.sha256(raw).hexdigest()
    if expected is not None and h!=expected:raise ValueError("evidence_hash")
    write(dst,raw)
    return {"bytes":len(raw),"sha256":h}
def snapshot():
    if os.getuid()==0:raise ValueError("not_root")
    os.umask(0o077)
    for p in (BASE,BASE/"v312",BASE/"v318"):private(p,stat.S_ISDIR,0o700)
    if shutil.disk_usage(BASE).free<2*1024*MIB:raise ValueError("disk")
    root=BASE/"v363-snapshot-20261127"
    root.mkdir(mode=0o700);syncdir(BASE)
    manifest={"schema":"remura.v363.local.snapshot.v1","start_ms":clock(),"cross_db_atomic":False,"files":{}}
    deadline=time.monotonic()+90
    for rel,cap in DBS.items():
        dst=root/rel;dst.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        manifest["files"][rel]=backup_db(BASE/rel,dst,cap*MIB,deadline)
    # Copy immutable content-addressed proofs after the database snapshots.
    rel="v318/evidence-v324";src=BASE/rel;private(src,stat.S_ISDIR,0o700)
    (root/rel).mkdir(mode=0o700)
    total=0
    for p in sorted(src.iterdir()):
        if p.name.startswith(".stage-"):continue
        if not re.fullmatch("[a-f0-9]{64}",p.name):raise ValueError("evidence_name")
        item=copy_private(p,root/rel/p.name,min(MIB,16*MIB-total),p.name)
        total+=item["bytes"];manifest["files"][rel+"/"+p.name]=item
    for rel,cap in AUX.items():
        src=BASE/rel;private(src,stat.S_ISDIR,0o700);(root/rel).mkdir(mode=0o700)
        names=RULES if rel.endswith("rules") else WITNESS
        if {p.name for p in src.iterdir()}!=names:raise ValueError("aux_scope")
        total=0
        for n in sorted(names):
            item=copy_private(src/n,root/rel/n,min(MIB,cap-total))
            total+=item["bytes"];manifest["files"][rel+"/"+n]=item
    # Verify multifactor COT and rule dependencies against copied evidence.
    evidence=root/"v318/evidence-v324"
    with closing(sqlite3.connect((root/"v318/multifactor.sqlite3").as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        for ident,raw in db.execute("SELECT id,packet FROM v318_observations"):
            if hashlib.sha256(raw).hexdigest()!=ident:raise ValueError("observation_digest")
            e=json.loads(raw)["evidence"]
            for h in (e["cot_sha256"],e["rules_sha256"]):
                if not re.fullmatch("[a-f0-9]{64}",h) or not (evidence/h).is_file() or digest(evidence/h)!=h:raise ValueError("missing_evidence")
            for h in json.loads((evidence/e["rules_sha256"]).read_bytes()).values():
                if not re.fullmatch("[a-f0-9]{64}",h) or not (evidence/h).is_file() or digest(evidence/h)!=h:raise ValueError("missing_rule")
    rules=root/"v318/radar-v331-rules"
    for n,h in json.loads((rules/"pins.json").read_bytes()).items():
        if n+".py" not in RULES or digest(rules/(n+".py"))!=h:raise ValueError("radar_rule")
    total=sum(v["bytes"] for v in manifest["files"].values())
    if total>CAP-2*MIB:raise ValueError("total_capacity")
    for rel,item in manifest["files"].items():
        if digest(root/rel)!=item["sha256"]:raise ValueError("snapshot_digest")
    manifest.update(end_ms=clock(),bytes=total,complete=True)
    for p in sorted({root/Path(n).parent for n in manifest["files"]},key=lambda p:len(p.parts),reverse=True):syncdir(p)
    syncdir(root/"v318");syncdir(root/"v312")
    raw=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
    if len(raw)>MIB:raise ValueError("manifest_size")
    write(root/"manifest.json",raw);syncdir(root)
    write(root/"COMPLETE",(hashlib.sha256(raw).hexdigest()+"\n").encode());syncdir(root)
    return {"status":"LOCAL_SNAPSHOT_COMPLETE","bytes":total,"databases":len(DBS),"files":len(manifest["files"]),"cross_db_atomic":False}
class Tests(unittest.TestCase):
    def test_sqlite_backup(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a.db";b=Path(d)/"b.db"
            with closing(sqlite3.connect(a)) as db:
                db.execute("CREATE TABLE t(x)");db.execute("INSERT INTO t VALUES(1)");db.commit()
            a.chmod(0o600);old=digest(a)
            r=backup_db(a,b,MIB,time.monotonic()+5)
            self.assertEqual(r["integrity_check"],"ok")
            self.assertEqual(digest(a),old)
            with closing(sqlite3.connect(b)) as db:self.assertEqual(db.execute("SELECT x FROM t").fetchone(),(1,))
    def test_proof(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a";b=Path(d)/"b"
            a.write_bytes(b"evidence");a.chmod(0o600)
            self.assertEqual(copy_private(a,b,100,digest(a))["sha256"],digest(b))
            with self.assertRaises(ValueError):copy_private(a,Path(d)/"c",100,"0"*64)
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:
        os.umask(0o077);unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--snapshot"]:
        try:print("V363 SNAPSHOT",json.dumps(snapshot(),sort_keys=True))
        except Exception as e:print("V363 SNAPSHOT STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("--selftest | separately authorized --snapshot")
