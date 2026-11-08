"""Offline-only tests for v1.65 draft preview; NEVER contact VPS or broker."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "v165_release_offline_preview",
    ROOT / "deploy/oracle/v165_release_offline_preview.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReleaseV165OfflinePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = m.read_sources(ROOT)

    def test_source_pins_are_exactly_fourteen_approved_files(self):
        self.assertEqual(len(m.SOURCE_BLOBS),14)
        self.assertEqual(len(m.PAGE_NAMES),9)
        self.assertEqual(len(m.BACKEND),3)
        self.assertEqual(set(m.SOURCE_BLOBS),
                         set(m.PAGE_NAMES)|set(m.BACKEND)|{"nav.js","sw.js"})
        self.assertEqual(m.BASE_MAIN_SHA, "5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74")
        self.assertTrue(all(m.git_blob(value)==m.SOURCE_BLOBS[key]
                            for key,value in self.source.items()))

    def test_all_nine_pages_reference_next_nav_cache_only_in_memory(self):
        after=m.preview(self.source)
        self.assertEqual(set(after),set(self.source))
        for name in m.PAGE_NAMES:
            self.assertEqual(after[name].count(b"nav.js?v=165"),1,name)
            self.assertNotIn(b"nav.js?v=164",after[name],name)
            self.assertEqual(after[name],
                             self.source[name].replace(b"nav.js?v=164",b"nav.js?v=165"))
        self.assertEqual(after["scripts/private_server.py"],
                         self.source["scripts/private_server.py"])

    def test_banner_at_page_top_provided_through_single_nav_script(self):
        after=m.preview(self.source)
        nav=after["nav.js"]
        self.assertIn(b"REMURA " + "· Aggiornamento v1.65".encode(), nav)
        self.assertIn(b"DATA_ORA_REALE_SOLO_AL_RILASCIO",nav)
        self.assertIn(b'document.body.prepend(release)',nav)
        self.assertNotIn(b"Aggiornamento v1.64",nav)

    def test_real_install_timestamp_is_not_claimed_by_offline_preview(self):
        preview=m.status(ROOT)
        self.assertFalse(preview["releaseInstalled"])
        self.assertFalse(preview["previewWrittenToDisk"])
        self.assertEqual(preview["operationalDecision"],m.NO_GO)
        self.assertEqual(preview["state"],"OFFLINE_PREVIEW_ONLY_NO_RELEASE")

    def test_simulated_italian_winter_timestamp(self):
        moment=datetime(2026,11,8,14,0,tzinfo=timezone.utc)
        nav=m.preview(self.source,simulated_install_time=moment)["nav.js"]
        self.assertIn(b"08/11/2026 15:00 (Italia)",nav)
        self.assertNotIn(b"DATA_ORA_REALE_SOLO_AL_RILASCIO",nav)

    def test_simulated_italian_summer_timestamp(self):
        moment=datetime(2026,7,8,14,0,tzinfo=timezone.utc)
        nav=m.preview(self.source,simulated_install_time=moment)["nav.js"]
        self.assertIn(b"08/07/2026 16:00 (Italia)",nav)

    def test_naive_timestamp_and_unpinned_main_base_rejected(self):
        with self.assertRaisesRegex(ValueError,"SIMULATED_TIME_MUST_BE_AWARE"):
            m.preview(self.source,simulated_install_time=datetime(2026,11,8))
        with self.assertRaisesRegex(ValueError,"UNPINNED_MAIN_BASE"):
            m.preview(self.source,base_main_sha="f"*40)

    def test_unexpected_additional_file_or_missing_page_rejected(self):
        for changes in (
            {"private/remura.env":b"NON_SCANNARE"},
            {"other-file.txt":b"FAKE"},
        ):
            with self.assertRaisesRegex(ValueError,"UNREVIEWED_SOURCE_FILE_SET"):
                m.preview({**self.source,**changes})
        missing=dict(self.source)
        del missing["asset.html"]
        with self.assertRaisesRegex(ValueError,"UNREVIEWED_SOURCE_FILE_SET"):
            m.preview(missing)

    def test_mutation_or_truncated_source_fail_closed_before_stamping(self):
        for name, data in (
            ("nav.js",b"REMURA v1.65 FAKE"),
            ("sw.js",b"cache-anything"),
            ("index.html",b"<html></html>"),
            ("scripts/private_server.py",b"exec the payload"),
        ):
            sample=dict(self.source)
            sample[name]=data
            with self.assertRaisesRegex(ValueError,"SOURCE_BLOB_DIVERGED"):
                m.preview(sample)
        sample=dict(self.source)
        sample["nav.js"]="not bytes"
        with self.assertRaisesRegex(ValueError,"SOURCE_BLOB_DIVERGED"):
            m.preview(sample)

    def test_incorrect_banner_rejected_even_with_modified_pin(self):
        sample=dict(self.source)
        sample["nav.js"]=self.source["nav.js"].replace(
            m.SOURCE_BANNER,"REMURA · Aggiornamento v1.64 · BAD".encode("utf-8"))
        with patch.dict(m.SOURCE_BLOBS,{"nav.js":m.git_blob(sample["nav.js"])}):
            with self.assertRaisesRegex(ValueError,"GLOBAL_TOP_BANNER_MISSING"):
                m.preview(sample)

    def test_missing_private_api_sw_bypass_rejected_with_modified_pin(self):
        sample=dict(self.source)
        sample["sw.js"]=self.source["sw.js"].replace(
            b'url.pathname.includes("/private-api/")',
            b'url.pathname.includes("/public-only/")')
        with patch.dict(m.SOURCE_BLOBS,{"sw.js":m.git_blob(sample["sw.js"])}):
            with self.assertRaisesRegex(ValueError,"OFFLINE_SW_SAFETY"):
                m.preview(sample)

    def test_sw_cache_changes_only_expected_release_key(self):
        staged=m.preview(self.source)
        self.assertEqual(staged["sw.js"],
                         self.source["sw.js"].replace(m.SOURCE_SW,m.TARGET_SW))
        self.assertIn(b"remura-shell-v79-v1.65-storage-diagnostic",staged["sw.js"])
        self.assertIn(b'url.pathname.includes("/private-api/")',staged["sw.js"])

    def test_structural_inspection_of_legacy_backup_rollback_and_reconciler(self):
        self.assertEqual(len(m.legacy_release_structure(ROOT)),3)

    def test_live_gates_never_self_attested_by_offline_preview(self):
        report=m.status(ROOT)
        self.assertEqual(report["versionedPagesPreviewed"],9)
        self.assertEqual(report["sourceFilesChecked"],14)
        self.assertEqual(report["legacyGuardModulesInspected"],3)
        self.assertEqual(len(report["previewSha256"]),64)
        for field in ("liveVpsContacted","sqliteOpened","backupOrRestorePerformed",
                      "rollbackPerformed","autoupdaterChanged","releaseInstalled"):
            self.assertIs(report[field],False,field)
        self.assertEqual(set(report["pendingLiveGates"]),set(m.REQUIRED_LIVE_GATES))
        self.assertGreater(len(report["pendingLiveGates"]),5)

    def test_running_offline_preview_does_not_change_any_repo_file(self):
        paths=[ROOT/p for p in m.SOURCE_BLOBS]
        before={str(p):(p.stat().st_mtime_ns,p.stat().st_size) for p in paths}
        m.status(ROOT)
        after={str(p):(p.stat().st_mtime_ns,p.stat().st_size) for p in paths}
        self.assertEqual(before,after)

    def test_no_process_database_network_or_recovery_mutators_in_preview(self):
        src=(ROOT/"deploy/oracle/v165_release_offline_preview.py").read_text()
        tree=ast.parse(src)
        imported={alias.name.partition(".")[0] for node in ast.walk(tree)
                  if isinstance(node,ast.Import)
                  for alias in node.names}
        self.assertTrue(imported.isdisjoint(
            {"subprocess","socket","sqlite3","urllib","requests","shutil","tempfile"}))
        self.assertNotIn("os.system",src)
        self.assertNotIn("os.replace",src)
        self.assertNotIn("write_bytes(",src)
        self.assertNotIn("GitHub",src.split("def main():")[-1])

    def test_local_source_symlink_rejected(self):
        with tempfile.TemporaryDirectory(prefix="remura-v165-offline-") as tmp:
            root=Path(tmp)
            for name,blob in self.source.items():
                item=root/name
                item.parent.mkdir(parents=True,exist_ok=True)
                item.write_bytes(blob)
            (root/"nav.js").unlink()
            (root/"nav.js").symlink_to(ROOT/"nav.js")
            with self.assertRaisesRegex(ValueError,"NOT_A_REGULAR_BOUNDED_SOURCE_FILE"):
                m.read_sources(root)

    def test_no_direct_release_apply_or_rollback_entrypoints_exist(self):
        names={n.name for n in ast.parse(
            (ROOT/"deploy/oracle/v165_release_offline_preview.py").read_text()).body
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertTrue({"preview","status","read_sources"} <= names)
        self.assertFalse({"apply","deploy","rollback","restore"} & names)


if __name__ == "__main__":
    unittest.main()
