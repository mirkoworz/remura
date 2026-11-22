#!/usr/bin/env python3
# REMURA COT v0.6 LAB — forward-only atomic capture on v0.5 synthetic sidecar.
"""Append *future synthetic observations* without importing overwritten legacy.

No Oracle, filesystem path, network, actual CFTC fetch or migration runner.
Legacy is quarantined: old first_seen cannot date an overwritten value.
All receipt times and provider names remain untrusted local claims.
"""
from __future__ import annotations
from hashlib import sha256
import json
import sqlite3

from cot_sidecar_cutover_v05_lab import SyntheticCutover
from cot_atomic_ingest_v02_lab import SOURCES
from cot_revision_lineage_v01_lab import RevisionError, normalized_rows, parsed_stamp

SCHEMA="remura.cot.forward_only_sidecar.v06.lab"
ENVELOPE_SCHEMA="remura.cot.forward_only_capture.v06.lab"

def pack(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True)

def digest(text):
    return sha256(text.encode("ascii")).hexdigest()

class ForwardOnlyCOT:
    def __init__(self, *, synthetic=False):
        if synthetic is not True:
            raise RevisionError("synthetic_only_no_live_cutover")
        self.fixture=SyntheticCutover(synthetic=True)
        self.fixture.migrate()
        self.db=self.fixture._db

    def close(self):
        self.fixture.close()

    def capture(self, rows, *, received_utc, source_claim, fail_after=None):
        at=parsed_stamp(received_utc)
        if type(source_claim) is not str or source_claim not in SOURCES:
            raise RevisionError("unsupported_source_claim")
        if fail_after not in (None,"event","versions"):
            raise RevisionError("invalid_synthetic_failpoint")
        clean=normalized_rows(rows,at)
        envelope=pack({"schema":ENVELOPE_SCHEMA,"source_claim":source_claim,
                       "local_received_at":received_utc,
                       "rows":[json.loads(packed) for *_,packed in clean]})
        h=digest(envelope)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            duplicate=self.db.execute(
                "SELECT 1 FROM cot_v05_capture_events WHERE envelope_sha256=?",
                (h,)).fetchone()
            if duplicate:
                self.db.execute("COMMIT")
                return {"schema":SCHEMA,"status":"EXACT_EVENT_IDEMPOTENT",
                        "new_versions":0,"new_event":False,"legacy_imported":False,
                        "scientific_admission":False}
            event_id=self.db.execute("""INSERT INTO cot_v05_capture_events
                (received_utc,source_claim,envelope_sha256,payload_json)
                VALUES(?,?,?,?)""",(received_utc,source_claim,h,envelope)).lastrowid
            if fail_after=="event":
                raise RuntimeError("synthetic_fault_after_event")
            inserted=0
            for dataset,code,report_date,rowhash,packed in clean:
                latest=self.db.execute("""SELECT v.version,v.received_utc,v.content_sha256
                    FROM cot_v05_current_head AS hd
                    JOIN cot_v05_versions AS v ON
                    v.dataset=hd.dataset AND v.code=hd.code AND
                    v.report_date=hd.report_date AND v.version=hd.version
                    WHERE hd.dataset=? AND hd.code=? AND hd.report_date=?""",
                    (dataset,code,report_date)).fetchone()
                if latest and latest[1]>received_utc:
                    raise RevisionError("nonmonotonic_local_receipt")
                if latest and latest[1]==received_utc and latest[2]!=rowhash:
                    raise RevisionError("same_receipt_conflicting_revision")
                if latest and latest[2]==rowhash:
                    continue
                version=1 if latest is None else latest[0]+1
                self.db.execute("""INSERT INTO cot_v05_versions
                    (dataset,code,report_date,version,event_id,received_utc,
                     content_sha256,payload_json)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (dataset,code,report_date,version,event_id,
                     received_utc,rowhash,packed))
                self.db.execute("""INSERT INTO cot_v05_current_head
                    (dataset,code,report_date,version) VALUES(?,?,?,?)
                    ON CONFLICT(dataset,code,report_date)
                    DO UPDATE SET version=excluded.version""",
                    (dataset,code,report_date,version))
                inserted+=1
            if fail_after=="versions":
                raise RuntimeError("synthetic_fault_after_versions")
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise
        return {"schema":SCHEMA,"status":"FORWARD_ONLY_LOCAL_CAPTURE_UNATTESTED",
                "new_versions":inserted,"new_event":True,"legacy_imported":False,
                "scientific_admission":False}

    def as_of(self, *, dataset, code, report_date, decision_utc):
        from cot_revision_lineage_v01_lab import identify
        at=parsed_stamp(decision_utc)
        if identify(dataset,code,report_date)>at.date():
            raise RevisionError("decision_before_report_reference")
        row=self.db.execute("""SELECT v.version,v.received_utc,v.content_sha256,
                         v.payload_json,e.envelope_sha256,e.payload_json,e.source_claim
            FROM cot_v05_versions AS v JOIN cot_v05_capture_events AS e
                 ON e.event_id=v.event_id
            WHERE v.dataset=? AND v.code=? AND v.report_date=?
                AND v.received_utc<=?
            ORDER BY v.version DESC LIMIT 1""",
            (dataset,code,report_date,decision_utc)).fetchone()
        if row is None:
            return {"status":"UNKNOWN_NO_FORWARD_CAPTURE_AT_DECISION",
                    "positions":None,"version":None,
                    "legacy_fallback_allowed":False,"scientific_admission":False}
        version,received,row_hash,payload,event_hash,event_payload,source=row
        if digest(payload)!=row_hash or digest(event_payload)!=event_hash:
            raise RevisionError("sidecar_payload_corrupted")
        event=json.loads(event_payload)
        values=json.loads(payload)
        if (type(values) is not list or len(values)!=4 or
                values[:3]!=[dataset,code,report_date] or
                values not in event.get("rows",[]) or
                event.get("local_received_at")!=received or
                event.get("source_claim")!=source):
            raise RevisionError("capture_provenance_mismatch")
        return {"status":"FORWARD_ONLY_LOCAL_VERSION_UNATTESTED",
                "positions":values[3],"version":version,"local_received_utc":received,
                "event_sha256":event_hash,"legacy_fallback_allowed":False,
                "independent_first_seen_verified":False,"scientific_admission":False}

    def audit(self):
        """Forward-only checks after ingest; v0.5 audit is schema-only by design."""
        state=self.fixture._sidecar_state()
        from cot_sidecar_cutover_v05_lab import SIDECAR_TABLES,SIDECAR_TRIGGERS
        if state["tables"]!=sorted(SIDECAR_TABLES) or state["triggers"]!=sorted(SIDECAR_TRIGGERS):
            raise RevisionError("sidecar_schema_changed")
        if self.fixture._legacy_hash()!=self.fixture._legacy_at_cutover:
            raise RevisionError("legacy_modified")
        if self.db.execute("PRAGMA foreign_key_check").fetchall():
            raise RevisionError("foreign_keys_failed")
        evs=self.db.execute("""SELECT event_id,received_utc,source_claim,
                          envelope_sha256,payload_json FROM cot_v05_capture_events""").fetchall()
        versions=self.db.execute("""SELECT dataset,code,report_date,version,event_id,
                    received_utc,content_sha256,payload_json FROM cot_v05_versions""").fetchall()
        heads=self.db.execute("""SELECT dataset,code,report_date,version
                        FROM cot_v05_current_head""").fetchall()
        if max(map(len,(evs,versions,heads)))>20000:
            raise RevisionError("synthetic_audit_row_limit")
        captures={}
        for eid,utc,source,h,payload in evs:
            parsed_stamp(utc)
            if digest(payload)!=h:
                raise RevisionError("event_hash_corrupt")
            data=json.loads(payload)
            if data.get("schema")!=ENVELOPE_SCHEMA or data.get("local_received_at")!=utc or data.get("source_claim")!=source or source not in SOURCES:
                raise RevisionError("event_metadata_corrupt")
            captures[eid]=(utc,data.get("rows"))
        chains={}
        for dataset,code,date,version,eid,utc,rowhash,payload in versions:
            if digest(payload)!=rowhash:
                raise RevisionError("version_hash_corrupt")
            parsed_stamp(utc)
            source=captures.get(eid)
            data=json.loads(payload)
            if (source is None or source[0]!=utc or data not in source[1] or
                    data[:3]!=[dataset,code,date]):
                raise RevisionError("version_source_mismatch")
            chains.setdefault((dataset,code,date),[]).append((version,utc))
        headmap={(d,c,r):v for d,c,r,v in heads}
        if set(headmap)!=set(chains):
            raise RevisionError("head_key_set_mismatch")
        for key,seq in chains.items():
            ordered=sorted(seq)
            if [v for v,_ in ordered]!=list(range(1,len(ordered)+1)):
                raise RevisionError("version_gap")
            if any(x[1]>=y[1] for x,y in zip(ordered,ordered[1:])):
                raise RevisionError("revision_clocks_not_increasing")
            if headmap.get(key)!=ordered[-1][0]:
                raise RevisionError("stale_current_head")
        return {"schema":SCHEMA,"status":"FORWARD_ONLY_FIXTURE_CONSISTENT_UNATTESTED",
                "events":len(evs),"versions":len(versions),"heads":len(heads),
                "legacy_quarantined":True,"oracle_examined":False,
                "independent_provenance":False,"live_migration_permitted":False}
