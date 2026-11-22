# REMURA Shark Science COT v0.4 LAB - global integrity audit, 22/11/2026.
"""Read-only reconciliation of the synthetic v0.2/v0.3 append-only COT store.

Per-key as_of() alone does not detect a deleted current_head or an event whose
provenance was corrupted in another market. This *global* audit does.
Only accepts an explicitly synthetic SQLite connection; never accepts file
paths, Oracle, network/Secrets, or the live production collector.
Local hashes and trigger existence are NOT independent time/source witnesses.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import sqlite3

from cot_atomic_ingest_v02_lab import SCHEMA, SOURCES
from cot_revision_lineage_v01_lab import RevisionError, parsed_stamp

REQUIRED_TRIGGERS=frozenset(("events_no_update","events_no_delete",
                              "versions_no_update","versions_no_delete"))
MAX_ROWS=20000


def audit_fixture(db, *, synthetic=False):
    if synthetic is not True or not isinstance(db,sqlite3.Connection):
        raise RevisionError("synthetic_connection_required")
    reasons=set()
    triggers={x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'")}
    if not REQUIRED_TRIGGERS.issubset(triggers):
        reasons.add("IMMUTABILITY_TRIGGER_MISSING")
    if db.execute("PRAGMA foreign_key_check").fetchall():
        reasons.add("FOREIGN_KEY_BROKEN")
    events=db.execute("""SELECT event_id,source_claim,received_at,
        envelope_sha256,envelope_json,row_count FROM capture_events""").fetchall()
    versions=db.execute("""SELECT dataset,code,report_date,version,event_id,
        received_at,content_sha256,content_payload_json FROM versions""").fetchall()
    heads=db.execute("""SELECT dataset,code,report_date,version
        FROM current_head""").fetchall()
    if any(len(v)>MAX_ROWS for v in (events,versions,heads)):
        raise RevisionError("audit_bounded_rows_exceeded")

    envelopes={}
    for event_id,source,at,digest,packed,count in events:
        try:
            parsed_stamp(at)
            payload=json.loads(packed)
            if not isinstance(payload,dict):
                raise ValueError()
            canonical=json.dumps(payload,sort_keys=True,
                separators=(",",":"),ensure_ascii=True)
            if canonical != packed:
                reasons.add("EVENT_CANONICAL_FORM_INVALID")
            if sha256(packed.encode("ascii")).hexdigest()!=digest:
                reasons.add("EVENT_HASH_MISMATCH")
            if source not in SOURCES:
                reasons.add("EVENT_SOURCE_INVALID")
            if (payload.get("schema")!=SCHEMA or
                payload.get("local_received_at")!=at or
                payload.get("source_claim")!=source):
                reasons.add("EVENT_METADATA_MISMATCH")
            rows=payload.get("rows")
            if not isinstance(rows,list) or type(count) is not int or len(rows)!=count:
                reasons.add("EVENT_ROWCOUNT_INVALID")
            envelopes[event_id]=(at,rows if isinstance(rows,list) else [])
        except (ValueError,TypeError,UnicodeError,OverflowError,RevisionError):
            reasons.add("EVENT_PAYLOAD_INVALID")

    by_key=defaultdict(list)
    for dataset,code,report,version,event_id,at,digest,packed in versions:
        key=(dataset,code,report)
        by_key[key].append((version,at))
        try:
            parsed_stamp(at)
            payload=json.loads(packed)
            if (type(payload) is not list or len(payload)!=4 or
                    payload[:3]!=[dataset,code,report]):
                reasons.add("VERSION_KEY_OR_SHAPE_INVALID")
            if sha256(packed.encode("ascii")).hexdigest()!=digest:
                reasons.add("VERSION_HASH_MISMATCH")
            event=envelopes.get(event_id)
            if event is None:
                reasons.add("VERSION_EVENT_MISSING")
            else:
                if event[0]!=at:
                    reasons.add("VERSION_EVENT_CLOCK_MISMATCH")
                if payload not in event[1]:
                    reasons.add("VERSION_PAYLOAD_NOT_IN_EVENT")
        except (ValueError,TypeError,UnicodeError,OverflowError,RevisionError):
            reasons.add("VERSION_PAYLOAD_INVALID")

    current={(dataset,code,report):version for dataset,code,report,version in heads}
    if set(current)!=set(by_key):
        reasons.add("MISSING_OR_EXTRA_CURRENT_HEAD")
    for key,history in by_key.items():
        ordered=sorted(history)
        actual_versions=[v for v,_ in ordered]
        if actual_versions!=list(range(1,len(ordered)+1)):
            reasons.add("NONCONTIGUOUS_VERSIONS")
        if any(a[1]>=b[1] for a,b in zip(ordered,ordered[1:])):
            reasons.add("REVISION_CLOCK_NOT_INCREASING")
        if current.get(key)!=ordered[-1][0]:
            reasons.add("CURRENT_HEAD_NOT_LATEST")
    return {
        "schema":"remura.cot.global_integrity.v04.lab",
        "status":("QUARANTINE_FIXTURE_INTEGRITY_FAILURE" if reasons else
                  "UNKNOWN_EMPTY_FIXTURE" if not events else
                  "LOCAL_FIXTURE_CONSISTENT_UNATTESTED"),
        "issues":sorted(reasons),
        "counts":{"capture_events":len(events),
                  "versions":len(versions),"heads":len(heads)},
        "independent_first_seen_verified":False,
        "real_oracle_examined":False,
        "live_upgrade_allowed":False,
        "provider_calls":0,
        "write_operations_performed":0,
    }
