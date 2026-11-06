"""Track B: disposable, OFFLINE dual-database CVD/price-ingest rehearsal.

Uses the ACTUAL price_store.ingest function and same-source 2-market adapter,
but only with synthetic in-memory cTrader-like documents, 34 simulated markets,
a temporary price SQLite and a SEPARATE private CVD SQLite. Does NOT run
Oracle, touch collector LIVE, replay markets, fetch broker data or start CVD.
Numbers from a GitHub-hosted runner cannot be projected onto 1/8 OCPU Oracle.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from scripts import price_store
from scripts import shark_cvd_same_source_adapter as adapter
from scripts import shark_cvd_scan_coverage as scans
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_cvd_source_lineage as lineage
from test_shark_cvd_same_source_preflight import (
    AT, SECRET, inputs, original_document, stamp,
)

KEY=b"synthetic-only-private-staging-hmac-2026"


def ingestion(path, original):
    connection=price_store.connect(path,timeout=2)
    try:
        return price_store.ingest(connection,original,now=AT)
    finally:
        connection.close()


def source_payload():
    # Original two pilot documents must match the price-only SHA witness.
    rows,pilot=inputs()
    markets={symbol:(pilot[symbol] if symbol in pilot
                     else original_document(symbol))
             for symbol in protocol.FROZEN_UNIVERSE}
    return rows,pilot,{"schema":"remura-price-v1",
                       "generatedAt":stamp(AT),"markets":markets}


def saved_price_rows(path):
    with sqlite3.connect(path) as db:
        return db.execute("SELECT symbol,payload FROM prices ORDER BY symbol").fetchall()


def private_rows(path):
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT symbol,closed_at,attempted_at,state,source_hmac,"
            "new_confirmations FROM "+scans.TABLE+" ORDER BY symbol"
        ).fetchall()


def capture(path,rows,pilot):
    db=sqlite3.connect(path,timeout=1)
    try:
        return adapter.capture(db,rows,pilot,secret=KEY,enabled=True)
    finally:
        db.close()


def initialize_private(path):
    db=sqlite3.connect(path)
    try:
        scans.ensure_schema(db)
    finally:
        db.close()


def rss_kib():
    # Single test process RSS snapshot, NOT child peaks, Oracle PSI or CPU quota.
    try:
        with open("/proc/self/status",encoding="ascii") as stream:
            for line in stream:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError,ValueError,IndexError):
        pass
    return None


class SyntheticDualDatabaseCoexistence(unittest.TestCase):
    def test_concurrent_actual_ingest_vs_two_pilot_scans_and_both_restores(self):
        rows,pilot,payload=source_payload()
        with tempfile.TemporaryDirectory(prefix="remura-b-coload-") as folder:
            root=Path(folder)
            base=root/"price-baseline.sqlite"
            parallel=root/"price-parallel.sqlite"
            cvd=root/"cvd-private.sqlite"
            initialize_private(cvd)
            ref=ingestion(base,payload)
            self.assertEqual(len(ref["saved"]),34)
            self.assertEqual(ref["errors"],{})
            cpu_start=time.process_time()
            wall_start=time.perf_counter()
            mem_start=rss_kib()
            with patch.object(adapter,"_utc_now",return_value=AT):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    ingest_job=pool.submit(ingestion,parallel,payload)
                    cvd_job=pool.submit(capture,cvd,rows,pilot)
                    added=ingest_job.result(timeout=15)
                    recorded=cvd_job.result(timeout=15)
            elapsed=time.perf_counter()-wall_start
            cpu=time.process_time()-cpu_start
            self.assertEqual(added,ref)
            self.assertEqual(saved_price_rows(base),saved_price_rows(parallel))
            self.assertEqual(len(saved_price_rows(parallel)),34)
            self.assertEqual(recorded["scanAttemptsRecorded"],2)
            self.assertEqual(recorded["cvdMarketsUncovered"],32)
            self.assertFalse(recorded["crossDatabaseAtomicityEstablished"])
            self.assertFalse(recorded["stagingOrReleaseAuthorized"])
            self.assertFalse(recorded["tradingEdgeEstablished"])
            original=private_rows(cvd)
            self.assertEqual([row[0] for row in original],["EURUSD","XAUUSD"])
            for symbol,_,_,state,mac,count in original:
                self.assertEqual(mac,lineage._mac(KEY,lineage._document_sha(pilot[symbol])))
                self.assertIn(state,("EVALUATED","NOT_EVALUABLE"))
                self.assertTrue(count is None or count>=0)
            # Backup/restore both databases separately. This does NOT make
            # their snapshots a single atomic time-consistent checkpoint.
            for original_path,name in ((parallel,"price"),(cvd,"cvd")):
                restored=root/(name+"-restore.sqlite")
                source=sqlite3.connect(original_path)
                dest=sqlite3.connect(restored)
                try:
                    source.backup(dest)
                    for connection in (source,dest):
                        self.assertEqual(
                            connection.execute("PRAGMA integrity_check").fetchone()[0],
                            "ok")
                    self.assertEqual(
                        source.execute(
                            "SELECT name FROM sqlite_master WHERE type='trigger' "
                            "ORDER BY name").fetchall(),
                        dest.execute(
                            "SELECT name FROM sqlite_master WHERE type='trigger' "
                            "ORDER BY name").fetchall())
                finally:
                    dest.close()
                    source.close()
                if name=="price":
                    self.assertEqual(saved_price_rows(original_path),
                                     saved_price_rows(restored))
                else:
                    self.assertEqual(private_rows(original_path),
                                     private_rows(restored))
                    with sqlite3.connect(restored) as db:
                        with self.assertRaises(sqlite3.IntegrityError):
                            db.execute("DELETE FROM "+scans.TABLE)
                        db.rollback()
            metrics={
                "schema":"remura-synthetic-dual-db-coload-v1",
                "status":"GITHUB_SYNTHETIC_ONLY_ORACLE_NO_GO",
                "priceMarketsIngested":34,"cvdPilotScans":2,
                "cvdMarketsNotCovered":32,
                "jointProcessWallSeconds":round(elapsed,3),
                "jointProcessCpuSeconds":round(cpu,3),
                "rssBeforeMiB":round(mem_start/1024,2) if mem_start is not None else None,
                "rssAfterMiB":round(rss_kib()/1024,2) if rss_kib() is not None else None,
                "realOracleCpuQuotaMeasured":False,
                "realOracleP95P99LockMeasured":False,
                "crossDatabaseAtomicSnapshot":False,
                "syntheticRestoreBothSqlites":True,
                "actualCollectorBrokerRequestsMade":0,
                "liveIngestInterferenceCertified":False,
                "releaseAuthorized":False,
                "tradingEdgeProven":False,
            }
            safe=json.dumps(metrics,sort_keys=True,separators=(",",":"))
            self.assertNotIn(SECRET,safe)
            self.assertNotIn(KEY.decode(),safe)
            print("REMURA_B_CVD_COLOAD_SYNTHETIC="+safe)

    def test_price_ingest_sqlite_writer_busy_does_not_corrupt_private_ledger(self):
        rows,pilot,payload=source_payload()
        with tempfile.TemporaryDirectory(prefix="remura-b-busy-") as folder:
            root=Path(folder)
            price_path=root/"price.sqlite"
            cvd_path=root/"private-cvd.sqlite"
            writer=price_store.connect(price_path,timeout=0.05)
            blocked=sqlite3.connect(price_path)
            initialize_private(cvd_path)
            try:
                blocked.execute("BEGIN IMMEDIATE")
                with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                    price_store.ingest(writer,payload,now=AT)
                self.assertEqual(
                    writer.execute("SELECT count(*) FROM prices").fetchone()[0],0)
                # Separate CVD ledger remains writable while price DB is
                # BUSY. This is NOT a proof of shared source/commit timing.
                with patch.object(adapter,"_utc_now",return_value=AT):
                    out=capture(cvd_path,rows,pilot)
                self.assertEqual(out["scanAttemptsRecorded"],2)
                self.assertFalse(out["crossDatabaseAtomicityEstablished"])
                blocked.rollback()
                result=price_store.ingest(writer,payload,now=AT)
                self.assertEqual(len(result["saved"]),34)
                self.assertEqual(result["errors"],{})
                self.assertEqual(len(private_rows(cvd_path)),2)
            finally:
                blocked.rollback()
                blocked.close()
                writer.close()

    def test_source_valid_cvd_does_not_certify_failed_price_commit(self):
        rows,pilot,payload=source_payload()
        with tempfile.TemporaryDirectory(prefix="remura-b-split-") as folder:
            root=Path(folder)
            private=root/"private-cvd.sqlite"
            initialize_private(private)
            with patch.object(adapter,"_utc_now",return_value=AT):
                result=capture(private,rows,pilot)
            self.assertEqual(result["scanAttemptsRecorded"],2)
            self.assertFalse(result["crossDatabaseAtomicityEstablished"])
            # Simulate an ingest failure after CVD commit; the absence
            # of a price DB transaction means the two proofs CANNOT be
            # promoted to a valid jointly recorded prospective observation.
            invalid={**payload,"schema":"not-an-ingest"}
            with self.assertRaises(ValueError):
                ingestion(root/"price.sqlite",invalid)
            self.assertEqual(len(private_rows(private)),2)
            self.assertEqual(len(saved_price_rows(root/"price.sqlite")),0)
            self.assertFalse(result["stagingOrReleaseAuthorized"])


if __name__=="__main__":
    unittest.main()
