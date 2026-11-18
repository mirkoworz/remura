#!/usr/bin/env python3
# REMURA v0.8.146 LAB — 18/11/2026, sessione successiva alle 09:49 CET
"""Candidate startup condition for existing systemd services, no installation.
Exit 0 permits start, 1 inhibits, 255 unsafe/error. No file writes, DB or network.
"""
import os,stat,sys
from pathlib import Path
WORK=Path("/var/lib/remura-autoupdate")
MARKERS={"updater":"maintenance-v165.inhibit","collector":"collector-v165.inhibit"}

def evaluate(work,role,uid):
    # Absence is accepted only inside a verified private work directory.
    if role not in MARKERS:return 255
    fd=None
    try:
        work=Path(work)
        fd=os.open(work,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        s=os.fstat(fd)
        if s.st_uid!=uid or s.st_mode&0o077:return 255
        # lstat via directory fd: even dangling symlinks and invalid objects inhibit.
        try:
            os.stat(MARKERS[role],dir_fd=fd,follow_symlinks=False)
        except FileNotFoundError:return 0
        return 1
    except (OSError,ValueError,TypeError):return 255
    finally:
        if fd is not None:os.close(fd)

def main():
    if os.geteuid()!=0 or len(sys.argv)!=2:return 255
    return evaluate(WORK,sys.argv[1],0)
if __name__=="__main__":sys.exit(main())
