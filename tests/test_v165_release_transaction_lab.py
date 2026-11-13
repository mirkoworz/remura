"""v1.65 isolated synthetic release transaction tests. NO VPS or provider access."""
from __future__ import annotations

import ast
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"deploy/oracle/v165_release_transaction_lab.py"
spec=importlib.util.spec_from_file_location("v165_release_transaction_lab", SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class V165SyntheticTransactionTests(unittest.TestCase):
    def test_no_implicit_or_unknown_mode_allowed(self):
        for mode in (None, "LIVE", "V165_APPLY", "OFFLINE", ""):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(m.LabRejection,"STOP_OFFLINE_MODE_REQUIRED"):
                    m.simulate(mode=mode)

    def test_wal_backup_isolation_and_no_live_attestations(self):
        result=m.simulate(mode=m.MODE)
        self.assertEqual(result["schema"],m.SCHEMA)
        self.assertTrue(result["syntheticSqliteWalBackupRestored"])
        self.assertTrue(result["syntheticIntegrityAndRowsVerified"])
        self.assertTrue(result["syntheticFileRollbackVerified"])
        self.assertTrue(result["syntheticUpdaterStateUnchanged"])
        for field in ("realVpsContacted","realDatabaseRead","realBackupCreated",
                      "realRestoreVerified","realFilesInstalled",
                      "realAutoupdaterChanged","offhostBackupVerified",
                      "oracleBillingVerified","releaseAuthorized","researchLiveEnabled"):
            self.assertIs(result[field],False,field)
        self.assertEqual(result["operationalDecision"],m.NO_GO)

    def test_fake_release_manifest_has_exactly_14_public_file_paths(self):
        self.assertEqual(len(m.EXPECTED_FILES),14)
        staged=m.staged_files(m.synthetic_files())
        self.assertEqual(set(staged),m.EXPECTED_FILES)
        self.assertTrue(all(b"FICTIONAL" in x for x in staged.values()))
        self.assertTrue(all(b"V165" in x for x in staged.values()))
        self.assertNotIn("private/remura.env",staged)
        self.assertNotIn("private/remura-prices.sqlite3",staged)

    def test_synthetic_backup_uses_genuine_wal_with_uncheckpointed_records(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-test-") as tmp:
            root=Path(tmp)
            source=root/"fake.sqlite3"
            snap=root/"snap.sqlite3"
            with closing(m._fake_db(source)) as db:
                self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0],"wal")
                self.assertTrue((root/"fake.sqlite3-wal").is_file())
                self.assertGreater((root/"fake.sqlite3-wal").stat().st_size,0)
                m._consistent_backup(db,snap)
                self.assertEqual(m._validate_db(snap),2)
                self.assertIn(("EURUSD",101),m.RECORDS)
                self.assertIn(("XAUUSD",202),m.RECORDS)

    def test_restore_is_rejected_if_cipherless_snapshot_is_modified(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-test-") as tmp:
            root=Path(tmp)
            with closing(m._fake_db(root/"fake.sqlite3")) as source:
                snapshot=root/"snapshot.sqlite3"
                m._consistent_backup(source,snapshot)
                digest=m.sha(snapshot.read_bytes())
                with snapshot.open("r+b") as handle:
                    handle.seek(78)
                    data=handle.read(1)
                    self.assertTrue(data)
                    handle.seek(78)
                    handle.write(bytes((data[0]^0x10,)))
                with self.assertRaisesRegex(m.LabRejection,"STOP_SNAPSHOT_DIGEST_CHANGED"):
                    m.isolated_restore(snapshot,root/"restore.sqlite3",digest)

    def test_restore_with_wrong_hash_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-test-") as tmp:
            root=Path(tmp)
            with closing(m._fake_db(root/"fake.sqlite3")) as source:
                snapshot=root/"snapshot.sqlite3"
                m._consistent_backup(source,snapshot)
                with self.assertRaisesRegex(m.LabRejection,"STOP_SNAPSHOT_DIGEST_CHANGED"):
                    m.isolated_restore(snapshot,root/"restored.sqlite3","0"*64)

    def test_missing_snapshot_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-test-") as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(m.LabRejection,"STOP_SNAPSHOT_MISSING"):
                m.isolated_restore(root/"missing.sqlite3",root/"restored.sqlite3","0"*64)
            target=root/"target.sqlite3"
            target.write_bytes(b"FICTIONAL")
            (root/"link.sqlite3").symlink_to(target)
            with self.assertRaisesRegex(m.LabRejection,"STOP_SNAPSHOT_MISSING"):
                m.isolated_restore(root/"link.sqlite3",root/"restored.sqlite3","0"*64)

    def test_every_injected_failure_is_detected_and_code_rolled_back(self):
        for fault in sorted(m.FAULTS):
            with self.subTest(fault=fault):
                report=m.simulate(mode=m.MODE,fault=fault)
                self.assertEqual(report["state"],"SYNTHETIC_FAILURE_REJECTED")
                self.assertTrue(report["syntheticFaultDetected"])
                self.assertTrue(report["syntheticFileRollbackVerified"])
                self.assertTrue(report["syntheticUpdaterStateUnchanged"])
                self.assertFalse(report["realFilesInstalled"])
                self.assertFalse(report["releaseAuthorized"])
                self.assertEqual(report["operationalDecision"],m.NO_GO)

    def test_unknown_fault_rejected_before_any_temp_database(self):
        with patch.object(m.tempfile,"TemporaryDirectory",
                          side_effect=AssertionError("should not start lab")):
            with self.assertRaisesRegex(m.LabRejection,"STOP_UNKNOWN_FAULT"):
                m.simulate(mode=m.MODE,fault="make-real-release")

    def test_unexpected_file_name_fails_allowlist(self):
        initial=m.synthetic_files()
        for name in ("private/ctrader-refresh-token.json","any.txt",
                     "../../secret", "deploy/oracle/release_v165.py"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(m.LabRejection,"STOP_FILE_ALLOWLIST"):
                    m.simulate(mode=m.MODE,before={**initial,name:b"SENSITIVE"})

    def test_missing_file_fails_allowlist(self):
        original=m.synthetic_files()
        del original["nav.js"]
        with self.assertRaisesRegex(m.LabRejection,"STOP_FILE_ALLOWLIST"):
            m.simulate(mode=m.MODE,before=original)

    def test_non_bytes_and_oversized_fake_content_fail_before_backup(self):
        for altered in ("NOT_BYTES",b"x"*100001,b""):
            with self.subTest(altered=type(altered).__name__):
                original=m.synthetic_files()
                original["nav.js"]=altered
                with self.assertRaisesRegex(m.LabRejection,"STOP_BOUNDED_FAKE_FILES"):
                    m.simulate(mode=m.MODE,before=original)

    def test_updater_mock_marker_is_false_proof_not_sha(self):
        result=m.simulate(mode=m.MODE)
        self.assertFalse(result["realAutoupdaterChanged"])
        self.assertTrue(result["syntheticUpdaterStateUnchanged"])
        self.assertNotIn("installedSha",result)
        self.assertNotIn("FICTIONAL_V164",json.dumps(result))

    def test_no_install_deploy_or_vps_entrypoint(self):
        code=SCRIPT.read_text()
        parsed=ast.parse(code)
        names={x.name for x in parsed.body
               if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertTrue({"simulate","staged_files","isolated_restore"} <= names)
        self.assertTrue({"apply","deploy","install","reconcile","rollback_from"} .isdisjoint(names))
        self.assertIn('parser.add_argument("--simulate-offline", required=True',code)
        self.assertNotIn('parser.add_argument("--apply"',code)
        self.assertNotIn('parser.add_argument("--database"',code)

    def test_network_and_process_imports_absent_from_lab_script(self):
        tree=ast.parse(SCRIPT.read_text())
        imported={x.name.partition(".")[0] for n in ast.walk(tree)
                  if isinstance(n,ast.Import) for x in n.names}
        self.assertTrue(imported.isdisjoint(
            {"socket","requests","urllib","http","subprocess","paramiko","ctypes"}))
        source=SCRIPT.read_text()
        self.assertNotIn("os.system(",source)
        self.assertNotIn("subprocess.run(",source)
        self.assertNotIn("systemctl ",source)
        self.assertNotIn("opt/remura",source)
        self.assertNotIn("PRAGMA wal_checkpoint",source)

    def test_temp_directories_destroyed_after_simulation(self):
        created=[]
        real=m.tempfile.TemporaryDirectory
        def track(*args,**kwargs):
            o=real(*args,**kwargs)
            created.append(Path(o.name))
            return o
        with patch.object(m.tempfile,"TemporaryDirectory",side_effect=track):
            m.simulate(mode=m.MODE)
        self.assertEqual(len(created),1)
        self.assertFalse(created[0].exists())

    def test_synthetic_row_mismatch_never_claims_restore(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-test-") as tmp:
            p=Path(tmp)/"wrong.sqlite3"
            with closing(sqlite3.connect(p)) as db:
                db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY, fictional INTEGER)")
                db.execute("CREATE TABLE status(key TEXT PRIMARY KEY,value TEXT)")
                db.execute("INSERT INTO prices VALUES ('EURUSD',999)")
                db.execute("INSERT INTO status VALUES ('source','FICTIONAL_ONLY')")
                db.commit()
            with self.assertRaisesRegex(m.LabRejection,"STOP_RESTORED_ROWS_CHANGED"):
                m._validate_db(p)

    def test_src_has_synthetic_era_only_and_no_price_api(self):
        report=m.simulate(mode=m.MODE)
        self.assertEqual(report["state"],"OFFLINE_SYNTHETIC_ONLY")
        self.assertTrue(report["localTemporaryDirectoriesOnly"])
        self.assertNotIn("CTRADER_",json.dumps(report))
        self.assertNotIn("REMURA_STORAGE_DIAG_ENABLED",json.dumps(report))


if __name__=="__main__":
    unittest.main()
