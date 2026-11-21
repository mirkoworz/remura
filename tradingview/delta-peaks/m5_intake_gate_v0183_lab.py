# REMURA TradingView v0.8.183 LAB — 21/11/2026 Europe/Rome
# Offline synthetic event timing gate ONLY; zero trading/capture/PNL functions.
"""Preregistered V2 M5 capture arrival check, independent of outcome values.

The program refuses late or duplicate candidates before they could be assigned.
It never reorders by future quality, replaces absent pairs, or accesses signals.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import re
import sys
from holdout_freeze_v0182_lab import guard, phase, FreezeError

SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_ITEMS = 60
M5 = timedelta(minutes=5)
GRACE = timedelta(seconds=120)

class TimingError(ValueError):
    pass

def parse_utc(s: object) -> datetime:
    if not isinstance(s,str) or len(s)>35:
        raise TimingError("timestamp_invalid")
    try:
        dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise TimingError("timestamp_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):
        raise TimingError("timestamp_timezone")
    return dt.astimezone(timezone.utc)

def evaluate(events: object) -> dict[str,object]:
    output: dict[str,object] = {
        "schema":"remura.tradingview.m5_intake_gate.v0183.lab",
        "version":"0.8.183", "mode":"OFFLINE_FIXTURE_ONLY",
        "status":"NO_DATA", "eligible":0, "late":0, "out_of_window":0,
        "development":0, "holdout_1":0, "holdout_2":0,
        "provenance_attested":False, "outcomes_evaluated":False,
        "edge_claim_allowed":False, "capture_activated":False,
        "decision":"NO_GO_LIVE",
    }
    try:
        # Don't check any event if pinned protocol or source is drifted.
        freeze=guard()
        if freeze["protocol"]!="CVD_PROSPECTIVE_V2_PINNED":
            raise TimingError("protocol_unpinned")
        if not isinstance(events,list) or not 1<=len(events)<=MAX_ITEMS:
            raise TimingError("items_missing_or_too_many")
        rows=[]
        seen_ids=set()
        seen_times=set()
        for entry in events:
            if not isinstance(entry,dict) or set(entry)!={
                "source","decision_digest","bar_close_utc","next_close_utc","received_utc"
            }:
                raise TimingError("entry_shape_invalid")
            digest=entry["decision_digest"]
            if (entry["source"]!="OFFLINE_SYNTHETIC_M5"
                    or not isinstance(digest,str) or not SHA.fullmatch(digest)
                    or digest in seen_ids):
                raise TimingError("untrusted_or_duplicate_decision")
            seen_ids.add(digest)
            close=parse_utc(entry["bar_close_utc"])
            nxt=parse_utc(entry["next_close_utc"])
            recv=parse_utc(entry["received_utc"])
            if (close.minute%5 or close.second or close.microsecond
                    or nxt-close!=M5):
                raise TimingError("non_m5_close")
            # A conflicting or duplicate close timestamp cannot be assigned
            # silently even if the decision IDs differ.
            if close in seen_times:
                raise TimingError("duplicate_or_conflicting_m5_close")
            seen_times.add(close)
            if recv<close:
                raise TimingError("received_before_close")
            rows.append((close,recv,nxt))
        eligible=late=out=development=h1=h2=0
        # Preserve caller order; no reorder based on outcomes or later quality.
        for close,received,nxt in rows:
            p=phase(close)
            if p=="OUTSIDE_RESERVED_WINDOWS":
                out+=1
                continue
            if received>close+GRACE or received>=nxt:
                late+=1
                continue
            eligible+=1
            if p=="DEVELOPMENT_FROZEN": development+=1
            elif p=="HOLDOUT_1": h1+=1
            elif p=="HOLDOUT_2": h2+=1
        output.update(status="BOUNDARIES_REVIEWED_OFFLINE_ONLY",
                      eligible=eligible, late=late, out_of_window=out,
                      development=development, holdout_1=h1, holdout_2=h2)
    except (TimingError, FreezeError, ValueError, TypeError, OSError,UnicodeError):
        output["status"]="INVALID_OR_PROTOCOL_DRIFT_NO_GO"
    return output

def main(argv: list[str])->int:
    if argv!=["--synthetic-self-check"]:
        print("REMURA_V0183_INTAKE=NO_GO_BAD_ARGUMENTS")
        return 2
    e=[{"source":"OFFLINE_SYNTHETIC_M5","decision_digest":"a"*64,
        "bar_close_utc":"2026-11-23T00:05:00Z",
        "next_close_utc":"2026-11-23T00:10:00Z",
        "received_utc":"2026-11-23T00:06:59Z"}]
    answer=evaluate(e)
    if answer["status"]!="BOUNDARIES_REVIEWED_OFFLINE_ONLY" or answer["holdout_1"]!=1:
        print("REMURA_V0183_INTAKE=NO_GO_FIXTURE_MISMATCH")
        return 3
    print(json.dumps(answer,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
