#!/usr/bin/env python3
# REMURA v0.8.148 LAB — 18/11/2026, sessione successiva alle 09:56 CET
"""Read-only preflight. No service changes, lock acquisition, DB or network.
Not an installer; release authorization remains external.
"""
import argparse,hashlib,io,json,os,stat,subprocess,tarfile
from pathlib import Path
from abc_v165_stage_bundle_v1 import inspect_bundle,rows,PIN
from abc_installed_baseline_readonly_v1 import code_status,blob

BUNDLE="6804531c819ec16af972755b042394ac5c9acee23b7c03f70a09ab765369cfcc"
APP=Path("/opt/remura")
WORK=Path("/var/lib/remura-autoupdate")
UNITS={"remura-private.service":"56bbca6a35c8fc5c0b748ebad97e89cfcc61e0c9",
       "remura-autoupdate.service":"abdbe86a16ab0a806620629b2ede64af14d8bc7d",
       "remura-autoupdate.timer":"dca0376a3651de9b947b9f2903a685f9e6db2827"}
UPDATER="53ca8ec381e30d019f1cc8570e33e0150e6c233e"
MARKERS=("maintenance-v165.inhibit","collector-v165.inhibit")
PROPS=("LoadState","ActiveState","UnitFileState","FragmentPath","DropInPaths","NeedDaemonReload",
       "User","Group","WorkingDirectory","ProtectSystem","NoNewPrivileges","EnvironmentFiles")

def regular_bytes(path,limit):
    p=Path(path)
    if not p.is_absolute() or p.resolve()!=p:raise ValueError("UNSAFE_PATH")
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or not 0<a.st_size<=limit:raise ValueError("UNSAFE_FILE")
        with os.fdopen(os.dup(fd),"rb") as f:b=f.read(limit+1)
        z=os.fstat(fd);q=p.lstat()
        key=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
        if len(b)!=a.st_size or key(a)!=key(z) or key(a)!=key(q):raise ValueError("UNSTABLE_FILE")
        return b,a
    finally:os.close(fd)

def load_manifest(path):
    path=Path(path).absolute()
    raw,_=regular_bytes(path,8*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=BUNDLE:raise ValueError("BUNDLE_PIN")
    report=inspect_bundle(path)
    if report["bundle_sha256"]!=BUNDLE:raise ValueError("BUNDLE_CHANGED")
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as t:
        d=json.load(t.extractfile("MANIFEST.json"))
    return list(rows(d).values())

def load_public_manifest(path):
    raw,_=regular_bytes(Path(path).absolute(),1024*1024)
    return list(rows(json.loads(raw)).values())

def existing_application(root,manifest):
    counts={};findings=[]
    for r in manifest:
        name=r["path"]
        if r["operation"]=="add":
            p=root/name
            try:
                if p.parent.resolve()!=p.parent or not p.parent.is_dir():result="unsafe_parent"
                else:
                    p.lstat();result="unexpected_existing"
            except FileNotFoundError:result="expected_absent"
            except OSError:result="unavailable"
        else:result=code_status(root,name,r["base_git_blob"])
        counts[result]=counts.get(result,0)+1
        if result not in ("exact","stamp_only","expected_absent"):findings.append(name)
    return {"counts":counts,"mismatched_application_paths":findings,
            "baseline_bytes_candidate":not findings and counts.get("exact",0)+counts.get("stamp_only",0)==79 and counts.get("expected_absent")==76,
            "ownership_attested":False}

def properties(unit):
    args=["systemctl","show",unit,"--no-pager"]
    for k in PROPS:args.extend(("-p",k))
    raw=subprocess.check_output(args,stderr=subprocess.DEVNULL,text=True,timeout=10)
    return dict(x.split("=",1) for x in raw.splitlines() if "=" in x)

def unit_report(unit,props):
    exact=False
    try:
        b,s=regular_bytes(Path(props.get("FragmentPath") or "/nonexistent"),128*1024)
        exact=s.st_uid==0 and not s.st_mode&0o022 and blob(b)==UNITS[unit]
    except (OSError,ValueError):pass
    out={"reference_fragment_exact":exact,"loaded":props.get("LoadState")=="loaded",
         "no_dropins_or_pending_reload":props.get("DropInPaths")=="" and props.get("NeedDaemonReload")=="no",
         "active":props.get("ActiveState")=="active"}
    if unit=="remura-private.service":
        out["expected_effective_metadata"]=all(props.get(k)==v for k,v in {
            "User":"remura","Group":"remura","WorkingDirectory":str(APP),
            "ProtectSystem":"strict","NoNewPrivileges":"yes",
            "EnvironmentFiles":str(APP/"private/remura.env")+" (ignore_errors=no)"}.items())
    elif unit=="remura-autoupdate.timer":out["enabled"]=props.get("UnitFileState")=="enabled"
    else:out["expected_effective_metadata"]=props.get("User")=="root" and props.get("ProtectSystem")=="strict" and props.get("NoNewPrivileges")=="yes"
    return out

def work_report(work,uid):
    try:
        if work.resolve()!=work:return {"state":"unsafe","lock_acquired":False}
        s=work.lstat();l=(work/"lock").lstat()
        ok=stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&0o077
        ok=ok and stat.S_ISREG(l.st_mode) and l.st_uid==uid and l.st_nlink==1 and not l.st_mode&0o077
        markers={}
        for n in MARKERS:
            try:(work/n).lstat();markers[n]="present_inhibits"
            except FileNotFoundError:markers[n]="absent"
        return {"state":"metadata_only" if ok else "unsafe","markers":markers,"lock_acquired":False}
    except OSError:return {"state":"unavailable","lock_acquired":False}

def oracle_report(path,manifest_only=False):
    if os.geteuid()!=0:raise ValueError("ROOT_REQUIRED")
    manifest=load_public_manifest(path) if manifest_only else load_manifest(path)
    if APP.resolve()!=APP:raise ValueError("APP_UNSAFE")
    report=existing_application(APP,manifest)
    units={u:unit_report(u,properties(u)) for u in UNITS}
    updater=False
    try:
        b,s=regular_bytes(APP/"deploy/oracle/autoupdate.py",128*1024)
        updater=blob(b)==UPDATER and s.st_uid==0 and not s.st_mode&0o022
    except (OSError,ValueError):pass
    v=os.statvfs(APP)
    return {"schema":"remura.v165.preflight.readonly.v1","application":report,"units":units,
            "updater_exact_and_root_owned":updater,"work":work_report(WORK,0),
            "disk_available_bytes":v.f_bavail*v.f_frsize,"bundle_sha256":None if manifest_only else BUNDLE,
            "manifest_sha256":PIN,"package_bytes_verified_on_target":not manifest_only,
            "release_authorized":False,"installable":False,"coherent_live_snapshot":False,
            "unresolved":["backup_freshness","ownership_and_modes","actual_lock_lease","effective_guard_installation",
                          "shark_custody","external_quotas","signed_release","owner_maintenance_authorization"]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--bundle",type=Path)
    g.add_argument("--manifest",type=Path)
    a=p.parse_args()
    try:print(json.dumps(oracle_report(a.manifest or a.bundle,manifest_only=a.manifest is not None),sort_keys=True))
    except (ValueError,OSError,subprocess.SubprocessError):
        print(json.dumps({"status":"unavailable_or_unsafe","release_authorized":False,"installable":False}))
        return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
