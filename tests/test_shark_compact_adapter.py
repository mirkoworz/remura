"""Future-only v1.62 scanner compact batch opt-in (synthetic SQLite).

The LIVE scan_once entrypoint never opts in; this test uses local SQLite
fixtures, exact original price_view and COT classifier, zero HTTP/broker.
"""
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
import signals_monitor as live

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact
from scripts import shark_price_only_universe as legacy_research
from test_shark_staging_scan import fixture,clone,standard_state,NOW,stamp


class CompactScannerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)/"standard.sqlite"
        self.new=Path(tmp.name)/"compact.sqlite"
        fixture(self.base)
        clone(self.base,self.new)

    def run_compact(self,*,path=None,targets=None,now=NOW):
        with patch.object(witness,"_clock",return_value=now+timedelta(seconds=2)):
            return live.scan_once_with_compact_price_only_research(
                self.new if path is None else path,now,targets=targets)

    def test_live_default_and_compact_optin_match_all_legacy_tables(self):
        baseline=live.scan_once(self.base,NOW)
        research=self.run_compact()
        self.assertEqual(baseline,{
            k:v for k,v in research.items() if k!="priceOnlyResearch"})
        self.assertEqual(standard_state(self.base),standard_state(self.new))
        self.assertEqual(research["priceOnlyResearch"]["batchStatus"],
                         "COMPACT_BATCH_SEALED")
        self.assertEqual(research["priceOnlyResearch"]["storedMarkets"],34)
        with sqlite3.connect(self.new) as db:
            census=compact.summary(db)
            self.assertEqual(census["immutableBatches"],1)
            self.assertEqual(census["fullScanDenominator"],34)
            self.assertEqual(census["fullScanPriceCandidates"],1)
            self.assertEqual(census["fullScanUnknowns"],0)
            self.assertGreater(census["theoreticalFullScanDaysAt15Min"],1000)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_universe'").fetchone()[0],0)
            integrity=compact.verify(
                db,scan_slot=compact._slot(stamp(NOW.replace(minute=15,second=0,microsecond=0))))
            self.assertEqual(integrity["status"],"ARCHIVE_VERIFIED")
            payload=db.execute(
                "SELECT payload_zlib FROM research_price_only_batches"
            ).fetchone()[0]
        self.assertLess(len(payload),4096)
        result=json.dumps(research)+json.dumps(census)
        self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",result)
        self.assertNotIn("1.01",result)
        self.assertEqual(research["priceOnlyResearch"]["extraBrokerRequests"],0)

    def test_full_34_prices_and_missing_cot_yields_34_price_candidates(self):
        with tempfile.TemporaryDirectory() as path:
            file=Path(path)/"all34.sqlite"
            fixture(file,with_cot=False,all_priced=True)
            r=self.run_compact(path=file)
            self.assertEqual(r["examined"],0)
            self.assertEqual(r["priceOnlyResearch"]["eligiblePriceCandidates"],34)
            with sqlite3.connect(file) as db:
                result=compact.summary(db)
                self.assertEqual(result["fullScanDenominator"],34)
                self.assertEqual(result["fullScanPriceCandidates"],34)
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_original_scan_can_repeat_but_compact_original_is_immutable(self):
        live.scan_once(self.base,NOW)
        self.run_compact()
        live.scan_once(self.base,NOW)
        rerun=self.run_compact()
        self.assertEqual(rerun["priceOnlyResearch"]["batchStatus"],
                         "DUPLICATE_BATCH")
        self.assertEqual(standard_state(self.base),standard_state(self.new))
        with sqlite3.connect(self.new) as db:
            self.assertEqual(compact.summary(db)["immutableBatches"],1)
            self.assertEqual(compact.summary(db)["fullScanDenominator"],34)

    def test_targeted_scan_is_not_counted_as_full_denominator(self):
        research=self.run_compact(targets=("EURUSD",))
        self.assertEqual(research["priceOnlyResearch"]["storedMarkets"],1)
        self.assertFalse(research["priceOnlyResearch"]["fullMarketDenominator"])
        with sqlite3.connect(self.new) as db:
            result=compact.summary(db)
            self.assertEqual(result["immutableBatches"],1)
            self.assertEqual(result["fullScanDenominator"],0)
            self.assertEqual(
                result["targetedScansExcludedFromMainDenominator"],1)
        self.run_compact()  # same time slot, but a DIFFERENT full-scan scope
        with sqlite3.connect(self.new) as db:
            result=compact.summary(db)
            self.assertEqual(result["immutableBatches"],2)
            self.assertEqual(result["fullScanDenominator"],34)

    def test_cot_reader_exception_never_erases_price_only_denominator(self):
        with patch.object(live,"cot_series",side_effect=ValueError("cot_late")) as reader:
            result=self.run_compact()
        self.assertEqual(reader.call_count,34)
        self.assertEqual(result["examined"],0)
        self.assertEqual(result["priceOnlyResearch"]["storedMarkets"],34)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(compact.summary(db)["fullScanDenominator"],34)
            self.assertEqual(compact.summary(db)["fullScanPriceCandidates"],1)

    def test_one_market_price_error_is_counted_as_unknown_not_omitted(self):
        original=live.price_view
        def broken(doc,now,quality=None):
            if doc is not None and doc["symbol"]=="EURUSD":
                raise ValueError("synthetic_local_price_failure")
            return original(doc,now,quality=quality)
        with patch.object(live,"price_view",side_effect=broken):
            result=self.run_compact()
        self.assertEqual(result["priceOnlyResearch"]["storedMarkets"],34)
        self.assertEqual(result["priceOnlyResearch"]["unknownObservations"],1)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(compact.summary(db)["fullScanUnknowns"],1)
            self.assertEqual(compact.summary(db)["fullScanDenominator"],34)

    def test_fair_34x4000_old_rows_vs_new_compact_batches(self):
        # Both scanners use the SAME 34 synthetic market sources (4k M15
        # each), no profiler on either path, no COT/HTTP/broker requests.
        with tempfile.TemporaryDirectory() as root:
            raw_path=Path(root)/"raw_rows.sqlite"
            cmp_path=Path(root)/"compact_batches.sqlite"
            fixture(raw_path,with_cot=False,all_priced=True,m15_count=4000)
            clone(raw_path,cmp_path)
            with patch.object(witness,"_clock",return_value=NOW+timedelta(seconds=2)):
                started=time.perf_counter()
                raw=live.scan_once_with_price_only_research(raw_path,NOW)
                raw_time=time.perf_counter()-started
                started=time.perf_counter()
                batch=live.scan_once_with_compact_price_only_research(cmp_path,NOW)
                batch_time=time.perf_counter()-started
            self.assertEqual(standard_state(raw_path),standard_state(cmp_path))
            self.assertEqual(raw["priceOnlyResearch"]["marketsAttempted"],34)
            self.assertEqual(batch["priceOnlyResearch"]["storedMarkets"],34)
            with sqlite3.connect(raw_path) as db:
                raw_bytes=db.execute("PRAGMA page_count").fetchone()[0]*db.execute(
                    "PRAGMA page_size").fetchone()[0]
                rows=legacy_research.summary(db)
                self.assertEqual(rows["totalScans"],34)
            with sqlite3.connect(cmp_path) as db:
                compact_bytes=db.execute("PRAGMA page_count").fetchone()[0]*db.execute(
                    "PRAGMA page_size").fetchone()[0]
                batches=compact.summary(db)
                self.assertEqual(batches["fullScanDenominator"],34)
                self.assertEqual(batches["fullScanPriceCandidates"],34)
                self.assertEqual(batches["immutableBatches"],1)
                self.assertLess(batches["compressedBytes"],8192)
                check=compact.verify(
                    db,scan_slot=stamp(NOW.replace(minute=15,second=0,microsecond=0)))
                self.assertEqual(check["marketObservations"],34)
            self.assertLess(compact_bytes,raw_bytes)
            self.assertLess(raw_time,40)
            self.assertLess(batch_time,40)
            print("REMURA_TRACK_B_COMPACT_FAIR4000="+json.dumps({
                "markets":34,"m15BarsPerMarket":4000,
                "rawMarketRows":34,"compactBatchRows":1,
                "rawDbBytes":raw_bytes,
                "compactDbBytes":compact_bytes,
                "compressedBatchBytes":batches["compressedBytes"],
                "rawScanSeconds":round(raw_time,3),
                "compactScanSeconds":round(batch_time,3),
                "sameSqualincomeState":True,
                "snapshotVersionValidated":batch["priceOnlyResearch"]["snapshotVersionValidated"],
                "readOnlySnapshotMs":batch["priceOnlyResearch"]["readOnlySnapshotMs"],
                "sqliteWriterLockMs":batch["priceOnlyResearch"]["sqliteWriterLockMs"],
                "profilerUsed":False,"oracleMeasured":False,
                "tradingEdgeEstablished":False,
            },sort_keys=True,separators=(",",":")))

    def test_two_phase_snapshot_detects_competing_ingest_and_never_uses_stale_prices(self):
        # Another process commits a price revision while the READ snapshot
        # is held. WAL permits that legitimate writer, but the scanner must
        # reject its prepared observations before ANY scanner write.
        original=live.classify
        updated=[False]
        with sqlite3.connect(self.new) as source:
            previous=source.execute(
                "SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0]
        def revised_during_read(cot,price):
            if not updated[0]:
                with sqlite3.connect(self.new,timeout=1.0) as updater:
                    updater.execute(
                        "UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                        (previous+" ",))
                updated[0]=True
            return original(cot,price)
        with patch.object(live,"classify",side_effect=revised_during_read):
            with self.assertRaisesRegex(
                    sqlite3.OperationalError,
                    "research_source_changed_before_atomic_commit"):
                self.run_compact()
        self.assertTrue(updated[0])
        self.assertEqual(standard_state(self.new),standard_state(self.base))
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0],
                previous+" ")

    def test_snapshot_allows_concurrent_other_writer_without_partial_scanner_writes(self):
        # Verify the source read phase DOES NOT hold SQLite's writer
        # reservation. A disjoint status update must be permitted, but
        # because it invalidates the read snapshot, the scan fails safely.
        original=live.price_view
        injected=[False]
        def with_external_writer(doc,when,quality=None):
            if not injected[0]:
                with sqlite3.connect(self.new,timeout=1.0) as other:
                    other.execute(
                        "INSERT OR REPLACE INTO status(key,value) VALUES(?,?)",
                        ("test_external_writer","observed"))
                injected[0]=True
            return original(doc,when,quality=quality)
        with patch.object(live,"price_view",side_effect=with_external_writer):
            with self.assertRaisesRegex(
                    sqlite3.OperationalError,
                    "research_source_changed_before_atomic_commit"):
                self.run_compact()
        self.assertTrue(injected[0])
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT value FROM status WHERE key='test_external_writer'"
            ).fetchone()[0],"observed")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_compact_two_phase_uses_one_original_price_and_cot_read_each(self):
        real_latest=live.latest
        real_audit=live.audit_market
        real_view=live.price_view
        real_cot=live.cot_series
        counts={"latest":0,"audit":0,"price":0,"cot":0}
        def latest(*args,**kwargs):
            counts["latest"]+=1
            return real_latest(*args,**kwargs)
        def audit(*args,**kwargs):
            counts["audit"]+=1
            return real_audit(*args,**kwargs)
        def view(*args,**kwargs):
            counts["price"]+=1
            return real_view(*args,**kwargs)
        def cot(*args,**kwargs):
            counts["cot"]+=1
            return real_cot(*args,**kwargs)
        with patch.object(live,"latest",side_effect=latest):
            with patch.object(live,"audit_market",side_effect=audit):
                with patch.object(live,"price_view",side_effect=view):
                    with patch.object(live,"cot_series",side_effect=cot):
                        result=self.run_compact()
        # Only EURUSD has prices; the other 33 are absent, not re-fetched.
        self.assertEqual(counts,{"latest":34,"audit":34,"price":1,"cot":34})
        metadata=result["priceOnlyResearch"]
        self.assertTrue(metadata["snapshotVersionValidated"])
        self.assertGreaterEqual(metadata["readOnlySnapshotMs"],0)
        self.assertGreaterEqual(metadata["sqliteWriterLockMs"],0)
        self.assertFalse(metadata["alertsEnabled"])
        self.assertEqual(metadata["extraBrokerRequests"],0)

    def test_late_seal_error_rolls_back_original_squalincome_and_batch(self):
        # The original v1.62 EURUSD baseline would have committed
        # BEFORE the old end-of-scan compact seal. This regression proves
        # the new single BEGIN IMMEDIATE boundary really rolls it back.
        baseline_state=standard_state(self.base)
        with patch.object(compact,"seal",side_effect=sqlite3.OperationalError("disk_full")):
            with self.assertRaisesRegex(sqlite3.OperationalError,"disk_full"):
                self.run_compact()
        self.assertEqual(standard_state(self.new),baseline_state)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_last_scan").fetchone()[0],0)

    def test_real_process_sigkill_before_commit_keeps_db_atomic(self):
        # Stronger than a caught SystemExit: kill a separate Linux process
        # AFTER SQLite has written BOTH the original Squalincome changes and
        # the final research block, but BEFORE the single outer COMMIT.
        # WAL recovery must show NEITHER group of uncommitted writes.
        import multiprocessing
        import os
        import signal
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("Linux fork required for disposable crash test")
        expected=standard_state(self.base)
        def crash_child():
            real_seal=compact.seal
            def after_insert(db,rows,*,full,clock=None):
                real_seal(db,rows,full=full,clock=clock)
                # Verify both original history and research batch were
                # written to this connection before the hard kill.
                assert db.execute(
                    "SELECT count(*) FROM squalincome_history").fetchone()[0]==1
                assert db.execute(
                    "SELECT count(*) FROM research_price_only_batches").fetchone()[0]==1
                os.kill(os.getpid(),signal.SIGKILL)
            with patch.object(compact,"seal",side_effect=after_insert):
                self.run_compact()
        child=multiprocessing.get_context("fork").Process(target=crash_child)
        child.start()
        child.join(timeout=15)
        if child.is_alive():
            child.kill()
            child.join(timeout=5)
            self.fail("crashed_writer_child_hung")
        self.assertEqual(child.exitcode,-signal.SIGKILL)
        self.assertEqual(standard_state(self.new),expected)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_last_scan").fetchone()[0],0)
        # An ordinary *fresh* retry is allowed after WAL recovery. No
        # fabricated past observation or retroactive data repair.
        recovered=self.run_compact()
        self.assertEqual(recovered["priceOnlyResearch"]["batchStatus"],
                         "COMPACT_BATCH_SEALED")
        with sqlite3.connect(self.new) as db:
            verified=compact.verify(
                db,scan_slot=stamp(NOW.replace(
                    minute=15,second=0,microsecond=0)))
            self.assertEqual(verified["marketObservations"],34)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")

    def test_interrupt_after_batch_write_rolls_back_all_origins(self):
        baseline_state=standard_state(self.base)
        real_seal=compact.seal
        def interrupted(db,rows,*,full,clock=None):
            result=real_seal(db,rows,full=full,clock=clock)
            self.assertEqual(result["status"],"COMPACT_BATCH_SEALED")
            raise SystemExit("simulated_worker_termination_before_commit")
        with patch.object(compact,"seal",side_effect=interrupted):
            with self.assertRaisesRegex(SystemExit,"before_commit"):
                self.run_compact()
        self.assertEqual(standard_state(self.new),baseline_state)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_other_sqlite_reader_never_sees_a_half_filled_scan(self):
        # The original Squalincome baseline and the compact batch have
        # already been written on the scanner connection when seal runs,
        # but neither should be visible to an independent SQLite reader.
        real_seal=compact.seal
        def inspect_before_commit(db,rows,*,full,clock=None):
            with sqlite3.connect(self.new,timeout=1.0) as outside:
                self.assertEqual(outside.execute(
                    "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
                self.assertEqual(outside.execute(
                    "SELECT count(*) FROM squalincome_last_scan").fetchone()[0],0)
                self.assertEqual(outside.execute(
                    "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)
            return real_seal(db,rows,full=full,clock=clock)
        with patch.object(compact,"seal",side_effect=inspect_before_commit):
            self.run_compact()
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],1)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],1)

    def test_sqlite_busy_writer_is_visible_and_does_not_corrupt_either_table(self):
        # Concurrent ingest writer (simulated by a real separate SQLite
        # BEGIN IMMEDIATE) must NEVER cause a partial research/legacy scan.
        with sqlite3.connect(self.new) as setup:
            compact.ensure_schema(setup)
        outside=sqlite3.connect(self.new,timeout=1.0)
        try:
            outside.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                self.run_compact(targets=("EURUSD",))
        finally:
            outside.rollback()
            outside.close()
        self.assertEqual(standard_state(self.new),standard_state(self.base))
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)

    def test_optin_sqlite_connect_timeout_also_bounds_schema_setup(self):
        # WAL/setup happens *inside* price_store.connect(); a PRAGMA set only
        # after connect() returned could still wait the original 30 seconds.
        holder=sqlite3.connect(self.new,timeout=1.0)
        try:
            holder.execute("BEGIN IMMEDIATE")
            began=time.perf_counter()
            with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                self.run_compact(targets=("EURUSD",))
            waited=time.perf_counter()-began
            self.assertLess(waited,12.0)  # 5s opt-in + slow CI margin
            print("REMURA_TRACK_B_BUSY_CONNECT_SECONDS="+str(round(waited,3)))
        finally:
            holder.rollback()
            holder.close()
        self.assertEqual(standard_state(self.new),standard_state(self.base))
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_legacy_price_store_connection_default_still_30_seconds(self):
        # A pure connection contract test, without waiting 30 seconds.
        import inspect
        from price_store import connect as original_connect
        self.assertEqual(inspect.signature(original_connect).parameters[
            "timeout"].default,30.0)
        with sqlite3.connect(self.base) as existing:
            self.assertEqual(existing.execute(
                "PRAGMA journal_mode").fetchone()[0].lower(),"wal")
        from price_store import connect
        normal=connect(self.base)
        self.assertEqual(normal.execute(
            "PRAGMA busy_timeout").fetchone()[0],30000)
        normal.close()
        research=connect(self.base,timeout=5.0)
        self.assertEqual(research.execute(
            "PRAGMA busy_timeout").fetchone()[0],5000)
        research.close()

    def test_compact_result_reports_actual_sqlite_writer_lock_interval(self):
        result=self.run_compact()
        locked=result["priceOnlyResearch"]["sqliteWriterLockMs"]
        self.assertGreaterEqual(locked,0)
        self.assertLess(locked,12000)
        with sqlite3.connect(self.new) as db:
            self.assertEqual(compact.summary(db)["immutableBatches"],1)

    def test_concurrent_ingest_writer_cannot_partially_modify_scan(self):
        # Verify the real writer reservation. Use a short second-connection
        # timeout to avoid slowing the synthetic suite.
        real_seal=compact.seal
        def competing_ingest(db,rows,*,full,clock=None):
            with sqlite3.connect(self.new,timeout=0.2) as other:
                with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                    other.execute("INSERT OR REPLACE INTO status VALUES (?,?)",
                                  ("synthetic_ingest","should_rollback"))
            return real_seal(db,rows,full=full,clock=clock)
        with patch.object(compact,"seal",side_effect=competing_ingest):
            result=self.run_compact()
        self.assertEqual(result["priceOnlyResearch"]["batchStatus"],
                         "COMPACT_BATCH_SEALED")
        with sqlite3.connect(self.new) as db:
            self.assertIsNone(db.execute(
                "SELECT value FROM status WHERE key='synthetic_ingest'").fetchone())
            self.assertEqual(compact.summary(db)["fullScanDenominator"],34)

    def test_error_on_seal_propagates_not_masked_as_missing_data(self):
        with patch.object(compact,"seal",side_effect=sqlite3.OperationalError("disk_full")):
            with self.assertRaisesRegex(sqlite3.OperationalError,"disk_full"):
                self.run_compact()
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],0)

    def test_compact_and_old_per_market_writer_do_not_mix(self):
        # Two opt-in functions exist, but each creates only its own storage.
        self.run_compact()
        with sqlite3.connect(self.new) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_universe'").fetchone()[0],0)
        with sqlite3.connect(self.base) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_batches'").fetchone()[0],0)

    def test_isolated_sqlite_backup_and_restore_recovers_both_scanner_and_batch(self):
        # Simulate the native SQLite online backup API. This tests data
        # correctness only; it does NOT operate on or certify Oracle backups.
        self.run_compact()
        restored=self.new.with_name("restored_compact.sqlite")
        with sqlite3.connect(self.new) as original, sqlite3.connect(restored) as dest:
            original.backup(dest)
        self.assertEqual(standard_state(restored),standard_state(self.new))
        with sqlite3.connect(restored) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            audit=compact.verify(
                db,scan_slot=stamp(NOW.replace(minute=15,second=0,microsecond=0)))
            self.assertEqual(audit["status"],"ARCHIVE_VERIFIED")
            self.assertEqual(audit["marketObservations"],34)
            self.assertEqual(compact.summary(db)["fullScanDenominator"],34)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM research_price_only_batches")
        with sqlite3.connect(self.new) as original:
            self.assertEqual(original.execute(
                "SELECT count(*) FROM research_price_only_batches").fetchone()[0],1)

    def test_production_entrypoint_has_not_changed(self):
        self.assertEqual(live.scan_once.__name__,"scan_once")
        self.assertEqual(live.scan_once_with_h1_frames.__name__,
                         "scan_once_with_h1_frames")
        self.assertTrue(callable(live.scan_once_with_compact_price_only_research))


if __name__=="__main__":
    unittest.main()
