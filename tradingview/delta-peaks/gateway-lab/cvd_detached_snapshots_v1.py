#!/usr/bin/env python3
# REMURA v0.8.81 LAB — 14/11/2026 19:58 CET
"""Private staging input only: never connect to source SQLite files.
Caller must supply an already coherent, detached, trusted export and digest.
No disk writes, network, printing, or live backup creation.
"""
from contextlib import contextmanager,ExitStack
from hashlib import sha256
import os,re,sqlite3,stat,time

MAX_TOTAL_BYTES=32*1024*1024
MAX_CHECK_SECONDS=5
NAMES=("core.sqlite3","private.sqlite3")

def _private(st,kind):
    predicate=stat.S_ISDIR if kind=="directory" else stat.S_ISREG
    if not predicate(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode&0o077:
        raise ValueError("snapshot_private_permissions")
    if kind=="file" and st.st_nlink!=1:
        raise ValueError("snapshot_hardlink")

def _identity(s):
    return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns

def _read_export(fd,name,expected,remaining):
    for ext in ("-wal","-shm","-journal"):
        try:
            os.stat(name+ext,dir_fd=fd,follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError("snapshot_sidecar_present")
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        before=os.fstat(f);_private(before,"file")
        if not 100<=before.st_size<=remaining:
            raise ValueError("snapshot_size")
        with os.fdopen(os.dup(f),"rb") as stream:
            raw=stream.read(before.st_size+1)
        if len(raw)!=before.st_size or _identity(before)!=_identity(os.fstat(f)):
            raise ValueError("snapshot_changed")
        if sha256(raw).hexdigest()!=expected:
            raise ValueError("snapshot_digest_mismatch")
        # WAL-mode files require a coherent exporter; do not silently ignore WAL.
        if raw[:16]!=b"SQLite format 3\x00" or raw[18:20]!=b"\x01\x01":
            raise ValueError("snapshot_not_standalone_sqlite")
        return raw
    finally:
        os.close(f)

def _connection(raw):
    db=sqlite3.connect(":memory:")
    try:
        db.deserialize(raw)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("PRAGMA query_only=ON")
        deadline=time.monotonic()+MAX_CHECK_SECONDS
        db.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
        if db.execute("PRAGMA quick_check(1)").fetchall()!=[("ok",)]:
            raise ValueError("snapshot_integrity")
        db.set_progress_handler(None,0)
        return db
    except BaseException:
        db.close()
        raise

@contextmanager
def open_snapshots(root,digests,*,explicit=False):
    if explicit is not True:
        raise ValueError("explicit_detached_snapshot_required")
    if (type(digests) is not dict or set(digests) not in ({"core.sqlite3"},set(NAMES)) or
        any(type(v) is not str or not re.fullmatch("[0-9a-f]{64}",v) for v in digests.values())):
        raise ValueError("snapshot_manifest")
    if len(set(digests.values()))!=len(digests):
        raise ValueError("snapshot_sources_not_distinct")
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        _private(os.fstat(fd),"directory")
        remaining=MAX_TOTAL_BYTES
        with ExitStack() as stack:
            conns=[]
            for name in NAMES:
                if name not in digests:
                    conns.append(None);continue
                raw=_read_export(fd,name,digests[name],remaining)
                remaining-=len(raw)
                db=_connection(raw);del raw
                stack.callback(db.close);conns.append(db)
            yield tuple(conns)
    finally:
        os.close(fd)
