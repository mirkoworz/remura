# REMURA v0.8.104 LAB — 16/11/2026 15:05 CET
"""Synthetic historical verification before rotation. No durable authority.
Historical pin is audit-only, never an authorization to restore or publish.
"""
import base64,hashlib,json,subprocess
from contextlib import contextmanager
from cvd_joint_rotating_publication_v1 import RotatingJoint,open_rotating_joint
from cvd_joint_encrypted_v1 import NODE,MAX_CIPHER,NAME
from cvd_joint_backup_v1 import read_exact
from cvd_joint_publication_v1 import validate,MAX_FILE,need
from cvd_runtime_private_state_v1 import encoded,digest,_no_duplicates,PERIOD

def sha(raw):return hashlib.sha256(raw).hexdigest()

class History:
    """Bounded append-only fixture receipts, separate in-memory object."""
    def __init__(self,custody,*,synthetic=False):
        need(synthetic is True and custody.latest().phase=="GENESIS")
        self.c=custody;self._receipts=()
    def empty(self):return not self._receipts
    def record(self,p,raw):
        need(p==self.c.latest() and p.phase=="STABLE" and 1<=p.sequence<=96)
        need(p.sequence==len(self._receipts)+1 and type(raw) is bytes and 0<len(raw)<=MAX_CIPHER)
        if self._receipts:
            old=self._receipts[-1][0]
            need(p.generation==old.generation and p.cutoff_ms==old.cutoff_ms+PERIOD)
        self._receipts=self._receipts+((p,sha(raw)),)
    def receipt(self,p,seq):
        need(p==self.c.latest() and p.phase=="STABLE" and 1<=seq<=p.sequence)
        need(len(self._receipts)==p.sequence and self._receipts[-1][0]==p)
        return self._receipts[seq-1]

def historical_open(raw,old,key):
    # Explicit old AAD used only for authenticated inspection. Never modify
    # the current custody or reuse an old pin in the current decode API.
    try:
        need(type(raw) is bytes and 0<len(raw)<=MAX_CIPHER and old.phase=="STABLE")
        e=json.loads(raw,object_pairs_hook=_no_duplicates)
        need(type(e) is dict and set(e)=={"v","nonce","ct","tag"} and encoded(e)==raw)
        req={"synthetic":True,"mode":"open","key":key.hex(),"generation":old.generation,
             "sequence":old.sequence,"cutoff_ms":old.cutoff_ms,"data":e}
        wire=encoded(req);need(len(wire)<=MAX_CIPHER+4096)
        r=subprocess.run(["node",str(NODE)],input=wire,stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL,timeout=20,check=True)
        need(0<len(r.stdout)<=MAX_CIPHER)
        out=json.loads(r.stdout,object_pairs_hook=_no_duplicates)
        need(type(out) is dict and set(out)=={"plaintext"} and type(out["plaintext"]) is str)
        plain=base64.b64decode(out["plaintext"],validate=True)
        need(0<len(plain)<=MAX_FILE and base64.b64encode(plain).decode("ascii")==out["plaintext"])
        w=json.loads(plain,object_pairs_hook=_no_duplicates)
        need(type(w) is dict and set(w)=={"state","sha256"} and encoded(w)==plain)
        s=w["state"];need(w["sha256"]==digest(s)==old.state_digest)
        l=validate(s,old.generation)
        need(s["cache"]["claim_ms"]==old.cutoff_ms and l.summary()["cycles_recorded"]==old.sequence)
        return s
    except (OSError,subprocess.SubprocessError,ValueError,TypeError,KeyError):
        raise ValueError("synthetic_historical_backup_denied") from None

class HistoricalJoint(RotatingJoint):
    def __init__(self,j,history):
        super().__init__(j,j.dest,j.dest_guard);self.h=history
    def audit(self,p):
        out=super().status(p)
        current,recorded=self.h.receipt(p,p.sequence)
        need(current==p and sha(read_exact(self.dest,self.name(p.sequence)))==recorded)
        verified=1
        if p.sequence>1:
            old,ct_digest=self.h.receipt(p,p.sequence-1)
            need(old.generation==p.generation and old.cutoff_ms==p.cutoff_ms-PERIOD)
            raw=read_exact(self.dest,self.name(old.sequence))
            need(sha(raw)==ct_digest)
            previous=historical_open(raw,old,self._key)
            now,_=self.read()
            need(digest(now)==p.state_digest)
            a,b=previous["archive"],now["archive"]
            need(a["first_cutoff"]==b["first_cutoff"] and a["cycles"]==b["cycles"])
            need(a["records"]==b["records"][:-1])
            need(read_exact(self.dest,self.name(old.sequence))==raw)
            verified=2
        self.authority(p,"STABLE");self.both()
        return {**out,"authenticated_retained_copies":verified,"historical_pin_audit_only":True}
    def bootstrap(self,core,*,expected,cutoff,windows,cycles):
        need(self.h.empty())
        return super().bootstrap(core,expected=expected,cutoff=cutoff,windows=windows,cycles=cycles)
    def cycle(self,core,*,expected,cutoff,windows):
        self.audit(expected)
        return super().cycle(core,expected=expected,cutoff=cutoff,windows=windows)
    def publish(self,pending,s):
        stable,_=super().publish(pending,s)
        raw=read_exact(self.dest,self.name(stable.sequence))
        need(raw==read_exact(self.fd,NAME))
        # If receipt creation fails after stable finalization, this wrapper
        # may not audit/cycle/prune. Never reconstruct receipt from disk.
        self.h.record(stable,raw)
        return stable,self.audit(stable)
    def prune(self,expected,*,allow_synthetic_prune=False):
        need(allow_synthetic_prune is True)
        need(self.audit(expected)["authenticated_retained_copies"]==2)
        super().prune(expected,allow_synthetic_prune=True)
        return self.audit(expected)

@contextmanager
def open_historical_joint(source,destination,custody,*,generation,key,history,synthetic=False):
    need(synthetic is True and type(history) is History and history.c is custody)
    with open_rotating_joint(source,destination,custody,generation=generation,key=key,synthetic=True) as j:
        yield HistoricalJoint(j,history)
