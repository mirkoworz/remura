#!/usr/bin/env python3
# REMURA v0.8.82 LAB — 14/11/2026 20:28 CET
"""Single-flight advisory lock for cooperating D runtimes on the same host.
Existing private directory and stable empty lock inode required. No creation,
truncation, unlink, PID files, waiting, or host-wide exclusivity claim.
"""
from contextlib import contextmanager
import fcntl,os,stat
NAME="remura-d-preview.lock"

def _check(s,kind):
    if (not kind(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077):
        raise ValueError("private_runtime_lock_permissions")

@contextmanager
def single_flight(root):
    d=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        _check(os.fstat(d),stat.S_ISDIR)
        f=os.open(NAME,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=d)
        try:
            s=os.fstat(f);_check(s,stat.S_ISREG)
            if s.st_nlink!=1 or s.st_size!=0:raise ValueError("runtime_lock_inode")
            identity=(s.st_dev,s.st_ino)
            def still_held():
                x=os.stat(NAME,dir_fd=d,follow_symlinks=False)
                _check(x,stat.S_ISREG)
                if (x.st_dev,x.st_ino)!=identity or x.st_nlink!=1 or x.st_size!=0:
                    raise ValueError("runtime_lock_replaced")
            try:
                fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("runtime_already_running") from None
            still_held()
            yield still_held
        finally:
            os.close(f)
    finally:
        os.close(d)
