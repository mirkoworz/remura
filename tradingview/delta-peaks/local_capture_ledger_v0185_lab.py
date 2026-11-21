# REMURA TradingView v0.8.185 LAB — 21/11/2026 Europe/Rome
# Local, synthetic-only hash-chained slot evidence. Not external timestamp proof.
"""Fail-closed capture ledger to prevent SILENT local mutation within a supplied batch.

A self-authored SHA-256 chain is NOT independently anchored, cannot certify missing
market activity, and cannot provide authentic capture timestamps. No outcomes,
orderflow, trading orders or secrets are collected.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from hashlib import sha256
import json
import re
import sys
from holdout_freeze_v0182_lab import guard, phase, FreezeError
from m5_intake_gate_v0183_lab import parse_utc, M5, GRACE

HEX = re.compile(r"^[0-9a-f]{64}$")
ZERO = "0" * 64
MAX_SLOTS = 60
STATUSES = frozenset({"CAPTURED_TIMELY", "CAPTURED_LATE", "NOT_CAPTURED"})
class LedgerError(ValueError):
    pass

def digest(event: dict[str,object]) -> str:
    body = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(body.encode("ascii")).hexdigest()

def make_entry(slot: str, status: str, received: str | None, decision: str | None,
               previous: str) -> dict[str,object]:
    item: dict[str,object] = {
        "source": "OFFLINE_SYNTHETIC_LEDGER",
        "slot_close_utc": slot,
        "status": status,
        "received_utc": received,
        "decision_digest": decision,
        "previous_hash": previous,
    }
    item["entry_hash"] = digest(item)
    return item

def review(payload: object) -> dict[str,object]:
    result: dict[str,object] = {
        "schema":"remura.tradingview.capture_ledger.v0185.lab",
        "version":"0.8.185",
        "status":"INVALID_OR_UNATTESTED",
        "fold":"UNKNOWN",
        "entries":None,
        "timely":None,
        "late":None,
        "not_captured":None,
        "local_hash_chain_consistent":False,
        "independent_timestamp_anchor":False,
        "ledger_is_independently_signed":False,
        "market_coverage_attested":False,
        "future_outcomes_used":False,
        "institutional_edge_established":False,
        "automatic_capture_enabled":False,
        "decision":"NO_GO_LIVE",
    }
    try:
        check = guard()
        if check.get("protocol") != "CVD_PROSPECTIVE_V2_PINNED":
            raise LedgerError("frozen_protocol_invalid")
        if not isinstance(payload, dict) or set(payload) != {
            "source", "fold", "requested_closes_utc", "ledger"
        } or payload["source"] != "OFFLINE_SYNTHETIC_COMPLETE_PLAN":
            raise LedgerError("payload_shape_invalid")
        fold = payload["fold"]
        if fold not in ("HOLDOUT_1", "HOLDOUT_2"):
            raise LedgerError("fold_invalid")
        schedule, entries = payload["requested_closes_utc"], payload["ledger"]
        if (not isinstance(schedule,list) or not isinstance(entries,list) or
                not 1 <= len(schedule) <= MAX_SLOTS or len(entries) != len(schedule)):
            raise LedgerError("incomplete_or_oversized_plan")
        times = [parse_utc(s) for s in schedule]
        if any(t.minute%5 or t.second or t.microsecond or phase(t)!=fold for t in times):
            raise LedgerError("slot_not_M5_or_wrong_fold")
        if any(x>=y for x,y in zip(times,times[1:])):
            raise LedgerError("duplicate_or_unordered_slot")
        previous=ZERO
        timely=late=missing=0
        decisions=set()
        for s,close,event in zip(schedule,times,entries):
            if not isinstance(event,dict) or set(event) != {
                "source", "slot_close_utc", "status", "received_utc",
                "decision_digest", "previous_hash", "entry_hash"
            }:
                raise LedgerError("entry_shape_invalid")
            if (event["source"]!="OFFLINE_SYNTHETIC_LEDGER" or
                    event["slot_close_utc"]!=s or event["status"] not in STATUSES or
                    event["previous_hash"]!=previous or
                    not isinstance(event["entry_hash"],str) or
                    not HEX.fullmatch(event["entry_hash"])):
                raise LedgerError("entry_lineage_invalid")
            hashed = {k:v for k,v in event.items() if k!="entry_hash"}
            if digest(hashed) != event["entry_hash"]:
                raise LedgerError("hash_chain_tampered")
            previous = event["entry_hash"]
            if event["status"]=="NOT_CAPTURED":
                if event["received_utc"] is not None or event["decision_digest"] is not None:
                    raise LedgerError("not_captured_has_receipt")
                missing += 1
                continue
            decision=event["decision_digest"]
            if not isinstance(decision,str) or not HEX.fullmatch(decision) or decision in decisions:
                raise LedgerError("duplicate_or_bad_decision")
            decisions.add(decision)
            recv=parse_utc(event["received_utc"])
            if recv < close:
                raise LedgerError("capture_before_close")
            allowed=recv <= close + GRACE and recv < close + M5
            if event["status"] == "CAPTURED_TIMELY":
                if not allowed:raise LedgerError("false_timely_claim")
                timely+=1
            else:
                if allowed:raise LedgerError("false_late_claim")
                late+=1
        result.update(
            status="OFFLINE_UNANCHORED_CHAIN_CONSISTENT",
            fold=fold, entries=len(entries),
            timely=timely, late=late, not_captured=missing,
            local_hash_chain_consistent=True,
        )
    except (LedgerError, FreezeError, TypeError, ValueError, UnicodeError, OSError, KeyError, OverflowError):
        pass
    return result

def demo() -> dict[str,object]:
    slots = ["2026-11-23T00:05:00Z","2026-11-23T00:10:00Z","2026-11-23T00:15:00Z"]
    records=[]
    previous=ZERO
    for s,kind,received,decision in zip(
        slots,
        ("CAPTURED_TIMELY","CAPTURED_LATE","NOT_CAPTURED"),
        ("2026-11-23T00:07:00Z","2026-11-23T00:12:01Z",None),
        ("a"*64,"b"*64,None)
    ):
        rec=make_entry(s,kind,received,decision,previous)
        records.append(rec)
        previous=rec["entry_hash"]
    return {
        "source":"OFFLINE_SYNTHETIC_COMPLETE_PLAN",
        "fold":"HOLDOUT_1",
        "requested_closes_utc":slots,
        "ledger":records,
    }

def main(argv: list[str]) -> int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_TV_V0185_LEDGER=NO_GO_BAD_ARGUMENTS")
        return 2
    verdict=review(demo())
    if (verdict["status"]!="OFFLINE_UNANCHORED_CHAIN_CONSISTENT" or
            verdict["timely"]!=1 or verdict["late"]!=1 or verdict["not_captured"]!=1 or
            verdict["institutional_edge_established"]):
        print("REMURA_TV_V0185_LEDGER=NO_GO_INVALID_FIXTURE")
        return 3
    print(json.dumps(verdict,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
