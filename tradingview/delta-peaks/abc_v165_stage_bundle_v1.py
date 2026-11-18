#!/usr/bin/env python3
# REMURA v0.8.159 LAB — 18/11/2026, sessione successiva alle 13:29 CET
"""Build and verify an offline, non-installable pinned ABC application bundle.
No deployment, network, credentials, live timestamp substitution or extraction.
"""
import argparse,hashlib,io,json,os,re,stat,tarfile,tempfile
from pathlib import Path

PIN="73635db92dd9f709ae078119a161ab12b7c9a63ca18782b99e7e1f6357c3c2c1"
SCHEMA="remura.abc.v165.stage.bundle.lab.v1"
LIMIT=8*1024*1024
PATH=re.compile(r"(?:scripts/[A-Za-z_][A-Za-z_0-9]*[.]py|[A-Za-z0-9_-]+[.](?:html|js|css|webp|svg|webmanifest))\Z")

def need(x):
    if not x:raise ValueError("STAGE_BUNDLE_GATE_FAILED")
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":")).encode()
def descriptor(manifest):
    return {"schema":SCHEMA,"manifest_sha256":PIN,
            "application":manifest["application"],
            "deployment_reference":manifest["deployment_reference"],
            "release_authorized":False,"installable":False}
def rows(d):
    need(set(d)=={"schema","manifest_sha256","application","deployment_reference","release_authorized","installable"})
    need(d["schema"]==SCHEMA and d["manifest_sha256"]==PIN
         and d["release_authorized"] is False and d["installable"] is False)
    data={k:d[k] for k in ("application","deployment_reference")}
    need(sha(canonical(data))==PIN)
    a=d["application"]
    need(len(a)==155 and len(d["deployment_reference"])==28)
    names=[r["path"] for r in a]
    need(names==sorted(set(names)) and all(PATH.fullmatch(n) for n in names))
    need(sum(r["bytes"] for r in a)<LIMIT)
    return {r["path"]:r for r in a}
def put(t,n,b):
    h=tarfile.TarInfo(n);h.size=len(b);h.mode=0o644
    h.uid=h.gid=h.mtime=0
    t.addfile(h,io.BytesIO(b))
def inspect_bundle(path):
    path=Path(path)
    s=path.lstat()
    need(stat.S_ISREG(s.st_mode) and 0<s.st_size<=LIMIT)
    # Hash and parse the same bounded in-memory bytes; no extraction or executable code.
    with open(path,"rb") as f:b=f.read(LIMIT+1)
    need(len(b)==s.st_size and len(b)<=LIMIT)
    report, _, _ = inspect_bundle_bytes(b)
    return report

def inspect_bundle_bytes(b):
    """Parse exactly the immutable supplied bytes; never reopen a path."""
    need(type(b) is bytes and 0<len(b)<=LIMIT)
    app={}
    with tarfile.open(fileobj=io.BytesIO(b),mode="r:") as t:
        items=t.getmembers()
        need(len(items)==156 and items[0].name=="MANIFEST.json")
        need(all(m.type==tarfile.REGTYPE and m.mode==0o644 and m.uid==m.gid==m.mtime==0 and not m.pax_headers for m in items))
        raw=t.extractfile(items[0]).read()
        d=json.loads(raw);need(raw==canonical(d))
        expected=rows(d)
        need([m.name for m in items[1:]]==["app/"+n for n in expected])
        for m in items[1:]:
            r=expected[m.name[4:]]
            data=t.extractfile(m).read()
            need(m.size==r["bytes"] and len(data)==r["bytes"] and sha(data)==r["candidate_sha256"])
            app[m.name[4:]]=data
        # Reject appended bytes, noncanonical headers, alternate tar encodings.
        rebuilt=io.BytesIO()
        with tarfile.open(fileobj=rebuilt,mode="w",format=tarfile.USTAR_FORMAT) as out:
            for m in items:put(out,m.name,t.extractfile(m).read())
        need(rebuilt.getvalue()==b)
    return {"schema":SCHEMA,"bundle_sha256":sha(b),"bundle_bytes":len(b),
            "application_paths":155,"deployment_reference_only":28,
            "installable":False,"release_authorized":False},d,app
def build_bundle(path,manifest,app):
    path=Path(path).absolute()
    need(path.parent==path.parent.resolve() and path.parent.is_dir())
    need(not os.path.lexists(path))
    d=descriptor(manifest);expected=rows(d)
    need(set(app)==set(expected))
    for n,r in expected.items():
        b=app[n];need(type(b) is bytes and len(b)==r["bytes"] and sha(b)==r["candidate_sha256"])
    fd,name=tempfile.mkstemp(prefix=".remura-stage-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            with tarfile.open(fileobj=f,mode="w",format=tarfile.USTAR_FORMAT) as t:
                put(t,"MANIFEST.json",canonical(d))
                for n in expected:put(t,"app/"+n,app[n])
            f.flush();os.fsync(f.fileno())
        report=inspect_bundle(name)
        # Atomic no-overwrite publication within one filesystem.
        os.link(name,path)
        dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
        return report
    finally:os.unlink(name)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    x=p.add_mutually_exclusive_group(required=True)
    x.add_argument("--build",type=Path,help="new offline tar; requires pinned reference Git checkouts")
    x.add_argument("--verify",type=Path,help="existing offline tar; no Git checkout required")
    a=p.parse_args()
    if a.build:
        # Reuse exact pinned Git material already validated in ABC CI.
        import abc_v165_repository_manifest_fixture_v1 as f
        from abc_v165_repository_manifest_lab_v1 import build
        f.Tests.setUpClass()
        c=f.Tests
        out=build_bundle(a.build,build(c.base,c.overlay,c.deploy,synthetic=True),{**c.base,**c.overlay})
    else:out=inspect_bundle(a.verify)
    print("REMURA_STAGE_BUNDLE="+json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
