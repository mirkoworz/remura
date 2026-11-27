# REMURA v0.8.95 LAB — 16/11/2026 13:22 CET
"""Synthetic custody simulation, never an external authority or live adapter.

A reservation in independent custody precedes any local mutation. A lost
acknowledgement leaves PENDING and blocks every subsequent operation. No
automatic reconciliation, takeover, reset, recovery or collection.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
import re
from cvd_incremental_persistence_v1 import open_store
from cvd_incremental_preview_v1 import checked_cutoff
from cvd_runtime_private_state_v1 import PERIOD

def need(ok):
    if not ok:raise ValueError("synthetic_custody_denied")

@dataclass(frozen=True)
class Pin:
    generation:str
    sequence:int
    phase:str
    cutoff_ms:int|None
    state_digest:str|None

class SyntheticCustody:
    """Test variable in a separate object, not durable or independently secured."""
    def __init__(self,generation,*,synthetic=False):
        need(synthetic is True and type(generation) is str and re.fullmatch("[0-9a-f]{32}",generation))
        self._pin=Pin(generation,0,"GENESIS",None,None)
        self._lock=Lock()
    def latest(self):
        with self._lock:return self._pin
    def reserve(self,expected,cutoff):
        checked_cutoff(cutoff)
        with self._lock:
            p=self._pin
            need(p==expected and p.phase in ("GENESIS","STABLE"))
            need(p.phase=="GENESIS" or cutoff==p.cutoff_ms+PERIOD)
            self._pin=Pin(p.generation,p.sequence+1,"PENDING",cutoff,p.state_digest)
            return self._pin
    def finalize(self,expected,status):
        with self._lock:
            p=self._pin
            need(p==expected and p.phase=="PENDING")
            need(status["status"]=="CURRENT_SYNTHETIC" and status["claim_ms"]==p.cutoff_ms==status["last_cutoff_ms"])
            d=status["state_digest"]
            need(type(d) is str and re.fullmatch("[0-9a-f]{64}",d))
            self._pin=Pin(p.generation,p.sequence,"STABLE",p.cutoff_ms,d)
            return self._pin

class Pinned:
    def __init__(self,store,custody,generation):
        self._store=store;self._custody=custody;self._generation=generation
    def _authority(self,expected,phase):
        p=self._custody.latest()
        need(type(expected) is Pin and p==expected and p.generation==self._generation and p.phase==phase)
        return p
    def status(self,expected):
        p=self._authority(expected,"STABLE")
        s=self._store.status()
        need(s["state_digest"]==p.state_digest and s["claim_ms"]==p.cutoff_ms==s["last_cutoff_ms"] and s["status"]=="CURRENT_SYNTHETIC")
        self._authority(expected,"STABLE")
        # Do not claim real independent protection; authority is a fixture object.
        return {**s,"synthetic_pin_matched":True,"independent_rollback_protection":False}
    def bootstrap(self,core,*,expected,cutoff,windows):
        p=self._authority(expected,"GENESIS")
        try:self._store.status()
        except FileNotFoundError:pass
        else:raise ValueError("synthetic_custody_existing_state")
        pending=self._custody.reserve(p,cutoff)
        self._store.initialize(cutoff)
        self._store.complete(core,cutoff=cutoff,windows=windows)
        s=self._store.status()
        stable=self._custody.finalize(pending,s)
        return stable,self.status(stable)
    def cycle(self,core,*,expected,cutoff,windows):
        p=self._authority(expected,"STABLE")
        self.status(p)
        checked_cutoff(cutoff)
        need(cutoff==p.cutoff_ms+PERIOD)
        pending=self._custody.reserve(p,cutoff)
        need(self._store.claim(cutoff) is True)
        self._store.complete(core,cutoff=cutoff,windows=windows)
        s=self._store.status()
        stable=self._custody.finalize(pending,s)
        return stable,self.status(stable)

@contextmanager
def open_pinned(root,custody,*,generation,synthetic=False):
    need(synthetic is True and type(custody) is SyntheticCustody and type(generation) is str)
    need(custody.latest().generation==generation)
    with open_store(root,synthetic=True) as store:
        yield Pinned(store,custody,generation)
