#!/usr/bin/env python3
"""REMURA Filone B v20.7: export ONLY CFTC historical data from a copied SQLite DB.

No network, no schema mutation, no pricing engine and no production access.
Use on a local/offline COPY of remura-prices.sqlite3. Output to stdout.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

MAX_ROWS = 5000
SCHEMA = "remura-cot-intelligence-snapshot-v1"


def read_snapshot(db_path: str | Path, limit: int = MAX_ROWS) -> dict:
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise ValueError("INVALID_ROW_LIMIT")
    location = Path(db_path).expanduser().resolve(strict=True)
    if not location.is_file():
        raise ValueError("SQLITE_SNAPSHOT_NOT_FILE")
    # mode=ro rejects a missing database and forbids database writes.
    uri = "file:" + quote(str(location)) + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        db.execute("PRAGMA query_only=ON")
        # Contract/date are keys in the existing collector schema. Never join
        # a different contract's capture clock or backfill unknown legacy rows.
        cursor = db.execute("""
            SELECT r.dataset, r.code, r.report_date, r.oi,
                   r.first_long, r.first_short, r.second_long, r.second_short,
                   fs.first_seen_at
            FROM cot_reports AS r
            LEFT JOIN cot_first_seen AS fs
              ON fs.dataset = r.dataset AND fs.code = r.code
             AND fs.report_date = r.report_date
            WHERE (r.dataset = 'tff' AND r.code IN
                ('099741','096742','097741','232741','090741','092741',
                 '112741','13874A','209742','124603','098662'))
               OR (r.dataset = 'disagg' AND r.code IN
                ('088691','084691','067651'))
            ORDER BY r.report_date DESC, r.dataset, r.code
            LIMIT ?
        """, (limit,))
        names = [col[0] for col in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]
        return {
            "schema": SCHEMA, "source": "existing_private_cftc_cache",
            "captureClock": "first_local_capture_not_official_publication",
            "rows": rows, "rowCount": len(rows),
            "truncated": len(rows) == limit
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline CFTC-only read-only snapshot")
    parser.add_argument("--db", required=True, help="Path to an OFFLINE COPY of SQLite archive")
    parser.add_argument("--limit", type=int, default=MAX_ROWS)
    args = parser.parse_args()
    print(json.dumps(read_snapshot(args.db, args.limit), ensure_ascii=False,
                     allow_nan=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
