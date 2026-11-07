"""REMURA Track B: one-pass periodic feature gate, OFF in all LIVE defaults.

Verifies that the production periodic loop calls ONE Squalincome scanner:
legacy unless TWO explicit research values match exactly. No second polling
thread, broker API, schema migration or data access to LIVE. The post-ingest
path and H1 paired logic remain v1.62 behavior.

An actual compact scan is exercised only against synthetic SQLite fixtures.
"""
from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

import private_server as server
import signals_monitor as scanner
from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact
from scripts import shark_first_invocation as first_gate
from test_shark_staging_scan import fixture, clone, standard_state, NOW

ON={
    "REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1",
    "REMURA_SHARK_COMPACT_RESEARCH_ACK":"ACK_UNVALIDATED_PROSPECTIVE_RESEARCH",
}


class PeriodicSinglePassTests(unittest.TestCase):
    def test_default_and_partial_gates_leave_existing_scan_alone(self):
        inert=(
            {},
            {"REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1"},
            {"REMURA_SHARK_COMPACT_RESEARCH_ACK":ON[
                "REMURA_SHARK_COMPACT_RESEARCH_ACK"]},
            {"REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"true",
             "REMURA_SHARK_COMPACT_RESEARCH_ACK":ON[
                 "REMURA_SHARK_COMPACT_RESEARCH_ACK"]},
            {"REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1",
             "REMURA_SHARK_COMPACT_RESEARCH_ACK":"yes"},
            {"REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"0",
             "REMURA_SHARK_COMPACT_RESEARCH_ACK":ON[
                 "REMURA_SHARK_COMPACT_RESEARCH_ACK"]},
        )
        for values in inert:
            with self.subTest(env=values):
                with patch.object(server,"observe_squalincome",
                                  return_value={"legacy":True}) as legacy:
                    with patch.object(
                            scanner,"scan_once_with_compact_price_only_research",
                            side_effect=AssertionError("unexpected_research")) as research:
                        self.assertEqual(server.observe_periodic_squalincome(
                            "a-disposable-path",env=values),{"legacy":True})
                legacy.assert_called_once_with("a-disposable-path")
                research.assert_not_called()

    def test_exact_two_flags_route_to_research_once_without_legacy_scan(self):
        with patch.object(server,"observe_squalincome",
                          side_effect=AssertionError("duplicate_scan")) as legacy:
            with patch.object(
                    first_gate,"first_invocation",
                    return_value={"status":"FIRST_INVOCATION_WITNESSED"}) as activation:
                with patch.object(
                        scanner,"scan_once_with_compact_price_only_research",
                        return_value={"research":True}) as research:
                    self.assertEqual(server.observe_periodic_squalincome(
                        "test.sqlite",env=ON),{"research":True})
        activation.assert_called_once_with("test.sqlite")
        research.assert_called_once_with("test.sqlite")
        legacy.assert_not_called()

    def test_witness_failure_blocks_research_without_legacy_fallback(self):
        with patch.object(first_gate,"first_invocation",
                          side_effect=sqlite3.OperationalError("database is locked")):
            with patch.object(server,"observe_squalincome") as old:
                with patch.object(
                        scanner,"scan_once_with_compact_price_only_research") as new:
                    with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                        server.observe_periodic_squalincome("test.sqlite",env=ON)
        old.assert_not_called()
        new.assert_not_called()

    def test_real_synthetic_single_pass_preserves_all_legacy_tables(self):
        with tempfile.TemporaryDirectory(prefix="remura-route-") as scratch:
            baseline=Path(scratch)/"legacy.sqlite"
            routed=Path(scratch)/"research.sqlite"
            fixture(baseline,with_cot=True,all_priced=True,m15_count=1024)
            clone(baseline,routed)
            with patch.object(scanner,"utcnow",return_value=NOW):
                legacy=server.observe_periodic_squalincome(
                    baseline,env={})
                with patch.object(
                        witness,"_clock",
                        return_value=NOW+timedelta(seconds=2)):
                    optimized=server.observe_periodic_squalincome(
                        routed,env=ON)
            self.assertEqual(
                {k:v for k,v in optimized.items() if k!="priceOnlyResearch"},
                legacy)
            self.assertEqual(standard_state(baseline),standard_state(routed))
            with sqlite3.connect(baseline) as db:
                self.assertFalse(db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name=?",
                    (compact.TABLE,)).fetchone())
                self.assertIsNone(first_gate.read(db))
            with sqlite3.connect(routed) as db:
                activation=first_gate.read(db)
                self.assertIsNotNone(activation)
                self.assertEqual(activation, witness._iso(NOW+timedelta(seconds=2)))
                snapshot=compact.summary(db)
                self.assertEqual(snapshot["fullScanDenominator"],34)
                self.assertEqual(snapshot["immutableBatches"],1)
                self.assertEqual(db.execute(
                    "PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(
                optimized["priceOnlyResearch"]["extraBrokerRequests"],0)
            self.assertFalse(
                optimized["priceOnlyResearch"]["alertsEnabled"])

    def test_post_ingest_keeps_existing_targeted_scanner_even_when_flagged(self):
        options={
            **ON,
            "REMURA_SQUALINCOME_AFTER_INGEST_ENABLED":"1",
            "REMURA_SQUALINCOME_MONITOR_ENABLED":"1",
            "REMURA_COLLECTOR_ENABLED":"1",
            "REMURA_COT_SYNC_ENABLED":"1",
        }
        with patch.object(server,"observe_squalincome",
                          return_value={"examined":0,"newEvents":0}) as legacy:
            with patch.object(
                    scanner,"scan_once_with_compact_price_only_research",
                    side_effect=AssertionError("research_must_not_run")) as research:
                with patch.object(server,"record_scan_timing"):
                    with patch.object(server,"h1_paired_enabled",return_value=False):
                        result=server.observe_updated_batch(
                            "synthetic-path",["EURUSD"],env=options,
                            batch_completed=NOW)
        self.assertEqual(result,{"examined":0,"newEvents":0})
        legacy.assert_called_once_with(
            "synthetic-path",targets=("EURUSD",))
        research.assert_not_called()

    def test_periodic_loop_calls_exactly_one_selected_observer(self):
        class Once:
            checked=0
            def is_set(self):
                self.checked+=1
                return self.checked>1
            def wait(self,_):
                return True
        stop=Once()
        with patch.object(server,"observe_periodic_squalincome",
                          return_value={"examined":0,"newEvents":0}) as one:
            with patch.object(server,"record_scan_timing"):
                with patch.object(server,"update_validation") as validation:
                    with patch.object(server,"update_dual24") as dual:
                        server.squalincome_loop("test-path",stop)
        one.assert_called_once_with("test-path")
        validation.assert_called_once_with("test-path")
        dual.assert_called_once_with("test-path")


if __name__=="__main__":
    unittest.main()
