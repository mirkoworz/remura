#!/usr/bin/env python3
"""REMURA research: offline M15 backtest from a private SQLite price snapshot.

No web requests, no order submission, no schema changes, and no use of
price_store.connect() (which creates tables / enables WAL). Reads exactly one
approved symbol from the existing prices table with SQLite mode=ro/query_only.
This is exploratory, not a validated or executable trade recommendation.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote

from price_feed import MARKETS
from shark_science import STRATEGIES, _bars, _time, evaluate

MAX_PAYLOAD_CHARS = 8_000_000


def load_price_document(db_path, symbol):
    """Read an existing broker-consistent JSON payload, never create a DB."""
    if not isinstance(symbol, str) or symbol not in MARKETS:
        raise ValueError("symbol_not_supported")
    path = Path(db_path).expanduser().absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError("database_unavailable")
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db:
            db.execute("PRAGMA query_only=ON")
            row = db.execute(
                "SELECT source,broker_symbol,payload FROM prices WHERE symbol=?",
                (symbol,)
            ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise ValueError("database_read_failed") from exc
    if row is None:
        raise ValueError("symbol_not_archived")
    source, broker, payload = row
    if (source != "ctrader" or not isinstance(broker, str)
            or not broker.strip() or not isinstance(payload, str)
            or len(payload) > MAX_PAYLOAD_CHARS):
        raise ValueError("unverified_ctrader_payload")
    try:
        data = json.loads(payload)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_stored_document") from exc
    if (not isinstance(data, dict)
            or data.get("symbol") != symbol
            or data.get("provider") != "ctrader"
            or data.get("providerSymbol") != broker):
        raise ValueError("source_or_broker_mismatch")
    times = data.get("timeframes")
    rows = times.get("M15") if isinstance(times, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > 5000:
        raise ValueError("invalid_stored_m15")
    if not isinstance(rows[-1], dict) or data.get("lastComplete") != rows[-1].get("t"):
        raise ValueError("last_complete_mismatch")
    return rows


def archive_quality(clean):
    """Describe usable contiguous M15 history; no price values exposed."""
    gaps = 0
    largest_gap_minutes = 0
    longest = current = 1
    weeks = set()
    for i, row in enumerate(clean):
        stamp = row[0]
        year, week, _ = stamp.isocalendar()
        weeks.add((year, week))
        if i == 0:
            continue
        interval = int((stamp - clean[i-1][0]).total_seconds() // 60)
        if interval != 15:
            gaps += 1
            largest_gap_minutes = max(largest_gap_minutes, interval)
            current = 1
        else:
            current += 1
            longest = max(longest, current)
    return {"archivedWeeks": len(weeks), "gapsDetected": gaps,
            "largestGapMinutes": largest_gap_minutes if gaps else None,
            "longestContiguousM15": longest,
            # This is coverage, not a strategy's statistical confidence.
            "historyCoverage": "limited" if len(weeks) < 8 else "review_required"}


def analyze_database(db_path, symbol, *, as_of, round_trip_cost_bps,
                     strategy="breakout", hold_bars=4, lookback=12):
    rows = load_price_document(db_path, symbol)
    clean = _bars(rows, as_of)
    if not clean:
        raise ValueError("no_closed_m15")
    results = evaluate(rows, as_of=as_of, strategy=strategy,
                       hold_bars=hold_bars, lookback=lookback,
                       round_trip_cost_bps=round_trip_cost_bps)
    last_close = clean[-1][0] + dt.timedelta(minutes=15)
    # This is a bounded, sanitized research result. No raw OHLC / broker name.
    return {"symbol": symbol, "source": "private_sqlite_readonly",
            "observedBars": len(clean),
            "firstBarAt": clean[0][0].isoformat(),
            "lastClosedAt": last_close.isoformat(),
            "elapsedDays": round((last_close - clean[0][0]).total_seconds() / 86400, 2),
            "archiveQuality": archive_quality(clean),
            **results}


def main():
    parser = argparse.ArgumentParser(
        description="REMURA offline research from existing local private SQLite (read only)")
    parser.add_argument("--database", required=True,
                        help="Local existing SQLite file; not uploaded or modified")
    parser.add_argument("--symbol", default="EURUSD", choices=sorted(MARKETS))
    parser.add_argument("--as-of", required=True, help="Explicit UTC assessment timestamp")
    parser.add_argument("--cost-bps", required=True, type=float,
                        help="Estimated positive round-trip spread+fees+slippage in bps")
    parser.add_argument("--strategy", choices=STRATEGIES, default="breakout")
    parser.add_argument("--hold-bars", type=int, default=4)
    parser.add_argument("--lookback", type=int, default=12)
    args = parser.parse_args()
    try:
        result = analyze_database(
            args.database, args.symbol, as_of=args.as_of,
            round_trip_cost_bps=args.cost_bps, strategy=args.strategy,
            hold_bars=args.hold_bars, lookback=args.lookback
        )
    except (ValueError, OSError) as exc:
        # Never echo local filesystem paths, tokens, raw broker payloads or prices.
        parser.error("lettura_ricerca_non_disponibile: " + str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
