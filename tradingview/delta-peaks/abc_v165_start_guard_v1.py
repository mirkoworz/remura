#!/usr/bin/env python3
# REMURA v0.8.153 LAB — 18/11/2026, sessione successiva alle 11:13 CET
"""Candidate startup condition; no installation.
Exit 0 permits start, 1 inhibits, 255 unsafe/error. No writes, DB or network.
The executable AND its ancestors must be independently secured before invoking
this root-side helper. This script cannot attest its own pre-execution trust.
"""
import os,stat,sys
from pathlib import Path
WORK=Path("/var/lib/remura-autoupdate")
MARKERS={"updater":"maintenance-v165.inhibit","collector":"collector-v165.inhibit"}
FLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
def trusted_dir(fd,uid,private=False):
    s=os.fstat(fd)
    return stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&(0o077 if private else 0o022)
def open_chain(anchor,parts,uid):
    """Duplicate anchor, check every directory from a trusted fd; reject traversal."""
    fd=os.dup(anchor)
    try:
        if not trusted_dir(fd,uid):raise ValueError("UNTRUSTED_ANCESTOR")
        for name in parts:
            if type(name) is not str or name in ("",".","..") or "/" in name:
                raise ValueError("UNTRUSTED_PATH_COMPONENT")
            child=os.open(name,FLAGS,dir_fd=fd)
            os.close(fd);fd=child
            if not trusted_dir(fd,uid):raise ValueError("UNTRUSTED_ANCESTOR")
        return fd
    except BaseException:
        os.close(fd);raise
def evaluate_fd(fd,role,uid):
    if role not in MARKERS or not trusted_dir(fd,uid,private=True):return 255
    try:
        # Even dangling symlinks, directories and invalid marker objects inhibit.
        os.stat(MARKERS[role],dir_fd=fd,follow_symlinks=False)
    except FileNotFoundError:return 0
    return 1
def evaluate(work,role,uid):
    # Disposable LAB fixture helper; production entrypoint uses anchored check.
    fd=None
    try:
        fd=os.open(Path(work),FLAGS)
        return evaluate_fd(fd,role,uid)
    except (OSError,ValueError,TypeError):return 255
    finally:
        if fd is not None:os.close(fd)
def evaluate_anchored(work,role,uid):
    root=None;fd=None
    try:
        p=Path(work)
        if not p.is_absolute() or p.anchor!="/" or not p.parts[1:]:return 255
        root=os.open("/",FLAGS)
        fd=open_chain(root,p.parts[1:],uid)
        return evaluate_fd(fd,role,uid)
    except (OSError,ValueError,TypeError):return 255
    finally:
        if fd is not None:os.close(fd)
        if root is not None:os.close(root)
def main():
    if os.geteuid()!=0 or len(sys.argv)!=2:return 255
    return evaluate_anchored(WORK,sys.argv[1],0)
if __name__=="__main__":sys.exit(main())
