"""REMURA Track B local archival contract: synthetic causality, no LIVE.

Self-contained original COT+price+private-CVD graphs, exact row replay into
fresh IN-MEMORY SQLite from ZIP, no deletion, no overwrite, source read-only.
No GitHub artifact uploaded and no real user account or broker document.
"""
from __future__ import annotations

import base64
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import shark_research_local_archive as archive
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from scripts import shark_cvd_ledger as cvd
from scripts import shark_cvd_scan_coverage as scans
from test_shark_cvd_scan_coverage import make_doc, stamp, DAY, KEY
from test_shark_cvd_cot_price_triage import (
    source_with_verified_divergence, original_cvd_event,
)
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,NOW,OBSERVED,insert_history,iso
from test_shark_cvd_ledger import QUALITY,SECRET


def rebuild_in_memory(filename, scope):
    """Test-only replay of all research rows/schema to verify no loss."""
    restored=sqlite3.connect(":memory:")
    with zipfile.ZipFile(filename) as zipped:
        manifest=json.loads(zipped.read(archive.MANIFEST))
        tables=manifest[scope]
        for table,meta in tables.items():
            restored.execute(meta["createTableSql"])
        for table,meta in tables.items():
            records=[]
            with zipped.open(meta["entry"]) as source:
                for line in source:
                    row=json.loads(line)["values"]
                    vals=[base64.b64decode(x["data"]) if (
                          isinstance(x,dict) and x.get("kind")=="blob-base64")
                          else x for x in row]
                    records.append(vals)
            if records:
                cols=", ".join('"'+x+'"' for x in meta["columns"])
                q=", ".join("?" for _ in meta["columns"])
                restored.executemany(
                    f'INSERT INTO "{table}" ({cols}) VALUES ({q})',records)
            for trigger in meta["triggers"]:
                restored.execute(trigger["sql"])
        restored.commit()
    return restored


class LocalResearchArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix="remura-local-proof-")
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/"causal-proof.zip"
        self.main,original=create()
        self.private=sqlite3.connect(":memory:")
        cvd.ensure_schema(self.private)
        scans.ensure_schema(self.private)
        scan_doc=make_doc(count=60)
        scan_end=DAY+timedelta(minutes=900)
        scans.record(
            self.private,symbol="EURUSD",slot_closed_at=stamp(scan_end),
            source_document=scan_doc,secret=KEY,
            clock=scan_end+__import__("datetime").timedelta(minutes=1))
        doc=source_with_verified_divergence(self.main,original)
        event=original_cvd_event(doc)
        witness.witness(self.main,clock=AT)
        with self.main:
            id_=insert_history(self.main)
            proof=bundle.record(
                self.main,history_id=id_,observed_document=doc,clock=NOW,
                capture_cvd_prefix=True)
        self.assertEqual(proof["state"],"BOTH_LOCAL_PROOFS_PRESENT")
        result=cvd.append(
            self.private,event,QUALITY,
            source_collected_at=iso(OBSERVED),
            hmac_secret=SECRET,now=OBSERVED,source_document=doc)
        self.assertTrue(result["sourceDocumentBound"])
        self.addCleanup(self.main.close)
        self.addCleanup(self.private.close)

    def _archive(self,**options):
        self.main.execute("PRAGMA query_only=ON")
        self.private.execute("PRAGMA query_only=ON")
        return archive.export_bundle(
            self.main,self.private,self.path,**options)

    def test_export_verify_and_replay_all_rows_without_mutating_sources(self):
        m_changes=self.main.total_changes
        p_changes=self.private.total_changes
        out=self._archive()
        self.assertEqual(out["status"],"LOCAL_ARCHIVE_INTEGRITY_VERIFIED")
        self.assertEqual(out["sourceRowsDeleted"],0)
        self.assertEqual(out["sourceDatabaseModified"],False)
        self.assertFalse(out["readyForAutomaticPrune"])
        self.assertFalse(out["freesSqliteCapacity"])
        self.assertEqual(len(out["sha256"]),64)
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
        self.assertEqual(m_changes,self.main.total_changes)
        self.assertEqual(p_changes,self.private.total_changes)
        self.assertGreater(out["rows"],8)
        self.assertEqual(archive.verify_bundle(self.path)["sha256"],out["sha256"])
        self.assertEqual(out["tableRowCounts"]["private.research_cvd_scan_attempts"],1)
        self.assertEqual(out["cvdScanAttemptCapacity"]["archivedAttempts"],1)
        self.assertFalse(out["cvdScanAttemptHmacIndependentVerification"])
        with zipfile.ZipFile(self.path) as z:
            meta=json.loads(z.read("manifest.json"))
            self.assertFalse(meta["includesRawOHLCOrOutcomePaths"])
            self.assertFalse(meta["includesPriceOnlyFull34Cohorts"])
            self.assertFalse(meta["privateHmacSecretIncluded"])
            self.assertFalse(meta["completeOCIBackupOrRestore"])
            self.assertTrue(meta["scanAttemptCoverageIncluded"])
            self.assertFalse(meta["scanAttemptHmacCanBeRecomputedWithoutPrivateKey"])
            self.assertFalse(meta["sourceDataDeleted"])
            self.assertEqual(set(meta["main"]),set(archive.MAIN_TABLES))
            self.assertEqual(set(meta["private"]),set(archive.PRIVATE_TABLES))
        for scope,source in (("main",self.main),("private",self.private)):
            rebuilt=rebuild_in_memory(self.path,scope)
            try:
                for table in archive.ALLOW[scope]:
                    order=archive._stable_order(source,table)
                    left=source.execute(
                        f"SELECT * FROM {table} ORDER BY {order}").fetchall()
                    right=rebuilt.execute(
                        f"SELECT * FROM {table} ORDER BY {order}").fetchall()
                    self.assertEqual(left,right,table)
                    self.assertEqual(
                        sorted(x[0] for x in source.execute(
                            "SELECT name FROM sqlite_master "
                            "WHERE type='trigger' AND tbl_name=?",(table,))),
                        sorted(x[0] for x in rebuilt.execute(
                            "SELECT name FROM sqlite_master "
                            "WHERE type='trigger' AND tbl_name=?",(table,))))
            finally:
                rebuilt.close()
        # No authorizer, no README scripts, no external cloud upload.
        visible=json.dumps(out)
        for private in ("PRIVATE_FAKE_BROKER_IDENTIFIER",
                        "099741","source_document","hmac_secret","providerSymbol"):
            self.assertNotIn(private,visible)

    def test_both_readonly_connections_are_mandatory(self):
        with self.assertRaisesRegex(ValueError,
                                    "readonly_sqlite_connection_required"):
            archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())
        self.main.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,
                                    "readonly_sqlite_connection_required"):
            archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())

    def test_no_overwrite_and_failure_never_partially_publishes(self):
        self._archive()
        old_hash=archive.verify_bundle(self.path)["sha256"]
        with self.assertRaises(FileExistsError):
            self._archive()
        self.assertEqual(old_hash,archive.verify_bundle(self.path)["sha256"])
        self.path.unlink()
        with self.assertRaisesRegex(ValueError,"archive_resource_limit_exceeded"):
            self._archive(max_rows=1)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.glob(".remura-evidence-*.tmp")),[])
        with self.assertRaisesRegex(ValueError,"archive_resource_limit_exceeded"):
            self._archive(max_bytes=1024)
        self.assertFalse(self.path.exists())

    def test_missing_required_proof_does_not_label_export_complete(self):
        self.private.execute("DROP TABLE research_cvd_m15_prefix_proofs")
        self.private.execute("PRAGMA query_only=ON")
        self.main.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,"causal_provenance_table_missing"):
            archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())

    def test_scan_ledger_v2_is_required_and_private_hmac_survives_replay(self):
        self._archive()
        replay=rebuild_in_memory(self.path,"private")
        try:
            original=self.private.execute(
                "SELECT * FROM research_cvd_scan_attempts").fetchone()
            restored=replay.execute(
                "SELECT * FROM research_cvd_scan_attempts").fetchone()
            self.assertEqual(original,restored)
            self.assertEqual(len(original),9)
            self.assertEqual(len(original[5]),64)  # session_prefix_hmac
            self.assertEqual(original[8],scans.SCHEMA)
            with self.assertRaises(sqlite3.IntegrityError):
                replay.execute("UPDATE research_cvd_scan_attempts SET reason='DATA_MISSING'")
            replay.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                replay.execute("DELETE FROM research_cvd_scan_attempts")
        finally:
            replay.close()
        self.assertNotIn("PRIVATE_TEST_BROKER_DO_NOT_EXPORT",self.path.read_bytes().decode("latin1"))
        self.assertNotIn(KEY.decode(),self.path.read_bytes().decode("latin1"))

    def test_missing_v2_scan_table_or_trigger_is_fail_closed(self):
        self.private.execute("DROP TABLE research_cvd_scan_attempts")
        self.private.execute("PRAGMA query_only=ON")
        self.main.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,"causal_provenance_table_missing"):
            archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())

    def test_v1_bundle_remains_verifiable_without_claiming_new_scan_coverage(self):
        self._archive()
        old=self.path.parent/"legacy-v1.zip"
        with zipfile.ZipFile(self.path) as source:
            manifest=json.loads(source.read(archive.MANIFEST))
            manifest["schema"]=archive.LEGACY_SCHEMA
            manifest["private"].pop(archive.SCAN_TABLE)
            manifest.pop("scanAttemptCoverageIncluded")
            manifest.pop("scanAttemptHmacCanBeRecomputedWithoutPrivateKey")
            with zipfile.ZipFile(old,"w",compression=zipfile.ZIP_DEFLATED) as dest:
                for item in source.namelist():
                    if item==archive.MANIFEST:
                        dest.writestr(item,archive._json(manifest))
                    elif item!=f"evidence/private/{archive.SCAN_TABLE}.jsonl":
                        dest.writestr(item,source.read(item))
        report=archive.verify_bundle(old)
        self.assertEqual(report["schema"],archive.LEGACY_SCHEMA)
        self.assertIsNone(report["cvdScanAttemptCapacity"])
        self.assertNotIn("private."+archive.SCAN_TABLE,report["tableRowCounts"])

    def test_scan_hmac_zip_tamper_rejected_even_when_zip_crc_is_valid(self):
        self._archive()
        edited=self.path.parent/"tampered.zip"
        with zipfile.ZipFile(self.path) as source:
            with zipfile.ZipFile(edited,"w",compression=zipfile.ZIP_DEFLATED) as dest:
                for item in source.namelist():
                    data=source.read(item)
                    if item==f"evidence/private/{archive.SCAN_TABLE}.jsonl":
                        row=json.loads(data)
                        self.assertEqual(len(row["values"][5]),64)
                        row["values"][5]="0"*64
                        data=archive._json(row)
                    dest.writestr(item,data)
        with self.assertRaisesRegex(ValueError,"archive_hash_or_count_mismatch"):
            archive.verify_bundle(edited)

    def test_missing_scan_immutability_trigger_or_capacity_preflight_rejected(self):
        with patch.object(archive,"MAX_SCAN_ATTEMPTS",0):
            self.main.execute("PRAGMA query_only=ON")
            self.private.execute("PRAGMA query_only=ON")
            with self.assertRaisesRegex(ValueError,"cvd_scan_archive_capacity_corrupt"):
                archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())
        self.private.execute("PRAGMA query_only=OFF")
        self.private.execute("DROP TRIGGER research_cvd_scan_no_delete")
        self.private.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,"cvd_scan_archive_immutability_missing"):
            archive.export_bundle(self.main,self.private,self.path)
        self.assertFalse(self.path.exists())

    def test_private_sqlite_disk_restore_from_verified_archive(self):
        self._archive()
        self.assertEqual(archive.verify_bundle(self.path)["status"],
                         "LOCAL_ARCHIVE_INTEGRITY_VERIFIED")
        replay=rebuild_in_memory(self.path,"private")
        saved=self.path.parent/"restored-private.sqlite3"
        disk=sqlite3.connect(saved)
        try:
            replay.backup(disk)
            self.assertEqual(disk.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(
                disk.execute("SELECT * FROM research_cvd_scan_attempts").fetchall(),
                self.private.execute("SELECT * FROM research_cvd_scan_attempts").fetchall())
            self.assertEqual(
                disk.execute("SELECT count(*) FROM research_cvd_m15_prefix_proofs").fetchone(),
                self.private.execute("SELECT count(*) FROM research_cvd_m15_prefix_proofs").fetchone())
            for trigger in scans.TRIGGERS:
                self.assertIsNotNone(disk.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                    (trigger,)).fetchone())
            with self.assertRaises(sqlite3.IntegrityError):
                disk.execute("DELETE FROM research_cvd_scan_attempts")
        finally:
            disk.close()
            replay.close()

    def test_corrupted_or_incomplete_zip_is_rejected(self):
        self._archive()
        original=self.path.read_bytes()
        self.path.write_bytes(original[:len(original)//2])
        with self.assertRaises(ValueError):
            archive.verify_bundle(self.path)

    def test_reject_path_outside_existing_local_directory_and_invalid_bounds(self):
        self.main.execute("PRAGMA query_only=ON")
        self.private.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):
            archive.export_bundle(
                self.main,self.private,self.path.parent/"missing"/"proof.zip")
        with self.assertRaises(ValueError):
            archive.export_bundle(
                self.main,self.private,self.path.parent/"proof.txt")
        for bad in (0,True,120001,"100"):
            with self.subTest(rows=bad):
                with self.assertRaises(ValueError):
                    archive.export_bundle(
                        self.main,self.private,self.path,max_rows=bad)
        self.assertFalse(self.path.exists())


if __name__=="__main__":
    unittest.main()
