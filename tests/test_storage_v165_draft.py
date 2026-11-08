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
import storage_inventory_v165 as m


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
        script=(ROOT/"scripts"/"storage_inventory_v165.py").read_text()
        tree=ast.parse(script)
        imports={a.name for node in ast.walk(tree)
                 if isinstance(node,ast.Import) for a in node.names}
        self.assertTrue({"sqlite3","requests","socket","subprocess","urllib"}.isdisjoint(imports))
        for filename in ("private_server.py","price_store.py","signals_monitor.py",
                         "cot_monitor.py","update_myfxbook.py"):
            self.assertNotIn("storage_inventory_v165",
                             (ROOT/"scripts"/filename).read_text())


# Release-candidate integration: no LIVE host access and no server deployment.
import http.client
import json
from http.server import ThreadingHTTPServer
import threading
from unittest.mock import patch
import storage_cache_v165 as cache_module
import private_server as private


class DraftStorageCacheTests(unittest.TestCase):
    def test_disabled_default_no_worker_or_sampling(self):
        obj = cache_module.StorageMetadataCache(sampler=lambda _: self.fail("probe called"))
        self.assertEqual(obj.peek()["state"], "UNKNOWN_MISSING_OR_STALE_CACHE")
        self.assertFalse(obj._started)
        self.assertEqual(obj.peek()["operationalDecision"], cache_module.NO_GO)

    def test_wrong_database_path_cannot_probe_actual_vps(self):
        result=cache_module._live_sample("/home/example/not-remura.sqlite3")
        self.assertEqual(result["state"],"UNKNOWN_OUT_OF_SCOPE_DATABASE_PATH")
        self.assertFalse(result["offhostBackupVerified"])

    def test_refresh_once_cached_memory_only(self):
        calls=[]
        def sampler(db):
            calls.append(db)
            return {
                "schema":cache_module.SCHEMA,"state":"METADATA_ONLY_NEVER_OFFHOST_PROOF",
                "sampledAtUtc":"2026-11-08T12:00:00+00:00",
                "metadata":m._empty("UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE"),
                "offhostBackupVerified":False,
                "restoreOutsideVpsVerified":False,"oracleBillingVerified":False,
                "researchLiveEnabled":False,"operationalDecision":cache_module.NO_GO}
        obj=cache_module.StorageMetadataCache(sampler=sampler)
        obj.refresh_once("fictional")
        self.assertEqual(calls,["fictional"])
        snap=obj.peek()
        snap["state"]="MUTATED_BY_HTTP"
        self.assertEqual(obj.peek()["state"],"METADATA_ONLY_NEVER_OFFHOST_PROOF")
        self.assertEqual(calls,["fictional"])

    def test_stale_cache_suppresses_values(self):
        obj=cache_module.StorageMetadataCache(sampler=lambda _:cache_module._unavailable("FICTITIOUS"))
        obj.refresh_once("fictional")
        then=obj._observed
        with patch.object(cache_module.time,"monotonic",return_value=then+cache_module.TTL_SECONDS+1):
            self.assertEqual(obj.peek()["state"],"UNKNOWN_MISSING_OR_STALE_CACHE")
            self.assertIsNone(obj.peek()["metadata"])

    def test_failure_hidden_not_echoed(self):
        def sampler(db):
            raise ValueError("SECRET_PROVIDER_TOKEN")
        obj=cache_module.StorageMetadataCache(sampler=sampler)
        obj.refresh_once("fictional")
        self.assertEqual(obj.peek()["state"],"UNKNOWN_SAMPLER_EXCEPTION")
        self.assertNotIn("SECRET",repr(obj.peek()))

    def test_untrusted_sampler_cannot_claim_operational_go(self):
        obj=cache_module.StorageMetadataCache(sampler=lambda _:{
            **cache_module._unavailable("FICTITIOUS"),
            "operationalDecision":"GO","offhostBackupVerified":True})
        obj.refresh_once("fictional")
        self.assertEqual(obj.peek()["state"],"UNKNOWN_INVALID_SAMPLER_PAYLOAD")


    def _valid_sample(self, metadata=None):
        if metadata is None:
            metadata=m._empty("UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE")
        return {
            "schema":cache_module.SCHEMA,
            "state":"METADATA_ONLY_NEVER_OFFHOST_PROOF",
            "sampledAtUtc":"2026-11-08T13:45:00+00:00",
            "metadata":metadata,
            "offhostBackupVerified":False,
            "restoreOutsideVpsVerified":False,
            "oracleBillingVerified":False,
            "researchLiveEnabled":False,
            "operationalDecision":cache_module.NO_GO,
        }

    def test_only_allowlisted_fields_reach_private_http_cache(self):
        for injected in (
            {"serverFilesystemPath":"/opt/remura/private"},
            {"CTRADER_TOKEN":"NEVER_ECHO"},
            {"debugDetails":{"privateKey":"NEVER_ECHO"}},
        ):
            obj=cache_module.StorageMetadataCache(
                sampler=lambda _, bad=injected:{**self._valid_sample(),**bad})
            obj.refresh_once("fictional")
            snapshot=obj.peek()
            self.assertEqual(snapshot["state"],"UNKNOWN_INVALID_SAMPLER_PAYLOAD")
            self.assertNotIn("NEVER_ECHO",repr(snapshot))
            self.assertNotIn("/opt/remura",repr(snapshot))

    def test_nested_inventory_new_fields_do_not_leak_secrets(self):
        original=self._valid_sample()
        for injected in (
            {**original["metadata"],"privatePath":"/opt/remura/private/secret"},
            {**original["metadata"],"localBackups":{
                "state":"UNKNOWN_NO_SCANNED_BACKUP",
                "token":"PRIVATE_KEY_MUST_NOT_LEAK"}},
        ):
            obj=cache_module.StorageMetadataCache(
                sampler=lambda _, data=injected:self._valid_sample(data))
            obj.refresh_once("fictional")
            snapshot=obj.peek()
            self.assertEqual(snapshot["state"],"UNKNOWN_INVALID_SAMPLER_PAYLOAD")
            self.assertNotIn("PRIVATE_KEY_MUST_NOT_LEAK",repr(snapshot))
            self.assertNotIn("/opt/remura",repr(snapshot))

    def test_false_billing_evidence_and_bad_timestamp_fail_closed(self):
        for injected in (
            {"oracleBillingVerified":True},
            {"sampledAtUtc":"/secret/storage/account/credential"},
            {"state":"METADATA_ONLY_NEVER_OFFHOST_PROOF;TOKEN"},
            {"metadata":None},
        ):
            obj=cache_module.StorageMetadataCache(
                sampler=lambda _, bad=injected:{**self._valid_sample(),**bad})
            obj.refresh_once("fictional")
            self.assertEqual(obj.peek()["state"],"UNKNOWN_INVALID_SAMPLER_PAYLOAD")

    def test_valid_synthetic_inventory_survives_strict_cache_filter(self):
        with tempfile.TemporaryDirectory(prefix="remura-c4bf-") as directory:
            root=Path(directory)
            (root/m.DB_NAME).write_bytes(b"FICTITIOUS_DATA_NOT_SQLITE")
            metadata=m.inventory(root,mode=m.LAB_MODE)
            self.assertEqual(metadata["state"],"METADATA_ONLY_NOT_INDEPENDENTLY_ATTESTED")
            obj=cache_module.StorageMetadataCache(
                sampler=lambda _:self._valid_sample(metadata))
            obj.refresh_once("fictional")
            self.assertEqual(obj.peek()["state"],"METADATA_ONLY_NEVER_OFFHOST_PROOF")
            self.assertEqual(obj.peek()["metadata"]["operationalDecision"],m.NO_GO)

    def test_simulated_slow_sampler_never_blocks_cached_read(self):
        entered=threading.Event()
        release=threading.Event()
        def slow(_):
            entered.set()
            release.wait(2)
            return self._valid_sample()
        obj=cache_module.StorageMetadataCache(sampler=slow)
        thread=threading.Thread(target=obj.refresh_once,args=("fictional",),daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertEqual(obj.peek()["state"],"UNKNOWN_MISSING_OR_STALE_CACHE")
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(obj.peek()["state"],"METADATA_ONLY_NEVER_OFFHOST_PROOF")

    def test_thread_starts_once_only_when_explicitly_called(self):
        stop=threading.Event()
        invoked=[]
        def once(_):
            invoked.append(1)
            stop.set()
            return cache_module._unavailable("FICTIONAL_SCAN")
        obj=cache_module.StorageMetadataCache(sampler=once)
        self.assertTrue(obj.start("fictional",stop))
        self.assertFalse(obj.start("fictional",stop))
        self.assertTrue(stop.wait(2))
        self.assertEqual(len(invoked),1)

    def test_sample_interval_and_cache_ttl_not_polling_each_http_get(self):
        self.assertGreaterEqual(cache_module.PERIOD_SECONDS,600)
        self.assertGreater(cache_module.TTL_SECONDS,cache_module.PERIOD_SECONDS)
        source=(ROOT/"scripts"/"private_server.py").read_text()
        self.assertNotIn("_live_sample(",source)
        self.assertNotIn("inventory(",source)
        self.assertIn('_STORAGE_CACHE.peek()',source)
        self.assertIn('os.environ.get("REMURA_STORAGE_DIAG_ENABLED","0")=="1"',source)

    def _get_resource(self,enabled):
        server=ThreadingHTTPServer(("127.0.0.1",0),
                                  private.http_handler("/tmp/fictional.sqlite3"))
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            with patch.dict(os.environ,{"REMURA_STORAGE_DIAG_ENABLED":"1" if enabled else "0"}), \
                 patch.object(private,"resource_snapshot",return_value={"schema":"remura-resources-v1","legacyField":1}), \
                 patch.object(private._STORAGE_CACHE,"peek",return_value=cache_module._unavailable("TEST_ONLY")) as peek:
                connection=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
                try:
                    connection.request("GET","/private-api/resources")
                    response=connection.getresponse()
                    payload=json.loads(response.read())
                    self.assertEqual(response.status,200)
                finally:
                    connection.close()
                self.assertEqual(peek.call_count,1 if enabled else 0)
                return payload
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def test_http_flag_off_preserves_legacy_resource_response(self):
        self.assertEqual(self._get_resource(False),
                         {"schema":"remura-resources-v1","legacyField":1})

    def test_http_flag_on_uses_cached_data_only_without_vps_scan(self):
        response=self._get_resource(True)
        self.assertEqual(response["legacyField"],1)
        self.assertEqual(response["storageInventory"]["state"],"TEST_ONLY")
        self.assertFalse(response["storageInventory"]["offhostBackupVerified"])

    def test_draft_scanner_imports_no_network_or_database_engine(self):
        import ast
        source=(ROOT/"scripts"/"storage_cache_v165.py").read_text()
        modules={item.name for node in ast.walk(ast.parse(source))
                 if isinstance(node,ast.Import) for item in node.names}
        self.assertTrue({"sqlite3","requests","socket","subprocess","urllib"}.isdisjoint(modules))
        self.assertNotIn("sqlite3.connect",source)
        self.assertNotIn("shutil.copy",source)


if __name__=="__main__":unittest.main()
