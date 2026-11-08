"""REMURA C4b(f): metadata-only temp folder, never touch VPS in CI."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import track_c_c4bf_metadata_inventory as m


class ReadonlyInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="remura-c4bf-")
        self.root = Path(self.temp.name)
        self.core = self.root / m.DB_NAME

    def tearDown(self):
        self.temp.cleanup()

    def scan(self, **opts):
        return m.inventory(self.root, mode=m.LAB_MODE, **opts)

    def core_file(self):
        self.core.write_bytes(b"FICTIONAL_DATABASE_METADATA_NOT_A_REAL_SQLITE_DB")
        return self.core

    def archive(self, *, name="backup-v156-20261108T123000Z-abcdef"):
        folder=self.root/m.BACKUP_DIR/name
        folder.mkdir(parents=True)
        (folder/m.DB_NAME).write_bytes(b"FICTIONAL_BACKUP")
        (folder/"manifest.txt").write_text("FICTIONAL_HASH",encoding="ascii")
        return folder

    def test_missing_core_is_unknown_not_zero(self):
        x=self.scan()
        self.assertEqual(x["state"],"UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")
        self.assertIsNone(x["main"])
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_only_known_main_and_absent_sidecars(self):
        source=self.core_file()
        before=(source.stat().st_mtime_ns,source.read_bytes())
        x=self.scan()
        self.assertEqual(x["main"]["apparentBytes"],len(before[1]))
        self.assertEqual(x["wal"]["state"],"NOT_PRESENT_AT_METADATA_INSTANT")
        self.assertIsNone(x["shm"]["apparentBytes"])
        self.assertEqual((source.stat().st_mtime_ns,source.read_bytes()),before)
        self.assertEqual(x["localBackups"]["state"],"UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY")
        self.assertFalse(x["offhostBackupExistsVerified"])

    def test_wal_and_shm_size_counted_without_open(self):
        self.core_file()
        (self.root/(m.DB_NAME+"-wal")).write_bytes(b"W"*100)
        (self.root/(m.DB_NAME+"-shm")).write_bytes(b"S"*64)
        x=self.scan()
        self.assertEqual(x["wal"]["apparentBytes"],100)
        self.assertEqual(x["shm"]["apparentBytes"],64)
        self.assertFalse(x["sourceUnmodifiedProven"])

    def test_local_archive_metadata_does_not_verify_restore(self):
        self.core_file();self.archive()
        x=self.scan()
        self.assertEqual(x["localBackups"]["archives"],1)
        self.assertEqual(x["localBackups"]["state"],"LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE")
        self.assertGreater(x["localBackups"]["apparentBytes"],0)
        self.assertFalse(x["backupRestoreIntegrityVerified"])
        self.assertFalse(x["offhostBackupExistsVerified"])

    def test_no_local_archives_does_not_positively_verify_anything(self):
        self.core_file();(self.root/m.BACKUP_DIR).mkdir()
        x=self.scan()
        self.assertEqual(x["localBackups"]["state"],"UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE")
        self.assertIsNone(x["localBackups"]["apparentBytes"])

    def rollback(self, *, name="rollback-v164-abcdefgh"):
        folder=self.root/m.BACKUP_DIR/name
        folder.mkdir(parents=True, exist_ok=True)
        (folder/"manifest.json").write_text("FICTIONAL_ROLLBACK_MANIFEST",encoding="ascii")
        nested=folder/"scripts"
        nested.mkdir()
        (nested/"price_store.py").write_bytes(b"FICTIONAL_SOURCE_COPY")
        return folder

    def test_v164_rollback_only_is_not_database_backup(self):
        self.core_file()
        self.rollback()
        x=self.scan()
        self.assertEqual(x["localBackups"]["archives"],0)
        self.assertEqual(x["localBackups"]["rollbacks"],1)
        self.assertIsNone(x["localBackups"]["apparentBytes"])
        self.assertGreater(x["localBackups"]["rollbackApparentBytes"],0)
        self.assertEqual(x["localBackups"]["state"],
                         "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF")
        self.assertFalse(x["backupRestoreIntegrityVerified"])

    def test_v156_sqlite_archive_and_v164_code_rollback_separate(self):
        self.core_file();self.archive();self.rollback()
        x=self.scan()
        self.assertEqual(x["localBackups"]["archives"],1)
        self.assertEqual(x["localBackups"]["rollbacks"],1)
        self.assertEqual(x["localBackups"]["state"],
                         "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE")
        self.assertFalse(x["offhostBackupExistsVerified"])

    def test_symlink_or_missing_manifest_inside_v164_rollback_invalid(self):
        self.core_file()
        folder=self.rollback()
        (folder/"manifest.json").unlink()
        self.assertEqual(self.scan()["localBackups"]["state"],
                         "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS")
        (folder/"manifest.json").write_bytes(b"FICTIONAL")
        link=folder/"scripts"/"symlink"
        try:link.symlink_to(self.core)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        self.assertEqual(self.scan()["localBackups"]["state"],
                         "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS")

    def test_deep_rollback_tree_rejected_in_bounded_read_only_pass(self):
        self.core_file()
        folder=self.rollback()
        cursor=folder
        for i in range(m.MAX_ROLLBACK_DEPTH+2):
            cursor=cursor/("sub"+str(i))
            cursor.mkdir()
        x=self.scan()
        self.assertEqual(x["localBackups"]["state"],
                         "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS")

    def test_incomplete_or_unknown_backup_layout_fails_closed(self):
        self.core_file()
        base=self.root/m.BACKUP_DIR
        base.mkdir()
        (base/"candidate-v156-pending").mkdir()
        x=self.scan()
        self.assertEqual(x["localBackups"]["state"],"UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS")

    def test_missing_manifest_fails_backup_coverage(self):
        self.core_file()
        archive=self.archive()
        (archive/"manifest.txt").unlink()
        x=self.scan()
        self.assertEqual(x["localBackups"]["state"],"UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS")

    def test_symlink_core_rejected(self):
        target=self.root/"SECRET"
        target.write_bytes(b"secret")
        try: self.core.symlink_to(target)
        except (OSError,NotImplementedError): self.skipTest("symlink unavailable")
        x=self.scan()
        self.assertEqual(x["state"],"UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")
        self.assertNotIn(str(target),repr(x))

    def test_symlink_sidecar_rejected(self):
        self.core_file()
        sidecar=self.root/(m.DB_NAME+"-wal")
        try: sidecar.symlink_to(self.core)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        self.assertEqual(self.scan()["state"],"UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")

    def test_symlink_backup_dir_rejected(self):
        self.core_file()
        folder=self.root/"shadow"
        folder.mkdir()
        try: (self.root/m.BACKUP_DIR).symlink_to(folder)
        except (OSError,NotImplementedError): self.skipTest("symlink unavailable")
        x=self.scan()
        self.assertEqual(x["localBackups"]["state"],"UNKNOWN_BACKUP_DIRECTORY_TYPE")

    def test_hardlinked_main_rejected(self):
        self.core_file()
        link=self.root/"hard"
        try:os.link(self.core,link)
        except OSError:self.skipTest("hardlink unavailable")
        self.assertEqual(self.scan()["state"],"UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")

    def test_synthetic_low_disk_is_pressure_not_a_go(self):
        self.core_file()
        x=self.scan(lab_free_override=0)
        self.assertEqual(x["pressure"],"RESEARCH_PRESSURE_CAUTION")
        self.assertEqual(x["filesystem"]["availableBytes"],0)
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_nominal_disk_is_still_no_go(self):
        self.core_file()
        x=self.scan()
        self.assertEqual(x["operationalDecision"],m.NO_GO)
        self.assertFalse(x["oracleAlwaysFreeBillingVerified"])
        self.assertFalse(x["allOtherPrivateStorageCovered"])
        self.assertEqual(x["newNetworkCalls"],0)

    def test_out_of_scope_and_live_without_approval_rejected(self):
        with self.assertRaisesRegex(ValueError,"explicit_metadata_audit_mode"):
            m.inventory(self.root)
        with self.assertRaisesRegex(ValueError,"explicit_live_path_authorization"):
            m.inventory("/opt/remura/private",mode=m.LIVE_MODE)
        with self.assertRaisesRegex(ValueError,"explicit_live_path_authorization"):
            m.inventory(self.root,mode=m.LIVE_MODE,live_approved=True)
        with self.assertRaisesRegex(ValueError,"strict_lab_directory"):
            m.inventory("/opt/remura/private",mode=m.LAB_MODE)
        with self.assertRaisesRegex(ValueError,"only_bounded_lab"):
            self.scan(lab_free_override=True)

    def test_no_sqlite_or_network_import_and_no_server_activation(self):
        script=(ROOT/"scripts"/"track_c_c4bf_metadata_inventory.py").read_text()
        tree=ast.parse(script)
        imports={a.name for node in ast.walk(tree)
                 if isinstance(node,ast.Import) for a in node.names}
        self.assertTrue({"sqlite3","requests","socket","subprocess","urllib"}.isdisjoint(imports))
        for filename in ("private_server.py","price_store.py","signals_monitor.py",
                         "cot_monitor.py","update_myfxbook.py"):
            self.assertNotIn("track_c_c4bf_metadata_inventory",
                             (ROOT/"scripts"/filename).read_text())

if __name__=="__main__":unittest.main()
