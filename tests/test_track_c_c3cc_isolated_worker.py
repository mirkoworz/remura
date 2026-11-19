"""Track C3c-c offline independent worker crash/timeout/resource tests.

All COT responses fake; source and research SQLite in temporary directory.
No new cron, worker process on VPS, service, HTTP or LIVE integration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ast
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cot_monitor
from price_store import connect
import track_c_c3b_durable_shadow as shadow
import track_c_c3cc_isolated_worker as lab

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
STAMP = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
LATER = (NOW + timedelta(seconds=21)).strftime("%Y-%m-%dT%H:%M:%SZ")


def meta(index=1):
    return {"symbol": "EURUSD", "source": "cot", "seenAtUtc": STAMP,
            "coreCommittedAtUtc": STAMP,
            "originalSha256": f"{index:064x}"}


def fake_rows(dataset):
    spec = cot_monitor.DATASETS[dataset]
    return [{
        "report_date_as_yyyy_mm_dd": "2026-11-03T00:00:00",
        "cftc_contract_market_code": code,
        "open_interest_all": "1000",
        **{key: "100" for key in spec["keys"]},
    } for code in spec["codes"]]


class TrackC3ccIsolatedWorkerLab(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="remura-c3b-")
        self.root = Path(self.tmp.name)
        self.research = self.root / shadow.FILE
        self.core = self.root / "synthetic-original-core.sqlite3"
        self.assertEqual(shadow.prepare(self.research, mode=shadow.MODE),
                         shadow.SCHEMA)

    def tearDown(self):
        self.tmp.cleanup()

    def stage(self, index=1):
        return shadow.stage(self.research, meta(index), at=STAMP,
                            enabled=True, mode=shadow.MODE)

    def run_worker(self, behavior="ack", timeout_seconds=2.0):
        return lab.run_lab_once(self.research, at=STAMP, enabled=True,
                                mode=lab.MODE, behavior=behavior,
                                timeout_seconds=timeout_seconds)

    def collect_core(self):
        calls = []
        def fetch(dataset, at):
            self.assertEqual(at, NOW)
            calls.append(dataset)
            return fake_rows(dataset)
        result = cot_monitor.collect_once(self.core, now=NOW, fetch=fetch)
        self.assertEqual(result["errors"], {})
        self.assertEqual(result["saved"], {"tff": 11, "disagg": 3})
        self.assertEqual(calls, ["tff", "disagg"])
        db = connect(self.core)
        try:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM cot_reports").fetchone()[0], 14)
        finally:
            db.close()

    def test_independent_subprocess_ack_is_synthetic_not_first_seen(self):
        self.collect_core()
        self.assertEqual(self.stage(), shadow.STAGED)
        self.assertEqual(self.run_worker(), shadow.ACKED)
        s = shadow.inspect_lab(self.research, mode=shadow.MODE)
        self.assertEqual(s["syntheticAck"], 1)
        self.assertFalse(s["realCollectorIsolationProven"])
        self.assertFalse(s["actualEdgeEstablished"])
        self.assertEqual(self.run_worker(), shadow.UNKNOWN)
        self.collect_core()

    def test_abrupt_worker_death_does_not_rollback_core(self):
        self.collect_core()
        self.assertEqual(self.stage(), shadow.STAGED)
        self.assertEqual(self.run_worker("crash"), shadow.UNKNOWN)
        self.assertEqual(shadow.inspect_lab(
            self.research, mode=shadow.MODE)["leased"], 1)
        self.collect_core()
        self.assertIsNone(shadow.claim(
            self.research, at=LATER, enabled=True, mode=shadow.MODE))
        s = shadow.inspect_lab(self.research, mode=shadow.MODE)
        self.assertEqual(s["unknown"], 1)
        self.assertEqual(s["syntheticAck"], 0)

    def test_stalled_worker_is_killed_within_parent_timeout(self):
        self.assertEqual(self.stage(), shadow.STAGED)
        before = time.monotonic()
        self.assertEqual(self.run_worker("stall", .6), shadow.UNKNOWN)
        self.assertLess(time.monotonic() - before, 3.0)
        self.collect_core()
        self.assertIsNone(shadow.claim(
            self.research, at=LATER, enabled=True, mode=shadow.MODE))
        self.assertEqual(shadow.inspect_lab(
            self.research, mode=shadow.MODE)["unknown"], 1)

    def test_cpu_spin_is_bounded_by_timeout_or_rlimit(self):
        self.assertEqual(self.stage(), shadow.STAGED)
        started = time.monotonic()
        self.assertEqual(self.run_worker("spin", 1.1), shadow.UNKNOWN)
        self.assertLess(time.monotonic() - started, 3.0)
        self.collect_core()

    def test_saturated_queue_refuses_extra_without_core_loss(self):
        self.collect_core()
        for i in range(1, shadow.MAX_PENDING + 1):
            self.assertEqual(self.stage(i), shadow.STAGED)
        self.assertEqual(self.stage(99), shadow.UNKNOWN)
        s = shadow.inspect_lab(self.research, mode=shadow.MODE)
        self.assertEqual(s["pending"], shadow.MAX_PENDING)
        self.collect_core()
        self.assertEqual(self.run_worker("crash"), shadow.UNKNOWN)
        self.assertEqual(self.stage(99), shadow.UNKNOWN)
        self.collect_core()

    def test_locked_research_db_is_not_a_core_transaction_lock(self):
        self.collect_core()
        self.assertEqual(self.stage(), shadow.STAGED)
        blocker = sqlite3.connect(str(self.research), timeout=0.025)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            blocker.execute("UPDATE c3b_schema_guard SET version=version")
            self.assertEqual(self.run_worker(), shadow.UNKNOWN)
            self.assertEqual(self.stage(2), shadow.UNKNOWN)
            self.collect_core()
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(self.run_worker(), shadow.ACKED)

    def test_disabled_wrong_path_and_mode_fail_closed(self):
        self.assertEqual(lab.run_lab_once(
            self.research, at=STAMP, mode=lab.MODE), shadow.UNKNOWN)
        with self.assertRaisesRegex(ValueError, "explicit_isolated"):
            lab.run_lab_once(self.research, at=STAMP, enabled=True)
        with self.assertRaises(ValueError):
            lab.run_lab_once("/opt/remura/private/remura-prices.sqlite3",
                             at=STAMP, enabled=True, mode=lab.MODE)
        with self.assertRaises(ValueError):
            lab.run_lab_once(self.research, at=STAMP, enabled=True,
                             mode=lab.MODE, behavior="production")
        with self.assertRaises(ValueError):
            lab.run_lab_once(self.research, at=STAMP, enabled=True,
                             mode=lab.MODE, timeout_seconds=60)
        self.assertEqual(shadow.inspect_lab(
            self.research, mode=shadow.MODE)["total"], 0)

    def test_subprocess_drops_parent_credentials_and_pythonpath(self):
        self.assertEqual(self.stage(), shadow.STAGED)
        with patch.dict(os.environ, {
                "CTRADER_CLIENT_SECRET": "DO_NOT_LEAK",
                "GITHUB_TOKEN": "DO_NOT_LEAK",
                "PYTHONPATH": "/not/trusted"}, clear=False):
            self.assertEqual(self.run_worker(), shadow.ACKED)
        # Sanitized subprocess output is only the literal SYNTHETIC_ACK.
        self.assertEqual(shadow.inspect_lab(
            self.research, mode=shadow.MODE)["syntheticAck"], 1)

    def test_static_isolation_no_live_imports_or_provider_clients(self):
        tree = ast.parse((ROOT / "scripts" /
                          "track_c_c3cc_isolated_worker.py").read_text("utf-8"))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(a.name for a in node.names)
            if isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        self.assertFalse(any(
            name.startswith(("private_server", "cot_monitor", "requests",
                             "urllib", "socket", "ctrader_feed",
                             "scripts.private_server", "scripts.cot_monitor"))
            for name in names))
        live_files = ("private_server.py", "cot_monitor.py",
                      "price_store.py", "signals_monitor.py",
                      "update_myfxbook.py")
        for filename in live_files:
            content = (ROOT / "scripts" / filename).read_text("utf-8")
            self.assertNotIn("track_c_c3cc_isolated_worker", content)
        self.assertNotIn("core", str(self.research))


if __name__ == "__main__":
    unittest.main()
