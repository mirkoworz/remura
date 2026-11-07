#!/usr/bin/env python3
"""Track C: OFFLINE-ONLY synthetic shadow handoff/SQLite failure rehearsal.

This is NOT a market-data recorder, a provider witness, a predictor or a LIVE
integration. It only tests a proposed narrow interface for the already
existing Track B FIRST-SEEN modules, which remain isolated on PR #89.

It cannot access production SQLite: ONLY one in-memory SQLite database is
accepted. No broker, Myfxbook, CFTC, network, disk, schedules or background
processes. SHA256 witnesses here attest only to caller-provided synthetic
material, never provider authenticity or trading utility.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3

PILOT = ("EURUSD", "XAUUSD")
SOURCES = ("cot", "price", "retail")
MAX_AGE = {
    "cot": timedelta(days=14),
    "price": timedelta(minutes=90),
    "retail": timedelta(minutes=35),
}
MODE = "OFFLINE_SYNTHETIC_ONLY"
SCHEMA = "remura-track-c-inmemory-shadow-rehearsal-v1"
TABLE = "track_c_synthetic_shadow_receipts"
MAX_ROWS = 48  # Only an isolated, deliberately small rehearsal limit.


def _memory_only(db):
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    disks = db.execute("PRAGMA database_list").fetchall()
    if len(disks) != 1 or disks[0][1] != "main" or disks[0][2]:
        raise ValueError("only_single_in_memory_sqlite_allowed")


def prepare(db):
    """Create research rehearsal schema ONLY in an isolated memory database."""
    _memory_only(db)
    if db.in_transaction:
        raise ValueError("clean_memory_transaction_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            observed_at TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('cot','price','retail')),
            read_at TEXT NOT NULL,
            local_sha256 TEXT NOT NULL,
            UNIQUE(symbol,observed_at,source)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS track_c_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS track_c_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
    return SCHEMA


def _utc(value):
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError("strict_utc_timestamp_required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid_utc_timestamp") from exc


def _receipt(symbol, source, value, observed):
    if type(value) is not dict or set(value) != {"readAtUtc", "document"}:
        raise ValueError("original_in_memory_source_envelope_required")
    read = _utc(value["readAtUtc"])
    age = observed - read
    if not timedelta(0) <= age <= MAX_AGE[source]:
        raise ValueError("future_or_stale_source")
    doc = value["document"]
    if type(doc) is not dict or not doc:
        raise ValueError("nonempty_synthetic_original_required")
    try:
        canonical = json.dumps(
            {"symbol": symbol, "source": source, "document": doc},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("uncanonicalizable_original") from exc
    if len(canonical) > 65536:
        raise ValueError("oversized_synthetic_original")
    return value["readAtUtc"], hashlib.sha256(canonical).hexdigest()


def rehearse(db, *, now_utc, pair, mode=None):
    """Atomic synthetic TWO-market receipt transfer.

    Accept caller-provided originals in memory, not a later current/latest
    snapshot. COT and PRICE mandatory, retail optional/UNKNOWN. No CVD here.
    Reports only metadata counts, NOT a verified source/decision join.
    """
    _memory_only(db)
    if mode != MODE:
        raise ValueError("explicit_offline_mode_required")
    if db.in_transaction:
        raise ValueError("clean_transaction_required")
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)
    ).fetchone() is None:
        raise ValueError("explicit_rehearsal_schema_required")
    for trigger in ("track_c_no_update", "track_c_no_delete"):
        if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger,)
        ).fetchone() is None:
            raise ValueError("append_only_trigger_required")
    now = _utc(now_utc)
    if type(pair) is not list or len(pair) != 2:
        raise ValueError("exactly_two_pilot_observations_required")
    by_symbol = {}
    rows = []
    for item in pair:
        if type(item) is not dict or set(item) != {
            "symbol", "observedAtUtc", "sources"
        }:
            raise ValueError("exact_observation_contract_required")
        symbol = item["symbol"]
        if symbol not in PILOT or symbol in by_symbol:
            raise ValueError("duplicate_or_unapproved_pilot_symbol")
        by_symbol[symbol] = True
        observed = _utc(item["observedAtUtc"])
        if not timedelta(0) <= now - observed <= timedelta(seconds=30):
            raise ValueError("future_or_retroactive_observation")
        sources = item["sources"]
        if type(sources) is not dict or any(s not in SOURCES for s in sources):
            raise ValueError("unapproved_source")
        if "cot" not in sources or "price" not in sources:
            raise ValueError("cot_and_price_required")
        for source in SOURCES:
            if source in sources and sources[source] is not None:
                read, digest = _receipt(symbol, source, sources[source], observed)
                rows.append((symbol, item["observedAtUtc"], source, read, digest))
            elif source != "retail":
                raise ValueError("mandatory_source_unavailable")
    if set(by_symbol) != set(PILOT):
        raise ValueError("both_pilot_markets_required")
    db.execute("BEGIN IMMEDIATE")
    try:
        existing = db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
        if existing + len(rows) > MAX_ROWS:
            raise ValueError("bounded_rehearsal_capacity_reached")
        for row in rows:
            db.execute(
                f"INSERT INTO {TABLE}(symbol,observed_at,source,read_at,local_sha256)"
                " VALUES(?,?,?,?,?)", row)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {
        "schema": SCHEMA,
        "state": "SYNTHETIC_HANDOFF_ONLY_NOT_PROSPECTIVE_EVIDENCE",
        "pilotMarkets": len(PILOT),
        "receipts": len(rows),
        "missingRetail": sum("retail" not in it["sources"] or
                             it["sources"]["retail"] is None for it in pair),
        "cvd": "UNKNOWN",
        "trackBOriginalSourceVerified": False,
        "outcomesObserved": False,
        "tradingAuthorized": False,
        "brokerCalls": 0,
    }
