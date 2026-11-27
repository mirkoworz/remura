# REMURA Cloudflare D1 LAB Cleanup PLAN v0.1 — aggiornamento 12/11/2026 ore 23:39 CET
# SOLO PIANIFICAZIONE OFFLINE. Nessuna chiamata HTTP, secret, deploy o esecuzione SQL reale.
# Non avviare cleanup LIVE senza autorizzazione e senza preflight di sola lettura.
"""Pure, offline construction of a narrowly-scoped D1 synthetic-row cleanup plan.

This file never connects to Cloudflare and NEVER executes SQL. The only DELETE
it can construct is restricted to an exact lab-only record in the test database.
"""
from __future__ import annotations

from dataclasses import dataclass

DATABASE = "remura-tv-lab-test"  # Never use remura-tv-lab.
TEST_KEY = "REMURA_SYNTHETIC_WRITE_20261112"
SYNTHETIC_JSON = '{"synthetic":true,"test_only":true,"market_data":false}'
SYMBOL = "LAB:TEST_ONLY"
VERSION = "synthetic-test-v0.1"

# SELECT preflight must confirm one fully matching record before any future cleanup.
PREFLIGHT_SQL = (
    "SELECT event_key, symbol, version, timeframe, event_type, is_timely, raw_json "
    "FROM tv_flow_events WHERE event_key = ? LIMIT 2"
)
# The extra WHERE clauses make deletion impossible if the key was accidentally
# reused for a real market event. The exact raw_json comparison is intentional.
DELETE_SQL = (
    "DELETE FROM tv_flow_events "
    "WHERE event_key = ? AND symbol = 'LAB:TEST_ONLY' "
    "AND version = 'synthetic-test-v0.1' AND timeframe = '5' "
    "AND event_type = 'HEARTBEAT' AND is_timely = 0 AND raw_json = ?"
)


class UnsafeCleanup(Exception):
    """Fail-closed if a purported synthetic row does not match exactly."""


@dataclass(frozen=True)
class CleanupPlan:
    database: str
    preflight_sql: str
    preflight_params: tuple[str]
    delete_sql: str
    delete_params: tuple[str, str]


def verify_preflight_rows(rows: list[dict]) -> None:
    if len(rows) != 1:
        raise UnsafeCleanup("expected_one_synthetic_row")
    item = rows[0]
    if not isinstance(item, dict) or not (
        item.get("event_key") == TEST_KEY
        and item.get("symbol") == SYMBOL
        and item.get("version") == VERSION
        and item.get("timeframe") == "5"
        and item.get("event_type") == "HEARTBEAT"
        and item.get("is_timely") == 0
        and item.get("raw_json") == SYNTHETIC_JSON
    ):
        raise UnsafeCleanup("synthetic_row_not_exact")


def plan_only() -> CleanupPlan:
    return CleanupPlan(
        database=DATABASE,
        preflight_sql=PREFLIGHT_SQL,
        preflight_params=(TEST_KEY,),
        delete_sql=DELETE_SQL,
        delete_params=(TEST_KEY, SYNTHETIC_JSON),
    )


if __name__ == "__main__":
    # No SQL execution under any mode. No credentials are accepted.
    print("REMURA_LAB_CLEANUP=PLAN_ONLY")
    print("DATABASE=remura-tv-lab-test")
    print("ROWS_MAX_TARGET=1")
    print("REMOTE_WRITE=DISABLED")
