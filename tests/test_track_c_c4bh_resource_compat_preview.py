"""C4b(h): fictitious legacy resource response and fail-closed preview."""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import track_c_c4bh_resource_compat_preview as m
import track_c_c4bf_metadata_inventory as inventory

TIME = "2026-11-08T13:00:00+00:00"
NOW = "2026-11-08T13:02:00Z"


def legacy():
    return {
        "schema": "remura-resources-v1",
        "sampledAt": TIME,
        "memory": {"total": 1024, "used": 256, "swapTotal": 0, "swapUsed": 0},
        "cpu": {"logical": 1, "load1": 0.4},
        "disk": {"total": 10000, "used": 1000},
        "network": {"rxSinceInterfaceStart": 123, "txSinceInterfaceStart": 456},
        "uptimeSeconds": 360,
        "webApi": {"allGet": 6, "privateGet": 3},
        "oracle": {"bill": "unverified", "limits": "unverified",
                   "networkMonthly": None, "externalApiCalls": None},
    }


class LegacyCompatibilityLab(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="remura-c4bf-")
        self.root = Path(self.temp.name)
        (self.root/inventory.DB_NAME).write_bytes(b"FICTIONAL_METADATA_CORE")

    def tearDown(self):
        self.temp.cleanup()

    def report(self):
        return inventory.inventory(self.root, mode=inventory.LAB_MODE)

    def preview(self, *, enabled=False, snap=None, data=None, now=NOW):
        return m.preview(legacy() if snap is None else snap, enabled=enabled,
                         inventory_report=data, observed_at_utc=now, mode=m.MODE)

    def test_default_off_exactly_preserves_legacy_shape_and_values(self):
        old = legacy()
        actual = m.preview(old, mode=m.MODE)
        self.assertEqual(actual, old)
        self.assertEqual(set(actual), m.FIELDS)
        self.assertNotIn("storageInventory", actual)
        self.assertIsNot(actual, old)

    def test_disabled_ignores_untrusted_inventory_even_with_secrets(self):
        secret = {"secret": "NEVER_ECHO"}
        actual = self.preview(data=secret)
        self.assertEqual(actual, legacy())
        self.assertNotIn("NEVER_ECHO", repr(actual))

    def test_simulated_opt_in_adds_one_sanitized_field_only(self):
        original = legacy()
        report = self.report()
        out = self.preview(enabled=True, snap=original, data=report)
        self.assertEqual({k: out[k] for k in original}, original)
        self.assertEqual(set(out)-set(original), {"storageInventory"})
        self.assertEqual(out["storageInventory"]["status"],
                         "FRESH_FORMAT_VALID_BUT_NOT_AUTHENTICATED")
        self.assertIsNone(out["storageInventory"]["wal"]["apparentBytes"])
        self.assertFalse(out["storageInventory"]["remoteEndpointCurrentlyImplemented"])
        self.assertFalse(out["storageInventory"]["offhostRestoreProven"])
        self.assertEqual(out["storageInventory"]["operationalDecision"], m.NO_GO)

    def test_mutating_result_does_not_mutate_input(self):
        inp = legacy()
        res = self.preview(snap=inp)
        res["memory"]["used"] = 900
        self.assertEqual(inp["memory"]["used"], 256)

    def test_simulation_missing_inventory_is_not_a_success(self):
        out = self.preview(enabled=True)
        self.assertEqual(out["storageInventory"]["status"],
                         "MISSING_EXTENSION_ON_EXISTING_ENDPOINT")
        self.assertFalse(out["storageInventory"]["currentVpsCapacityProven"])

    def test_simulation_rejects_extra_secret_and_does_not_echo(self):
        data = self.report()
        data["apiKey"] = "NEVER_ECHO"
        out = self.preview(enabled=True, data=data)
        self.assertEqual(out["storageInventory"]["status"],
                         "UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")
        self.assertNotIn("NEVER_ECHO", repr(out))

    def test_local_snapshots_not_offhost_restore(self):
        back = self.root/inventory.BACKUP_DIR/"backup-v156-20261108T120000Z-aabbcc"
        back.mkdir(parents=True)
        (back/inventory.DB_NAME).write_bytes(b"FICTIONAL_LOCAL_IMAGE")
        (back/"manifest.txt").write_bytes(b"NOT_A_VERIFIED_HASH")
        out = self.preview(enabled=True, data=self.report())
        self.assertEqual(out["storageInventory"]["localBackups"]["localSnapshotDirectoriesReported"],1)
        self.assertFalse(out["storageInventory"]["offhostRestoreProven"])
        self.assertFalse(out["storageInventory"]["oracleBillingProven"])

    def test_stale_hypothetical_sample_does_not_prove_capacity(self):
        snap=legacy()
        snap["sampledAt"]="2026-11-07T13:00:00+00:00"
        out=self.preview(enabled=True, snap=snap, data=self.report())
        self.assertEqual(out["storageInventory"]["status"],
                         "MISSING_FRESH_ATTESTED_RESOURCE_EVIDENCE")
        self.assertFalse(out["storageInventory"]["currentVpsCapacityProven"])

    def test_future_hypothetical_sample_does_not_prove_capacity(self):
        snap=legacy()
        snap["sampledAt"]="2026-11-09T13:00:00+00:00"
        out=self.preview(enabled=True,snap=snap,data=self.report())
        self.assertEqual(out["storageInventory"]["status"],
                         "MISSING_FRESH_ATTESTED_RESOURCE_EVIDENCE")

    def test_missing_optional_legacy_data_keeps_identity(self):
        snap=legacy()
        snap["memory"]["total"]=None
        snap["disk"]["used"]=None
        snap["network"]["rxSinceInterfaceStart"]=None
        out=self.preview(snap=snap)
        self.assertEqual(out,snap)

    def test_unexpected_legacy_top_level_secret_rejected(self):
        snap=legacy()
        snap["token"]="NEVER_ECHO"
        with self.assertRaisesRegex(ValueError,"legacy_resource_shape_changed"):
            self.preview(snap=snap)

    def test_unexpected_nested_secret_rejected(self):
        snap=legacy()
        snap["webApi"]["apiKey"]="NEVER_ECHO"
        with self.assertRaisesRegex(ValueError,"unexpected_nested"):
            self.preview(snap=snap)

    def test_invalid_billing_proof_rejected(self):
        snap=legacy()
        snap["oracle"]["bill"]="zero_cost_certified"
        with self.assertRaisesRegex(ValueError,"billing_proof_not_available"):
            self.preview(snap=snap)

    def test_nan_or_non_json_primitive_rejected(self):
        for value in (float("nan"), object(), -1):
            with self.subTest(value_type=type(value).__name__):
                snap=legacy()
                snap["cpu"]["load1"]=value
                with self.assertRaisesRegex(ValueError,"unsafe_resource_scalar"):
                    self.preview(snap=snap)

    def test_missing_mode_or_string_enabled_rejected(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            m.preview(legacy())
        with self.assertRaisesRegex(ValueError,"explicit_boolean"):
            self.preview(enabled="true")

    def test_opt_in_requires_explicit_review_clock(self):
        with self.assertRaisesRegex(ValueError,"explicit_review_clock"):
            m.preview(legacy(),mode=m.MODE,enabled=True,inventory_report=self.report())

    def test_no_io_import_or_live_wiring(self):
        source = (ROOT/"scripts"/"track_c_c4bh_resource_compat_preview.py").read_text()
        tree=ast.parse(source)
        imports={alias.name for node in ast.walk(tree)
                 if isinstance(node, ast.Import) for alias in node.names}
        self.assertTrue({"os","pathlib","sqlite3","socket","requests","subprocess",
                         "urllib","resource_monitor"}.isdisjoint(imports))
        server=(ROOT/"scripts"/"private_server.py").read_text()
        resources=(ROOT/"scripts"/"resource_monitor.py").read_text()
        self.assertIn("self.response(200,resource_snapshot(counts))",server)
        self.assertNotIn("track_c_c4bh_resource_compat_preview",server)
        self.assertNotIn("track_c_c4bh_resource_compat_preview",resources)
        self.assertNotIn("storageInventory",resources)

    def test_never_infers_live_permissions_or_market_edge(self):
        out=self.preview(enabled=True,data=self.report())
        extra=out["storageInventory"]
        self.assertFalse(extra["researchLiveEnabled"])
        self.assertFalse(extra["providerFirstSeenProven"])
        self.assertFalse(extra["dataProvenanceAuthenticated"])
        self.assertEqual(extra["newNetworkCalls"],0)

if __name__=="__main__":
    unittest.main()
