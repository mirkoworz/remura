"""Synthetic end-to-end staging rehearsal with actual v1.62 Squalincome scan.

Runs *unmodified* signals_monitor.scan_once on two independent SQLite files:
(A) baseline and (B) a separately instrumented scan. Instrumentation is ONLY
a test-scoped classify hook that records price-only data before original
classification; no production backend import or monkeypatch is persisted.

The 34-market denominator is verified with no COT for 33 markets. The one
valid EURUSD report is paired with a synthetic, genuinely constructed trend.
This is a SOFTWARE test, never an empirical trading benchmark or quote.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import tracemalloc
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import signals_monitor as live
from cot_monitor import ensure_table as ensure_cot
from price_feed import market_document
from price_store import connect, latest as live_latest, audit_market as live_audit
from scripts import shark_price_only_universe as universe

UTC=timezone.utc
NOW=datetime(2026,11,4,11,16,tzinfo=UTC)
END=datetime(2026,11,4,11,0,tzinfo=UTC)


def stamp(when):
    return when.isoformat().replace("+00:00","Z")


def fixture(path, *, with_cot=True, all_priced=False, m15_count=1024):
    db=connect(path)
    live.ensure_tables(db)
    ensure_cot(db)
    m15=[]
    for i in range(m15_count):
        started=END-timedelta(minutes=15*(m15_count-i))
        op=1.01+i*0.00004
        cl=op+0.000025
        m15.append({"t":stamp(started),"o":op,"h":cl+0.00001,
                    "l":op-0.00001,"c":cl,"v":101})
    targets=live.monitored_symbols() if all_priced else ("EURUSD",)
    for symbol in targets:
        broker="SYNTHETIC_PRIVATE_BROKER"
        doc=market_document(symbol,"ctrader",broker,m15,NOW)
        db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",
                   (symbol,"ctrader",broker,doc["lastComplete"],
                    json.dumps(doc,separators=(",",":"))))
    if with_cot:
        for week,manager in (("2026-10-20",120.0),("2026-10-27",160.0)):
            db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                       ("tff","099741",week,1000.0,100.0,90.0,manager,110.0))
    db.commit()
    db.close()


def clone(source,destination):
    with sqlite3.connect(source) as db,sqlite3.connect(destination) as out:
        db.backup(out)


def standard_state(path):
    with sqlite3.connect(path) as db:
        return {
            name: db.execute("SELECT * FROM "+name+" ORDER BY rowid").fetchall()
            for name in ("squalincome_history","squalincome_observations",
                         "squalincome_events","squalincome_last_scan")
        }


def staged_scan(path, when=NOW):
    """Apply the staging observer before LIVE classify, without editing LIVE."""
    states=[]
    current={}
    original_classify=live.classify

    def get_document(db,symbol):
        doc=live_latest(db,symbol)
        current.clear()
        current.update(symbol=symbol,document=doc)
        return doc

    def audit(doc,at):
        q=live_audit(doc,at)
        current["quality"]=q
        return q

    def classified(cot,price):
        # This hook is in the TEST ONLY. It is called once for every market
        # in _scan_once AFTER price_view() but BEFORE classify() decides
        # whether the COT is accepted. No COT data enters capture().
        if not current.get("symbol") or "quality" not in current:
            raise AssertionError("original_scan_context_missing")
        doc=current["document"]
        reason=("price_present" if price is not None
                else live.price_exclusion(doc,when,quality=current["quality"]))
        with sqlite3.connect(path,timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            out=universe.capture_optional(
                db,symbol=current["symbol"],scan_at=stamp(when),
                observed_document=doc,quality=current["quality"],
                price_result=price,price_reason=reason,
                clock=when+timedelta(seconds=2))
        states.append(out["status"])
        return original_classify(cot,price)

    with ExitStack() as stack:
        stack.enter_context(patch.object(live,"latest",side_effect=get_document))
        stack.enter_context(patch.object(live,"audit_market",side_effect=audit))
        stack.enter_context(patch.object(live,"classify",side_effect=classified))
        original=live.scan_once(path,when)
    return original,states


class StagingScanTests(unittest.TestCase):
    def test_normal_34_market_scan_unchanged_by_independent_price_recording(self):
        with tempfile.TemporaryDirectory() as root:
            original=Path(root)/"baseline.sqlite"
            stage=Path(root)/"instrumented.sqlite"
            fixture(original)
            clone(original,stage)
            with sqlite3.connect(stage) as db:
                universe.ensure_schema(db)

            start=time.perf_counter()
            original_out=live.scan_once(original,NOW)
            baseline_seconds=time.perf_counter()-start
            original_tables=standard_state(original)
            self.assertEqual(original_out["baselines"],1)
            self.assertEqual(original_out["newEvents"],0)
            self.assertEqual(original_out["examined"],1)

            tracemalloc.start()
            try:
                started=time.perf_counter()
                stage_out,states=staged_scan(stage,NOW)
                elapsed=time.perf_counter()-started
                _,peak=tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(stage_out,original_out)
            self.assertEqual(standard_state(stage),original_tables)
            self.assertEqual(len(states),len(live.monitored_symbols()))
            self.assertEqual(len(states),34)
            self.assertNotIn("PRICE_UNIVERSE_NOT_RECORDED",states)
            with sqlite3.connect(stage) as db:
                census=universe.summary(db)
                self.assertEqual(census["totalScans"],34)
                self.assertEqual(census["byState"]["PRICE_CONTEXT_READY"],1)
                self.assertEqual(census["byState"]["PRICE_QUALITY_BLOCKED"],33)
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM research_price_only_universe "
                    "WHERE state='PRICE_CONTEXT_READY' AND symbol='EURUSD'"
                ).fetchone()[0],1)
                # No raw quotes or broker names in NEW evidence table.
                evidence=db.execute(
                    "SELECT * FROM research_price_only_universe").fetchall()
                serialized=json.dumps(evidence)
                self.assertNotIn("SYNTHETIC_PRIVATE_BROKER",serialized)
                self.assertNotIn("1.01",serialized)
                self.assertNotIn("099741",serialized)
                pages=db.execute("PRAGMA page_count").fetchone()[0]
                page_size=db.execute("PRAGMA page_size").fetchone()[0]
                stage_allocated=pages*page_size
                self.assertLess(stage_allocated,8*1024*1024)
            with sqlite3.connect(original) as baseline_db:
                baseline_allocated=(
                    baseline_db.execute("PRAGMA page_count").fetchone()[0]
                    *baseline_db.execute("PRAGMA page_size").fetchone()[0]
                )
            # 34 synthetic scan records, no price duplications or SQLite
            # service additions: the delta is a CI-only page-allocation bound.
            self.assertLess(stage_allocated-baseline_allocated,512*1024)
            # Synthetic GitHub-runner guards only, not Oracle capacity claims.
            self.assertLess(peak,96*1024*1024)
            self.assertLess(elapsed,8.0)
            self.assertGreaterEqual(baseline_seconds,0.0)
            # Public synthetic CI numbers ONLY: tracemalloc measures traced
            # Python allocations, NOT real resident memory or Oracle billing.
            print("REMURA_TRACK_B_SYNTHETIC_STAGE_METRICS="+json.dumps({
                "markets":len(states),
                "baselineSeconds":round(baseline_seconds,4),
                "instrumentedSeconds":round(elapsed,4),
                "incrementalSqliteKiB":round(
                    (stage_allocated-baseline_allocated)/1024,2),
                "tracedPeakMiB":round(peak/(1024*1024),3),
                "runnerOnlyNotOracleMeasurements":True,
                "realTradingEdgeProven":False,
            },sort_keys=True,separators=(",",":")))

            # Repeat unchanged source in SAME scan slot: same LIVE observation
            # and same 34 research rows; originals still byte-wise equivalent.
            repeat_base=live.scan_once(original,NOW)
            repeat_stage,repeated=staged_scan(stage,NOW)
            self.assertEqual(repeat_stage,repeat_base)
            self.assertEqual(standard_state(stage),standard_state(original))
            self.assertEqual(repeated.count("DUPLICATE_SCAN_SLOT"),34)
            with sqlite3.connect(stage) as db:
                self.assertEqual(universe.summary(db)["totalScans"],34)

    def test_full_34_market_ohlc_stress_without_cot_is_not_false_signal(self):
        # All 34 have complete 1024-M15 OHLC + H1/H4. Unlike the lean
        # rehearsal, this stresses JSON decoding, source hashes and rollups.
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)/"large_baseline.sqlite"
            staged=Path(root)/"large_stage.sqlite"
            fixture(base,with_cot=False,all_priced=True)
            clone(base,staged)
            with sqlite3.connect(staged) as db:
                universe.ensure_schema(db)
            self.assertGreater(base.stat().st_size,1024*1024)
            started=time.perf_counter()
            baseline=live.scan_once(base,NOW)
            baseline_seconds=time.perf_counter()-started
            tracemalloc.start()
            try:
                begun=time.perf_counter()
                instrumented,results=staged_scan(staged,NOW)
                elapsed=time.perf_counter()-begun
                _,peak=tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(instrumented,baseline)
            self.assertEqual(standard_state(staged),standard_state(base))
            self.assertEqual(baseline["examined"],0)  # no COT at all
            self.assertEqual(len(results),34)
            self.assertEqual(results.count("PRICE_CONTEXT_READY"),34)
            with sqlite3.connect(staged) as db:
                self.assertEqual(universe.summary(db)["totalScans"],34)
                self.assertEqual(
                    universe.summary(db)["byState"]["PRICE_CONTEXT_READY"],34)
                stage_size=(
                    db.execute("PRAGMA page_count").fetchone()[0]
                    *db.execute("PRAGMA page_size").fetchone()[0])
            with sqlite3.connect(base) as db:
                base_size=(
                    db.execute("PRAGMA page_count").fetchone()[0]
                    *db.execute("PRAGMA page_size").fetchone()[0])
            delta=stage_size-base_size
            self.assertGreaterEqual(delta,0)
            self.assertLess(delta,512*1024)
            self.assertLess(peak,128*1024*1024)
            self.assertLess(elapsed,45)
            print("REMURA_TRACK_B_SYNTHETIC_FULL34_METRICS="+json.dumps({
                "markets":34,"completeM15BarsPerMarket":1024,
                "cotReportRows":0,"priceOnlyCandidates":34,
                "baselineSeconds":round(baseline_seconds,4),
                "instrumentedSeconds":round(elapsed,4),
                "incrementalSqliteKiB":round(delta/1024,2),
                "tracedPeakMiB":round(peak/(1024*1024),3),
                "runnerOnlyNotOracleMeasurements":True,
                "realTradingEdgeProven":False
            },sort_keys=True,separators=(",",":")))

    def test_no_cot_reports_still_registers_price_only_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"no-cot.sqlite"
            fixture(path,with_cot=False)
            with sqlite3.connect(path) as db:
                universe.ensure_schema(db)
            legacy,states=staged_scan(path)
            self.assertEqual(legacy["examined"],0)
            self.assertEqual(legacy["baselines"],0)
            self.assertEqual(states.count("PRICE_CONTEXT_READY"),1)
            with sqlite3.connect(path) as db:
                self.assertEqual(universe.summary(db)["totalScans"],34)
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

if __name__=="__main__":
    unittest.main()
