# REMURA v0.8.162 LAB — 18/11/2026, sessione successiva alle 13:37 CET
"""Read-only bootstrap source census. No imports of candidate files, no execution.
Trust in this verifier, OS/interpreter and anchor is external. LAB only.
"""
import hashlib
import os
import stat

PINS = {
    "abc_v165_start_guard_v1.py": (2607, "ce2652f6b7c118cdf1e83f714b58b975071d5991dc897f3d4afa3131bfcd107c"),
    "abc_v165_locked_snapshot_v1.py": (3809, "e11e7297c7953faf90887ee72b5eecbf43fc5a240304558887f0f976ae23ebc3"),
    "abc_v165_stage_bundle_v1.py": (5118, "d29206be079b5ca80202254b04141ef16bfb94a006696e50ac92622d4b5286ab"),
    "abc_v165_locked_bundle_parser_v1.py": (1775, "eafb18d3ecc719b4b8a79c481482ade98c8f35bd2cb3f84d8f8fab26ff792f0c"),
}
FLAGS=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
DIRFLAGS=FLAGS|os.O_DIRECTORY

def require(ok):
    if not ok:
        raise ValueError("BOOTSTRAP_SOURCE_GATE")

def trusted_dir(fd,uid):
    s=os.fstat(fd)
    require(stat.S_ISDIR(s.st_mode) and s.st_uid==uid and not s.st_mode&0o7022)

def stamp(s):
    return (s.st_dev,s.st_ino,s.st_uid,s.st_gid,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def verify_sources(anchor,parts,uid):
    """Given independently trusted anchor, verify exact named source bytes.
    Return bytes for later review, never execute or append to sys.path.
    """
    require(type(uid) is int and uid>=0 and type(parts) in (list,tuple) and 1<=len(parts)<=12)
    fd=os.dup(anchor)
    try:
        trusted_dir(fd,uid)
        for part in parts:
            require(type(part) is str and part not in ("",".","..") and "/" not in part)
            child=os.open(part,DIRFLAGS,dir_fd=fd)
            os.close(fd)
            fd=child
            trusted_dir(fd,uid)
        before=stamp(os.fstat(fd))
        require(set(os.listdir(fd))==set(PINS))
        sources={}
        for name,(length,digest) in sorted(PINS.items()):
            f=os.open(name,FLAGS|os.O_NONBLOCK,dir_fd=fd)
            try:
                s=os.fstat(f)
                require(stat.S_ISREG(s.st_mode) and s.st_uid==uid and s.st_nlink==1
                        and stat.S_IMODE(s.st_mode) in (0o400,0o444,0o600,0o644)
                        and s.st_size==length)
                require(stamp(s)==stamp(os.stat(name,dir_fd=fd,follow_symlinks=False)))
                with os.fdopen(os.dup(f),"rb") as stream:
                    data=stream.read(length+1)
                require(len(data)==length and hashlib.sha256(data).hexdigest()==digest)
                require(stamp(s)==stamp(os.fstat(f))==stamp(os.stat(name,dir_fd=fd,follow_symlinks=False)))
                sources[name]=data
            finally:
                os.close(f)
        require(stamp(os.fstat(fd))==before and set(os.listdir(fd))==set(PINS))
        return sources
    finally:
        os.close(fd)
