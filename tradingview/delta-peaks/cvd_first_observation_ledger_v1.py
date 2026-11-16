# REMURA v0.8.95 LAB — 16/11/2026 13:22 CET
"""Synthetic first-observation ledger, bounded in memory, not a persisted archive.

A cohort is exactly N consecutive 15-minute fixed cutoffs, three new M5 slots
per cutoff. No retroactive baseline import. Empty verified window vs unobserved
window are distinct. Raw rows remain private fixture data; summary has counts
and chain head only. No outcomes, trade, market calendar or scientific promotion.
"""
import json,re
from copy import deepcopy
from cvd_incremental_preview_v1 import checked_cutoff
from cvd_archive_preview_v1 import validate_windows,MIN_CLOSE_MS
from cvd_runtime_private_state_v1 import encoded,digest,PERIOD,DELAY
from cvd_telemetry_preview_v1 import M5
MAX_CYCLES=96
MAX_BYTES=8*1024*1024
GAPS={"COLLECTION_NOT_ATTEMPTED","COLLECTION_UNCERTAIN"}
SCHEMA="remura.tv.first_observation.synthetic.v1"
def need(ok):
    if not ok:raise ValueError("synthetic_archive_denied")

class Ledger:
    def __init__(self,*,cohort,first_cutoff,cycles,synthetic=False):
        need(synthetic is True and type(cohort) is str and re.fullmatch("[0-9a-f]{32}",cohort))
        checked_cutoff(first_cutoff)
        need(type(cycles) is int and 1<=cycles<=MAX_CYCLES and first_cutoff-DELAY-2*M5>=MIN_CLOSE_MS)
        self._scope={"schema":SCHEMA,"cohort":cohort,"first_cutoff":first_cutoff,"cycles":cycles}
        self._head=digest(self._scope)
        self._records=()
        self._bytes=0
    def _expected(self,cutoff):
        need(len(self._records)<self._scope["cycles"] and type(cutoff) is int and cutoff==self._scope["first_cutoff"]+len(self._records)*PERIOD)
        checked_cutoff(cutoff)
        return cutoff-DELAY-2*M5,cutoff-DELAY
    def _append(self,cutoff,kind,window,reason,stats):
        a,z=self._expected(cutoff)
        body={"prev":self._head,"cutoff_ms":cutoff,"start_ms":a,"end_ms":z,
              "kind":kind,"window":window,"reason":reason,"stats":stats}
        wrapper={"record":body,"sha256":digest(body)}
        raw=encoded(wrapper)
        need(self._bytes+len(raw)<=MAX_BYTES)
        self._records=self._records+(raw,)
        self._bytes+=len(raw);self._head=wrapper["sha256"]
        return self.summary()
    def observe(self,*,cutoff,window):
        a,z=self._expected(cutoff)
        need(type(window) is dict and (window.get("start_ms"),window.get("end_ms"))==(a,z))
        valid,stats=validate_windows([window],as_of_ms=cutoff)
        need(all(r["bar_close_ms"]<=r["received_at_ms"]<=cutoff for r,_,_ in valid))
        return self._append(cutoff,"OBSERVED",deepcopy(window),None,stats)
    def gap(self,*,cutoff,reason):
        need(type(reason) is str and reason in GAPS)
        return self._append(cutoff,"UNOBSERVED",None,reason,None)
    def summary(self):
        seen=missing=unknown=duplicates=0
        for raw in self._records:
            b=json.loads(raw)["record"]
            if b["kind"]=="UNOBSERVED":unknown+=3
            else:
                seen+=b["stats"]["valid_unique_bars"]
                missing+=b["stats"]["missing_requested_slots"]
                duplicates+=b["stats"]["duplicate_rows"]
        return {"origin":"SYNTHETIC","head":self._head,"cycles_recorded":len(self._records),
                "cycles_planned":self._scope["cycles"],"slots_observed":seen,
                "slots_empty_at_first_observation":missing,"slots_unobserved":unknown,
                "slots_not_yet_recorded":3*(self._scope["cycles"]-len(self._records)),
                "duplicate_rows":duplicates,"serialized_record_bytes":self._bytes,
                "complete_schedule_recorded":len(self._records)==self._scope["cycles"],
                "scientific_admission":False,"independent_provenance":False}
    def synthetic_records(self,*,explicit=False):
        need(explicit is True)
        return self._records

def verify(*,cohort,first_cutoff,cycles,records,expected_head,synthetic=False):
    need(synthetic is True and type(records) is tuple and len(records)<=MAX_CYCLES and type(expected_head) is str and re.fullmatch("[0-9a-f]{64}",expected_head))
    need(all(type(raw) is bytes for raw in records) and sum(map(len,records))<=MAX_BYTES)
    ledger=Ledger(cohort=cohort,first_cutoff=first_cutoff,cycles=cycles,synthetic=True)
    for raw in records:
        w=json.loads(raw)
        need(type(w) is dict and set(w)=={"record","sha256"} and encoded(w)==raw)
        b=w["record"];need(type(b) is dict and b.get("prev")==ledger._head and w["sha256"]==digest(b))
        if b.get("kind")=="OBSERVED":ledger.observe(cutoff=b["cutoff_ms"],window=b["window"])
        elif b.get("kind")=="UNOBSERVED":ledger.gap(cutoff=b["cutoff_ms"],reason=b["reason"])
        else:raise ValueError("synthetic_archive_kind")
        need(ledger._records[-1]==raw)
    need(ledger._head==expected_head)
    return ledger.summary()
