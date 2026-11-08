"""C4b(g): test-only proposed private endpoint data transport, not live."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import track_c_c4bg_resource_transport_contract as m
import track_c_c4bf_metadata_inventory as files

NOW = "2026-11-08T12:45:00Z"


class ProposedTransport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="remura-c4bf-")
        self.base = Path(self.temp.name)
        (self.base/files.DB_NAME).write_bytes(b"FICTIONAL_DATABASE_NOT_SQLITE")

    def tearDown(self):
        self.temp.cleanup()

    def raw(self):
        item = files.inventory(self.base, mode=files.LAB_MODE)
        return {"schema": m.SCHEMA,
                "resourceSchema": m.SOURCE,
                "sampledAtUtc": "2026-11-08T12:44:00Z",
                "inventory": item}

    def check(self, payload=None, **opts):
        if payload is None:
            payload = self.raw()
        return m.review(payload, observed_at_utc=NOW, mode=m.MODE, **opts)

    def test_missing_extension_is_expected_today(self):
        x = m.review(None, observed_at_utc=NOW, mode=m.MODE)
        self.assertEqual(x["status"], "MISSING_EXTENSION_ON_EXISTING_ENDPOINT")
        self.assertFalse(x["remoteEndpointCurrentlyImplemented"])
        self.assertEqual(x["operationalDecision"], m.NO_GO)

    def test_synthetic_metadata_valid_format_is_still_unattested(self):
        x = self.check()
        self.assertEqual(x["status"], "FRESH_FORMAT_VALID_BUT_NOT_AUTHENTICATED")
        self.assertFalse(x["dataProvenanceAuthenticated"])
        self.assertFalse(x["offhostRestoreProven"])
        self.assertEqual(x["core"]["state"], "REPORTED_SIZE_NOT_ATTESTED")
        self.assertEqual(x["wal"]["state"], "REPORTED_ABSENT_NOT_ZERO_PROOF")
        self.assertIsNone(x["wal"]["apparentBytes"])
        self.assertEqual(x["operationalDecision"], m.NO_GO)

    def test_existing_local_backup_is_never_offhost_proof(self):
        root = self.base/files.BACKUP_DIR/"backup-v156-20261108T123000Z-abcdef"
        root.mkdir(parents=True)
        (root/files.DB_NAME).write_bytes(b"FICTIONAL_BACKUP")
        (root/"manifest.txt").write_bytes(b"FICTITIOUS_MANIFEST")
        x = self.check()
        self.assertEqual(x["localBackups"]["localSnapshotDirectoriesReported"], 1)
        self.assertFalse(x["localBackups"]["offhostRecoveryAttested"])
        self.assertFalse(x["offhostRestoreProven"])

    def test_future_timestamp_is_missing_not_safe(self):
        payload = self.raw()
        payload["sampledAtUtc"] = "2026-11-08T12:46:00Z"
        self.assertEqual(self.check(payload)["status"],
                         "MISSING_FRESH_ATTESTED_RESOURCE_EVIDENCE")

    def test_old_timestamp_cannot_establish_current_headroom(self):
        payload = self.raw()
        payload["sampledAtUtc"] = "2026-11-07T12:44:00Z"
        x = self.check(payload)
        self.assertEqual(x["status"], "MISSING_FRESH_ATTESTED_RESOURCE_EVIDENCE")
        self.assertFalse(x["currentVpsCapacityProven"])

    def test_rejects_secret_field_and_never_echoes(self):
        payload = self.raw()
        payload["OCI_API_KEY"] = "SHOULD_NEVER_APPEAR"
        x = self.check(payload)
        self.assertEqual(x["status"], "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")
        self.assertNotIn("SHOULD_NEVER_APPEAR", repr(x))

    def test_rejects_path_or_filename_leak_inside_inventory(self):
        payload = self.raw()
        payload["inventory"]["fullPath"] = "/opt/remura/private/very-private"
        x = self.check(payload)
        self.assertEqual(x["status"], "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")
        self.assertNotIn("/opt/remura/private", repr(x))

    def test_rejects_fake_offhost_recovery_or_free_billing_claim(self):
        for key in ("offhostBackupExistsVerified","backupRestoreIntegrityVerified",
                    "oracleAlwaysFreeBillingVerified", "sourceUnmodifiedProven"):
            with self.subTest(key=key):
                payload = self.raw()
                payload["inventory"][key] = True
                self.assertEqual(self.check(payload)["status"],
                                 "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")

    def test_rejects_missing_local_counts_claiming_zero(self):
        payload = self.raw()
        payload["inventory"]["localBackups"]["archives"] = 0
        self.assertEqual(self.check(payload)["status"],
                         "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")

    def test_noninteger_disk_or_boolean_size_rejected(self):
        for value in ("100000", -5, True):
            with self.subTest(value=value):
                payload = self.raw()
                payload["inventory"]["filesystem"]["availableBytes"] = value
                self.assertEqual(self.check(payload)["status"],
                                 "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")

    def test_false_zero_size_for_absent_wal_forbidden(self):
        payload = self.raw()
        payload["inventory"]["wal"]["apparentBytes"] = 0
        self.assertEqual(self.check(payload)["status"],
                         "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")

    def test_extraneous_source_schema_or_mode_cannot_enable_live(self):
        payload = self.raw()
        payload["resourceSchema"] = "remura-resources-v2"
        self.assertEqual(self.check(payload)["status"],
                         "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")
        with self.assertRaisesRegex(ValueError, "offline_contract_mode"):
            m.review(self.raw(), observed_at_utc=NOW)

    def test_low_synthetic_free_space_is_pressure_warning_only(self):
        payload = self.raw()
        payload["inventory"]["filesystem"]["availableBytes"] = 0
        x = self.check(payload)
        self.assertEqual(x["diskPressureReported"], "REVIEW_LOW_LAB_HEADROOM")
        self.assertFalse(x["researchLiveEnabled"])

    def test_no_network_or_database_import_or_existing_live_wiring(self):
        tree = ast.parse((ROOT/"scripts"/"track_c_c4bg_resource_transport_contract.py").read_text())
        names = {alias.name for node in ast.walk(tree)
                 if isinstance(node, ast.Import) for alias in node.names}
        self.assertTrue({"sqlite3","socket","requests","urllib","subprocess"}.isdisjoint(names))
        for filename in ("private_server.py","resource_monitor.py","price_store.py",
                         "cot_monitor.py","signals_monitor.py","update_myfxbook.py"):
            self.assertNotIn("track_c_c4bg_resource_transport_contract",
                             (ROOT/"scripts"/filename).read_text())

    def test_existing_resource_endpoint_has_no_sqlite_inventory(self):
        text = (ROOT/"scripts"/"resource_monitor.py").read_text()
        self.assertNotIn("storageInventory", text)
        self.assertNotIn("track_c_c4bf_metadata_inventory", text)
        self.assertNotIn("remura-prices.sqlite3", text)
        server = (ROOT/"scripts"/"private_server.py").read_text()
        self.assertIn("self.response(200,resource_snapshot(counts))", server)
        self.assertNotIn("storageInventory", server)

if __name__ == "__main__":
    unittest.main()
