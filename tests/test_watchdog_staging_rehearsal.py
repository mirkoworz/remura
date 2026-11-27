"""Isolated and adversarial rehearsal: NEVER interacts with production."""
from pathlib import Path
import ast
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from watchdog_staging_rehearsal import (
    audit_shared_server, sha256, simulate_rollback, verify_staged_bundle
)

SERVER = "scripts/private_server.py"
WATCHDOG = "scripts/collector_watchdog.py"


class OfflineStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {
            SERVER: (ROOT / SERVER).read_bytes(),
            WATCHDOG: (ROOT / WATCHDOG).read_bytes(),
        }
        cls.manifest = (SERVER, WATCHDOG)
        cls.pins = {path: sha256(content) for path, content in cls.files.items()}

    def verify(self, manifest=None, files=None, pins=None):
        return verify_staged_bundle(
            self.manifest if manifest is None else manifest,
            self.files if files is None else files,
            self.pins if pins is None else pins
        )

    def test_genuine_branch_bundle_hash_and_import_contract(self):
        self.assertEqual(self.verify(), (True, "OFFLINE_PINS_MATCH_NO_RELEASE_AUTHORITY"))

    def test_missing_watchdog_rejected(self):
        self.assertEqual(self.verify(files={SERVER: self.files[SERVER]})[1], "FILE_SET_MISMATCH")

    def test_wrong_pin_rejected(self):
        p = dict(self.pins)
        p[WATCHDOG] = "0" * 64
        self.assertEqual(self.verify(pins=p)[1], "HASH_MISMATCH")

    def test_changed_server_with_old_pin_rejected(self):
        files = dict(self.files)
        files[SERVER] += b"\n# unreviewed change\n"
        self.assertEqual(self.verify(files=files)[1], "HASH_MISMATCH")

    def test_syntax_invalid_even_with_new_matching_pin(self):
        files = dict(self.files)
        files[WATCHDOG] = b"def broken(:"
        pins = {name: sha256(data) for name, data in files.items()}
        self.assertEqual(self.verify(files=files, pins=pins)[1], "SOURCE_INVALID")

    def test_invalid_paths_fail_closed(self):
        for name in ("../outside", "/opt/remura/test", "scripts//fake", "scripts/./fake",
                     ".github/secrets", "scripts/../fake"):
            with self.subTest(name=name):
                files = dict(self.files)
                files[name] = b"synthetic"
                pins = {path: sha256(data) for path, data in files.items()}
                result = self.verify(manifest=tuple(files), files=files, pins=pins)
                self.assertEqual(result, (False, "UNSAFE_PATH"))

    def test_untrusted_digest_format_rejected(self):
        pins = dict(self.pins)
        pins[WATCHDOG] = "Z" * 64
        self.assertEqual(self.verify(pins=pins)[1], "INVALID_DIGEST")

    def test_malformed_bundle_rejected(self):
        self.assertEqual(self.verify(files=None, pins={})[1], "FILE_SET_MISMATCH")
        self.assertEqual(verify_staged_bundle((), {}, {})[1], "INVALID_BUNDLE")

    def test_shared_file_forks_always_require_review(self):
        base = "def server():\n    return 1\n\ndef health():\n    return 0\n"
        b = base.replace("return 1", "return 2")
        v165 = base.replace("return 0", "return 3")
        watchdog = base.replace("return 0", "return 4")
        outcome = audit_shared_server(base, {"B#89": b, "v1.65#98": v165, "watchdog#99": watchdog})
        self.assertEqual(outcome["state"], "MANUAL_RECONCILIATION_REQUIRED")
        self.assertIn(("v1.65#98", "watchdog#99"), outcome["overlap_pairs"])
        self.assertFalse(outcome["release_authorized"])

    def test_nonoverlapping_changes_still_require_review(self):
        base = "def a():\n    return 1\n\ndef b():\n    return 2\n"
        outcome = audit_shared_server(base, {
            "B#89": base.replace("return 1", "return 3"),
            "Watchdog#99": base.replace("return 2", "return 4")
        })
        self.assertEqual(outcome["state"], "MANUAL_RECONCILIATION_REQUIRED")
        self.assertFalse(outcome["overlap_pairs"])

    def test_no_drift_is_not_release_authorization(self):
        base = "value = 1\n"
        outcome = audit_shared_server(base, {"B#89": base})
        self.assertEqual(outcome["state"], "NO_FORK_CHANGES_OBSERVED")
        self.assertFalse(outcome["release_authorized"])

    def test_invalid_fork_syntax_is_rejected(self):
        self.assertEqual(audit_shared_server("x=1", {"B#89": "def oops(:"})["state"], "INVALID_INPUT")

    def test_rollback_on_failure_before_replace(self):
        self.assertEqual(simulate_rollback(b"original", b"candidate", "before_replace"),
                         (True, "SYNTHETIC_ROLLBACK_VERIFIED"))

    def test_rollback_on_failure_after_replace(self):
        self.assertEqual(simulate_rollback(b"original", b"candidate", "after_replace"),
                         (True, "SYNTHETIC_ROLLBACK_VERIFIED"))

    def test_successful_staging_is_not_live_deploy(self):
        self.assertEqual(simulate_rollback(b"original", b"candidate", "none"),
                         (True, "SYNTHETIC_STAGING_VERIFIED_NOT_DEPLOYED"))

    def test_simulation_refuses_unknown_steps_and_large_inputs(self):
        self.assertEqual(simulate_rollback(b"a", b"b", "sudo systemctl")[1], "INVALID_INPUT")
        self.assertEqual(simulate_rollback(b"a", b"b" * 2_000_001)[1], "INVALID_INPUT")

    def test_no_network_or_live_access_from_rehearsal(self):
        script = (ROOT / "scripts" / "watchdog_staging_rehearsal.py").read_text("utf-8")
        tree = ast.parse(script)
        imports = [n.names[0].name for n in tree.body if isinstance(n, ast.Import)]
        self.assertEqual(imports, ["ast", "difflib", "hashlib", "os", "tempfile"])
        for marker in ("requests.", "urlopen(", "subprocess.", "systemctl", "/opt/remura",
                       "socket.", "ssh ", "oci ", "shutdown("):
            self.assertNotIn(marker, script)


if __name__ == "__main__":
    unittest.main()
