#!/usr/bin/env python3
"""REMURA v1.84 OWNER activation candidate. Default: read-only preflight.
Never changes provider config, credentials, D1, Access, or database schema.
No provider quota is inferred. Activation requires separately established gate.
"""
import argparse, hashlib, http.client, json, os, stat, subprocess, tempfile, time
from pathlib import Path

SHA = "448f12c219759286976d40478b88c5f75588d82a"
ROOT = Path("/opt/remura")
BASE = ROOT/"local"/"remura-ui"
RELEASE = BASE/"releases"/SHA
PENDING = BASE/"pending"/SHA
SCRIPTS = ROOT/"scripts"
SERVER = SCRIPTS/"private_server.py"
ADAPTER = SCRIPTS/"owner_static_resolver.py"
OLD = "0853194762f3f0340451a69c9ed8b4e0261db42d"
NEW = "a2918130c5bfc688cb875e5d25e2998f43e40be7"
MOD = "f62155baebf226da116ffd4947a943fcbf5a6502"
MANIFEST = "eef3a6777f81ae2714059cdfe77f3e3fb653b189"
SERVICE = "remura-private.service"

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def digest(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def verified(p, expected):
    require(p.is_file() and not p.is_symlink(), "not regular file: "+p.name)
    b = p.read_bytes()
    require(digest(b)==expected, "digest mismatch: "+p.name)
    return b

def command(*args):
    return subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=60)

def state(unit):
    return subprocess.run(["systemctl","is-active",unit],capture_output=True,
                          text=True,timeout=10).stdout.strip()

def safe_root_tree(p):
    s=p.lstat()
    require(stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode & 0o022,
            "directory not root-controlled: "+str(p))

def local_get(path):
    c=http.client.HTTPConnection("127.0.0.1",8765,timeout=4)
    try:
        c.request("GET",path)
        r=c.getresponse()
        return r.status,r.getheader("Content-Type",""),r.getheader("Cache-Control",""),r.read(2_000_001)
    finally:
        c.close()

def health():
    status,_,_,body=local_get("/private-api/health")
    require(status==200 and json.loads(body).get("name")=="REMURA Private","health failed")

def readiness(new):
    last=None
    for _ in range(12):
        try:
            require(state(SERVICE)=="active","service not active")
            health()
            if new:
                for path in ("index.html","nav.js","sw.js","cot-archive-entry.mjs"):
                    status,mime,cache,b=local_get("/"+path)
                    require(status==200 and b==(RELEASE/path).read_bytes(),"asset mismatch: "+path)
                    if path.endswith(".mjs"):
                        require("javascript" in mime.lower(),"module MIME")
                    if path=="sw.js":
                        require("no-store" in cache.lower(),"SW cache")
            return
        except Exception as e:
            last=e
            time.sleep(1)
    raise RuntimeError("local readiness failed") from last

def preflight(manifest):
    require(os.geteuid()==0,"root required")
    require(state(SERVICE)=="active","service not active")
    require(state("remura-autoupdate.timer")=="inactive","autoupdate not inactive")
    for p in (ROOT/"local",BASE,BASE/"releases",BASE/"pending",RELEASE,PENDING):
        safe_root_tree(p)
    require(not os.path.lexists(BASE/"active"),"active pointer exists")
    require(not os.path.lexists(ADAPTER),"adapter already exists")
    require(not os.path.lexists(PENDING/"rollback"),"rollback directory already exists")
    old=verified(SERVER,OLD)
    new=verified(PENDING/"private_server.py",NEW)
    mod=verified(PENDING/"owner_static_resolver.py",MOD)
    m=json.loads(verified(manifest,MANIFEST))
    require(m["activationAuthorized"] is False and m["originalServerBlob"]==OLD,"manifest mismatch")
    files=m["files"]
    names={f["path"] for f in files}
    require(len(files)==len(names)==79,"inventory count")
    require({p.relative_to(RELEASE).as_posix() for p in RELEASE.rglob("*") if p.is_file()}==names,"inventory differs")
    for p in RELEASE.rglob("*"):
        s=p.lstat()
        require(s.st_uid==0 and not s.st_mode & 0o022 and not p.is_symlink(),"unsafe stage entry")
    for f in files:
        p=RELEASE/f["path"]
        require(p.resolve()==p and p.resolve().is_relative_to(RELEASE),"unsafe path")
        b=verified(p,f["gitBlob"])
        require(len(b)==f["bytes"],"size mismatch")
    compile(new,"private_server.py","exec")
    compile(mod,"owner_static_resolver.py","exec")
    for path in ("index.html","sw.js","cot-archive-entry.mjs"):
        command("runuser","-u","remura","--","test","-r",str(RELEASE/path))
    health()
    print("PREFLIGHT OK — no changes, no provider calls issued by this script")
    return old,new,mod

def atomic_write(path,b,mode,uid,gid):
    fd,temp=tempfile.mkstemp(prefix=".remura-v184-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(b)
            f.flush()
            os.fsync(f.fileno())
        os.chown(temp,uid,gid)
        os.chmod(temp,mode)
        os.replace(temp,path)
    finally:
        if os.path.lexists(temp):
            os.unlink(temp)

def activate(old,new,mod):
    original=SERVER.stat()
    mode=stat.S_IMODE(original.st_mode)
    backup=PENDING/"rollback"
    backup.mkdir(mode=0o700)
    atomic_write(backup/"private_server.py",old,0o600,0,0)
    require(verified(backup/"private_server.py",OLD)==old,"backup mismatch")
    attempted=False
    pointer=False
    module=False
    changed=False
    try:
        atomic_write(ADAPTER,mod,0o644,0,0)
        module=True
        atomic_write(SERVER,new,mode,original.st_uid,original.st_gid)
        changed=True
        os.symlink(RELEASE,BASE/"active",target_is_directory=True)
        pointer=True
        attempted=True
        command("systemctl","restart",SERVICE)
        readiness(True)
    except (Exception,KeyboardInterrupt):
        if pointer:
            (BASE/"active").unlink()
        if changed:
            atomic_write(SERVER,verified(backup/"private_server.py",OLD),mode,original.st_uid,original.st_gid)
        if module:
            ADAPTER.unlink()
        if attempted:
            command("systemctl","restart",SERVICE)
            readiness(False)
        print("ROLLBACK: old code restored; health OK if restarted")
        raise
    print("V184 OWNER ACTIVE — local health and static asset checks OK")
    print("Browser, actual source freshness, access controls and collaborators are separate gates")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--activate",action="store_true")
    p.add_argument("--free-gate-confirmed",action="store_true")
    a=p.parse_args()
    if a.activate and not a.free_gate_confirmed:
        p.error("activation blocked: external free-plan gate not confirmed")
    old,new,mod=preflight(a.manifest)
    if a.activate:
        activate(old,new,mod)
