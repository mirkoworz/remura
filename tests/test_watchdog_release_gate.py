"""Fail-closed offline checks: v1.64 release MUST NOT ship the new module."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from watchdog_release_gate import check_bundle

SERVER = ROOT / "scripts" / "private_server.py"
WATCHDOG = ROOT / "scripts" / "collector_watchdog.py"
OLD_RELEASE = ROOT / "deploy" / "oracle" / "release_v164.py"
UPDATER = ROOT / "deploy" / "oracle" / "autoupdate.py"


def constant_assignment(path, key):
    tree = ast.parse(path.read_text("utf-8"), str(path))
    for item in tree.body:
        if isinstance(item, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == key
            for target in item.targets
        ):
            return ast.literal_eval(item.value)
    raise AssertionError("constant not found: " + key)


class WatchdogReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SERVER.read_text("utf-8")
        cls.watchdog = WATCHDOG.read_text("utf-8")

    def check(self, manifest, server=None, watchdog=None):
        return check_bundle(
            manifest,
            self.server if server is None else server,
            self.watchdog if watchdog is None else watchdog,
        )

    def test_old_v164_manifest_is_incompatible_and_remains_unchanged(self):
        manifest = constant_assignment(OLD_RELEASE, "FILES")
        self.assertIn("scripts/private_server.py", manifest)
        self.assertNotIn("scripts/collector_watchdog.py", manifest)
        self.assertEqual(self.check(manifest), (False, "DEPENDENCY_NOT_STAGED"))

    def test_future_manifest_must_stage_both_modules(self):
        self.assertEqual(self.check(("scripts/private_server.py", "scripts/collector_watchdog.py")),
                         (True, "BUNDLE_CONTRACT_READY_OFFLINE_ONLY"))

    def test_missing_private_server_is_denied(self):
        self.assertEqual(self.check(("scripts/collector_watchdog.py",))[1], "DEPENDENCY_NOT_STAGED")

    def test_missing_watchdog_module_is_denied(self):
        self.assertEqual(self.check(("scripts/private_server.py",))[1], "DEPENDENCY_NOT_STAGED")

    def test_unknown_or_duplicate_manifest_is_denied(self):
        for manifest in (None, {}, ("scripts/private_server.py",) * 2 +
                         ("scripts/collector_watchdog.py",),
                         ["scripts/private_server.py", 123, "scripts/collector_watchdog.py"]):
            with self.subTest(manifest=repr(manifest)[:60]):
                self.assertEqual(self.check(manifest)[1], "MANIFEST_INVALID")

    def test_broken_server_syntax_is_denied(self):
        self.assertEqual(self.check(("scripts/private_server.py","scripts/collector_watchdog.py"),
                                    server="def broken(:")[1], "SOURCE_INVALID")

    def test_broken_watchdog_syntax_is_denied(self):
        self.assertEqual(self.check(("scripts/private_server.py","scripts/collector_watchdog.py"),
                                    watchdog="def broken(:")[1], "SOURCE_INVALID")

    def test_missing_snapshot_function_is_denied(self):
        self.assertEqual(self.check(("scripts/private_server.py","scripts/collector_watchdog.py"),
                                    watchdog="def unrelated(): pass")[1], "WATCHDOG_CONTRACT_MISSING")

    def test_missing_import_is_denied(self):
        removed=self.server.replace(
            "snapshot as collector_watchdog_snapshot",
            "something_else as collector_watchdog_snapshot",
        )
        self.assertNotEqual(removed, self.server)
        self.assertEqual(self.check(("scripts/private_server.py","scripts/collector_watchdog.py"),
                                    server=removed)[1], "WATCHDOG_CONTRACT_MISSING")

    def test_missing_http_observability_field_is_denied(self):
        replaced=self.server.replace('"collectorWatchdog":collector_watchdog_snapshot(',
                                     '"collectorAux":collector_watchdog_snapshot(')
        self.assertNotEqual(replaced, self.server)
        self.assertEqual(self.check(("scripts/private_server.py","scripts/collector_watchdog.py"),
                                    server=replaced)[1], "WATCHDOG_CONTRACT_MISSING")

    def test_autoupdater_requires_manual_release_for_code_changes(self):
        manual = constant_assignment(UPDATER, "MANUAL_ONLY")
        self.assertIn("scripts/", manual)
        self.assertIn("deploy/oracle/", manual)

    def test_no_live_api_calls_or_service_restart_in_guard(self):
        guard=(ROOT/"scripts"/"watchdog_release_gate.py").read_text("utf-8")
        mod=ast.parse(guard)
        imports=[m.module for m in mod.body if isinstance(m, ast.ImportFrom)]
        modules=[m.names[0].name for m in mod.body if isinstance(m, ast.Import)]
        self.assertEqual(modules, ["ast"])
        self.assertIn("__future__", imports)
        for token in ("subprocess.", "urlopen(", "systemctl", "os.system(", "requests.", "socket."):
            self.assertNotIn(token, guard)


if __name__ == "__main__":
    unittest.main()
