"""REMURA Track B: real Squalincome adapter is OFF by default and COT-independent.

These are synthetic fixtures on disposable SQLite files. Verify unchanged
LIVE entrypoint and full 34-market opt-in BEFORE COT query, same connection,
no additional source/API queries, no output secrets and failure visibility.
"""
from __future__ import annotations

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
from scripts import shark_price_only_universe as research
from test_shark_staging_scan import fixture,clone,standard_state,NOW


class OptInScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.default=Path(self.tmp.name)/"default.sqlite"
        self.research=Path(self.tmp.name)/"research.sqlite"
        fixture(self.default)
        clone(self.default,self.research)

    def _scan(self, path=None, now=NOW, *, targets=None):
        with patch.object(witness,"_clock",return_value=now+timedelta(seconds=2)):
            return live.scan_once_with_price_only_research(
                self.research if path is None else path,now,targets=targets)

    def test_default_scan_has_no_research_import_table_or_changed_behavior(self):
        normal=live.scan_once(self.default,NOW)
        with sqlite3.connect(self.default) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE name='research_price_only_universe'").fetchone()[0],0)
        experimental=self._scan()
        self.assertEqual({k:v for k,v in experimental.items()
                          if k!="priceOnlyResearch"},normal)
        self.assertEqual(standard_state(self.research),
                         standard_state(self.default))
        self.assertEqual(experimental["priceOnlyResearch"]["marketsAttempted"],34)
        self.assertEqual(experimental["priceOnlyResearch"]["extraBrokerRequests"],0)
        with sqlite3.connect(self.research) as db:
            values=research.summary(db)
            self.assertEqual(values["totalScans"],34)
            self.assertEqual(values["byState"]["PRICE_CONTEXT_READY"],1)
            self.assertEqual(values["byState"]["PRICE_QUALITY_BLOCKED"],33)

    def test_price_only_writes_before_cot_reader_even_if_cot_fails(self):
        with patch.object(live,"cot_series",side_effect=ValueError("missing Cot")) as cot:
            out=self._scan(targets=("EURUSD",))
        self.assertEqual(cot.call_count,1)
        self.assertEqual(out["examined"],0)
        self.assertEqual(out["priceOnlyResearch"]["marketsAttempted"],1)
        self.assertEqual(out["priceOnlyResearch"]["byState"]["PRICE_CONTEXT_READY"],1)
        with sqlite3.connect(self.research) as db:
            self.assertEqual(research.summary(db)["totalScans"],1)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_last_scan").fetchone()[0],0)

    def test_one_price_view_per_market_and_no_extra_cot_or_broker_calls(self):
        original_view=live.price_view
        original_cot=live.cot_series
        original_latest=live.latest
        original_audit=live.audit_market
        calls={"price":0,"cot":0,"latest":0,"audit":0}
        def observed_price(*args,**kwargs):
            calls["price"]+=1
            return original_view(*args,**kwargs)
        def observed_cot(*args,**kwargs):
            calls["cot"]+=1
            return original_cot(*args,**kwargs)
        def observed_latest(*args,**kwargs):
            calls["latest"]+=1
            return original_latest(*args,**kwargs)
        def observed_audit(*args,**kwargs):
            calls["audit"]+=1
            return original_audit(*args,**kwargs)
        with patch.object(live,"price_view",side_effect=observed_price):
            with patch.object(live,"cot_series",side_effect=observed_cot):
                with patch.object(live,"latest",side_effect=observed_latest):
                    with patch.object(live,"audit_market",side_effect=observed_audit):
                        out=self._scan()
        # Legacy scanner deliberately skips price_view(None) for 33 markets;
        # it must NOT be called an extra time by the research adapter.
        self.assertEqual(calls,{"price":1,"cot":34,"latest":34,"audit":34})
        self.assertEqual(out["priceOnlyResearch"]["marketsAttempted"],34)
        self.assertFalse(out["priceOnlyResearch"]["cotFilterAppliedToResearch"])

    def test_repeated_scans_are_deduplicated_without_legacy_changes(self):
        self._scan()
        live.scan_once(self.default,NOW)
        second=self._scan()
        live.scan_once(self.default,NOW)
        self.assertEqual(second["priceOnlyResearch"]["byState"]
                         .get("DUPLICATE_SCAN_SLOT"),34)
        # The normal scan updates its diagnostic summary after the first
        # baseline (newBaselines switches 1 -> 0). Compare like-for-like
        # after TWO scans instead of incorrectly claiming it is immutable.
        self.assertEqual(standard_state(self.research),
                         standard_state(self.default))
        with sqlite3.connect(self.research) as db:
            self.assertEqual(research.summary(db)["totalScans"],34)

    def test_targeted_scan_does_not_replace_full_scan_diagnostics(self):
        first=self._scan()
        with sqlite3.connect(self.research) as db:
            summary_before=db.execute(
                "SELECT summary FROM squalincome_last_scan").fetchone()[0]
        second=self._scan(now=NOW+timedelta(minutes=5),targets=("EURUSD",))
        self.assertEqual(second["priceOnlyResearch"]["marketsAttempted"],1)
        with sqlite3.connect(self.research) as db:
            summary_after=db.execute(
                "SELECT summary FROM squalincome_last_scan").fetchone()[0]
            self.assertEqual(summary_before,summary_after)
            self.assertEqual(research.summary(db)["totalScans"],34)

    def test_missing_cot_on_entire_full_34_priced_universe(self):
        # Every market has complete synthetic OHLC and no COT source rows.
        second=Path(self.tmp.name)/"all_prices_no_cot.sqlite"
        fixture(second,with_cot=False,all_priced=True)
        with patch.object(witness,"_clock",return_value=NOW+timedelta(seconds=2)):
            result=live.scan_once_with_price_only_research(second,NOW)
        self.assertEqual(result["examined"],0)
        self.assertEqual(result["priceOnlyResearch"]["marketsAttempted"],34)
        self.assertEqual(result["priceOnlyResearch"]["byState"]["PRICE_CONTEXT_READY"],34)
        with sqlite3.connect(second) as db:
            self.assertEqual(research.summary(db)["totalScans"],34)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
            record=db.execute(
                "SELECT * FROM research_price_only_universe").fetchall()
        data=json.dumps(record)
        self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",data)
        self.assertNotIn("099741",data)

    def test_fair_34_market_4000_bar_benchmark_without_one_sided_profiler(self):
        # Instrumented and legacy scans have the SAME 34 x 4000 M15
        # synthetic local database. Neither uses tracemalloc, COT or HTTP.
        # This is not actual Oracle CPU/RSS/broker usage.
        large_original=Path(self.tmp.name)/"fair_baseline.sqlite"
        large_research=Path(self.tmp.name)/"fair_research.sqlite"
        fixture(large_original,with_cot=False,all_priced=True,m15_count=4000)
        clone(large_original,large_research)
        started=time.perf_counter()
        reference=live.scan_once(large_original,NOW)
        base_seconds=time.perf_counter()-started
        with patch.object(witness,"_clock",
                          return_value=NOW+timedelta(seconds=2)):
            started=time.perf_counter()
            enabled=live.scan_once_with_price_only_research(
                large_research,NOW)
            enabled_seconds=time.perf_counter()-started
        self.assertEqual(
            {k:v for k,v in enabled.items() if k!="priceOnlyResearch"},
            reference)
        self.assertEqual(standard_state(large_original),
                         standard_state(large_research))
        self.assertEqual(reference["examined"],0)
        self.assertEqual(
            enabled["priceOnlyResearch"]["byState"]["PRICE_CONTEXT_READY"],34)
        with sqlite3.connect(large_research) as db:
            self.assertEqual(research.summary(db)["totalScans"],34)
            size_enabled=(db.execute("PRAGMA page_count").fetchone()[0]*
                          db.execute("PRAGMA page_size").fetchone()[0])
        with sqlite3.connect(large_original) as db:
            size_base=(db.execute("PRAGMA page_count").fetchone()[0]*
                       db.execute("PRAGMA page_size").fetchone()[0])
        overhead_kib=(size_enabled-size_base)/1024
        self.assertGreaterEqual(overhead_kib,0)
        self.assertLess(overhead_kib,512)
        self.assertLess(enabled_seconds,60)
        print("REMURA_TRACK_B_OPTIN_FAIR4000="+json.dumps({
            "markets":34,"m15BarsPerMarket":4000,"cotReports":0,
            "baselineSeconds":round(base_seconds,3),
            "optinSeconds":round(enabled_seconds,3),
            "additionalSqliteKiB":round(overhead_kib,2),
            "profilerOnEitherScan":False,
            "brokerCallsAdded":0,"actualOracleResourcesMeasured":False,
            "profitabilityEstablished":False
        },sort_keys=True,separators=(",",":")))

    def test_db_failure_raises_in_optin_and_is_not_converted_to_ND(self):
        with patch.object(research,"capture_optional",
                          side_effect=sqlite3.OperationalError("DB_CONSTRAINT")):
            with self.assertRaisesRegex(sqlite3.OperationalError,"DB_CONSTRAINT"):
                self._scan(targets=("EURUSD",))
        with sqlite3.connect(self.research) as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_legacy_entrypoint_and_h1_entrypoint_are_still_present(self):
        # No query string/environment var silently opts the LIVE scanner in.
        self.assertEqual(live.scan_once.__name__,"scan_once")
        self.assertEqual(live.scan_once_with_h1_frames.__name__,
                         "scan_once_with_h1_frames")
        self.assertTrue(callable(live.scan_once_with_price_only_research))


if __name__=="__main__":
    unittest.main()
