"""Offline tests for v1.56 guarded backup. No production DB or network access."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("backup_v156", ROOT/"deploy/oracle/backup_v156.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.private = self.base/"private"
        self.private.mkdir()
        self.source = self.private/"remura-prices.sqlite3"
        with sqlite3.connect(self.source) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE status(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT INTO prices VALUES ('EURUSD', 'PRICE_NOT_TO_PRINT')")
            db.execute("INSERT INTO status VALUES ('state', 'PRIVATE_NOT_TO_PRINT')")
        self.patches = [
            patch.object(tool,"APP",self.base),
            patch.object(tool,"PRIVATE",self.private),
            patch.object(tool,"SOURCE",self.source),
            patch.object(tool,"BACKUPS",self.private/"predeploy-backups"),
        ]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def test_check_is_read_only(self):
        before = self.source.read_bytes()
        self.assertEqual(tool.validate_source()[1], (1,1))
        self.assertEqual(before, self.source.read_bytes())
        self.assertFalse(tool.BACKUPS.exists())
        with patch("sys.argv",["backup_v156.py","--check"]),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tool.main(),0)
        self.assertIn("NESSUNA_SCRITTURA=SI",out.getvalue())

    def test_snapshot_and_isolated_restore_without_touching_source(self):
        before = self.source.read_bytes()
        details = tool.create_backup()
        self.assertIn("RESTORE_TEST=OK",details)
        self.assertEqual(before,self.source.read_bytes())
        folders=list(tool.BACKUPS.glob("backup-v156-*"))
        self.assertEqual(len(folders),1)
        snapshot=folders[0]/"remura-prices.sqlite3"
        self.assertEqual(tool.inspect(snapshot),(1,1))
        self.assertTrue((folders[0]/"manifest.txt").is_file())
        self.assertEqual(snapshot.stat().st_mode&0o777,0o600)
        self.assertNotIn("PRIVATE_NOT_TO_PRINT","\n".join(details))
        self.assertNotIn("PRICE_NOT_TO_PRINT","\n".join(details))
        # A second run does not delete or overwrite previous backup.
        tool.create_backup()
        self.assertEqual(len(list(tool.BACKUPS.glob("backup-v156-*"))),2)

    def test_detects_corrupt_schema_and_aborts_before_backup(self):
        with sqlite3.connect(self.source) as db:
            db.execute("DROP TABLE status")
        with self.assertRaisesRegex(RuntimeError,"SOURCE_SCHEMA"):
            tool.create_backup()
        self.assertFalse(tool.BACKUPS.exists())

    def test_rejects_source_symlink_and_space_low(self):
        self.source.unlink()
        self.source.symlink_to(self.base/"wrong.sqlite")
        with self.assertRaisesRegex(RuntimeError,"SOURCE_MISSING_OR_LINK"):
            tool.validate_source()
        self.source.unlink()
        with sqlite3.connect(self.source) as db:
            db.execute("CREATE TABLE prices(x)")
            db.execute("CREATE TABLE status(x)")
        class Disk:
            free=0
        with patch.object(tool.shutil,"disk_usage",return_value=Disk()):
            with self.assertRaisesRegex(RuntimeError,"DISK_SPACE"):
                tool.create_backup()

    def test_cli_fails_closed_no_sensitive_exception_text(self):
        with patch("sys.argv",["backup_v156.py","--check"]), \
             patch.object(tool,"validate_source",side_effect=sqlite3.DatabaseError("SECRET_PAYLOAD")), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(tool.main(),1)
        self.assertIn("PREFLIGHT_SQLITE=STOP",out.getvalue())
        self.assertNotIn("SECRET_PAYLOAD",out.getvalue())


if __name__ == "__main__":
    unittest.main()
