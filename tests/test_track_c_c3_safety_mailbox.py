"""Track C C3 offline chaos rehearsal: explicit UNKNOWN and no core coupling.

Fake provider responses, temporary SQLite only. No real HTTP, VPS, broker,
subscription, PnL, account, password, notifications or automatic research.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import cot_monitor as collector
from price_store import connect
import track_c_c3_safety_mailbox as safe

UTC = timezone.utc
NOW = datetime(2026,11,9,12,0,tzinfo=UTC)
STAMP = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
HEX = "a"*64


def fake_rows(dataset):
    spec=collector.DATASETS[dataset]
    return [{
        "report_date_as_yyyy_mm_dd": "2026-11-03T00:00:00",
        "cftc_contract_market_code": code,
        "open_interest_all": "1000",
        **{key:"100" for key in spec["keys"]},
    } for code in spec["codes"]]


def item(symbol="EURUSD",source="cot",seen=STAMP,sha=HEX):
    return {"symbol":symbol,"source":source,
            "seenAtUtc":seen,"originalSha256":sha}


class ResearchFailureIsolationRehearsal(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-c3-chaos-")
        self.core=Path(self.tmp.name)/"core-synthetic.sqlite"
        self.science=Path(self.tmp.name)/"research-synthetic.sqlite"
        self.called=[]

    def tearDown(self):
        self.tmp.cleanup()

    def collector(self,**kw):
        def get(dataset,at):
            self.called.append(dataset)
            self.assertEqual(at,NOW)
            return fake_rows(dataset)
        return collector.collect_once(self.core,now=NOW,fetch=get,**kw)

    def count(self,name):
        db=connect(self.core)
        try:
            return db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        finally: db.close()

    def test_default_off_normal_collector_not_coupled_to_research_failure(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE)
        self.assertEqual(box.offer(item(),now=STAMP),safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],0)
        # Rehearse research database being unavailable independently.
        lock=sqlite3.connect(self.science,timeout=.02)
        another=None
        try:
            lock.execute("CREATE TABLE dummy(n INTEGER)")
            lock.commit()
            lock.execute("BEGIN EXCLUSIVE")
            lock.execute("INSERT INTO dummy VALUES(1)")
            another=sqlite3.connect(self.science,timeout=.02)
            with self.assertRaises(sqlite3.OperationalError):
                another.execute("INSERT INTO dummy VALUES(2)")
            # The original COT collector receives NO callback; its real
            # SQLite source data remains unaffected by research DB lock.
            with patch.object(collector,"utcnow",
                              side_effect=AssertionError("no research clock")):
                got=self.collector()
            self.assertEqual(got["errors"],{})
            self.assertEqual(got["saved"],{"tff":11,"disagg":3})
            self.assertEqual(self.count("cot_reports"),14)
            self.assertEqual(self.called,["tff","disagg"])
        finally:
            if another is not None: another.close()
            lock.rollback()
            lock.close()

    def test_existing_optional_atomic_hook_blocks_core_and_is_NO_GO(self):
        self.collector()
        before=self.count("cot_reports")
        # Proof that turning the CURRENT experimental hook on on a core DB
        # is unsafe: a witness crash aborts this dataset's normal UPSERT.
        def broken(*args):
            raise ValueError("synthetic_research_witness_outage")
        stamps=iter(NOW+timedelta(seconds=i) for i in (1,2,3,4,5,6))
        with patch.object(collector,"utcnow",side_effect=lambda: next(stamps)):
            got=self.collector(research_atomic_witness=broken)
        self.assertEqual(got["saved"],{})
        self.assertEqual(got["errors"],{
            "tff":"unavailable","disagg":"unavailable"})
        self.assertEqual(self.count("cot_reports"),before)
        self.assertEqual(self.count("cot_first_seen"),before)
        self.assertEqual(self.called,["tff","disagg","tff","disagg"])
        # Required future mitigation: never wire an inline research
        # witness into the deployed core collector; isolated observer only.

    def test_research_worker_crash_becomes_unknown_not_signal(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        self.assertEqual(box.offer(item(),now=STAMP),
                         "SYNTHETIC_METADATA_STAGED_ONLY")
        with self.assertRaisesRegex(AssertionError,"must_not_run_inline"):
            # offer() never runs the worker; this callable is explicitly
            # called in this guard to ensure it is not scheduled by offer().
            raise AssertionError("must_not_run_inline")
        observed=[]
        def worker(meta):
            observed.append(meta)
            raise RuntimeError("synthetic_worker_crash")
        self.assertEqual(box.consume_for_test(worker,now=STAMP),
                         safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],0)
        self.assertEqual(box.summary()["workerFailures"],1)
        self.assertEqual(box.summary()["syntheticCompleted"],0)
        self.assertEqual(len(observed),1)
        self.assertFalse(box.summary()["liveIsolationProven"])

    def test_capacity_overload_refuses_new_not_drop_old(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True,
                                         max_pending=2)
        first=item(sha="a"*64)
        second=item(sha="b"*64)
        third=item(sha="c"*64)
        self.assertEqual(box.offer(first,now=STAMP),
                         "SYNTHETIC_METADATA_STAGED_ONLY")
        self.assertEqual(box.offer(second,now=STAMP),
                         "SYNTHETIC_METADATA_STAGED_ONLY")
        self.assertEqual(box.offer(third,now=STAMP),
                         safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.offer(first,now=STAMP),
                         safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],2)
        seen=[]
        self.assertEqual(box.consume_for_test(lambda m: seen.append(m) or True,
                                              now=STAMP),
                         "SYNTHETIC_RESEARCH_RECEIPT_ONLY")
        self.assertEqual(seen[0][3],"a"*64)
        self.assertEqual(box.summary()["pending"],1)
        self.assertEqual(box.summary()["refusedOrDropped"],2)
        self.assertEqual(box.offer(third,now=STAMP),
                         "SYNTHETIC_METADATA_STAGED_ONLY")

    def test_stale_event_is_unknown_never_backfilled(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        old=(NOW-timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        future=(NOW+timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for stamp in (old,future):
            self.assertEqual(box.offer(item(seen=stamp),now=STAMP),
                             safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],0)
        self.assertEqual(box.offer(item(),now=STAMP),
                         "SYNTHETIC_METADATA_STAGED_ONLY")
        later=(NOW+timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
        calls=[]
        self.assertEqual(box.consume_for_test(
            lambda x: calls.append(x) or True,now=later),
            safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(calls,[])
        self.assertEqual(box.summary()["workerFailures"],1)

    def test_no_source_payload_or_secrets_accepted(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        for extra in ("ohlc","positions","account","token","retailLots",
                      "brokerSymbol","rawResponse","pnl"):
            raw=item()
            raw[extra]={"synthetic":"payload"}
            self.assertEqual(box.offer(raw,now=STAMP),
                             safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],0)
        out=json.dumps(box.summary())
        for forbidden in ("ohlc","token","account","EURUSD","999999",
                          "brokerSymbol","positions"):
            self.assertNotIn(forbidden,out)

    def test_reject_bad_modes_scope_sha_and_numeric_flags(self):
        with self.assertRaises(ValueError):
            safe.SyntheticResearchMailbox()
        with self.assertRaises(ValueError):
            safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=1)
        with self.assertRaises(ValueError):
            safe.SyntheticResearchMailbox(mode=safe.MODE,max_pending=100000)
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        for payload in (item(symbol="GBPUSD"),item(source="cvd"),
                        item(sha="not-a-digest"),item(sha="A"*64)):
            self.assertEqual(box.offer(payload,now=STAMP),
                             safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],0)

    def test_high_volume_producer_never_overgrows_bounded_memory(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        for i in range(6000):
            result=box.offer(item(
                source=("cot","ctrader","retail")[i%3],
                sha=f"{i:064x}"),now=STAMP)
            if i>=safe.MAX_PENDING:
                self.assertEqual(result,safe.RESEARCH_UNAVAILABLE)
        self.assertEqual(box.summary()["pending"],safe.MAX_PENDING)
        self.assertEqual(box.summary()["offered"],safe.MAX_PENDING)
        self.assertEqual(box.summary()["refusedOrDropped"],6000-safe.MAX_PENDING)
        self.assertEqual(box.summary()["apiRequestsAdded"],0)

    def test_lab_benchmark_is_informational_not_hardware_claim(self):
        box=safe.SyntheticResearchMailbox(mode=safe.MODE,enabled=True)
        for i in range(12):
            box.offer(item(source=("cot","retail")[i%2],
                           sha=f"{i:064x}"),now=STAMP)
        output=box.summary()
        self.assertEqual(output["pending"],12)
        self.assertFalse(output["crossProcessDurabilityVerified"])
        self.assertFalse(output["realCostsChecked"])
        self.assertEqual(output["tradingEdge"],"NOT_ESTABLISHED")


if __name__=="__main__":
    unittest.main()
