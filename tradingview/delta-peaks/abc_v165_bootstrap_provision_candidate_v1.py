# REMURA v0.8.165 LAB — 18/11/2026, sessione successiva alle 15:29 CET
"""Code-only bootstrap provision candidate.
Never executes embedded sources, changes systemd, reads private data or installs v1.65.
Root use requires separate owner authorization and independent verifier provenance.
No network. An interrupted publication is deliberately retained and never overwritten.
"""
import hashlib
import os
import stat
import sys

PINS = {
    "abc_v165_start_guard_v1.py": (2607, "ce2652f6b7c118cdf1e83f714b58b975071d5991dc897f3d4afa3131bfcd107c"),
    "abc_v165_locked_snapshot_v1.py": (3809, "e11e7297c7953faf90887ee72b5eecbf43fc5a240304558887f0f976ae23ebc3"),
    "abc_v165_stage_bundle_v1.py": (5118, "d29206be079b5ca80202254b04141ef16bfb94a006696e50ac92622d4b5286ab"),
    "abc_v165_locked_bundle_parser_v1.py": (1775, "eafb18d3ecc719b4b8a79c481482ade98c8f35bd2cb3f84d8f8fab26ff792f0c"),
}
SOURCES = {
    "abc_v165_start_guard_v1.py": "#!/usr/bin/env python3\n# REMURA v0.8.153 LAB — 18/11/2026, sessione successiva alle 11:13 CET\n\"\"\"Candidate startup condition; no installation.\nExit 0 permits start, 1 inhibits, 255 unsafe/error. No writes, DB or network.\nThe executable AND its ancestors must be independently secured before invoking\nthis root-side helper. This script cannot attest its own pre-execution trust.\n\"\"\"\nimport os,stat,sys\nfrom pathlib import Path\nWORK=Path(\"/var/lib/remura-autoupdate\")\nMARKERS={\"updater\":\"maintenance-v165.inhibit\",\"collector\":\"collector-v165.inhibit\"}\nFLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC\ndef trusted_dir(fd,uid,private=False):\n    s=os.fstat(fd)\n    return stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&(0o077 if private else 0o022)\ndef open_chain(anchor,parts,uid):\n    \"\"\"Duplicate anchor, check every directory from a trusted fd; reject traversal.\"\"\"\n    fd=os.dup(anchor)\n    try:\n        if not trusted_dir(fd,uid):raise ValueError(\"UNTRUSTED_ANCESTOR\")\n        for name in parts:\n            if type(name) is not str or name in (\"\",\".\",\"..\") or \"/\" in name:\n                raise ValueError(\"UNTRUSTED_PATH_COMPONENT\")\n            child=os.open(name,FLAGS,dir_fd=fd)\n            os.close(fd);fd=child\n            if not trusted_dir(fd,uid):raise ValueError(\"UNTRUSTED_ANCESTOR\")\n        return fd\n    except BaseException:\n        os.close(fd);raise\ndef evaluate_fd(fd,role,uid):\n    if role not in MARKERS or not trusted_dir(fd,uid,private=True):return 255\n    try:\n        # Even dangling symlinks, directories and invalid marker objects inhibit.\n        os.stat(MARKERS[role],dir_fd=fd,follow_symlinks=False)\n    except FileNotFoundError:return 0\n    return 1\ndef evaluate(work,role,uid):\n    # Disposable LAB fixture helper; production entrypoint uses anchored check.\n    fd=None\n    try:\n        fd=os.open(Path(work),FLAGS)\n        return evaluate_fd(fd,role,uid)\n    except (OSError,ValueError,TypeError):return 255\n    finally:\n        if fd is not None:os.close(fd)\ndef evaluate_anchored(work,role,uid):\n    root=None;fd=None\n    try:\n        p=Path(work)\n        if not p.is_absolute() or p.anchor!=\"/\" or not p.parts[1:]:return 255\n        root=os.open(\"/\",FLAGS)\n        fd=open_chain(root,p.parts[1:],uid)\n        return evaluate_fd(fd,role,uid)\n    except (OSError,ValueError,TypeError):return 255\n    finally:\n        if fd is not None:os.close(fd)\n        if root is not None:os.close(root)\ndef main():\n    if os.geteuid()!=0 or len(sys.argv)!=2:return 255\n    return evaluate_anchored(WORK,sys.argv[1],0)\nif __name__==\"__main__\":sys.exit(main())\n",
    "abc_v165_locked_snapshot_v1.py": "\"\"\"REMURA v0.8.158 LAB — 18/11/2026, 13:29 CET.\nDescriptor-bound candidate snapshot under the historical maintenance lock.\nNo CLI, installation, writes, signature acceptance, or service actions.\nCaller must independently establish executable/import and anchor trust.\n\"\"\"\nimport fcntl\nimport hashlib\nimport os\nimport stat\nfrom contextlib import contextmanager\nfrom abc_v165_start_guard_v1 import open_chain, trusted_dir\n\nBUNDLE_BYTES = 1771520\nBUNDLE_SHA256 = \"6804531c819ec16af972755b042394ac5c9acee23b7c03f70a09ab765369cfcc\"\nMARKER = \"maintenance-v165.inhibit\"\nFLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC\n\n\ndef require(ok):\n    if not ok:\n        raise ValueError(\"LOCKED_SNAPSHOT_GATE\")\n\n\ndef identity(s):\n    return s.st_dev, s.st_ino\n\n\ndef fingerprint(s):\n    return identity(s), s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_uid, s.st_nlink\n\n\ndef private_file(s, uid):\n    return (stat.S_ISREG(s.st_mode) and s.st_uid == uid\n            and not s.st_mode & 0o077 and s.st_nlink == 1)\n\n\ndef check_entry(directory, name, fd, uid):\n    s = os.fstat(fd)\n    require(private_file(s, uid))\n    require(fingerprint(s) == fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)))\n    return s\n\n\ndef read_exact(directory, name, uid, length, digest):\n    require(type(length) is int and 0 < length <= 8 * 1024 * 1024)\n    require(name not in (\"\", \".\", \"..\") and \"/\" not in name)\n    fd = os.open(name, FLAGS, dir_fd=directory)\n    try:\n        s = check_entry(directory, name, fd, uid)\n        require(s.st_size == length)\n        with os.fdopen(os.dup(fd), \"rb\") as stream:\n            data = stream.read(length + 1)\n        require(len(data) == length)\n        require(fingerprint(s) == fingerprint(check_entry(directory, name, fd, uid)))\n        require(hashlib.sha256(data).hexdigest() == digest)\n        return data\n    finally:\n        os.close(fd)\n\n\n@contextmanager\ndef _locked_snapshot(anchor, work_parts, stage_parts, uid, length, digest):\n    # Existing lock only: never recreate a missing lock or truncate it.\n    work = open_chain(anchor, work_parts, uid)\n    try:\n        require(trusted_dir(work, uid, private=True))\n        fd = os.open(\"lock\", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=work)\n        try:\n            original = check_entry(work, \"lock\", fd, uid)\n            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n            require(identity(original) == identity(check_entry(work, \"lock\", fd, uid)))\n            marker = os.stat(MARKER, dir_fd=work, follow_symlinks=False)\n            require(private_file(marker, uid))\n            stage = open_chain(anchor, stage_parts, uid)\n            try:\n                require(trusted_dir(stage, uid, private=True))\n                require(identity(os.fstat(stage)) != identity(os.fstat(work)))\n                data = read_exact(stage, \"remura-v165-candidate.tar\", uid, length, digest)\n                # Recheck the named lock and durable inhibit before exposing bytes.\n                require(identity(original) == identity(check_entry(work, \"lock\", fd, uid)))\n                require(fingerprint(marker) == fingerprint(os.stat(MARKER, dir_fd=work, follow_symlinks=False)))\n                yield data\n            finally:\n                os.close(stage)\n        finally:\n            os.close(fd)\n    finally:\n        os.close(work)\n\n\n@contextmanager\ndef locked_candidate_bytes(anchor, work_parts, stage_parts, uid):\n    \"\"\"Yield only the pinned immutable bytes, with the cooperative lock held.\n    Not authorization. No root bootstrap, coherent live snapshot, journal\n    authentication, or signature verification is inferred from this operation.\n    \"\"\"\n    with _locked_snapshot(anchor, work_parts, stage_parts, uid, BUNDLE_BYTES, BUNDLE_SHA256) as data:\n        yield data\n",
    "abc_v165_stage_bundle_v1.py": "#!/usr/bin/env python3\n# REMURA v0.8.144 LAB — 18/11/2026, sessione successiva alle 09:41 CET\n\"\"\"Build and verify an offline, non-installable pinned ABC application bundle.\nNo deployment, network, credentials, live timestamp substitution or extraction.\n\"\"\"\nimport argparse,hashlib,io,json,os,re,stat,tarfile,tempfile\nfrom pathlib import Path\n\nPIN=\"73635db92dd9f709ae078119a161ab12b7c9a63ca18782b99e7e1f6357c3c2c1\"\nSCHEMA=\"remura.abc.v165.stage.bundle.lab.v1\"\nLIMIT=8*1024*1024\nPATH=re.compile(r\"(?:scripts/[A-Za-z_][A-Za-z_0-9]*[.]py|[A-Za-z0-9_-]+[.](?:html|js|css|webp|svg|webmanifest))\\Z\")\n\ndef need(x):\n    if not x:raise ValueError(\"STAGE_BUNDLE_GATE_FAILED\")\ndef sha(b):return hashlib.sha256(b).hexdigest()\ndef canonical(x):return json.dumps(x,sort_keys=True,separators=(\",\",\":\")).encode()\ndef descriptor(manifest):\n    return {\"schema\":SCHEMA,\"manifest_sha256\":PIN,\n            \"application\":manifest[\"application\"],\n            \"deployment_reference\":manifest[\"deployment_reference\"],\n            \"release_authorized\":False,\"installable\":False}\ndef rows(d):\n    need(set(d)=={\"schema\",\"manifest_sha256\",\"application\",\"deployment_reference\",\"release_authorized\",\"installable\"})\n    need(d[\"schema\"]==SCHEMA and d[\"manifest_sha256\"]==PIN\n         and d[\"release_authorized\"] is False and d[\"installable\"] is False)\n    data={k:d[k] for k in (\"application\",\"deployment_reference\")}\n    need(sha(canonical(data))==PIN)\n    a=d[\"application\"]\n    need(len(a)==155 and len(d[\"deployment_reference\"])==28)\n    names=[r[\"path\"] for r in a]\n    need(names==sorted(set(names)) and all(PATH.fullmatch(n) for n in names))\n    need(sum(r[\"bytes\"] for r in a)<LIMIT)\n    return {r[\"path\"]:r for r in a}\ndef put(t,n,b):\n    h=tarfile.TarInfo(n);h.size=len(b);h.mode=0o644\n    h.uid=h.gid=h.mtime=0\n    t.addfile(h,io.BytesIO(b))\ndef inspect_bundle(path):\n    path=Path(path)\n    s=path.lstat()\n    need(stat.S_ISREG(s.st_mode) and 0<s.st_size<=LIMIT)\n    # Hash and parse the same bounded in-memory bytes; no extraction or executable code.\n    with open(path,\"rb\") as f:b=f.read(LIMIT+1)\n    need(len(b)==s.st_size and len(b)<=LIMIT)\n    with tarfile.open(fileobj=io.BytesIO(b),mode=\"r:\") as t:\n        items=t.getmembers()\n        need(len(items)==156 and items[0].name==\"MANIFEST.json\")\n        need(all(m.type==tarfile.REGTYPE and m.mode==0o644 and m.uid==m.gid==m.mtime==0 and not m.pax_headers for m in items))\n        raw=t.extractfile(items[0]).read()\n        d=json.loads(raw);need(raw==canonical(d))\n        expected=rows(d)\n        need([m.name for m in items[1:]]==[\"app/\"+n for n in expected])\n        for m in items[1:]:\n            r=expected[m.name[4:]]\n            need(m.size==r[\"bytes\"] and sha(t.extractfile(m).read())==r[\"candidate_sha256\"])\n        # Reject appended bytes, noncanonical headers, alternate tar encodings.\n        rebuilt=io.BytesIO()\n        with tarfile.open(fileobj=rebuilt,mode=\"w\",format=tarfile.USTAR_FORMAT) as out:\n            for m in items:put(out,m.name,t.extractfile(m).read())\n        need(rebuilt.getvalue()==b)\n    return {\"schema\":SCHEMA,\"bundle_sha256\":sha(b),\"bundle_bytes\":len(b),\n            \"application_paths\":155,\"deployment_reference_only\":28,\n            \"installable\":False,\"release_authorized\":False}\ndef build_bundle(path,manifest,app):\n    path=Path(path).absolute()\n    need(path.parent==path.parent.resolve() and path.parent.is_dir())\n    need(not os.path.lexists(path))\n    d=descriptor(manifest);expected=rows(d)\n    need(set(app)==set(expected))\n    for n,r in expected.items():\n        b=app[n];need(type(b) is bytes and len(b)==r[\"bytes\"] and sha(b)==r[\"candidate_sha256\"])\n    fd,name=tempfile.mkstemp(prefix=\".remura-stage-\",dir=path.parent)\n    try:\n        with os.fdopen(fd,\"wb\") as f:\n            with tarfile.open(fileobj=f,mode=\"w\",format=tarfile.USTAR_FORMAT) as t:\n                put(t,\"MANIFEST.json\",canonical(d))\n                for n in expected:put(t,\"app/\"+n,app[n])\n            f.flush();os.fsync(f.fileno())\n        report=inspect_bundle(name)\n        # Atomic no-overwrite publication within one filesystem.\n        os.link(name,path)\n        dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)\n        try:os.fsync(dfd)\n        finally:os.close(dfd)\n        return report\n    finally:os.unlink(name)\ndef main():\n    p=argparse.ArgumentParser(description=__doc__)\n    x=p.add_mutually_exclusive_group(required=True)\n    x.add_argument(\"--build\",type=Path,help=\"new offline tar; requires pinned reference Git checkouts\")\n    x.add_argument(\"--verify\",type=Path,help=\"existing offline tar; no Git checkout required\")\n    a=p.parse_args()\n    if a.build:\n        # Reuse exact pinned Git material already validated in ABC CI.\n        import abc_v165_repository_manifest_fixture_v1 as f\n        from abc_v165_repository_manifest_lab_v1 import build\n        f.Tests.setUpClass()\n        c=f.Tests\n        out=build_bundle(a.build,build(c.base,c.overlay,c.deploy,synthetic=True),{**c.base,**c.overlay})\n    else:out=inspect_bundle(a.verify)\n    print(\"REMURA_STAGE_BUNDLE=\"+json.dumps(out,sort_keys=True))\nif __name__==\"__main__\":main()\n",
    "abc_v165_locked_bundle_parser_v1.py": "# REMURA v0.8.160 LAB — 18/11/2026, sessione successiva alle 13:29 CET\n\"\"\"Independent byte-only adapter, retaining exact historic portable source.\nNo path access, install or privileged execution.\n\"\"\"\nimport io,json,tarfile\nfrom abc_v165_stage_bundle_v1 import SCHEMA,need,sha,canonical,rows,put\nfrom abc_v165_locked_snapshot_v1 import BUNDLE_BYTES,BUNDLE_SHA256\n\ndef inspect_bundle_bytes(b):\n    \"\"\"Parse exactly the immutable supplied bytes; never reopen a path.\"\"\"\n    need(type(b) is bytes and len(b)==BUNDLE_BYTES and sha(b)==BUNDLE_SHA256)\n    app={}\n    with tarfile.open(fileobj=io.BytesIO(b),mode=\"r:\") as t:\n        items=t.getmembers()\n        need(len(items)==156 and items[0].name==\"MANIFEST.json\")\n        need(all(m.type==tarfile.REGTYPE and m.mode==0o644 and m.uid==m.gid==m.mtime==0 and not m.pax_headers for m in items))\n        raw=t.extractfile(items[0]).read()\n        d=json.loads(raw);need(raw==canonical(d))\n        expected=rows(d)\n        need([m.name for m in items[1:]]==[\"app/\"+n for n in expected])\n        for m in items[1:]:\n            r=expected[m.name[4:]]\n            data=t.extractfile(m).read()\n            need(m.size==r[\"bytes\"] and len(data)==r[\"bytes\"] and sha(data)==r[\"candidate_sha256\"])\n            app[m.name[4:]]=data\n        # Reject appended bytes, noncanonical headers, alternate tar encodings.\n        rebuilt=io.BytesIO()\n        with tarfile.open(fileobj=rebuilt,mode=\"w\",format=tarfile.USTAR_FORMAT) as out:\n            for m in items:put(out,m.name,t.extractfile(m).read())\n        need(rebuilt.getvalue()==b)\n    return {\"schema\":SCHEMA,\"bundle_sha256\":sha(b),\"bundle_bytes\":len(b),\n            \"application_paths\":155,\"deployment_reference_only\":28,\n            \"installable\":False,\"release_authorized\":False},d,app\n",
}
DEST="remura-maintenance-v165"
DIRFLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC

def need(ok):
    if not ok:raise ValueError("BOOTSTRAP_PROVISION_GATE")

def trusted(fd,uid):
    s=os.fstat(fd)
    need(stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&0o7022)

def source_bytes():
    need(set(SOURCES)==set(PINS))
    data={n:s.encode("utf-8") for n,s in SOURCES.items()}
    for n,(length,digest) in PINS.items():
        need(len(data[n])==length and hashlib.sha256(data[n]).hexdigest()==digest)
    return data

def publish(parent,uid):
    """Publish only to a new fixed child of an independently trusted fd.
    No replacement, arbitrary destination, activation or cleanup on failure.
    """
    trusted(parent,uid)
    data=source_bytes()
    os.mkdir(DEST,0o700,dir_fd=parent)
    os.fsync(parent)
    dest=os.open(DEST,DIRFLAGS,dir_fd=parent)
    try:
        trusted(dest,uid)
        need(stat.S_IMODE(os.fstat(dest).st_mode)==0o700)
        need(not os.listdir(dest))
        os.mkdir("sources",0o700,dir_fd=dest)
        os.fsync(dest)
        child=os.open("sources",DIRFLAGS,dir_fd=dest)
        try:
            trusted(child,uid)
            need(stat.S_IMODE(os.fstat(child).st_mode)==0o700)
            for name,b in sorted(data.items()):
                fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=child)
                with os.fdopen(fd,"wb") as f:
                    f.write(b)
                    f.flush()
                    os.fsync(f.fileno())
            os.fsync(child)
            need(set(os.listdir(child))==set(PINS))
            for name,(length,digest) in PINS.items():
                fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=child)
                with os.fdopen(fd,"rb") as f:
                    st=os.fstat(f.fileno())
                    need(stat.S_ISREG(st.st_mode) and st.st_uid==uid and st.st_nlink==1
                         and stat.S_IMODE(st.st_mode)==0o400 and st.st_size==length)
                    b=f.read(length+1)
                    need(len(b)==length and hashlib.sha256(b).hexdigest()==digest)
            os.fsync(child)
        finally:os.close(child)
        # This is a code-copy receipt only, never an executable authorization.
        fd=os.open("CODE_ONLY",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=dest)
        with os.fdopen(fd,"wb") as f:
            f.write(b"CODE_ONLY; INSTALL_AUTHORIZED=NO; EXECUTION_AUTHORIZED=NO\n")
            f.flush();os.fsync(f.fileno())
        os.fsync(dest)
        os.fsync(parent)
    finally:os.close(dest)

def main():
    if (sys.argv[1:]!=["--prepare-code-only"] or os.geteuid()!=0
        or not sys.flags.isolated or not sys.flags.no_site or not sys.flags.dont_write_bytecode):
        return 2
    fd=os.open("/",DIRFLAGS)
    try:
        trusted(fd,0)
        for name in ("usr","local","lib"):
            child=os.open(name,DIRFLAGS,dir_fd=fd)
            os.close(fd);fd=child
            trusted(fd,0)
        publish(fd,0)
        print("CODE_ONLY: 4/4 PINNED SOURCES; ACTIVATION NO; INSTALLATION NO")
        return 0
    except (OSError,ValueError):
        print("STOP: bootstrap not completed; do not overwrite or retry automatically")
        return 2
    finally:os.close(fd)

if __name__=="__main__":
    raise SystemExit(main())
