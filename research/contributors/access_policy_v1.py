# REMURA Contributors v0.6 LAB — 14/11/2026 23:37 CET
"""Synthetic identity policy, NOT Google authentication.
Only a trusted in-process test harness may construct LabIdentity.
No OAuth/JWT parser, network, HTTP endpoints, cookies or persistent state.
Never construct LabIdentity from a request body or unverified claims.
"""
from dataclasses import dataclass
from hashlib import sha256
import re
import secrets
from ledger_v1 import Principal

ID=re.compile(r"[A-Za-z0-9_.-]{1,64}")
EMAIL=re.compile(r"[a-z0-9][a-z0-9._+-]{0,62}@example\.invalid")
INVITE_TTL=86400
CHALLENGE_TTL=300
SESSION_TTL=3600
MAX_INVITES=2
MAX_CHALLENGES=16
MAX_SESSIONS=3

@dataclass(frozen=True)
class LabIdentity:
    subject: str
    email: str
    email_verified: bool
    nonce: str

def _hash(token):
    if type(token) is not str or not 32<=len(token)<=128 or not token.isascii():
        raise PermissionError("token")
    return sha256(token.encode("ascii")).digest()

def _issue():
    return secrets.token_urlsafe(32)

class LabAccess:
    def __init__(self,owner_subject,*,synthetic=False):
        if synthetic is not True or type(owner_subject) is not str or not ID.fullmatch(owner_subject):
            raise ValueError("synthetic_only")
        self._owner=owner_subject
        self._users={owner_subject:Principal("owner","OWNER")}
        self._disabled=set()
        self._invites={}
        self._challenges={}
        self._sessions={}
        self._slots=set()
        self._last=None

    def _now(self,now):
        if type(now) is not int or not 0<=now<=4102444800 or self._last is not None and now<self._last:
            raise ValueError("clock")
        self._last=now
        for d in (self._invites,self._challenges,self._sessions):
            for k,v in list(d.items()):
                if v[-1]<=now:del d[k]
        return now

    def challenge(self,*,now):
        self._now(now)
        if len(self._challenges)>=MAX_CHALLENGES:raise PermissionError("challenge_capacity")
        token=_issue()
        self._challenges[_hash(token)]=(now+CHALLENGE_TTL,)
        return token

    def _identity(self,identity,nonce,now):
        key=_hash(nonce)
        if self._challenges.pop(key,None) is None:
            raise PermissionError("challenge")
        if (type(identity) is not LabIdentity or type(identity.subject) is not str
            or not ID.fullmatch(identity.subject) or type(identity.email) is not str
            or not EMAIL.fullmatch(identity.email) or identity.email_verified is not True
            or type(identity.nonce) is not str or not identity.nonce.isascii()
            or not secrets.compare_digest(identity.nonce,nonce)):
            raise PermissionError("synthetic_identity")

    def _session(self,subject,now):
        if subject in self._disabled or subject not in self._users:
            raise PermissionError("not_authorized")
        # Replace prior session for this identity, not a client-supplied session ID.
        for k,v in list(self._sessions.items()):
            if v[0]==subject:del self._sessions[k]
        if len(self._sessions)>=MAX_SESSIONS:raise PermissionError("session_capacity")
        token=_issue();self._sessions[_hash(token)]=(subject,now+SESSION_TTL)
        return token

    def login(self,identity,nonce,*,now):
        self._now(now)
        self._identity(identity,nonce,now)
        return self._session(identity.subject,now)

    def _subject(self,token):
        v=self._sessions.get(_hash(token))
        if v is None or v[0] in self._disabled or v[0] not in self._users:
            raise PermissionError("session")
        return v[0]

    def principal(self,token,*,now):
        self._now(now)
        return self._users[self._subject(token)]

    def _owner_required(self,token):
        if self._subject(token)!=self._owner:raise PermissionError("owner_only")

    def invite(self,owner_token,email,slot,*,now):
        self._now(now);self._owner_required(owner_token)
        if (type(email) is not str or not EMAIL.fullmatch(email)
            or slot not in ("friend-a","friend-b") or slot in self._slots
            or len(self._invites)>=MAX_INVITES
            or any(v[0]==email or v[1]==slot for v in self._invites.values())):
            raise ValueError("invite_scope")
        token=_issue()
        self._invites[_hash(token)]=(email,slot,now+INVITE_TTL)
        return token

    def redeem(self,identity,nonce,invite_token,*,now):
        self._now(now)
        self._identity(identity,nonce,now)
        key=_hash(invite_token);v=self._invites.get(key)
        if (v is None or identity.email!=v[0] or v[1] in self._slots
            or identity.subject in self._users or identity.subject in self._disabled):
            raise PermissionError("invite")
        del self._invites[key]
        self._slots.add(v[1])
        self._users[identity.subject]=Principal(v[1],"CONTRIBUTOR")
        return self._session(identity.subject,now)

    def cancel_invite(self,owner_token,invite_token,*,now):
        self._now(now);self._owner_required(owner_token)
        if self._invites.pop(_hash(invite_token),None) is None:
            raise PermissionError("invite")

    def revoke(self,owner_token,slot,*,now):
        self._now(now);self._owner_required(owner_token)
        if slot not in ("friend-a","friend-b"):raise ValueError("slot")
        matches=[s for s,p in self._users.items() if p.subject==slot and p.role=="CONTRIBUTOR"]
        if len(matches)!=1:raise PermissionError("unknown_slot")
        subject=matches[0];self._disabled.add(subject)
        for k,v in list(self._sessions.items()):
            if v[0]==subject:del self._sessions[k]
        # Never reassign a previous slot; historic receipts retain their owner.
        return {"slot":slot,"status":"REVOKED"}

    def logout(self,token,*,now):
        self._now(now)
        if self._sessions.pop(_hash(token),None) is None:raise PermissionError("session")
