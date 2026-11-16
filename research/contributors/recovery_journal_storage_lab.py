# REMURA Contributors v0.23 LAB — 16/11/2026 07:14 CET
"""Synthetic-only POSIX journal persistence. Never use real user identifiers here.
The latest pin MUST be supplied from outside this directory. No self-trust on reopen.
Append-only cooperating writers; not a defense against privileged or same-UID tampering.
"""
import fcntl, json, os, stat
from pathlib import Path
from recovery_journal_candidate import verify, append, ZERO
LOCK="journal.lock"
MAX=1024
def deny():raise ValueError("journal_storage_denied")
def private(st):
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600:deny()
def name(i):return f"event-{i:02d}.json"
class Journal:
    def __init__(self,root,expected_pin,*,synthetic=False,initialize=False):
        if synthetic is not True or type(initialize) is not bool:deny()
        if initialize and expected_pin!=ZERO:deny()
        p=Path(root)
        if not p.is_absolute() or p.resolve()!=p:deny()
        self.fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self.lock=None;self.closed=False;self.poisoned=False
        try:
            st=os.fstat(self.fd)
            if st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:deny()
            if initialize and os.listdir(self.fd):deny()
            flags=os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK
            if initialize:flags|=os.O_CREAT|os.O_EXCL
            self.lock=os.open(LOCK,flags,0o600,dir_fd=self.fd)
            private(os.fstat(self.lock))
            fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if initialize:os.fsync(self.lock);os.fsync(self.fd)
            self.events=self._load(expected_pin)
            self.pin=expected_pin
        except BaseException:
            self.close();raise
    def _guard(self):
        if self.closed or self.poisoned:raise RuntimeError("journal_unavailable")
    def _load(self,pin):
        names=sorted(x for x in os.listdir(self.fd) if x!=LOCK)
        if len(names)>6 or names!=[name(i) for i in range(1,len(names)+1)]:deny()
        events=[]
        for n in names:
            f=os.open(n,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
            with os.fdopen(f,"rb") as stream:
                st=os.fstat(stream.fileno());private(st)
                if not 0<st.st_size<=MAX:deny()
                raw=stream.read(MAX+1)
                if len(raw)>MAX:deny()
                event=json.loads(raw)
                # Reject noncanonical bytes, duplicate keys, partial files and edits to encoding.
                if json.dumps(event,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()!=raw:deny()
                events.append(event)
        verify(events,pin)
        return events
    def snapshot(self):
        self._guard();return [dict(e) for e in self._load(self.pin)],self.pin
    def record(self,kind,at,subject,email_tag,role,slot,*,expected_pin):
        self._guard()
        if expected_pin!=self.pin:deny()
        current=self._load(expected_pin)
        result,new_pin=append(current,expected_pin,kind,at,subject,email_tag,role,slot)
        raw=json.dumps(result[-1],sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
        if len(raw)>MAX:deny()
        try:
            f=os.open(name(len(result)),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
            with os.fdopen(f,"wb") as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.fsync(self.fd)
            self.events=self._load(new_pin);self.pin=new_pin
        except BaseException:
            # Partial append or failed fsync is ambiguous. No delete, retry or automatic repair.
            self.poisoned=True;raise
        return new_pin
    def close(self):
        if not self.closed:
            self.closed=True
            if self.lock is not None:os.close(self.lock)
            os.close(self.fd)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
