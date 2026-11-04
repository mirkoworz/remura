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

    def test_production_entrypoint_has_not_changed(self):
        self.assertEqual(live.scan_once.__name__,"scan_once")
        self.assertEqual(live.scan_once_with_h1_frames.__name__,
                         "scan_once_with_h1_frames")
        self.assertTrue(callable(live.scan_once_with_compact_price_only_research))


if __name__=="__main__":
    unittest.main()
