# REMURA Contributors v0.9 LAB — 14/11/2026 23:43 CET
"""Integrated synthetic registry + archive, single SQLite database, no HTTP.
Only explicit new initialization or reopening of this LAB schema.
No migration from earlier databases, restoration or real identity data.
"""
import json
import os
import stat
import fcntl
from pathlib import Path
from threading import get_ident
from access_policy_v1 import LabAccess
from archive_v1 import Archive,FILENAME
from durable_access_v1 import _validate,MAX_BYTES
from ledger_v1 import Principal
from session_lab_v1 import SessionLab,_clock
from local_lab_v1 import CATALOG

LOCK="contributors-integrated-lab.lock"
TABLE="synthetic_identity_registry"

class BoundAccess(LabAccess):
    def __init__(self,archive,*,initialize):
        super().__init__("google-owner-fixture",synthetic=True)
        self.archive=archive
        self.poisoned=False
        if initialize:
            with archive._write():
                archive.db.execute("CREATE TABLE synthetic_identity_registry(id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL)")
                archive.db.execute("INSERT INTO synthetic_identity_registry VALUES(1,?)",(self._encoded(),))
        else:
            rows=archive.db.execute("SELECT id,state FROM synthetic_identity_registry").fetchall()
            if len(rows)!=1 or rows[0]["id"]!=1 or len(rows[0]["state"])>MAX_BYTES:
                raise ValueError("registry_missing_or_invalid")
            state=_validate(json.loads(rows[0]["state"]),self._owner)
            self._last=state["last_binding"]
            for row in state["users"]:
                sub,slot=row["subject"],row["slot"]
                self._users[sub]=Principal(slot,"CONTRIBUTOR")
                self._slots.add(slot)
                if row["revoked"]:self._disabled.add(sub)
            authors={r[0] for r in archive.db.execute("SELECT DISTINCT subject FROM entries")}
            if not authors<=self._slots:raise ValueError("unbound_contribution")

    def _encoded(self):
        data=_validate(dict(version=1,owner=self._owner,last_binding=self._last or 0,
            users=[dict(subject=sub,slot=p.subject,revoked=sub in self._disabled)
                   for sub,p in sorted(self._users.items()) if p.role=="CONTRIBUTOR"]),self._owner)
        raw=json.dumps(data,sort_keys=True,separators=(",",":"))
        if len(raw)>MAX_BYTES:raise ValueError("registry_size")
        return raw

    def _now(self,now):
        if self.poisoned:raise RuntimeError("registry_unavailable")
        return super()._now(now)

    def _persist(self):
        try:
            with self.archive._write():
                cur=self.archive.db.execute("UPDATE synthetic_identity_registry SET state=? WHERE id=1",(self._encoded(),))
                if cur.rowcount!=1:raise ValueError("registry_missing")
        except BaseException:
            self.poisoned=True
            raise

    def redeem(self,*args,**kwargs):
        token=super().redeem(*args,**kwargs)
        self._persist()
        return token

    def revoke(self,*args,**kwargs):
        result=super().revoke(*args,**kwargs)
        self._persist()
        return result

class IntegratedLab(SessionLab):
    """Same session-gated interface as v0.7, but durable identity + records.
    Fixed synthetic owner/catalog, one cooperating process/thread.
    Restart discards every challenge, invite and session.
    """
    def __init__(self,root,*,synthetic=False,initialize=False,clock=_clock):
        if synthetic is not True or type(initialize) is not bool:
            raise ValueError("synthetic_only")
        root=Path(root)
        if not root.is_absolute() or root.resolve()!=root:
            raise ValueError("private_absolute_root")
        st=root.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:
            raise ValueError("private_root")
        if initialize and any(root.iterdir()):raise ValueError("initialize_requires_empty_directory")
        path=root/FILENAME
        if not initialize and not os.path.lexists(path):raise FileNotFoundError(path)
        self._thread=get_ident();self._closed=False;self._clock=clock
        flags=os.O_RDWR|os.O_NOFOLLOW
        if initialize:flags|=os.O_CREAT|os.O_EXCL
        self._fd=os.open(root/LOCK,flags,0o600)
        try:
            st=os.fstat(self._fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600:
                raise ValueError("private_lock")
            fcntl.flock(self._fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self._archive=Archive(root,catalog=CATALOG,contributors=["friend-a","friend-b"],owners=["owner"],synthetic=True)
            try:self._access=BoundAccess(self._archive,initialize=initialize)
            except BaseException:
                self._archive.close()
                raise
        except BaseException:
            os.close(self._fd)
            raise

    def close(self):
        self._now()
        self._closed=True
        try:self._archive.close()
        finally:os.close(self._fd)
