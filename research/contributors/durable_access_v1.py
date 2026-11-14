# REMURA Contributors v0.8 LAB — 14/11/2026 23:41 CET
"""Durable synthetic identity registry, not Google authentication.
One cooperating local process, a dedicated private directory, explicit create.
Only identities/revocation persist. Invites, challenges, sessions die on restart.
No archive reopening or production migration is authorized by this module.
"""
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path
from threading import get_ident
from access_policy_v1 import LabAccess,ID
from ledger_v1 import Principal

STATE="contributors-identities-synthetic-lab.json"
LOCK="contributors-identities-synthetic-lab.lock"
MAX_BYTES=8192
SLOTS={"friend-a","friend-b"}

def _private_file(path):
    st=path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid()
        or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600):
        raise ValueError("private_file")

def _validate(data,owner):
    if (type(data) is not dict or set(data)!={"version","owner","last_binding","users"}
        or type(data["version"]) is not int or data["version"]!=1 or data["owner"]!=owner
        or type(data["last_binding"]) is not int or not 0<=data["last_binding"]<=4102444800
        or type(data["users"]) is not list or len(data["users"])>2):
        raise ValueError("registry_schema")
    subjects=set();slots=set()
    for row in data["users"]:
        if (type(row) is not dict or set(row)!={"subject","slot","revoked"}
            or type(row["subject"]) is not str or not ID.fullmatch(row["subject"])
            or row["subject"]==owner or row["subject"] in subjects
            or type(row["slot"]) is not str or row["slot"] not in SLOTS or row["slot"] in slots
            or type(row["revoked"]) is not bool):
            raise ValueError("registry_identity")
        subjects.add(row["subject"]);slots.add(row["slot"])
    return data

class DurableAccess:
    def __init__(self,root,owner_subject,*,synthetic=False,initialize=False):
        if synthetic is not True or type(initialize) is not bool:
            raise ValueError("synthetic_only")
        self._policy=LabAccess(owner_subject,synthetic=True)
        self._owner=owner_subject
        self._thread=get_ident()
        self._closed=False
        self._poisoned=False
        self._root=Path(root)
        if not self._root.is_absolute() or self._root.resolve()!=self._root:
            raise ValueError("private_absolute_root")
        st=self._root.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:
            raise ValueError("private_root")
        self._path=self._root/STATE
        lock=self._root/LOCK
        if initialize and any(self._root.iterdir()):
            raise ValueError("initialize_requires_empty_directory")
        flags=os.O_RDWR|os.O_NOFOLLOW
        if initialize:flags|=os.O_CREAT|os.O_EXCL
        self._fd=os.open(lock,flags,0o600)
        try:
            _private_file(lock)
            fcntl.flock(self._fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if initialize:
                self._save()
            else:
                _private_file(self._path)
                if self._path.stat().st_size>MAX_BYTES:raise ValueError("registry_size")
                with self._path.open("rb") as f:raw=f.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise ValueError("registry_size")
                data=_validate(json.loads(raw),owner_subject)
                self._policy._last=data["last_binding"]
                for row in data["users"]:
                    sub,slot=row["subject"],row["slot"]
                    self._policy._users[sub]=Principal(slot,"CONTRIBUTOR")
                    self._policy._slots.add(slot)
                    if row["revoked"]:self._policy._disabled.add(sub)
        except BaseException:
            os.close(self._fd)
            raise

    def _state(self):
        rows=[{"subject":sub,"slot":p.subject,"revoked":sub in self._policy._disabled}
              for sub,p in sorted(self._policy._users.items()) if p.role=="CONTRIBUTOR"]
        return _validate({"version":1,"owner":self._owner,"last_binding":self._policy._last or 0,
                          "users":rows},self._owner)

    def _save(self):
        # Only acknowledge mutations after file replacement and directory fsync.
        raw=json.dumps(self._state(),sort_keys=True,separators=(",",":")).encode("ascii")
        if len(raw)>MAX_BYTES:raise ValueError("registry_size")
        fd,tmp=tempfile.mkstemp(prefix=".identity-lab-",dir=self._root)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self._path)
            dfd=os.open(self._root,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(dfd)
            finally:os.close(dfd)
        finally:
            if os.path.lexists(tmp):os.unlink(tmp)

    def _guard(self):
        if self._closed or self._poisoned or get_ident()!=self._thread:
            raise RuntimeError("registry_unavailable")

    def _persist(self):
        try:self._save()
        except BaseException:
            # Mutation may or may not be on disk; never continue from uncertain RAM.
            self._poisoned=True
            raise

    def challenge(self,*,now):
        self._guard();return self._policy.challenge(now=now)

    def login(self,identity,nonce,*,now):
        self._guard();return self._policy.login(identity,nonce,now=now)

    def principal(self,token,*,now):
        self._guard();return self._policy.principal(token,now=now)

    def invite(self,token,email,slot,*,now):
        self._guard();return self._policy.invite(token,email,slot,now=now)

    def redeem(self,identity,nonce,invite_token,*,now):
        self._guard()
        token=self._policy.redeem(identity,nonce,invite_token,now=now)
        self._persist()
        return token

    def cancel_invite(self,token,invite_token,*,now):
        self._guard();return self._policy.cancel_invite(token,invite_token,now=now)

    def revoke(self,token,slot,*,now):
        self._guard()
        result=self._policy.revoke(token,slot,now=now)
        self._persist()
        return result

    def logout(self,token,*,now):
        self._guard();return self._policy.logout(token,now=now)

    def close(self):
        if self._closed or get_ident()!=self._thread:raise RuntimeError("registry_unavailable")
        self._closed=True
        os.close(self._fd)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
