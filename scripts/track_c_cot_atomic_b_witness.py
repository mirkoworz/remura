"""C2c-c: strictly OFFLINE atomic CFTC UPSERT to original B COT witness.

NOT a live recorder. Only a specifically named SQLite test file under
the OS temporary directory can use this object. The real CFTC collector has
no configured research callback; its ordinary path is unchanged.

The LAST operation inside the caller's original COT UPSERT transaction is
the frozen original B witness, which commits that same SQLite transaction.
If source-to-stored verification or witness insertion fails before commit,
both COT cache changes and research evidence roll back.
Local clocks are NOT CFTC-signed timestamps.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile

MODE = "OFFLINE_SYNTHETIC_PINNED_B_COT_ATOMIC_ONLY"
SCHEMA = "remura-track-c-atomic-cot-original-b-v1"
FILE_NAME = "track-c-synthetic-atomic.sqlite3"
MAX_RESPONSE_SPAN = timedelta(seconds=60)
MAX_INGEST_AFTER_HTTP = timedelta(seconds=30)
START = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _utc(t):
    if type(t) is not datetime or t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("explicit_true_utc_clock_required")
    return t.astimezone(timezone.utc)


def _lab_db(db):
    if type(db) is not sqlite3.Connection or not db.in_transaction:
        raise ValueError("only_active_original_sqlite_transaction_allowed")
    loc = db.execute("PRAGMA database_list").fetchall()
    if len(loc) != 1 or loc[0][1] != "main" or not loc[0][2]:
        raise ValueError("only_synthetic_temporary_sqlite_allowed")
    file = Path(loc[0][2]).resolve()
    root = Path(tempfile.gettempdir()).resolve()
    if file.name != FILE_NAME or not file.is_relative_to(root):
        raise ValueError("live_file_or_unapproved_sqlite_forbidden")


class OriginalBAtomicWitness:
    """Explicit future-research rehearsal callback, never set by scheduler."""

    def __init__(self, *, mode=None):
        if mode != MODE:
            raise ValueError("explicit_offline_rehearsal_mode_required")

    def __call__(self, db, dataset, started, received, recorded, frozen):
        _lab_db(db)
        a, b, c = _utc(started), _utc(received), _utc(recorded)
        if not (START <= a <= b <= c
                and b-a <= MAX_RESPONSE_SPAN
                and c-b <= MAX_INGEST_AFTER_HTTP):
            raise ValueError("post_http_cot_utc_sequence_invalid")
        if dataset not in ("tff", "disagg") or type(frozen) is not tuple or not frozen:
            raise ValueError("only_normalized_original_cot_response_allowed")

        # Require exact ORIGINAL Track B source in pinned checkout.
        # This module does not implement a replacement COT hash algorithm.
        try:
            from scripts import shark_cot_asof_witness as evidence
            from scripts import shark_cvd_incremental_protocol as study
        except ImportError as err:
            raise ValueError("original_pinned_track_b_witness_unavailable") from err
        if (study.protocol_sha256() != study.FROZEN_PROTOCOL_SHA256
                or study.FROZEN_PROTOCOL_SHA256 !=
                "09d833dafdd426254bc8fedccc367e41fa451ac8f2e6c99a9dac27f7387e2905"):
            raise ValueError("frozen_scientific_protocol_mismatch")
        objects = dict(db.execute(
            "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?)",
            (evidence.TABLE, "research_cot_asof_no_update",
             "research_cot_asof_no_delete")
        ).fetchall())
        if (objects.get(evidence.TABLE) != "table"
                or objects.get("research_cot_asof_no_update") != "trigger"
                or objects.get("research_cot_asof_no_delete") != "trigger"):
            raise ValueError("explicit_research_witness_migration_missing")

        seen = set()
        for row in frozen:
            if type(row) is not tuple or len(row) != 8:
                raise ValueError("not_the_original_normalized_cot_tuple")
            kind,code,week,*numbers = row
            if (kind != dataset or code not in evidence.DATASET_CODES[dataset]
                    or type(week) is not str):
                raise ValueError("original_dataset_code_mismatch")
            key = (kind,code,week)
            if key in seen:
                raise ValueError("duplicate_normalized_cot_response")
            seen.add(key)
            persisted = db.execute(
                "SELECT oi,first_long,first_short,second_long,second_short "
                "FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
                key
            ).fetchone()
            if persisted is None or tuple(persisted) != tuple(numbers):
                raise ValueError("sqlite_not_equal_to_exact_original_response")

        # MUST be the last operation that may raise before B commits.
        # The nested B context manager commits source and witness together.
        # Exceptions before commit roll back both.
        evidence.witness(db, clock=c)
        # No post-commit validation that could misreport committed data.
        # B's independent readiness check is a separate research operation.
