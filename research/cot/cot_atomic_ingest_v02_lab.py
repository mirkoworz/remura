# REMURA Shark Science - COT atomic ingest v0.2 LAB (22 Nov 2026, Europe/Rome)
"""Synthetic-only atomic capture event + immutable revision + current pointer.

No network, Oracle, file database, production collector, or third-party
timestamp. A source string and a local clock are *claims*, not external proof.
A single capture envelope binds source claim, rows and local receipt time.
All event, versions and read-head changes share ONE SQLite transaction.
"""
from __future__ import annotations

from hashlib import sha256
import json
import sqlite3

from cot_revision_lineage_v01_lab import (
    RevisionError, identify, normalized_rows, parsed_stamp,
)

SCHEMA = "remura.cot.atomic_capture.v02.lab"
SOURCES = frozenset(("CFTC_PRIMARY_CLAIM", "CFTC_FALLBACK_CLAIM"))


class AtomicOfflineCOTStore:
    """Only in-memory fixture. No constructor parameter accepts a db path."""

    def __init__(self, *, synthetic=False):
        if synthetic is not True:
            raise RevisionError("offline_synthetic_opt_in_required")
        self._db = sqlite3.connect(":memory:", isolation_level=None)
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript("""
            CREATE TABLE capture_events(
                event_id INTEGER PRIMARY KEY,
                source_claim TEXT NOT NULL, received_at TEXT NOT NULL,
                envelope_sha256 TEXT NOT NULL UNIQUE,
                envelope_json TEXT NOT NULL, row_count INTEGER NOT NULL
            );
            CREATE TABLE versions(
                dataset TEXT NOT NULL, code TEXT NOT NULL,
                report_date TEXT NOT NULL, version INTEGER NOT NULL,
                event_id INTEGER NOT NULL, received_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL, content_payload_json TEXT NOT NULL,
                PRIMARY KEY(dataset,code,report_date,version),
                FOREIGN KEY(event_id) REFERENCES capture_events(event_id)
            );
            CREATE INDEX versions_asof ON versions(
                dataset,code,report_date,received_at);
            CREATE TABLE current_head(
                dataset TEXT NOT NULL, code TEXT NOT NULL, report_date TEXT NOT NULL,
                version INTEGER NOT NULL,
                PRIMARY KEY(dataset,code,report_date),
                FOREIGN KEY(dataset,code,report_date,version)
                  REFERENCES versions(dataset,code,report_date,version)
            );
            CREATE TRIGGER events_no_update BEFORE UPDATE ON capture_events
              BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
            CREATE TRIGGER events_no_delete BEFORE DELETE ON capture_events
              BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
            CREATE TRIGGER versions_no_update BEFORE UPDATE ON versions
              BEGIN SELECT RAISE(ABORT,'immutable_version'); END;
            CREATE TRIGGER versions_no_delete BEFORE DELETE ON versions
              BEGIN SELECT RAISE(ABORT,'immutable_version'); END;
        """)

    def close(self):
        self._db.close()

    def counts(self):
        return tuple(self._db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                     for table in ("capture_events", "versions", "current_head"))

    def ingest(self, rows, *, received_utc, source_claim, fail_after_row=None):
        """A fixture failpoint injects a fault *inside* the transaction."""
        stamp = parsed_stamp(received_utc)
        if source_claim not in SOURCES or type(source_claim) is not str:
            raise RevisionError("unknown_source_claim")
        clean = normalized_rows(rows, stamp)
        if fail_after_row is not None and (
            type(fail_after_row) is not int or fail_after_row < 1
        ):
            raise RevisionError("invalid_fixture_failpoint")

        envelope = {
            "schema": SCHEMA,
            "source_claim": source_claim,
            "local_received_at": received_utc,
            "rows": [json.loads(packed) for _, _, _, _, packed in clean],
        }
        blob = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        envelope_hash = sha256(blob.encode("ascii")).hexdigest()

        self._db.execute("BEGIN IMMEDIATE")
        try:
            duplicate = self._db.execute(
                "SELECT event_id FROM capture_events WHERE envelope_sha256=?",
                (envelope_hash,)
            ).fetchone()
            if duplicate:
                self._db.execute("COMMIT")
                return {"status": "IDEMPOTENT_SYNTHETIC_REPLAY",
                        "new_versions": 0, "event_committed": False,
                        "external_attestation": False, "live_use_allowed": False}

            cursor = self._db.execute(
                """INSERT INTO capture_events
                (source_claim,received_at,envelope_sha256,envelope_json,row_count)
                VALUES(?,?,?,?,?)""",
                (source_claim, received_utc, envelope_hash, blob, len(clean)),
            )
            event_id = cursor.lastrowid
            n = 0
            for index, (dataset, code, report_date, digest, packed) in enumerate(clean, 1):
                prior = self._db.execute("""
                    SELECT v.version,v.received_at,v.content_sha256 FROM current_head h
                    JOIN versions v ON (v.dataset=h.dataset AND v.code=h.code
                        AND v.report_date=h.report_date AND v.version=h.version)
                    WHERE h.dataset=? AND h.code=? AND h.report_date=?
                """, (dataset, code, report_date)).fetchone()
                if prior is not None and prior[1] > received_utc:
                    raise RevisionError("nonmonotonic_local_capture")
                if prior is not None and prior[1] == received_utc and prior[2] != digest:
                    raise RevisionError("same_clock_conflicting_values")
                if prior is None or prior[2] != digest:
                    version = 1 if prior is None else prior[0] + 1
                    self._db.execute("""
                        INSERT INTO versions(dataset,code,report_date,version,event_id,
                            received_at,content_sha256,content_payload_json)
                        VALUES(?,?,?,?,?,?,?,?)
                    """, (dataset, code, report_date, version, event_id,
                          received_utc, digest, packed))
                    self._db.execute("""
                        INSERT INTO current_head(dataset,code,report_date,version)
                        VALUES(?,?,?,?)
                        ON CONFLICT(dataset,code,report_date)
                        DO UPDATE SET version=excluded.version
                    """, (dataset, code, report_date, version))
                    n += 1
                if fail_after_row == index:
                    raise RuntimeError("synthetic_crash_before_commit")
            self._db.execute("COMMIT")
        except BaseException:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise
        return {
            "status": "LOCAL_ATOMIC_EVENT_UNATTESTED",
            "new_versions": n, "event_committed": True,
            "event_sha256": envelope_hash,
            "external_attestation": False,
            "live_use_allowed": False,
        }

    def _decode_checked(self, row, key):
        version, received, digest, packed, event_hash, event_blob, source = row
        if sha256(packed.encode("ascii")).hexdigest() != digest:
            raise RevisionError("version_integrity_failure")
        if sha256(event_blob.encode("ascii")).hexdigest() != event_hash:
            raise RevisionError("event_integrity_failure")
        event = json.loads(event_blob)
        payload = json.loads(packed)
        if (payload[:3] != list(key) or
                event.get("local_received_at") != received or
                event.get("source_claim") != source or
                payload not in event.get("rows", [])):
            raise RevisionError("capture_event_mismatch")
        return payload[3]

    def as_of(self, *, dataset, code, report_date, decision_utc):
        decision = parsed_stamp(decision_utc)
        if identify(dataset, code, report_date) > decision.date():
            raise RevisionError("decision_before_report_reference")
        row = self._db.execute("""
            SELECT v.version,v.received_at,v.content_sha256,v.content_payload_json,
                   e.envelope_sha256,e.envelope_json,e.source_claim
            FROM versions v JOIN capture_events e ON e.event_id=v.event_id
            WHERE v.dataset=? AND v.code=? AND v.report_date=?
              AND v.received_at<=? ORDER BY v.version DESC LIMIT 1
        """, (dataset, code, report_date, decision_utc)).fetchone()
        if row is None:
            return {"status": "UNKNOWN", "positions": None, "version": None,
                    "external_attestation": False, "live_use_allowed": False}
        values = self._decode_checked(row, (dataset, code, report_date))
        return {
            "status": "LOCAL_VERSION_UNATTESTED",
            "positions": values, "version": row[0], "received_at": row[1],
            "source_claim": row[6], "event_sha256": row[4],
            "external_attestation": False, "live_use_allowed": False,
        }

    def current(self, *, dataset, code, report_date):
        """Check mutable head against the newest immutable version; fail closed."""
        identify(dataset, code, report_date)
        row = self._db.execute("""
            SELECT h.version, COALESCE(MAX(v.version),0)
            FROM current_head h JOIN versions v
              ON v.dataset=h.dataset AND v.code=h.code AND v.report_date=h.report_date
            WHERE h.dataset=? AND h.code=? AND h.report_date=?
            GROUP BY h.version
        """, (dataset, code, report_date)).fetchone()
        if row is None:
            return {"status": "UNKNOWN", "positions": None}
        if row[0] != row[1]:
            raise RevisionError("head_is_not_latest_immutable_version")
        v = self._db.execute("""
            SELECT received_at FROM versions
            WHERE dataset=? AND code=? AND report_date=? AND version=?
        """, (dataset, code, report_date, row[0])).fetchone()
        return self.as_of(dataset=dataset, code=code, report_date=report_date,
                          decision_utc=v[0])
