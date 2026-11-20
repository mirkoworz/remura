"""REMURA v0.8.173 LAB — 18/11/2026, sessione successiva alle 17:48 CET.
Descriptor-bound baseline read for a disposable fixture, application manifest only.
No live installer, write, private DB/config access, or service action.
Rechecks are not filesystem-wide atomicity or a guarantee against privileged races.
"""
import os
import stat
from abc_v165_stage_bundle_v1 import rows,PATH
from abc_v165_start_guard_v1 import open_chain
from abc_v165_transaction_plan_v1 import matches_base
from abc_v165_locked_snapshot_v1 import require
MAX_FILE=2*1024*1024
MAX_TOTAL=4*1024*1024
FLAGS=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC

def stamp(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,
            s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def directory(fd,uid,device):
    s=os.fstat(fd)
    require(stat.S_ISDIR(s.st_mode) and s.st_uid==uid and s.st_dev==device
            and not s.st_mode&0o7022)
    return stamp(s)

def metadata(parent,name):
    try:return os.stat(name,dir_fd=parent,follow_symlinks=False)
    except FileNotFoundError:return None

def valid_file(s,uid,device):
    return (s is not None and stat.S_ISREG(s.st_mode) and s.st_uid==uid
            and s.st_dev==device and s.st_nlink==1 and not s.st_mode&0o7022
            and 0<s.st_size<=MAX_FILE)

def read_baseline(root,manifest,uid,*,synthetic=False):
    require(synthetic is True and type(uid) is int and uid==os.getuid())
    expected=rows(manifest)
    require(len(expected)==155 and all(PATH.fullmatch(p) for p in expected))
    device=os.fstat(root).st_dev
    root_stamp=directory(root,uid,device)
    child=open_chain(root,("scripts",),uid)
    try:
        child_stamp=directory(child,uid,device)
        require(root_stamp[:2]!=child_stamp[:2])
        def location(path):
            parts=path.split("/")
            return (root,parts[0]) if len(parts)==1 else (child,parts[1])
        result={};seen={};total=0
        for path,row in expected.items():
            fd,name=location(path)
            s=metadata(fd,name)
            if row["operation"]=="add":
                require(s is None)
                seen[path]=None
                continue
            require(valid_file(s,uid,device))
            total+=s.st_size
            require(total<=MAX_TOTAL)
            item=os.open(name,FLAGS,dir_fd=fd)
            try:
                require(stamp(os.fstat(item))==stamp(s))
                with os.fdopen(os.dup(item),"rb") as stream:data=stream.read(s.st_size+1)
                end=metadata(fd,name)
                require(len(data)==s.st_size and end is not None
                        and stamp(s)==stamp(os.fstat(item))==stamp(end))
                require(matches_base(path,data,row["base_git_blob"]))
                result[path]=data
                seen[path]=stamp(s)
            finally:os.close(item)
        require(len(result)==79)
        for path,old in seen.items():
            fd,name=location(path)
            current=metadata(fd,name)
            require((current is None and old is None) or
                    (current is not None and old==stamp(current)))
        named=open_chain(root,("scripts",),uid)
        try:
            require(directory(named,uid,device)==child_stamp==directory(child,uid,device))
        finally:os.close(named)
        require(directory(root,uid,device)==root_stamp)
        return result
    finally:os.close(child)
