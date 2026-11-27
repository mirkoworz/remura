"""Safety checks for the one-shot Oracle B-P0 staging runner.

No network, no production database, no Oracle connection.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from scripts import shark_oracle_staging_gate as gate
from scripts import shark_cot_asof_witness as witness
import signals_monitor as live
from test_shark_staging_scan import fixture, NOW


class OracleStagingGateTests(unittest.TestCase):
    def test_guard_rejects_live_checkout(self):
        with patch.object(gate, "ROOT", Path("/opt/remura")):
            with self.assertRaisesRegex(RuntimeError, "staging_checkout"):
                gate.guard_host()

    def test_guard_rejects_root_user(self):
        with patch.object(gate, "ROOT", Path("/tmp/safe-research")):
            with patch.object(gate.os, "geteuid", return_value=0):
                with self.assertRaisesRegex(RuntimeError, "as_root"):
                    gate.guard_host()

    def test_guard_rejects_low_tmp_disk(self):
        class Usage:
            free = 1
        with patch.object(gate, "ROOT", Path("/tmp/safe-research")):
            with patch.object(gate.os, "geteuid", return_value=1000):
                with patch.object(gate.shutil, "disk_usage", return_value=Usage()):
                    with self.assertRaisesRegex(RuntimeError, "headroom"):
                        gate.guard_host()

    def test_staging_only_backup_restore_rollback(self):
        with tempfile.TemporaryDirectory(prefix="remura-test-") as folder:
            directory = Path(folder)
            database = directory / "compact.sqlite"
            fixture(database, with_cot=False, all_priced=False, m15_count=1024)
            with patch.object(witness, "_clock",
                              return_value=NOW + timedelta(seconds=2)):
                out = live.scan_once_with_compact_price_only_research(
                    database, NOW)
            self.assertEqual(out["priceOnlyResearch"]["storedMarkets"], 34)
            result = gate.verify_backup_restore_and_rollback(
                database, directory)
            self.assertEqual(result["sqliteRollback"], "PASS")
            self.assertEqual(result["sqliteBackupRestore"], "PASS")
            self.assertTrue(result["immutableTriggersPreserved"])
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute(
                    "PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
