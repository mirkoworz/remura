# REMURA Contributors v0.7 LAB — 14/11/2026 23:39 CET
"""In-process synthetic access-to-archive integration, not a public API.

Creates a NEW temporary archive per access-policy lifetime, so restarting an
in-memory identity registry cannot accidentally reassign old contributor records.
All calls must be made serially on the creating thread by trusted test code.
No browser endpoints, Google claims, cookies, external requests or live data.
"""
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import get_ident
from access_policy_v1 import LabAccess
from archive_v1 import Archive
from local_lab_v1 import CATALOG

def _clock():
    return int(datetime.now(timezone.utc).timestamp())

class SessionLab:
    def __init__(self, *, synthetic=False, clock=_clock):
        if synthetic is not True:
            raise ValueError("synthetic_only")
        self._thread=get_ident()
        self._closed=False
        self._clock=clock
        self._access=LabAccess("google-owner-fixture",synthetic=True)
        self._root=TemporaryDirectory(prefix="remura-session-lab-")
        try:
            self._archive=Archive(Path(self._root.name).resolve(),catalog=CATALOG,
                                  contributors=["friend-a","friend-b"],owners=["owner"],synthetic=True)
        except BaseException:
            self._root.cleanup()
            raise

    def _now(self):
        if self._closed or get_ident()!=self._thread:
            raise RuntimeError("closed_or_wrong_thread")
        return self._clock()

    def _stamp(self,now):
        return datetime.fromtimestamp(now,timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def challenge(self):
        return self._access.challenge(now=self._now())

    def login(self,identity,nonce):
        return self._access.login(identity,nonce,now=self._now())

    def invite(self,token,email,slot):
        return self._access.invite(token,email,slot,now=self._now())

    def redeem(self,identity,nonce,invite_token):
        return self._access.redeem(identity,nonce,invite_token,now=self._now())

    def cancel_invite(self,token,invite_token):
        return self._access.cancel_invite(token,invite_token,now=self._now())

    def revoke(self,token,slot):
        return self._access.revoke(token,slot,now=self._now())

    def logout(self,token):
        return self._access.logout(token,now=self._now())

    def submit(self,token,payload):
        now=self._now()
        actor=self._access.principal(token,now=now)
        return self._archive.submit(actor,payload,received_utc=self._stamp(now))

    def receipts(self,token):
        actor=self._access.principal(token,now=self._now())
        return self._archive.receipts(actor)

    def queue(self,token):
        actor=self._access.principal(token,now=self._now())
        return self._archive.queue(actor)

    def review(self,token,eid,action,reason):
        now=self._now()
        actor=self._access.principal(token,now=now)
        return self._archive.review(actor,eid,action,at_utc=self._stamp(now),reason=reason)

    def close(self):
        self._now()
        self._closed=True
        try:self._archive.close()
        finally:self._root.cleanup()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
