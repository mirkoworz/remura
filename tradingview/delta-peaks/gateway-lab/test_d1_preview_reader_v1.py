# REMURA v0.8.16 TEST — 13/11/2026, ore 13:09 CET
# Synthetic mocked HTTP only; no Cloudflare account, network, or live D1.
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_telemetry_v1 import T0, sample
import d1_preview_reader_v1 as m
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
TOKEN = "cfat_" + "q" * 50
DB_UUID = "b45b62ad-f537-4e94-8826-681ea4573fe6"

def db_list(name="remura-tv-lab", region="eu"):
    return {"success": True, "result": [{
        "name": name, "jurisdiction": region, "uuid": DB_UUID,
    }]}

def result_rows(rows):
    return {"success": True, "result": [
        {"success": True, "results": rows},
    ]}

def row():
    p = sample()
    return {
        "event_key": "|".join((
            p["symbol"], p["timeframe"], str(p["bar_close_ms"]),
            p["version"], p["event_type"],
        )),
        "received_at_ms": T0 + 1000,
        "bar_close_ms": p["bar_close_ms"],
        "symbol": p["symbol"],
        "timeframe": p["timeframe"],
        "event_type": p["event_type"],
        "version": p["version"],
        "is_timely": 1,
        "raw_json": json.dumps(p, separators=(",", ":")),
    }


class MainD1PreviewReaderTests(unittest.TestCase):
    def test_disabled_by_default_without_any_api_calls(self):
        with patch.object(m, "api_request") as api:
            with self.assertRaisesRegex(AuditError, "live_read_not_authorized"):
                m.fetch_preview_readonly(ACCOUNT, TOKEN, start_ms=T0, end_ms=T0+1000)
            api.assert_not_called()

    def test_no_mutating_sql_or_semicolon(self):
        m.assert_read_query(m.READ_SQL)
        self.assertTrue(m.READ_SQL.startswith("SELECT "))
        self.assertNotIn("DELETE", m.READ_SQL)
        for s in ("DELETE FROM tv_flow_events", "SELECT * FROM tv_flow_events;",
                  "UPDATE tv_flow_events SET event_type='X'"):
            with self.subTest(sql=s), self.assertRaises(AuditError):
                m.assert_read_query(s)

    def test_main_db_must_be_correct_eu(self):
        self.assertEqual(m.find_main_database(db_list()), DB_UUID)
        for params in [
            ("remura-tv-lab-test", "eu"),
            ("remura-tv-lab", "us"),
        ]:
            with self.subTest(params=params), self.assertRaises(AuditError):
                m.find_main_database(db_list(*params))

    def test_duplicate_named_main_db_rejected(self):
        payload = db_list()
        payload["result"].append(dict(payload["result"][0]))
        with self.assertRaises(AuditError):
            m.find_main_database(payload)

    def test_invalid_uuid_rejected(self):
        payload = db_list()
        payload["result"][0]["uuid"] = "bad"
        with self.assertRaises(AuditError):
            m.find_main_database(payload)

    def test_invalid_batch_or_partial_export_rejected(self):
        p = result_rows([row(), row()])
        with self.assertRaisesRegex(AuditError, "truncated"):
            m.parse_select_response(p, 1)
        p["result"].append({"success": True, "results": []})
        with self.assertRaises(AuditError):
            m.parse_select_response(p, 10)

    def test_invalid_or_extra_columns_rejected(self):
        p = result_rows([dict(row(), account_token="not-in-export")])
        with self.assertRaises(AuditError):
            m.parse_select_response(p, 10)

    def test_empty_result_list_is_valid_but_not_proof_of_data(self):
        self.assertEqual(m.parse_select_response(result_rows([]), 10), [])

    def test_wrong_query_limit_or_window_no_api(self):
        for limit in (0, 101, True, "10"):
            with self.subTest(limit=limit), patch.object(m, "api_request") as api:
                with self.assertRaises(AuditError):
                    m.fetch_preview_readonly(
                        ACCOUNT, TOKEN, start_ms=T0, end_ms=T0 + 5000,
                        limit=limit, explicit_live_approval=True)
                api.assert_not_called()
        with patch.object(m, "api_request") as api:
            with self.assertRaises(AuditError):
                m.fetch_preview_readonly(
                    ACCOUNT, TOKEN, start_ms=T0, end_ms=T0+86_400_001,
                    explicit_live_approval=True)
            api.assert_not_called()

    def test_explicitly_authorized_mocked_read_is_select_only(self):
        calls = []
        def fake(method, path, token, body=None):
            calls.append((method, path, body))
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("?name=remura-tv-lab"):
                return db_list()
            if path.endswith("/query"):
                return result_rows([row()])
            raise AssertionError("unexpected path")
        with (patch.object(m, "require_account_id", return_value=ACCOUNT),
              patch.object(m, "require_account_token", return_value=TOKEN),
              patch.object(m, "api_request", side_effect=fake)):
            result = m.fetch_preview_readonly(
                ACCOUNT, TOKEN, start_ms=T0, end_ms=T0 + 5000,
                limit=5, explicit_live_approval=True)
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["observations"][0]["verdict"],
                         "NESSUN_SEGNALE_OPERATIVO")
        self.assertFalse(result["observations"][0]["statistical_edge_validated"])
        self.assertEqual([method for method, _, _ in calls],
                         ["GET", "GET", "POST"])
        self.assertEqual(calls[2][2]["sql"], m.READ_SQL)
        self.assertEqual(calls[2][2]["params"], [T0, T0 + 5000, 6])
        self.assertNotIn("raw_json", json.dumps(result))
        self.assertTrue(all("remura-tv-lab-test" not in path
                            for _, path, _ in calls))

    def test_invalid_record_from_api_prevents_successful_report(self):
        bad = row()
        bad["is_timely"] = 0
        def fake(method, path, token, body=None):
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("?name=remura-tv-lab"):
                return db_list()
            return result_rows([bad])
        with (patch.object(m, "require_account_id", return_value=ACCOUNT),
              patch.object(m, "require_account_token", return_value=TOKEN),
              patch.object(m, "api_request", side_effect=fake)):
            with self.assertRaisesRegex(AuditError, "invalid"):
                m.fetch_preview_readonly(
                    ACCOUNT, TOKEN, start_ms=T0, end_ms=T0+5000,
                    explicit_live_approval=True)


if __name__ == "__main__":
    unittest.main()
