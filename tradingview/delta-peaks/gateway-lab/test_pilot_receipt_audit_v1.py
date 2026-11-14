#!/usr/bin/env python3
# REMURA LAB v0.8.38 — 14/11/2026 CET — strict TEST receipt audit + offline tests.
"""One bounded SELECT of pilot metadata, no raw JSON, secrets, or writes.

Only explicit --live-read permits network access. Default --self-test is offline.
Receipt evidence is not proof of provenance beyond gateway validation, or of alpha.
"""
import argparse
import contextlib
import datetime
import io
import os
import unittest
from unittest.mock import patch
from urllib.parse import quote

from cloudflare_d1_readonly_audit import (
    AuditError, api_request, require_account_id, require_account_token,
)
from d1_test_target_preflight_v1 import MAIN_DB, TEST_DB, inspect_verified_inventory

START_MS = int(datetime.datetime(2026, 11, 14, 6, 3, 11,
                                  tzinfo=datetime.timezone.utc).timestamp() * 1000)
LIMIT = 100
SQL = (
    "SELECT event_key, received_at_ms, bar_close_ms, symbol, timeframe, "
    "event_type, version, is_timely FROM tv_flow_events "
    "WHERE received_at_ms >= ? AND symbol = ? AND timeframe = ? AND version = ? "
    "ORDER BY received_at_ms ASC, event_key ASC LIMIT ?"
)
PARAMS = [START_MS, "FXCM:EURUSD", "5", "0.8.1-lab", LIMIT + 1]
COLUMNS = {"event_key", "received_at_ms", "bar_close_ms", "symbol",
           "timeframe", "event_type", "version", "is_timely"}


def summarize(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("invalid_receipt_response")
    batches = payload.get("result")
    if (not isinstance(batches, list) or len(batches) != 1
            or not isinstance(batches[0], dict)
            or batches[0].get("success") is not True):
        raise AuditError("invalid_receipt_batch")
    rows = batches[0].get("results")
    if not isinstance(rows, list) or len(rows) > LIMIT + 1:
        raise AuditError("invalid_receipt_limit")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != COLUMNS:
            raise AuditError("unexpected_receipt_columns")
        key = row["event_key"]
        received, close = row["received_at_ms"], row["bar_close_ms"]
        if (not isinstance(key, str) or not 1 <= len(key) <= 512 or key in seen
                or row["symbol"] != "FXCM:EURUSD" or row["timeframe"] != "5"
                or row["version"] != "0.8.1-lab"
                or row["event_type"] not in ("BAR_EVENT", "HEARTBEAT")
                or type(received) is not int or type(close) is not int
                or received < START_MS or close < 1_000_000_000_000
                or type(row["is_timely"]) is not int or row["is_timely"] not in (0, 1)
                or not -120_000 <= received - close <= 86_400_000):
            raise AuditError("invalid_or_duplicate_receipt")
        seen.add(key)
    sample = rows[:LIMIT]
    return {
        "status": "RECEIPTS_PRESENT" if sample else "NO_MATCHING_RECEIPTS",
        "sample_rows": len(sample),
        "more_available": len(rows) > LIMIT,
        "heartbeats": sum(r["event_type"] == "HEARTBEAT" for r in sample),
        "bar_events": sum(r["event_type"] == "BAR_EVENT" for r in sample),
        "timely": sum(r["is_timely"] == 1 for r in sample),
        "first_received_ms": min((r["received_at_ms"] for r in sample), default=None),
        "max_bar_close_lag_ms": max(
            (r["received_at_ms"] - r["bar_close_ms"] for r in sample), default=None),
    }


def read_live(account_id, token, *, explicit=False):
    if explicit is not True:
        raise AuditError("live_read_not_requested")
    account = require_account_id(account_id)
    token = require_account_token(token)
    base = f"/accounts/{account}/d1/database"
    ids = inspect_verified_inventory(api_request("GET", base + "?page=1&per_page=100", token))
    if ids[TEST_DB] == ids[MAIN_DB]:
        raise AuditError("test_db_not_isolated")
    endpoint = base + "/" + quote(ids[TEST_DB], safe="") + "/query"
    # Cloudflare D1 REST uses POST for the strictly read-only, parameterized SELECT.
    return summarize(api_request("POST", endpoint, token,
                                 {"sql": SQL, "params": list(PARAMS)}))


def envelope(rows):
    return {"success": True, "result": [{"success": True, "results": rows}]}


def sample_row(n=0):
    return {"event_key": "offline-fixture-" + str(n), "received_at_ms": START_MS + 5_000 + n,
            "bar_close_ms": START_MS + n, "symbol": "FXCM:EURUSD", "timeframe": "5",
            "event_type": "HEARTBEAT", "version": "0.8.1-lab", "is_timely": 1}


class ReceiptTests(unittest.TestCase):
    def test_empty_does_not_invent_receipts(self):
        result = summarize(envelope([]))
        self.assertEqual(result["status"], "NO_MATCHING_RECEIPTS")
        self.assertEqual(result["sample_rows"], 0)

    def test_first_receipt_and_lag(self):
        result = summarize(envelope([sample_row()]))
        self.assertEqual(result["status"], "RECEIPTS_PRESENT")
        self.assertEqual(result["heartbeats"], 1)
        self.assertEqual(result["max_bar_close_lag_ms"], 5000)

    def test_synthetic_and_other_feed_rejected(self):
        for field, value in [("symbol", "LAB:TEST_ONLY"), ("version", "synthetic-test-v0.1"),
                             ("timeframe", "1"), ("is_timely", True)]:
            item = sample_row()
            item[field] = value
            with self.assertRaises(AuditError):
                summarize(envelope([item]))

    def test_duplicate_or_raw_json_rejected(self):
        with self.assertRaises(AuditError):
            summarize(envelope([sample_row(), sample_row()]))
        item = sample_row()
        item["raw_json"] = "private"
        with self.assertRaises(AuditError):
            summarize(envelope([item]))

    def test_limit_is_sample_not_total(self):
        result = summarize(envelope([sample_row(i) for i in range(LIMIT + 1)]))
        self.assertEqual(result["sample_rows"], LIMIT)
        self.assertTrue(result["more_available"])

    def test_error_is_not_empty_data(self):
        for invalid in [{}, {"success": True, "result": []}, envelope([{}])]:
            with self.assertRaises(AuditError):
                summarize(invalid)

    def test_no_network_without_explicit_consent(self):
        with patch(__name__ + ".api_request") as api:
            with self.assertRaises(AuditError):
                read_live("", "")
        api.assert_not_called()

    def test_only_test_db_query_and_fixed_parameters(self):
        main = "00000000-0000-4000-8000-000000000001"
        test = "00000000-0000-4000-8000-000000000002"
        with (patch(__name__ + ".require_account_id", return_value="a"*32),
              patch(__name__ + ".require_account_token", return_value="fixture"),
              patch(__name__ + ".inspect_verified_inventory", return_value={MAIN_DB:main, TEST_DB:test}),
              patch(__name__ + ".api_request", side_effect=[{}, envelope([sample_row()])]) as api):
            result = read_live("mock", "mock", explicit=True)
        self.assertEqual(result["sample_rows"], 1)
        self.assertEqual(api.call_count, 2)
        args = api.call_args_list[1].args
        self.assertEqual(args[0], "POST")
        self.assertTrue(args[1].endswith("/" + test + "/query"))
        self.assertNotIn(main, args[1])
        self.assertEqual(args[3], {"sql": SQL, "params": PARAMS})
        self.assertTrue(SQL.startswith("SELECT "))
        self.assertNotIn("raw_json", SQL)


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--live-read", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        report = read_live(os.getenv("REMURA_CF_ACCOUNT_ID", ""),
                           os.getenv("REMURA_CF_D1_READ_TOKEN", ""), explicit=True)
    except (AuditError, ValueError, TypeError, KeyError, OSError):
        print("REMURA_TEST_RECEIPTS=UNKNOWN_READ_FAILED")
        return 2
    print("REMURA_TEST_RECEIPTS=" + report.pop("status"))
    for key, value in report.items():
        print(f"{key.upper()}={value}")
    print("TARGET=EU_D1_TEST_ONLY; SQL=SELECT; RAW_JSON=NOT_READ")
    print("SIGNAL_VALIDATION=NOT_PERFORMED; SAMPLE_NOT_TOTAL=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
