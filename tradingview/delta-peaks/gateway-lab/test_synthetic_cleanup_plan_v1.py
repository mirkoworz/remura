# REMURA D1 LAB Cleanup PLAN unit tests v0.1 — aggiornamento 12/11/2026 ore 23:40 CET
# Solo SQLite in memoria, dati sintetici: nessuna rete, credenziale o DB reale.
"""Tests that a proposed future cleanup cannot delete any real-market records."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

SOURCE = Path(__file__).with_name("synthetic_cleanup_plan_v1.py")
SPEC = importlib.util.spec_from_file_location("remura_d1_cleanup_plan", SOURCE)
import sys
plan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plan
SPEC.loader.exec_module(plan)


def synthetic():
    return {
        "event_key": plan.TEST_KEY,
        "received_at_ms": 1794520000000,
        "bar_close_ms": 1794520000000,
        "symbol": plan.SYMBOL,
        "timeframe": "5",
        "event_type": "HEARTBEAT",
        "version": plan.VERSION,
        "is_timely": 0,
        "raw_json": plan.SYNTHETIC_JSON,
    }


def database():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE tv_flow_events (
        event_key TEXT PRIMARY KEY,
        received_at_ms INTEGER NOT NULL,
        bar_close_ms INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        event_type TEXT NOT NULL,
        version TEXT NOT NULL,
        is_timely INTEGER NOT NULL,
        raw_json TEXT NOT NULL
    )""")
    return conn


def insert(conn, row):
    keys = tuple(row)
    placeholders = ",".join("?" for _ in keys)
    conn.execute(
        f"INSERT INTO tv_flow_events ({','.join(keys)}) VALUES ({placeholders})",
        tuple(row.values()),
    )


def preview_rows(conn):
    p = plan.plan_only()
    return [dict(r) for r in conn.execute(p.preflight_sql, p.preflight_params)]


def try_cleanup_in_memory(conn):
    p = plan.plan_only()
    plan.verify_preflight_rows(preview_rows(conn))
    return conn.execute(p.delete_sql, p.delete_params).rowcount


class SyntheticCleanupPlanTests(unittest.TestCase):
    def test_one_exact_test_record_only(self):
        conn = database()
        insert(conn, synthetic())
        self.assertEqual(try_cleanup_in_memory(conn), 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tv_flow_events").fetchone()[0], 0)

    def test_other_market_event_preserved(self):
        conn = database()
        insert(conn, synthetic())
        row = synthetic()
        row["event_key"] = "real|FXCM:EURUSD|2026-11-12"
        row["symbol"] = "FXCM:EURUSD"
        row["version"] = "0.8.1-lab"
        row["raw_json"] = '{"market":true}'
        insert(conn, row)
        self.assertEqual(try_cleanup_in_memory(conn), 1)
        self.assertEqual(conn.execute("SELECT symbol FROM tv_flow_events").fetchone()[0],
                         "FXCM:EURUSD")

    def test_missing_test_row_fails_closed(self):
        conn = database()
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_symbol_changed_fails_closed(self):
        conn = database()
        row = synthetic()
        row["symbol"] = "FXCM:EURUSD"
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tv_flow_events").fetchone()[0], 1)

    def test_payload_changed_fails_closed(self):
        conn = database()
        row = synthetic()
        row["raw_json"] = '{"synthetic":false,"test_only":true,"market_data":false}'
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_version_changed_fails_closed(self):
        conn = database()
        row = synthetic()
        row["version"] = "0.8.1-lab"
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_timeliness_changed_fails_closed(self):
        conn = database()
        row = synthetic()
        row["is_timely"] = 1
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_wrong_event_type_fails_closed(self):
        conn = database()
        row = synthetic()
        row["event_type"] = "BAR_EVENT"
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_wrong_timeframe_fails_closed(self):
        conn = database()
        row = synthetic()
        row["timeframe"] = "15"
        insert(conn, row)
        with self.assertRaises(plan.UnsafeCleanup):
            try_cleanup_in_memory(conn)

    def test_where_clause_prevents_delete_even_without_preflight(self):
        conn = database()
        row = synthetic()
        row["symbol"] = "FXCM:EURUSD"
        insert(conn, row)
        p = plan.plan_only()
        self.assertEqual(conn.execute(p.delete_sql, p.delete_params).rowcount, 0)

    def test_target_is_only_test_db(self):
        p = plan.plan_only()
        self.assertEqual(p.database, "remura-tv-lab-test")
        self.assertEqual(p.preflight_params, (plan.TEST_KEY,))
        self.assertEqual(p.delete_params, (plan.TEST_KEY, plan.SYNTHETIC_JSON))

    def test_sql_statements_are_narrow_and_parameterized(self):
        p = plan.plan_only()
        self.assertTrue(p.preflight_sql.startswith("SELECT "))
        self.assertTrue(p.delete_sql.startswith("DELETE FROM tv_flow_events WHERE "))
        self.assertEqual(p.delete_sql.count("?"), 2)
        self.assertNotIn("DROP ", p.delete_sql)
        self.assertNotIn("UPDATE ", p.delete_sql)

    def test_strict_preflight_rejects_many_or_invalid(self):
        with self.assertRaises(plan.UnsafeCleanup):
            plan.verify_preflight_rows([synthetic(), synthetic()])
        with self.assertRaises(plan.UnsafeCleanup):
            plan.verify_preflight_rows([{"symbol": "LAB:TEST_ONLY"}])


if __name__ == "__main__":
    unittest.main()
