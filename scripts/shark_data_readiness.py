"""REMURA Track B: read-only research readiness of existing private SQLite.

Checks *authentic* Squalincome observations against COT first_seen provenance
and currently retained closed M15. Does not backdate CVD detections from OHLC.
No writes, broker calls, internet, credentials, private OHLC or account data in
output. Main price database contains only rolling snapshots, not historical
per-candle ingestion timestamps. This is NOT a backtest or proof of an edge.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

SCHEMA = "remura-shark-data-readiness-v1"
PILOT = {"EURUSD": ("tff", "099741"), "XAUUSD": ("disagg", "088691")}
M15 = timedelta(minutes=15)
MAX_MARKET_BARS = 5000
UTC = timezone.utc


def _time(value):
    if not isinstance(value, str) or len(value) > 48:
        raise ValueError("invalid_utc")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("utc_required")
    return parsed.astimezone(UTC)


def _tables(db):
    names = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    return {
        "prices": "prices" in names,
        "squalincome_history": "squalincome_history" in names,
        "cot_first_seen": "cot_first_seen" in names,
    }


def _retained_price(db, symbol, exists):
    empty = {"bars": 0, "withVolume": 0, "withoutVolume": 0, "readable": False}
    if not exists:
        return empty, set()
    row = db.execute("SELECT payload FROM prices WHERE symbol=?", (symbol,)).fetchone()
    if not row:
        return empty, set()
    try:
        doc = json.loads(row[0])
        if (not isinstance(doc, dict) or doc.get("symbol") != symbol or
                doc.get("provider") != "ctrader" or
                not isinstance(doc.get("providerSymbol"), str) or
                not doc["providerSymbol"].strip()):
            return empty, set()
        frames = doc.get("timeframes", {})
        bars = frames.get("M15")
        if not isinstance(bars, list) or not 1 <= len(bars) <= MAX_MARKET_BARS:
            return empty, set()
        last = None
        closes = set()
        valid_volume = 0
        for bar in bars:
            opened = _time(bar["t"])
            op, hi, lo, close = (bar[k] for k in ("o", "h", "l", "c"))
            if (opened.second or opened.microsecond or opened.minute % 15 or
                    (last is not None and opened <= last) or
                    any(type(x) not in (int, float) or not 0 < x < float("inf")
                        for x in (op, hi, lo, close)) or
                    hi < max(op, close) or lo > min(op, close)):
                return empty, set()
            volume = bar.get("v")
            if volume is not None and (
                    type(volume) is not int or not 0 <= volume <= 2**53-1):
                return empty, set()
            valid_volume += int(volume is not None)
            closes.add(opened + M15)
            last = opened
        return {"bars": len(bars), "withVolume": valid_volume,
                "withoutVolume": len(bars)-valid_volume, "readable": True}, closes
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return empty, set()


def _first_seen(db, exists):
    data = {}
    if not exists:
        return data
    for dataset, code, report_date, first_seen in db.execute(
            "SELECT dataset,code,report_date,first_seen_at FROM cot_first_seen "
            "WHERE (dataset='tff' AND code='099741') OR "
            "(dataset='disagg' AND code='088691')"):
        try:
            key = (dataset, code, report_date)
            stamp = _time(first_seen)
            # If duplicated/malformed rows ever appear, use the LATER
            # availability: conservative, not optimistically earliest.
            data[key] = max(data.get(key, stamp), stamp)
        except (ValueError, TypeError, OverflowError):
            continue
    return data


def audit_connection(db):
    """Aggregate-only audit. Requires NO new state or collector functionality."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    tables = _tables(db)
    known = _first_seen(db, tables["cot_first_seen"])
    outputs = {}
    for symbol, (dataset, code) in PILOT.items():
        price, retained_closes = _retained_price(db, symbol, tables["prices"])
        reasons = Counter()
        seen = set()
        counted = 0
        # Live history records price-side observations, not CVD detections.
        if tables["squalincome_history"]:
            records = db.execute(
                "SELECT report_date,price_time,observed_at,cot_side,h1_side "
                "FROM squalincome_history WHERE symbol=? "
                "ORDER BY observed_at,id", (symbol,))
            for report_date, price_time, observed_at, side, h1 in records:
                try:
                    obs = _time(observed_at)
                    price_closed = _time(price_time)
                    report = datetime.fromisoformat(report_date).date()
                    if (report.isoformat() != report_date or
                            report > obs.date() or
                            price_closed > obs or side not in (-1, 1) or
                            h1 not in (-1, 1)):
                        reasons["observation_invalid_or_unverified"] += 1
                        continue
                except (ValueError, TypeError, OverflowError):
                    reasons["observation_invalid_or_unverified"] += 1
                    continue
                key = report_date  # first genuine recorded observation per COT week
                if key in seen:
                    reasons["same_cot_week_deduplicated"] += 1
                    continue
                seen.add(key)
                counted += 1
                if not price["readable"] or price_closed not in retained_closes:
                    reasons["observed_m15_not_retained"] += 1
                elif (dataset, code, report_date) not in known:
                    reasons["cot_first_seen_not_recorded"] += 1
                elif known[dataset, code, report_date] > obs:
                    reasons["cot_first_seen_after_observation"] += 1
                else:
                    reasons["price_context_research_possible"] += 1
        outputs[symbol] = {
            "archivedM15": price,
            "authenticFirstObservations": counted,
            "cohortReasons": dict(sorted(reasons.items())),
            "priceContextOnly": reasons["price_context_research_possible"],
            "cvdAsObservedProof": False,
            "verifiedCvdAsObservedEvents": None,
        }
    return {
        "schema": SCHEMA, "status": "OFFLINE_READ_ONLY",
        "tablesAvailable": tables, "markets": outputs,
        "priceRetention": "rolling_45_days_max_4000_m15_per_market",
        "historyRetention": "up_to_30_days_squalincome_history",
        "cotProvenance": "first_seen_observation_timestamp_not_publication_time",
        "cotValueRevisionSnapshots": False,
        "m15PerBarCollectionTimestamps": False,
        "cvdDetectionHistoryRecorded": False,
        "eligibleForRealCvdWalkForward": False,
        "edge": "NOT_ESTABLISHED", "pnl": "NOT_COMPUTED",
        "brokerCalls": 0, "ordersEnabled": False,
        "notificationsEnabled": False,
    }


def audit_path(path):
    """Open an existing SQLite database strictly read-only (no PRAGMA WAL writes)."""
    if not isinstance(path, (str, Path)):
        raise ValueError("invalid_db_path")
    local = Path(path).expanduser().resolve(strict=True)
    if not local.is_file():
        raise ValueError("not_a_database_file")
    uri = "file:" + quote(str(local), safe="/") + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=3) as db:
        db.execute("PRAGMA query_only=ON")
        return audit_connection(db)
