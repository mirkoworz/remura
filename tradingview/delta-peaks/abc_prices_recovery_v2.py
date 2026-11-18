#!/usr/bin/env python3
# REMURA v0.8.150 LAB — 18/11/2026, sessione delle 10:25 CET
"""Future owner-invoked price/COT recovery package. Never scheduled or automatic.
No broker calls, source checkpoint, live restore or deletion.
Owner-only opt-in memory recovery and a local signed receipt.
"""
import argparse,base64,datetime as dt,getpass,hashlib,io,json,os,re,sqlite3,stat,subprocess,tarfile,tempfile,time
from pathlib import Path
SOURCE=Path("/opt/remura/private/remura-prices.sqlite3")
MAX=64*1024*1024
MARGIN=8*1024*1024
SCHEMA="remura.prices.recovery.v2"
NAME="remura-prices.sqlite3"
FPR=re.compile(r"[A-F0-9]{40}\Z")
HEX=re.compile(r"[a-f0-9]{64}\Z")
def need(x):
    if not x:raise ValueError("RECOVERY_GATE_FAILED")
def private_dir(p):
    p=Path(p)
    need(p.is_absolute() and p.resolve()==p)
    s=p.lstat()
    need(stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077)
    return p
def regular(p,limit=MAX):
    p=Path(p)
    need(p.is_absolute() and p.resolve()==p)
    s=p.lstat()
    need(stat.S_ISREG(s.st_mode) and 0<s.st_size<=limit)
    return s
def canon(d):return json.dumps(d,sort_keys=True,separators=(",",":")).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def hash_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def gpg(home,*args,**kw):
    return subprocess.run(["gpg","--no-options","--homedir",str(home),"--batch","--no-tty",
                "--no-auto-key-retrieve","--auto-key-locate","local",*args],
                env={"PATH":os.environ["PATH"],"HOME":str(home),"LANG":"C","LC_ALL":"C"},
                stderr=subprocess.PIPE,timeout=120,check=True,**kw)
def recipient_check(home,primary,sub):
    private_dir(home)
    need(FPR.fullmatch(primary) and FPR.fullmatch(sub) and primary!=sub)
    secret=gpg(home,"--with-colons","--list-secret-keys",stdout=subprocess.PIPE).stdout
    need(not any(l.startswith((b"sec:",b"ssb:")) for l in secret.splitlines()))
    lines=gpg(home,"--with-colons","--list-keys",primary,stdout=subprocess.PIPE).stdout.decode().splitlines()
    parent=None;pending=None;good=False;keys=0
    for line in lines:
        f=line.split(":")
        if f[0] in ("pub","sub"):
            pending=f
            if f[0]=="pub":keys+=1;parent=None
        elif f[0]=="fpr" and pending is not None:
            if pending[0]=="pub":parent=f[9]
            elif parent==primary and f[9]==sub and "e" in pending[11] and pending[1] not in ("r","e","d","i"):
                good=True
            pending=None
    need(keys==1 and good)
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
def tmpfs():
    root=Path("/dev/shm")
    need(root.resolve()==root and root.is_dir())
    lines=Path("/proc/self/mountinfo").read_text().splitlines()
    need(any(x.split(" - ",1)[0].split()[4]=="/dev/shm" and x.split(" - ",1)[1].split()[0]=="tmpfs" for x in lines if " - " in x))
    return root
def disk(p):
    x=os.statvfs(p);return x.f_bavail*x.f_frsize
def schema_summary(db):
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {"prices_present":"prices" in names,"status_present":"status" in names,
            "cot_tables_present":sum(x in names for x in ("cot_reports","cot_first_seen")),
            "research_tables_present":sum(x.startswith("research_") for x in names),
            "known_shark_tables":{n:n in names for n in ("research_cvd_observations","research_cvd_shard_metadata",
                    "research_squalincome_cot_links","research_retail_original_first_seen","research_first_periodic_invocation","research_retail_segment_metadata")}}
def snapshot(source,target):
    regular(source)
    deadline=time.monotonic()+60
    with sqlite3.connect(source.as_uri()+"?mode=ro",uri=True,timeout=5) as a,sqlite3.connect(target,timeout=5) as b:
        a.execute("PRAGMA query_only=ON");a.execute("PRAGMA trusted_schema=OFF")
        # Avoid SQL from inside the backup callback.
        page=a.execute("PRAGMA page_size").fetchone()[0]
        def check(status,remaining,total):need(time.monotonic()<deadline and total*page<=MAX)
        a.backup(b,pages=128,progress=check,sleep=0.05)
        b.execute("PRAGMA journal_mode=DELETE")
        b.execute("PRAGMA trusted_schema=OFF")
        b.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        need(b.execute("PRAGMA quick_check").fetchall()==[("ok",)])
        summary=schema_summary(b)
        need(summary["prices_present"] and summary["status_present"])
    a.close();b.close()
    regular(target)
    need(not any(os.path.lexists(str(target)+s) for s in ("-wal","-shm","-journal")))
    return summary
def make_tar(db,package,generation,summary):
    m={"schema":SCHEMA,"generation":generation,"scope":"prices_and_embedded_cot_only",
       "captured_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"file":NAME,
       "bytes":db.stat().st_size,"sha256":hash_file(db),"sqlite_quick_check":"ok",
       "schema_summary":summary,"restore_policy":"isolated_manual_only"}
    raw=canon(m)
    with tarfile.open(package,"w:gz",compresslevel=6) as t:
        info=tarfile.TarInfo("manifest.json");info.size=len(raw);info.mode=0o600
        t.addfile(info,io.BytesIO(raw));t.add(db,arcname=NAME,recursive=False)
    regular(package,MAX+MARGIN)
    return m
def seal(home,sub,package,out):
    need(not os.path.lexists(out))
    fd,n=tempfile.mkstemp(prefix=".remura-cipher-",dir=out.parent)
    try:
        with os.fdopen(fd,"wb") as f,package.open("rb") as src:
            gpg(home,"--trust-model","always","--cipher-algo","AES256","--compress-algo","none",
                "--force-mdc","--recipient",sub+"!","--encrypt","--output","-",stdin=src,stdout=f)
            f.flush();os.fsync(f.fileno())
        regular(Path(n),MAX+2*MARGIN)
        os.link(n,out);syncdir(out.parent)
    finally:os.unlink(n)
def capture(outdir,home,primary,sub,generation):
    need(type(generation) is int and 6<=generation<=999999)
    outdir=private_dir(outdir);recipient_check(home,primary,sub)
    ram=tmpfs();size=regular(SOURCE).st_size
    # Size is rechecked by the snapshot progress callback. Conservative capacity gate.
    need(disk(ram)>=3*size+MARGIN and disk(outdir)>=MAX+2*MARGIN)
    out=outdir/("prices-%06d.tar.gpg"%generation)
    need(not os.path.lexists(out))
    with tempfile.TemporaryDirectory(prefix="remura-prices-",dir=ram) as d:
        db=Path(d)/NAME;package=Path(d)/"prices.tar.gz"
        summary=snapshot(SOURCE,db)
        m=make_tar(db,package,generation,summary)
        seal(home,sub,package,out)
    return {"status":"CIPHERTEXT_CREATED_PENDING_OWNER_RECOVERY","generation":generation,
            "archive":out.name,"cipher_bytes":out.stat().st_size,"cipher_sha256":hash_file(out),
            "scope":m["scope"],"independent_restore_verified":False,"witness_signed":False}
def recover_memory(image,expected_schema):
    # Independent SQLite connection to authenticated bytes; no plaintext file.
    need(16<=len(image)<=MAX)
    db=sqlite3.connect(":memory:")
    try:
        need(hasattr(db,"deserialize"))
        db.deserialize(image)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        deadline=time.monotonic()+60
        db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        need(db.execute("PRAGMA integrity_check").fetchall()==[("ok",)])
        summary=schema_summary(db)
        need(summary==expected_schema and summary["prices_present"] and summary["status_present"])
    finally:db.close()

RECEIPT_SCHEMA="remura.prices.recovery.receipt.v1"
def receipt_body(result,expected,signer):
    need(result["status"]=="DECRYPTION_AND_MEMBER_HASH_VERIFIED" and result["sqlite_restore_tested"] is True)
    need(HEX.fullmatch(expected) and FPR.fullmatch(signer))
    return {"schema":RECEIPT_SCHEMA,"generation":result["generation"],"cipher_sha256":expected,
            "scope":result["scope"],"sqlite_restore_tested":True,"recovery_method":"sqlite_deserialize_integrity_check",
            "signer":signer,"owner_clock_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "trusted_timestamp":False,"restore_authorized":False}

def verify_signature(home,body,sig,signer):
    private_dir(home)
    need(FPR.fullmatch(signer) and 0<len(sig)<=16384)
    with tempfile.TemporaryDirectory(prefix="remura-receipt-") as d:
        root=Path(d); payload=root/"payload"; signature=root/"sig"
        payload.write_bytes(body);signature.write_bytes(sig)
        r=gpg(home,"--status-fd","2","--verify",str(signature),str(payload),stdout=subprocess.PIPE)
    valid=[line.split()[2].decode() for line in r.stderr.splitlines() if line.startswith(b"[GNUPG:] VALIDSIG ")]
    need(valid==[signer])
    need(not any(line.startswith(tuple(b"[GNUPG:] "+x for x in (b"REVKEYSIG",b"EXPKEYSIG",b"EXPSIG",b"BADSIG",b"ERRSIG"))) for line in r.stderr.splitlines()))

def verify_receipt(path,home,expected,generation,signer):
    regular(path,65536)
    raw=path.read_bytes()
    env=json.loads(raw)
    need(raw==canon(env) and set(env)=={"payload","signature_b64"})
    p=env["payload"]
    need(p["schema"]==RECEIPT_SCHEMA and p["generation"]==generation and p["cipher_sha256"]==expected and HEX.fullmatch(expected))
    need(p["scope"]=="prices_and_embedded_cot_only" and p["signer"]==signer and p["sqlite_restore_tested"] is True)
    need(p["recovery_method"]=="sqlite_deserialize_integrity_check" and p["trusted_timestamp"] is False and p["restore_authorized"] is False)
    verify_signature(home,canon(p),base64.b64decode(env["signature_b64"],validate=True),signer)
    return {"status":"OWNER_RECEIPT_SIGNATURE_VERIFIED","generation":generation,"trusted_timestamp":False,"restore_authorized":False}

def sign_receipt(result,expected,home,outdir,signer):
    outdir=private_dir(outdir);private_dir(home)
    payload=receipt_body(result,expected,signer)
    path=outdir/("prices-%06d.receipt.json"%result["generation"])
    need(not os.path.lexists(path))
    raw=canon(payload)
    with tempfile.TemporaryDirectory(prefix=".remura-receipt-",dir=outdir) as d:
        root=Path(d); p=root/"payload"; p.write_bytes(raw)
        pw=getpass.getpass("Local signing passphrase: ")
        try:r=gpg(home,"--pinentry-mode","loopback","--passphrase-fd","0","--local-user",signer+"!",
                  "--detach-sign","--output","-",str(p),input=(pw+"\n").encode(),stdout=subprocess.PIPE)
        finally:del pw
        verify_signature(home,raw,r.stdout,signer)
        candidate=root/"receipt.json"
        with candidate.open("xb") as f:
            f.write(canon({"payload":payload,"signature_b64":base64.b64encode(r.stdout).decode()}))
            f.flush();os.fsync(f.fileno())
        os.chmod(candidate,0o600)
        verify_receipt(candidate,home,expected,result["generation"],signer)
        os.link(candidate,path);syncdir(outdir)
    return {"status":"OWNER_RECEIPT_SIGNED_LOCAL","generation":result["generation"],"sqlite_restore_tested":True,
            "witness_signed":True,"trusted_timestamp":False,"restore_authorized":False}

def verify_plain(raw,generation,recover=False):
    need(0<len(raw)<=MAX+MARGIN)
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as t:
        ms=t.getmembers()
        need([m.name for m in ms]==["manifest.json",NAME] and all(m.isfile() for m in ms))
        need(0<ms[0].size<=16384 and 0<ms[1].size<=MAX)
        body=t.extractfile(ms[0]).read();m=json.loads(body)
        need(body==canon(m) and m["schema"]==SCHEMA and m["generation"]==generation and m["scope"]=="prices_and_embedded_cot_only")
        need(m["file"]==NAME and m["bytes"]==ms[1].size and HEX.fullmatch(m["sha256"]))
        stream=t.extractfile(ms[1]);h=hashlib.sha256()
        recovered=bytearray() if recover else None
        need(stream.read(16)==b"SQLite format 3\x00")
        h.update(b"SQLite format 3\x00")
        if recovered is not None:recovered.extend(b"SQLite format 3\x00")
        for b in iter(lambda:stream.read(1024*1024),b""):
            h.update(b)
            if recovered is not None:recovered.extend(b)
        need(h.hexdigest()==m["sha256"])
        if recovered is not None:
            need(len(recovered)==m["bytes"])
            recover_memory(bytes(recovered),m["schema_summary"])
    return {"status":"DECRYPTION_AND_MEMBER_HASH_VERIFIED","generation":generation,
            "sqlite_restore_tested":bool(recover),"witness_signed":False,"scope":m["scope"]}
def verify_owner(cipher,home,expected,generation,recover=False):
    regular(cipher,MAX+2*MARGIN);private_dir(home)
    need(HEX.fullmatch(expected) and hash_file(cipher)==expected)
    pw=getpass.getpass("GPG passphrase: ")
    try:r=gpg(home,"--status-fd","2","--pinentry-mode","loopback","--passphrase-fd","0",
              "--max-output",str(MAX+MARGIN),"--decrypt","--output","-",str(cipher),
              input=(pw+"\n").encode(),stdout=subprocess.PIPE)
    finally:del pw
    need(b"[GNUPG:] DECRYPTION_OKAY" in r.stderr and b"[GNUPG:] GOODMDC" in r.stderr)
    need(hash_file(cipher)==expected)
    return verify_plain(r.stdout,generation,recover=recover)
def inspect_closed(path):
    regular(path)
    need(not any(os.path.lexists(str(path)+s) for s in ("-wal","-shm","-journal")))
    before=hash_file(path)
    with sqlite3.connect(path.as_uri()+"?mode=ro&immutable=1",uri=True) as db:
        db.execute("PRAGMA trusted_schema=OFF");db.execute("PRAGMA query_only=ON")
        summary=schema_summary(db)
    db.close()
    need(hash_file(path)==before)
    return {"status":"CLOSED_COPY_SCHEMA_ONLY","result":summary,"absence_elsewhere_proven":False}
def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="cmd",required=True)
    c=s.add_parser("capture");c.add_argument("--outdir",type=Path,required=True);c.add_argument("--keyring",type=Path,required=True)
    c.add_argument("--primary",required=True);c.add_argument("--subkey",required=True);c.add_argument("--generation",type=int,required=True)
    c.add_argument("--confirm-future-backup",action="store_true",required=True)
    v=s.add_parser("verify");v.add_argument("--cipher",type=Path,required=True);v.add_argument("--keyring",type=Path,required=True)
    v.add_argument("--sha256",required=True);v.add_argument("--generation",type=int,required=True)
    v.add_argument("--recover-memory",action="store_true");v.add_argument("--receipt-dir",type=Path);v.add_argument("--signer")
    q=s.add_parser("verify-receipt");q.add_argument("--receipt",type=Path,required=True);q.add_argument("--keyring",type=Path,required=True)
    q.add_argument("--sha256",required=True);q.add_argument("--generation",type=int,required=True);q.add_argument("--signer",required=True)
    i=s.add_parser("inspect-closed");i.add_argument("--db",type=Path,required=True);i.add_argument("--confirm-not-live",action="store_true",required=True)
    a=p.parse_args()
    try:
        if a.cmd=="capture":r=capture(a.outdir,a.keyring,a.primary,a.subkey,a.generation)
        elif a.cmd=="verify":
            need(bool(a.receipt_dir)==bool(a.signer) and (not a.receipt_dir or a.recover_memory))
            r=verify_owner(a.cipher,a.keyring,a.sha256,a.generation,a.recover_memory)
            if a.receipt_dir:r=sign_receipt(r,a.sha256,a.keyring,a.receipt_dir,a.signer)
        elif a.cmd=="verify-receipt":r=verify_receipt(a.receipt,a.keyring,a.sha256,a.generation,a.signer)
        else:r=inspect_closed(a.db)
        print(json.dumps(r,sort_keys=True))
    except (ValueError,OSError,sqlite3.Error,subprocess.SubprocessError,tarfile.TarError,KeyError,TypeError):
        print('{"status":"STOP_UNSAFE_OR_INCOMPLETE","restore_authorized":false}')
        return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
