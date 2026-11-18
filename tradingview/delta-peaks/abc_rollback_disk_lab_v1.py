# REMURA v0.8.142 LAB — 18/11/2026, sessione successiva alle 09:24 CET
"""Durable rollback journal on owned disposable filesystem only.
No CLI, no service commands, no deployment or production paths.
Use a new tempfile.mkdtemp(prefix="remura-journal-lab-") workspace.
"""
import base64
import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

LIMIT=4*1024*1024
SCHEMA="remura.abc.rollback.disk.lab.v1"
PATH=re.compile(r"(?:scripts/[A-Za-z_][A-Za-z_0-9]*[.]py|[A-Za-z0-9_-]+[.](?:html|js|css|webp|svg|webmanifest))\Z")

def require(x):
    if not x:
        raise ValueError("JOURNAL_GATE_FAILED")

def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)

def owned(p, directory=False):
    s=p.lstat()
    require(s.st_uid==os.getuid() and (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode) and s.st_nlink==1))
    return s

def atomic(p,b,mode):
    fd,name=tempfile.mkstemp(prefix=".journal-tmp-",dir=p.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(b)
            f.flush()
            os.fchmod(f.fileno(),mode)
            os.fsync(f.fileno())
        os.replace(name,p)
        syncdir(p.parent)
    finally:
        if os.path.lexists(name): os.unlink(name)

def pack(b,mode):
    require(type(b) is bytes and len(b)<=LIMIT and type(mode) is int and 0<=mode<=0o777)
    return {"data":base64.b64encode(b).decode("ascii"),"sha256":hashlib.sha256(b).hexdigest(),"mode":mode}

def unpack(x):
    require(type(x) is dict and set(x)=={"data","sha256","mode"})
    b=base64.b64decode(x["data"],validate=True)
    require(pack(b,x["mode"])==x)
    return b,x["mode"]

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":")).encode()

class Journal:
    def __init__(self,root,*,synthetic=False):
        require(synthetic is True)
        root=Path(root)
        require(root.is_absolute() and root==root.resolve() and root.parent==Path(tempfile.gettempdir()).resolve()
                and re.fullmatch(r"remura-journal-lab-[A-Za-z0-9_]+",root.name))
        require(owned(root,True).st_mode&0o077==0)
        require(owned(root/"app",True).st_mode&0o022==0)
        require(owned(root/"app"/"scripts",True).st_mode&0o022==0)
        self.root=root
        self.app=root/"app"
        self.path=root/"journal.json"

    @contextmanager
    def lock(self):
        fd=os.open(self.root/"lock",os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        try:
            s=os.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and s.st_nlink==1 and not s.st_mode&0o077)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            yield
        finally: os.close(fd)

    def target(self,p):
        require(type(p) is str and PATH.fullmatch(p))
        t=self.app/p
        require(owned(t.parent,True).st_mode&0o022==0)
        return t

    def current(self,p):
        t=self.target(p)
        if not os.path.lexists(t): return None
        s=owned(t)
        require(s.st_size<=LIMIT and not s.st_mode&0o7000)
        return pack(t.read_bytes(),stat.S_IMODE(s.st_mode))

    def write_doc(self,d):
        data=canonical(d)
        require(len(data)<=LIMIT*8)
        atomic(self.path,canonical({"payload":d,"sha256":hashlib.sha256(data).hexdigest()}),0o600)

    def read_doc(self):
        s=owned(self.path)
        require(not s.st_mode&0o077 and s.st_size<=LIMIT*10)
        envelope=json.loads(self.path.read_bytes())
        require(set(envelope)=={"payload","sha256"})
        d=envelope["payload"]
        require(hashlib.sha256(canonical(d)).hexdigest()==envelope["sha256"])
        require(set(d)=={"schema","phase","rows"} and d["schema"]==SCHEMA and d["phase"] in {"prepared","applied","rolled_back"})
        rows=d["rows"]
        require(type(rows) is list and 0<len(rows)<=155)
        paths=[]
        for r in rows:
            require(set(r)=={"path","before","after"})
            self.target(r["path"]);paths.append(r["path"])
            if r["before"] is not None: unpack(r["before"])
            unpack(r["after"])
            require(r["before"]!=r["after"])
        require(paths==sorted(set(paths)))
        return d

    def prepare(self,original,candidate):
        # Caller supplies already vetted exact bytes, no manifest trust implied.
        with self.lock():
            require(not os.path.lexists(self.path) and type(original) is dict and type(candidate) is dict
                    and 0<len(candidate)<=155 and set(original)<=set(candidate))
            require(sum(len(b) for b in list(original.values())+list(candidate.values()))<=LIMIT)
            rows=[]
            for p,b in sorted(candidate.items()):
                old=self.current(p)
                require((old is None and p not in original) or
                        (old is not None and p in original and unpack(old)[0]==original[p]))
                new=pack(b,old["mode"] if old else 0o644)
                require(new!=old)
                rows.append({"path":p,"before":old,"after":new})
            self.write_doc({"schema":SCHEMA,"phase":"prepared","rows":rows})

    def apply(self,*,crash_after=None):
        with self.lock():
            d=self.read_doc()
            require(d["phase"]=="prepared")
            require(crash_after is None or type(crash_after) is int and 0<=crash_after<=len(d["rows"]))
            require(all(self.current(r["path"])==r["before"] for r in d["rows"]))
            if crash_after==0: os._exit(75)
            for i,r in enumerate(d["rows"],1):
                b,mode=unpack(r["after"])
                atomic(self.target(r["path"]),b,mode)
                if crash_after==i: os._exit(75)
            require(all(self.current(r["path"])==r["after"] for r in d["rows"]))
            d["phase"]="applied"
            self.write_doc(d)

    def rollback(self,*,crash_after=None):
        with self.lock():
            d=self.read_doc()
            require(crash_after is None or type(crash_after) is int and 0<=crash_after<=len(d["rows"]))
            # Check entire transaction BEFORE any mutation; unknown bytes/mode stop.
            for r in d["rows"]:
                current=self.current(r["path"])
                if d["phase"]=="rolled_back": require(current==r["before"])
                else: require(current in (r["before"],r["after"]))
            if d["phase"]=="rolled_back": return "already_rolled_back"
            if crash_after==0: os._exit(75)
            for i,r in enumerate(reversed(d["rows"]),1):
                if self.current(r["path"])!=r["before"]:
                    t=self.target(r["path"])
                    if r["before"] is None:
                        t.unlink();syncdir(t.parent)
                    else:
                        b,mode=unpack(r["before"]);atomic(t,b,mode)
                if crash_after==i: os._exit(75)
            require(all(self.current(r["path"])==r["before"] for r in d["rows"]))
            d["phase"]="rolled_back";self.write_doc(d)
            return "rolled_back"
