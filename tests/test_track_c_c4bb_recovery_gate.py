"""C4b(b) only: synthetic temp SQLite inventory, backup, restore and kill gate."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import track_c_c4bb_recovery_gate as gate

class TrackC4bbRecoveryOffline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="remura-c4bb-")
        self.core = Path(self.temp.name) / gate.FILE

    def tearDown(self):
        self.temp.cleanup()

    def init(self, *, rows=3, journal="WAL"):
        db = sqlite3.connect(self.core, timeout=0.05)
        db.execute("PRAGMA journal_mode=" + journal)
        db.execute("CREATE TABLE lab_schema(version TEXT NOT NULL)")
        db.execute("INSERT INTO lab_schema VALUES(?)", (gate.LAB_SCHEMA,))
        db.execute("CREATE TABLE lab_receipts(id INTEGER PRIMARY KEY,witness TEXT NOT NULL)")
        for i in range(1, rows + 1):
            db.execute("INSERT INTO lab_receipts VALUES(?,?)", (i, f"{i:064x}"))
        db.commit()
        return db

    def run_lab(self, **kwargs):
        return gate.rehearse_backup_restore(
            self.core, mode=gate.MODE, enabled=True, **kwargs)

    def test_default_off_does_not_create_any_backup(self):
        with self.init():
            result = gate.rehearse_backup_restore(self.core, mode=gate.MODE)
        self.assertEqual(result["state"], "DISABLED_DEFAULT_OFF")
        self.assertFalse((self.core.parent / gate.BACKUP).exists())
        self.assertFalse(result["liveRestoreVerified"])

    def test_real_sqlite_online_backup_reopen_restore_synthetic(self):
        with self.init() as conn:
            result = self.run_lab()
            self.assertEqual(result["state"],
                             "SYNTHETIC_BACKUP_AND_REOPENED_RESTORE_MATCH")
            self.assertTrue(result["syntheticRestorePassed"])
            self.assertEqual(result["syntheticRowsCompared"], 3)
            self.assertFalse(result["liveBackupVerified"])
            self.assertFalse(result["crossHostRecoveryVerified"])
            self.assertEqual(conn.execute("SELECT count(*) FROM lab_receipts").fetchone()[0], 3)
            self.assertFalse((self.core.parent / gate.BACKUP).exists())
            self.assertFalse((self.core.parent / gate.RESTORED).exists())

    def test_staged_wal_is_included_in_backup(self):
        with self.init(rows=4) as conn:
            inv = gate.inventory_lab(self.core, mode=gate.MODE)
            self.assertEqual(inv["state"], "SYNTHETIC_FILE_SIZES_ONLY")
            self.assertEqual(inv["main"]["state"], "PRESENT_SYNTHETIC")
            self.assertFalse(inv["allLiveDatabaseFilesCovered"])
            self.assertEqual(self.run_lab()["syntheticRowsCompared"], 4)
            self.assertEqual(conn.execute("SELECT count(*) FROM lab_receipts").fetchone()[0], 4)

    def test_missing_wal_is_absent_not_zero_usage_assertion(self):
        with self.init(journal="DELETE"): pass
        inv = gate.inventory_lab(self.core, mode=gate.MODE)
        self.assertEqual(inv["wal"]["state"], "NOT_PRESENT_NOT_ZERO_USAGE_PROOF")
        self.assertIsNone(inv["wal"]["bytes"])
        self.assertTrue(self.run_lab()["syntheticRestorePassed"])

    def test_disk_shortage_fails_without_backup_creation(self):
        with self.init():
            result = self.run_lab(free_bytes_override=0)
        self.assertEqual(result["state"], "UNKNOWN_INSUFFICIENT_SYNTHETIC_FREE_SPACE")
        self.assertGreater(result["syntheticMinimumFreeBytes"], 0)
        self.assertFalse((self.core.parent / gate.BACKUP).exists())
        self.assertFalse(result["syntheticRestorePassed"])

    def test_corrupted_backup_is_not_a_pass_or_live_proof(self):
        with self.init() as db:
            result = self.run_lab(fault="corrupt_backup")
            self.assertEqual(db.execute("SELECT count(*) FROM lab_receipts").fetchone()[0], 3)
        self.assertEqual(result["state"], gate.UNKNOWN)
        self.assertFalse((self.core.parent / gate.BACKUP).exists())
        self.assertFalse(result["syntheticRestorePassed"])

    def test_existing_backup_never_overwritten(self):
        with self.init():
            backup = self.core.parent / gate.BACKUP
            backup.write_text("EXISTING_USER_BACKUP", encoding="ascii")
            result = self.run_lab()
            self.assertEqual(result["state"], gate.UNKNOWN)
            self.assertEqual(backup.read_text(encoding="ascii"), "EXISTING_USER_BACKUP")

    def test_wrong_schema_or_malformed_receipts_rejected(self):
        with self.init() as db:
            db.execute("UPDATE lab_schema SET version='NOT_A_LAB_SCHEMA'")
            db.commit()
            self.assertEqual(self.run_lab()["state"], gate.UNKNOWN)
            db.execute("UPDATE lab_schema SET version=?", (gate.LAB_SCHEMA,))
            db.execute("UPDATE lab_receipts SET witness='account_or_secret' WHERE id=1")
            db.commit()
            self.assertEqual(self.run_lab()["state"], gate.UNKNOWN)

    def test_symlink_and_external_live_path_rejected(self):
        with self.init():
            link = self.core.parent / gate.BACKUP
            try:
                link.symlink_to(self.core)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unsupported")
            self.assertEqual(self.run_lab()["state"], gate.UNKNOWN)
        with self.assertRaisesRegex(ValueError, "only_named_synthetic_temp"):
            gate.rehearse_backup_restore("/opt/remura/private/remura-prices.sqlite3",
                                         mode=gate.MODE, enabled=True)
        with self.assertRaisesRegex(ValueError, "explicit_offline"):
            gate.rehearse_backup_restore(self.core, enabled=True)

    def test_forged_hardlinks_or_sidecar_symlinks_rejected(self):
        with self.init(journal="DELETE"):
            sidecar = Path(str(self.core) + "-wal")
            try:
                sidecar.symlink_to(self.core)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unsupported")
            self.assertEqual(gate.inventory_lab(self.core, mode=gate.MODE)["state"], gate.UNKNOWN)
            self.assertEqual(self.run_lab()["state"], gate.UNKNOWN)

    def test_default_kill_switch_denies_probe_even_after_test_pass(self):
        with self.init():
            saved = self.run_lab()
        decision = gate.preview_kill_gate(saved, mode=gate.MODE, request_lab_probe=True)
        self.assertEqual(decision["state"], "KILL_SWITCH_ACTIVE")
        self.assertFalse(decision["hypotheticalLabProbeEligible"])
        self.assertFalse(decision["workerActuallyStarted"])
        self.assertFalse(decision["liveResearchEnabled"])
        self.assertEqual(decision["operationalDecision"], gate.NO_GO)

    def test_lab_kill_switch_toggle_does_not_enable_live(self):
        with self.init():
            success = self.run_lab()
        preview = gate.preview_kill_gate(success, mode=gate.MODE,
                                         kill_switch_active=False,
                                         request_lab_probe=True)
        self.assertTrue(preview["hypotheticalLabProbeEligible"])
        self.assertFalse(preview["workerActuallyStarted"])
        self.assertFalse(preview["liveResearchEnabled"])
        self.assertFalse(preview["independentExternalKillSwitchVerified"])
        for bad in (gate._result(gate.UNKNOWN), {"syntheticRestorePassed": True}):
            with self.subTest(bad=bad):
                self.assertFalse(gate.preview_kill_gate(
                    bad, mode=gate.MODE, kill_switch_active=False,
                    request_lab_probe=True)["hypotheticalLabProbeEligible"])

    def test_bad_inputs_fail_closed_and_no_secrets_in_output(self):
        with self.init():
            for value in (-1, "100", True):
                with self.assertRaises(ValueError):
                    self.run_lab(free_bytes_override=value)
            with self.assertRaises(ValueError):
                self.run_lab(fault="real_restore")
            with self.assertRaises(ValueError):
                gate.preview_kill_gate({}, mode=gate.MODE,
                                       kill_switch_active="false")
            result = self.run_lab()
        self.assertNotIn(str(self.core), repr(result))
        self.assertNotIn("EURUSD", repr(result))
        self.assertEqual(result["operationalDecision"], gate.NO_GO)
        self.assertEqual(result["newProviderCalls"], 0)

if __name__ == "__main__":
    unittest.main()
