# REMURA v0.8.90 LAB — 16/11/2026 13:04 CET
"""Synthetic-only rolling input cache, no persistence/network or live integration.
Observations frozen at their first cutoff; missing slots are not backfilled.
Exact equality to a full re-read only when the original rows did not change.
"""
from copy import deepcopy
from cvd_archive_preview_v1 import validate_windows
from cvd_private_runtime_preview_v1 import plan
from cvd_runtime_private_state_v1 import bucket,PERIOD
from cvd_telemetry_preview_v1 import M5
import json
MAX_BYTES=8*1024*1024
def need(ok):
    if not ok:raise ValueError("incremental_denied")
def checked_cutoff(now):
    need(type(now) is int and bucket(now)==now)
    return plan(now)
def ranges(windows):
    need(type(windows) is list and all(type(w) is dict for w in windows))
    return [(w.get("start_ms"),w.get("end_ms")) for w in windows]
def bounded(windows):
    need(len(json.dumps(windows,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode("ascii"))<=MAX_BYTES)
def check(windows,expected,now):
    need(ranges(windows)==expected)
    validate_windows(windows,as_of_ms=now)
    bounded(windows)
def copy_pages(windows):
    return deepcopy(windows)
def repage(expected,rows):
    return [{"start_ms":a,"end_ms":b,"rows":[r for r in rows if a<=r["bar_close_ms"]<=b]} for a,b in expected]
class RollingPreview:
    def __init__(self,*,now,windows,synthetic=False):
        need(synthetic is True)
        expected=checked_cutoff(now)
        check(windows,expected,now)
        self._windows=copy_pages(windows)
        self._now=now
    def next_ranges(self,now):
        expected=checked_cutoff(now)
        need(now==self._now+PERIOD)
        prev=checked_cutoff(self._now)
        a,b=prev[-1][1]+M5,expected[-1][1]
        need(b-a==2*M5 and a>=expected[0][0])
        return [(a,b)]
    def advance(self,*,now,windows):
        expected=checked_cutoff(now)
        new=self.next_ranges(now)
        check(windows,new,now)
        rows=[r for w in self._windows+windows for r in w["rows"]]
        candidate=repage(expected,rows)
        # Repacking must keep all still-in-range rows through exact duplicate checks;
        # overflow, invalid scope or conflicting rows fail before state update.
        check(candidate,expected,now)
        self._windows=copy_pages(candidate)
        self._now=now
        return self.summary()
    def summary(self):
        _,stats=validate_windows(self._windows,as_of_ms=self._now)
        return {**stats,"cutoff_ms":self._now,"origin":"SYNTHETIC",
                "first_observation_frozen":True,"scientific_admission":False,
                "persistent":False,"independent_provenance":False}
    def compare_reference(self,windows):
        expected=checked_cutoff(self._now)
        check(windows,expected,self._now)
        # Compare complete validated raw row multisets (including duplicates),
        # not just count or aggregate, without returning raw records.
        def groups(ws):
            g={}
            for w in ws:
                for r in w["rows"]:
                    g.setdefault(r["bar_close_ms"],[]).append(json.dumps(r,sort_keys=True,ensure_ascii=True,separators=(",",":")))
            return {k:sorted(v) for k,v in g.items()}
        old,new=groups(self._windows),groups(windows)
        count=sum(old.get(k)!=new.get(k) for k in set(old)|set(new))
        return {"status":"EXACT_INPUT_MATCH" if not count else "INPUT_DIVERGENCE_NO_PROMOTION",
                "differing_slots":count,"scientific_admission":False,
                "raw_returned":False,"persistent":False}
