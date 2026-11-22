#!/usr/bin/env python3
# REMURA COT sidecar v0.5 LAB — schema-only additive cutover rehearsal.
"""Never touches an on-disk database, Oracle, or operational COT collector.

The legacy cot_reports row may have been overwritten in the past. Creating an
append-only *empty* sidecar does NOT recover its past versions or prove when
its current value first became available. In-memory rehearsal only, no paths,
no external connections, no migration runner or deploy output.
"""
from __future__ import annotations
from hashlib import sha256
from json import dumps
import sqlite3
from cot_revision_lineage_v01_lab import RevisionError, identify, parsed_stamp

SIDECAR_TABLES = (
    "cot_v05_capture_events", "cot_v05_versions", "cot_v05_current_head"
)
SIDECAR_TRIGGERS = (
    "cot_v05_events_immutable_update", "cot_v05_events_immutable_delete",
    "cot_v05_versions_immutable_update", "cot_v05_versions_immutable_delete",
)
LEGACY_TABLES = ("cot_reports", "cot_first_seen")
SCHEMA = "remura.cot.additive_sidecar_cutover.v05.lab"

class SyntheticCutover:
    """An isolated in-memory object: callers cannot pass a real SQLite path."""
    def __init__(self, *, synthetic=False):
        if synthetic is not True:
            raise RevisionError("explicit_synthetic_fixture_required")
        self._db = sqlite3.connect(":memory:", isolation_level=None)
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript("""
            CREATE TABLE cot_reports(
                dataset TEXT NOT NULL, code TEXT NOT NULL,
                report_date TEXT NOT NULL, oi REAL NOT NULL,
                first_long REAL NOT NULL, first_short REAL NOT NULL,
                second_long REAL NOT NULL, second_short REAL NOT NULL,
                PRIMARY KEY(dataset,code,report_date));
            CREATE TABLE cot_first_seen(
                dataset TEXT NOT NULL, code TEXT NOT NULL,
                report_date TEXT NOT NULL, first_seen_at TEXT NOT NULL,
                PRIMARY KEY(dataset,code,report_date));
        """)
        self._locked = False
        self._legacy_at_cutover = None

    def close(self):
        self._db.close()

    def seed_legacy(self, *, dataset, code, report_date, values, first_seen):
        """Seed intentionally UNATTESTED legacy values before synthetic cutover."""
        if self._locked:
            raise RevisionError("legacy_seed_after_cutover_forbidden")
        identify(dataset, code, report_date)
        parsed_stamp(first_seen)
        if type(values) not in (tuple, list) or len(values) != 5 or any(
                type(v) not in (int,float) or not (0 <= v <= 1e11) for v in values):
            raise RevisionError("legacy_synthetic_values_invalid")
        if values[0] <= 0:
            raise RevisionError("legacy_open_interest_invalid")
        self._db.execute(
            """INSERT INTO cot_reports
            (dataset,code,report_date,oi,first_long,first_short,second_long,second_short)
            VALUES(?,?,?,?,?,?,?,?)""", (dataset,code,report_date,*values))
        self._db.execute(
            """INSERT INTO cot_first_seen(dataset,code,report_date,first_seen_at)
            VALUES(?,?,?,?)""", (dataset,code,report_date,first_seen))

    def _legacy_rows(self):
        return {
            t: self._db.execute("SELECT * FROM "+t+" ORDER BY 1,2,3").fetchall()
            for t in LEGACY_TABLES
        }

    def _legacy_hash(self):
        return sha256(dumps(self._legacy_rows(), sort_keys=True,
                            separators=(",",":")).encode()).hexdigest()

    def _sidecar_state(self):
        names = {row[0] for row in self._db.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','trigger')")}
        return {
            "tables": sorted(names.intersection(SIDECAR_TABLES)),
            "triggers": sorted(names.intersection(SIDECAR_TRIGGERS)),
        }

    def migrate(self, *, fail_after=None):
        """Atomic ADDITIVE schema rehearsal; no historical inserts and no DROP."""
        if fail_after not in (None, "tables", "triggers"):
            raise RevisionError("invalid_fixture_failpoint")
        old = self._legacy_hash()
        if self._locked:
            self.audit()
            if old != self._legacy_at_cutover:
                raise RevisionError("legacy_changed_after_cutover")
            return self.audit()
        if any(self._sidecar_state().values()):
            raise RevisionError("preexisting_sidecar_objects_not_owned_by_fixture")
        self._db.execute("SAVEPOINT cot_v05_schema")
        try:
            # sqlite3.executescript() commits open transactions: NEVER use it
            # inside an atomic cutover/savepoint. Execute DDL individually.
            for sql in (
                """CREATE TABLE cot_v05_capture_events(
                    event_id INTEGER PRIMARY KEY, received_utc TEXT NOT NULL,
                    source_claim TEXT NOT NULL, envelope_sha256 TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL)""",
                """CREATE TABLE cot_v05_versions(
                    dataset TEXT NOT NULL, code TEXT NOT NULL,
                    report_date TEXT NOT NULL, version INTEGER NOT NULL,
                    event_id INTEGER NOT NULL, received_utc TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
                    PRIMARY KEY(dataset,code,report_date,version),
                    FOREIGN KEY(event_id) REFERENCES cot_v05_capture_events(event_id))""",
                """CREATE TABLE cot_v05_current_head(
                    dataset TEXT NOT NULL, code TEXT NOT NULL,
                    report_date TEXT NOT NULL, version INTEGER NOT NULL,
                    PRIMARY KEY(dataset,code,report_date),
                    FOREIGN KEY(dataset,code,report_date,version)
                      REFERENCES cot_v05_versions(dataset,code,report_date,version))""",
            ):
                self._db.execute(sql)
            if fail_after == "tables":
                raise RuntimeError("synthetic_fault_after_tables")
            for sql in (
                """CREATE TRIGGER cot_v05_events_immutable_update
                BEFORE UPDATE ON cot_v05_capture_events
                BEGIN SELECT RAISE(ABORT,'immutable_capture'); END""",
                """CREATE TRIGGER cot_v05_events_immutable_delete
                BEFORE DELETE ON cot_v05_capture_events
                BEGIN SELECT RAISE(ABORT,'immutable_capture'); END""",
                """CREATE TRIGGER cot_v05_versions_immutable_update
                BEFORE UPDATE ON cot_v05_versions
                BEGIN SELECT RAISE(ABORT,'immutable_version'); END""",
                """CREATE TRIGGER cot_v05_versions_immutable_delete
                BEFORE DELETE ON cot_v05_versions
                BEGIN SELECT RAISE(ABORT,'immutable_version'); END""",
            ):
                self._db.execute(sql)
            if fail_after == "triggers":
                raise RuntimeError("synthetic_fault_after_triggers")
            if self._legacy_hash() != old:
                raise RevisionError("legacy_mutated_during_migration")
            self._db.execute("RELEASE SAVEPOINT cot_v05_schema")
        except BaseException:
            # When schema DDL is part of an open savepoint, ROLLBACK removes it.
            self._db.execute("ROLLBACK TO SAVEPOINT cot_v05_schema")
            self._db.execute("RELEASE SAVEPOINT cot_v05_schema")
            raise
        self._locked = True
        self._legacy_at_cutover = old
        return self.audit()

    def audit(self):
        if not self._locked:
            return {"schema":SCHEMA,"status":"NO_SCHEMA_CUTOVER_YET",
                    "oracle_examined":False,"live_allowed":False}
        state = self._sidecar_state()
        if (state["tables"] != sorted(SIDECAR_TABLES)
                or state["triggers"] != sorted(SIDECAR_TRIGGERS)):
            raise RevisionError("sidecar_schema_or_immutability_drift")
        if self._legacy_hash() != self._legacy_at_cutover:
            raise RevisionError("legacy_modified_since_cutover")
        if self._db.execute("PRAGMA foreign_key_check").fetchall():
            raise RevisionError("synthetic_foreign_key_violation")
        if any(self._db.execute("SELECT count(*) FROM "+t).fetchone()[0]
               for t in SIDECAR_TABLES):
            raise RevisionError("sidecar_unexpected_rows_in_schema_only_rehearsal")
        return {
            "schema": SCHEMA, "status":"SYNTHETIC_ADDITIVE_SCHEMA_ONLY",
            "legacy_tables_preserved":True,
            "legacy_rows_quarantined_not_versioned":True,
            "legacy_hash_sha256":self._legacy_at_cutover,
            "legacy_row_counts":{t:len(rows) for t,rows in self._legacy_rows().items()},
            "sidecar_versions":0,"sidecar_events":0,
            "sidecar_head_rows":0,"sidecar_triggers":len(SIDECAR_TRIGGERS),
            "legacy_first_seen_proven":False,
            "historical_asof_reconstructed":False,
            "independent_cftc_receipt_proven":False,
            "backup_restorable_on_oracle_proven":False,
            "live_migration_allowed":False,
            "oracle_examined":False,"external_calls":0,"live_allowed":False,
        }

    def legacy_asof(self, *, dataset, code, report_date, decision_utc):
        """Do not let the old overwritten value masquerade as historical."""
        identify(dataset,code,report_date)
        parsed_stamp(decision_utc)
        row = self._db.execute("""
            SELECT 1 FROM cot_reports WHERE dataset=? AND code=? AND report_date=?
        """,(dataset,code,report_date)).fetchone()
        return {
            "status": "LEGACY_PRESENT_UNATTESTED_NO_HISTORICAL_ASOF"
                      if row else "UNKNOWN_NO_LEGACY_ROW",
            "positions":None, "version":None,
            "backfill_allowed":False, "scientific_admission":False,
        }
