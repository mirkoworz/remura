"""REMURA Track B — offline prototype of a private append-only CVD observation ledger.

Not imported or activated by production. Caller supplies a separate private
SQLite DB and a stable HMAC secret via runtime config; do NOT use the REMURA
main SQLite or put keys in GitHub. No API, order, notification, prices, tick
counts, event IDs or broker symbols are persisted. Time is stamped at append.
Intended for *future* real observations only, never historical backfill.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import sqlite3

SCHEMA = "remura-cvd-future-observation-ledger-v1"
VERSION = "cvd-divergence-proxy-m15-v1"
PILOT = frozenset({"EURUSD", "XAUUSD"})
STEP = timedelta(minutes=15)
MAX_AGE = timedelta(minutes=90)
MAX_EVENTS = 4096
UTC = timezone.utc


def _utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("utc_z_required")
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_time") from exc
    if at.utcoffset() != timedelta(0):
        raise ValueError("invalid_timezone")
    return at


def _iso(value):
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clock(value):
    now = datetime.now(UTC) if value is None else value
    if (not isinstance(now, datetime) or now.tzinfo is None
            or now.utcoffset() != timedelta(0)):
        raise ValueError("trusted_utc_clock_required")
    return now.astimezone(UTC)


def _key(secret):
    if not isinstance(secret, bytes) or len(secret) < 16:
        raise ValueError("stable_private_hmac_secret_required")
    return secret


def ensure_schema(db):
    """Explicit opt-in only; NEVER called from the live server."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS research_cvd_observations(
            key TEXT PRIMARY KEY,
            source_hash TEXT NOT NULL,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            algorithm TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('bullish_regular','bearish_regular')),
            side TEXT NOT NULL CHECK(side IN ('bullish','bearish')),
            first_pivot TEXT NOT NULL,
            second_pivot TEXT NOT NULL,
            confirmed_at TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        # Fail shut on edits. Forward-only permanent record; bounded 4096 rows.
        db.execute("""CREATE TRIGGER IF NOT EXISTS research_cvd_no_update
          BEFORE UPDATE ON research_cvd_observations
          BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS research_cvd_no_delete
          BEFORE DELETE ON research_cvd_observations
          BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def append(db, event, quality, *, source_collected_at, hmac_secret, now=None):
    """Persist actual detection time, never trust externally supplied detectedAt.

    Source collection time still depends on truthful future instrumentation.
    Quality checks must independently attest closed M15, contiguous volumes
    and source freshness. Empty/invalid quality fails closed.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    secret = _key(hmac_secret)
    detected = _clock(now)
    if (not isinstance(event, dict) or not isinstance(quality, dict)
            or event.get("symbol") not in PILOT
            or event.get("algorithm") != VERSION
            or event.get("provider") != "ctrader"
            or event.get("timeframe") != "M15"
            or event.get("state") != "confirmed_technical_not_trade_signal"
            or quality.get("dataQualityVerified") is not True
            or quality.get("closedM15") is not True
            or quality.get("contiguousSession") is not True
            or quality.get("tickVolumeComplete") is not True
            or quality.get("h1Ready") is not True):
        raise ValueError("unverified_event_or_quality")
    provider = event.get("providerSymbol")
    if (not isinstance(provider, str) or not 1 <= len(provider.strip()) <= 100
            or not isinstance(event.get("id"), str)):
        raise ValueError("unverified_broker_or_identifier")
    provider = provider.strip()
    kind = event.get("type")
    side = event.get("side")
    if (kind, side) not in (("bullish_regular", "bullish"),
                            ("bearish_regular", "bearish")):
        raise ValueError("invalid_direction")
    try:
        first = _utc(event["first"]["pivotAt"])
        second = _utc(event["second"]["pivotAt"])
        confirmed = _utc(event["confirmedAt"])
        collected = _utc(source_collected_at)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid_event_dates") from exc
    day = first.date().isoformat()
    if (event.get("sessionUtc") != day or second.date() != first.date()
            or first.second or first.microsecond or first.minute % 15
            or second.second or second.microsecond or second.minute % 15
            or not 3*STEP <= second-first <= 36*STEP
            or confirmed != second + 3*STEP
            or confirmed > collected or collected > detected
            or detected - confirmed > MAX_AGE):
        raise ValueError("non_causal_or_stale_event")
    first_ms = int(first.timestamp()*1000)
    second_ms = int(second.timestamp()*1000)
    canonical = "|".join((VERSION, "ctrader", provider, event["symbol"],
                          "M15", day, kind, str(first_ms), str(second_ms)))
    if not hmac.compare_digest(event["id"], canonical):
        raise ValueError("event_id_lineage_mismatch")
    opaque = hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest()
    source_hash = hmac.new(secret, provider.encode(), hashlib.sha256).hexdigest()
    with db:
        count = db.execute("SELECT count(*) FROM research_cvd_observations").fetchone()[0]
        if count >= MAX_EVENTS:
            raise ValueError("private_ledger_capacity_reached")
        cur = db.execute(
            """INSERT OR IGNORE INTO research_cvd_observations
            (key,source_hash,symbol,algorithm,kind,side,first_pivot,
             second_pivot,confirmed_at,collected_at,detected_at,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (opaque, source_hash, event["symbol"], VERSION, kind, side,
             _iso(first), _iso(second), _iso(confirmed), _iso(collected),
             _iso(detected), _iso(detected)))
    return {
        "schema": SCHEMA,
        "state": "RECORDED" if cur.rowcount == 1 else "DUPLICATE",
        "newBrokerCalls": 0, "alertsEnabled": False,
    }


def aggregate(db):
    """Do not disclose individual IDs, times, prices or source hashes."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    total = db.execute(
        "SELECT count(*) FROM research_cvd_observations").fetchone()[0]
    return {"schema": SCHEMA, "events": total, "maxEvents": MAX_EVENTS,
            "storage": "separate_private_sqlite_only",
            "isLiveActive": False, "edge": "NOT_ESTABLISHED",
            "newBrokerCalls": 0, "alertsEnabled": False}
