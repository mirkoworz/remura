"""Synthetic-only compact batch storage and archive integrity tests.

No production SQLite, COT, broker calls, account IDs, or raw OHLC exports.
Uses the actual price-only prepare() from the v1.62 research contract.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import signals_monitor as live

from scripts import shark_price_only_compact as compact
from scripts import shark_price_only_universe as universe
from test_shark_staging_scan import fixture,NOW,stamp


def make_db(path):
    fixture(path,with_cot=False,all_priced=True)
    db=sqlite3.connect(path)
    compact.ensure_schema(db)
    return db


def prepared(db,markets=None,*,timestamp=NOW):
    markets=live.monitored_symbols() if markets is None else markets
    rows=[]
    for symbol in markets:
        doc=live.latest(db,symbol)
        qa=live.audit_market(doc,timestamp)
        px=live.price_view(doc,timestamp,quality=qa) if doc else None
        reason=("price_present" if px is not None
                else live.price_exclusion(doc,timestamp,quality=qa))
        row,_=universe.prepare(
            db,symbol=symbol,scan_at=stamp(timestamp),observed_document=doc,
            quality=qa,price_result=px,price_reason=reason,
            clock=timestamp+timedelta(seconds=2))
        rows.append(row)
    return rows


class CompactLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"private-synthetic.sqlite"
        self.db=make_db(self.path)

    def tearDown(self):
        self.db.close()

    def _full(self,rows=None,*,when=NOW):
        if rows is None:
            rows=prepared(self.db)
        with self.db:
            self.db.execute("BEGIN")
            result=compact.seal(
                self.db,rows,full=True,clock=when+timedelta(seconds=6))
        return result,rows

    def test_34_genuine_price_prepared_records_lossless_and_digest_verified(self):
        result,rows=self._full()
        self.assertEqual(result["status"],"COMPACT_BATCH_SEALED")
        self.assertEqual(result["storedMarkets"],34)
        self.assertEqual(result["eligiblePriceCandidates"],34)
        self.assertEqual(result["unverifiableMarketObservations"],0)
        self.assertTrue(result["isFullMarketDenominator"])
        self.assertTrue(result["noCotFiltering"])
        self.assertEqual(result["brokerCalls"],0)
        self.assertFalse(result["alertsEnabled"])
        census=compact.summary(self.db)
        self.assertEqual(census["fullScanBatches"],1)
        self.assertEqual(census["fullScanDenominator"],34)
        self.assertEqual(census["fullScanPriceCandidates"],34)
        self.assertEqual(census["targetedScansExcludedFromMainDenominator"],0)
        self.assertGreater(census["theoreticalFullScanDaysAt15Min"],1000)
        self.assertLess(result["compressedBytes"],result["uncompressedBytes"])
        self.assertLess(result["compressedBytes"],4096)
        row=self.db.execute(
            "SELECT payload_zlib,payload_sha256 FROM research_price_only_batches"
        ).fetchone()
        payload=compact._decode(*row)
        self.assertEqual(payload["schema"],compact.SCHEMA)
        self.assertEqual(payload["observations"],sorted(
            [list(x) for x in rows],key=lambda x:x[0]))
        self.assertEqual(compact.verify(
            self.db,scan_slot=rows[0][1])["marketObservations"],34)
        public=json.dumps(result)+json.dumps(census)
        self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",public)
        self.assertNotIn("1.01",public)
        self.assertNotIn("099741",public)
        self.assertFalse(census["profitabilityVerified"])

    def test_incomplete_full_scan_never_misrepresents_denominator(self):
        rows=prepared(self.db)
        with self.assertRaisesRegex(ValueError,"full_scan_must_contain_34_markets"):
            self._full(rows[:-1])
        self.assertEqual(compact.summary(self.db)["fullScanDenominator"],0)

    def test_failed_original_observation_is_explicit_unknown_not_missing_row(self):
        rows=prepared(self.db)
        failed=rows.pop()
        placeholder=compact.missing_row(
            symbol=failed[0],scan_at=stamp(NOW),
            clock=NOW+timedelta(seconds=2))
        rows.append(placeholder)
        result,_=self._full(rows)
        self.assertEqual(result["unverifiableMarketObservations"],1)
        self.assertEqual(result["eligiblePriceCandidates"],33)
        counts=compact.summary(self.db)
        self.assertEqual(counts["fullScanDenominator"],34)
        self.assertEqual(counts["fullScanUnknowns"],1)
        self.assertEqual(compact.verify(
            self.db,scan_slot=rows[0][1])["unknownObservations"],1)

    def test_duplicate_slot_immutable_even_if_second_payload_changes(self):
        result,rows=self._full()
        original=self.db.execute(
            "SELECT payload_sha256 FROM research_price_only_batches"
        ).fetchone()[0]
        with self.db:
            self.db.execute("BEGIN")
            changed=compact.seal(
                self.db,rows,full=True,clock=NOW+timedelta(seconds=7))
        self.assertEqual(changed["status"],"DUPLICATE_BATCH")
        self.assertEqual(compact.summary(self.db)["immutableBatches"],1)
        self.assertEqual(original,self.db.execute(
            "SELECT payload_sha256 FROM research_price_only_batches"
        ).fetchone()[0])

    def test_targeted_scan_separate_from_full_and_not_double_counted(self):
        rows=prepared(self.db)
        self._full(rows)
        with self.db:
            self.db.execute("BEGIN")
            targeted=compact.seal(
                self.db,rows[:2],full=False,
                clock=NOW+timedelta(seconds=6))
        self.assertEqual(targeted["storedMarkets"],2)
        self.assertFalse(targeted["isFullMarketDenominator"])
        state=compact.summary(self.db)
        self.assertEqual(state["immutableBatches"],2)
        self.assertEqual(state["fullScanBatches"],1)
        self.assertEqual(state["fullScanDenominator"],34)
        self.assertEqual(state["targetedScansExcludedFromMainDenominator"],1)

    def test_append_only_sqlite_triggers_and_corrupt_blob_detection(self):
        self._full()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "DELETE FROM research_price_only_batches")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE research_price_only_batches SET eligible_count=99")
        # Deliberate tampering only on synthetic fixture after removing a
        # test-only trigger. A production writer has no such control.
        self.db.execute("DROP TRIGGER research_compact_no_update")
        self.db.execute(
            "UPDATE research_price_only_batches SET payload_zlib=?",
            (sqlite3.Binary(b"broken"),))
        with self.assertRaises(ValueError):
            compact.verify(self.db,scan_slot=compact._slot(stamp(NOW)))

    def test_metadata_tampering_is_rejected(self):
        rows=prepared(self.db)
        self._full(rows)
        self.db.execute("DROP TRIGGER research_compact_no_update")
        self.db.execute(
            "UPDATE research_price_only_batches SET eligible_count=0")
        with self.assertRaisesRegex(ValueError,"archive_metadata_mismatch"):
            compact.verify(self.db,scan_slot=rows[0][1])

    def test_capacity_exhaustion_fails_closed_without_deleting_evidence(self):
        from unittest.mock import patch
        with patch.object(compact,"MAX_BATCHES",0):
            with self.assertRaisesRegex(ValueError,"compact_batch_capacity_reached"):
                self._full()
            info=compact.summary(self.db)
            self.assertTrue(info["capacityExhausted"])
            self.assertEqual(info["remainingBatchCapacity"],0)
            self.assertEqual(info["fullScanDenominator"],0)
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute("SELECT 1 FROM research_price_only_universe")

    def test_historical_and_future_backfill_not_accepted(self):
        rows=prepared(self.db)
        with self.assertRaisesRegex(ValueError,"batch_not_current"):
            self._full(rows,when=NOW+timedelta(days=3))
        self.assertEqual(compact.summary(self.db)["fullScanDenominator"],0)

    def test_duplicate_symbol_and_extraneous_market_rejected(self):
        rows=prepared(self.db)
        with self.assertRaisesRegex(ValueError,"duplicate_market_in_batch"):
            self._full([rows[0],*rows[0:33]])
        malformed=list(rows)
        wrong=list(rows[0])
        wrong[0]="SECRET_BROKER_NAME"
        malformed[0]=wrong
        with self.assertRaises(ValueError):
            self._full(malformed)

    def test_archive_compression_is_bounded_against_tampering(self):
        with self.assertRaises(ValueError):
            compact._decode(b"bad", "0"*64)
        with self.assertRaises(ValueError):
            compact._decode(b"not-zlib"*20000, "0"*64)

    def test_research_table_not_created_by_compact_store(self):
        self._full()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_universe'").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_batches'").fetchone()[0],1)


if __name__=="__main__":
    unittest.main()
