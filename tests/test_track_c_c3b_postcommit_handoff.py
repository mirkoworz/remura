"""Track C3b-b: original committed SQLite core -> separate WAL shadow (LAB).

Synthetic COT and price inputs only. A read-only source snapshot is hashed
after the original source collector's COMMIT; there is NO provider request,
new LIVE hook, retail FIRST-SEEN implementation, backdated source clock,
cross-DB atomicity or true delivery guarantee.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import cot_monitor as cot
import price_store
from price_feed import iso, market_document
import track_c_c3b_durable_shadow as shadow
import track_c_c3b_postcommit_handoff as post

NOW=datetime(2026,11,9,12,tzinfo=timezone.utc)
READ="2026-11-09T12:00:00Z"
LATER="2026-11-09T12:00:04Z"


def feed(dataset):
    spec=cot.DATASETS[dataset]
    return [
        {"report_date_as_yyyy_mm_dd":week+"T00:00:00",
         "cftc_contract_market_code":code,
         "open_interest_all":"1000",
         **{key:("120" if week=="2026-11-03" else "100")
            for key in spec["keys"]}}
        for week in ("2026-10-27","2026-11-03")
        for code in spec["codes"]
    ]


def price_bundle(symbol):
    bars=[]
    start=NOW-timedelta(minutes=64*15)
    value=1900.0 if symbol=="XAUUSD" else 1.12
    for i in range(64):
        p=value+i*.0001
        bars.append({"t":iso(start+timedelta(minutes=15*i)),
                     "o":p,"h":p+.003,"l":p-.003,"c":p+.0001,"v":10})
    return {"schema":"remura-price-v1","generatedAt":iso(NOW),
            "markets":{symbol:{
                "symbol":symbol,"provider":"ctrader",
                "providerSymbol":"SYNTHETIC-TEST-"+symbol,
                "timeframes":{"M15":bars}}}}


class PostcommitIsolatedHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-c3b-")
        root=Path(self.tmp.name)
        self.core=root/post.CORE_FILE
        self.research=root/shadow.FILE
        shadow.prepare(self.research,mode=shadow.MODE)
        self.calls=[]
        def fake_download(dataset,at):
            self.calls.append(dataset)
            self.assertEqual(at,NOW)
            return feed(dataset)
        result=cot.collect_once(self.core,NOW,fetch=fake_download)
        self.assertEqual(result["errors"],{})
        self.assertEqual(self.calls,["tff","disagg"])
        db=price_store.connect(self.core)
        try:
            for sym in ("EURUSD","XAUUSD"):
                out=price_store.ingest(db,price_bundle(sym),now=NOW)
                self.assertEqual(out["errors"],{})
                self.assertIn(sym,out["saved"])
                self.assertGreater(len(price_store.latest(
                    db,sym)["timeframes"]["H4"]),0)
        finally:db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def deliver(self,symbol="EURUSD",source="cot",at=READ,enabled=True):
        return post.dispatch(
            self.core,self.research,symbol=symbol,source=source,
            read_at=at,enabled=enabled,mode=post.MODE)

    def counts(self):
        return shadow.inspect_lab(self.research,mode=shadow.MODE)

    def test_original_core_commits_then_four_independent_shadow_receipts(self):
        for symbol in ("EURUSD","XAUUSD"):
            for source in ("cot","ctrader"):
                self.assertEqual(self.deliver(symbol,source),post.STAGED)
        self.assertEqual(self.counts()["pending"],4)
        self.assertEqual(len(self.calls),2)  # no extra CFTC GET
        self.assertEqual(self.deliver(),post.UNKNOWN)  # persistent dedup
        seen=set()
        for _ in range(4):
            job=shadow.claim(self.research,at=LATER,enabled=True,mode=shadow.MODE)
            self.assertIsNotNone(job)
            seen.add((job["symbol"],job["source"]))
            self.assertTrue(post.check_lease_source(
                self.core,self.research,job=job,
                checked_at=LATER,enabled=True,mode=post.MODE))
            self.assertEqual(shadow.finish(
                self.research,item_id=job["id"],
                lease_token=job["leaseToken"],at=LATER,
                synthetic_worker_ok=True,enabled=True,mode=shadow.MODE),
                shadow.ACKED)
        self.assertEqual(seen,{
            ("EURUSD","cot"),("XAUUSD","cot"),
            ("EURUSD","ctrader"),("XAUUSD","ctrader")})
        self.assertEqual(self.counts()["syntheticAck"],4)
        self.assertEqual(self.counts()["pending"],0)
        self.assertFalse(self.counts()["realCollectorIsolationProven"])
        self.assertFalse(self.counts()["actualEdgeEstablished"])

    def test_no_read_before_original_core_commit(self):
        with tempfile.TemporaryDirectory(prefix="remura-c3b-") as dirname:
            missing_core=Path(dirname)/post.CORE_FILE
            other_shadow=Path(dirname)/shadow.FILE
            shadow.prepare(other_shadow,mode=shadow.MODE)
            writer=price_store.connect(missing_core)
            try:
                rows=price_bundle("EURUSD")["markets"]["EURUSD"]["timeframes"]["M15"]
                original=market_document(
                    "EURUSD","ctrader","SYNTHETIC",rows,NOW)
                writer.execute(
                    "INSERT INTO prices VALUES (?,?,?,?,?)",
                    ("EURUSD","ctrader","SYNTHETIC",
                     original["lastComplete"],json.dumps(original)))
                self.assertTrue(writer.in_transaction)
                self.assertEqual(post.dispatch(
                    missing_core,other_shadow,symbol="EURUSD",
                    source="ctrader",read_at=READ,enabled=True,
                    mode=post.MODE),post.UNKNOWN)
                self.assertEqual(shadow.inspect_lab(
                    other_shadow,mode=shadow.MODE)["total"],0)
                writer.commit()
                self.assertEqual(post.dispatch(
                    missing_core,other_shadow,symbol="EURUSD",
                    source="ctrader",read_at=READ,enabled=True,
                    mode=post.MODE),post.STAGED)
            finally:writer.close()

    def test_separate_python_process_dispatch_and_rechecks_original_core(self):
        """Proof of a separate research process in CI, NOT a live daemon."""
        child = """import sys
import track_c_c3b_postcommit_handoff as bridge
import track_c_c3b_durable_shadow as shadow
core,research=sys.argv[1:]
status=bridge.dispatch(core,research,symbol='EURUSD',source='cot',
                       read_at='2026-11-09T12:00:00Z',
                       enabled=True,mode=bridge.MODE)
assert status==bridge.STAGED
job=shadow.claim(research,at='2026-11-09T12:00:04Z',
                 enabled=True,mode=shadow.MODE)
assert job is not None
valid=bridge.check_lease_source(
    core,research,job=job,checked_at='2026-11-09T12:00:04Z',
    enabled=True,mode=bridge.MODE)
assert valid is True
ack=shadow.finish(research,item_id=job['id'],lease_token=job['leaseToken'],
                  at='2026-11-09T12:00:04Z',
                  synthetic_worker_ok=valid,enabled=True,mode=shadow.MODE)
assert ack==shadow.ACKED
print('SYNTHETIC_HANDOFF_OK')
"""
        environment={"PYTHONPATH":str(ROOT/"scripts"),
                     "PYTHONDONTWRITEBYTECODE":"1"}
        result=subprocess.run([sys.executable,"-c",child,
                               str(self.core),str(self.research)],
                              text=True,capture_output=True,timeout=15,
                              env=environment,check=False)
        self.assertEqual(result.returncode,0,
                         "independent offline subprocess handoff failed")
        self.assertEqual(result.stdout.strip(),"SYNTHETIC_HANDOFF_OK")
        self.assertEqual(self.counts()["syntheticAck"],1)
        self.assertEqual(self.counts()["pending"],0)
        self.assertEqual(self.calls,["tff","disagg"])

    def test_core_commit_without_dispatch_has_no_research_receipt(self):
        # A loss/crash after a core transaction and BEFORE the research
        # dispatcher is a genuine remaining gap: no automatic backfill.
        self.assertEqual(self.counts()["total"],0)
        self.assertEqual(self.counts()["syntheticAck"],0)
        self.assertIsNone(shadow.claim(
            self.research,at=READ,enabled=True,mode=shadow.MODE))
        db=price_store.connect(self.core)
        try:
            self.assertIsNotNone(price_store.latest(db,"EURUSD"))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM cot_reports").fetchone()[0],28)
        finally:
            db.close()
        self.assertEqual(self.counts()["total"],0)

    def test_core_revision_after_stage_is_rejected_by_worker(self):
        self.assertEqual(self.deliver("XAUUSD","cot"),post.STAGED)
        self.assertEqual(self.deliver("EURUSD","ctrader"),post.STAGED)
        db=price_store.connect(self.core)
        try:
            with db:
                db.execute("UPDATE cot_reports SET first_long=first_long+1 "
                           "WHERE dataset='disagg' AND code='088691' "
                           "AND report_date='2026-11-03'")
                obj=price_store.latest(db,"EURUSD")
                obj["timeframes"]["M15"][-1]["c"]+=.00001
                db.execute(
                    "UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                    (json.dumps(obj),))
        finally:db.close()
        for _ in range(2):
            job=shadow.claim(self.research,at=LATER,enabled=True,
                             mode=shadow.MODE)
            self.assertFalse(post.check_lease_source(
                self.core,self.research,job=job,checked_at=LATER,
                enabled=True,mode=post.MODE))
            self.assertEqual(shadow.finish(
                self.research,item_id=job["id"],
                lease_token=job["leaseToken"],at=LATER,
                synthetic_worker_ok=False,enabled=True,mode=shadow.MODE),
                shadow.UNKNOWN)
        self.assertEqual(self.counts()["unknown"],2)
        self.assertEqual(self.counts()["syntheticAck"],0)

    def test_locked_research_is_not_allowed_to_block_core_writes(self):
        blocker=sqlite3.connect(str(self.research),timeout=.025)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            blocker.execute("UPDATE c3b_schema_guard SET version=version")
            self.assertEqual(self.deliver(),post.UNKNOWN)
            core_db=price_store.connect(self.core)
            try:
                result=price_store.ingest(
                    core_db,price_bundle("EURUSD"),now=NOW)
                self.assertIn("EURUSD",result["saved"])
            finally:core_db.close()
            self.assertEqual(self.counts()["total"],0)
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(self.counts()["total"],0)
        self.assertEqual(self.deliver(),post.STAGED)

    def test_stale_or_future_price_close_cannot_be_laundered(self):
        late="2026-11-09T12:04:00Z"
        early="2026-11-09T11:59:00Z"
        self.assertEqual(self.deliver("EURUSD","ctrader",at=late),post.UNKNOWN)
        self.assertEqual(self.deliver("XAUUSD","ctrader",at=early),post.UNKNOWN)
        self.assertEqual(self.counts()["total"],0)

    def test_missing_source_and_retail_are_unknown(self):
        db=price_store.connect(self.core)
        try:
            with db:
                db.execute("DELETE FROM prices WHERE symbol='XAUUSD'")
        finally:db.close()
        self.assertEqual(self.deliver("XAUUSD","ctrader"),post.UNKNOWN)
        self.assertEqual(self.deliver("EURUSD","retail"),post.UNKNOWN)
        self.assertEqual(self.deliver("GBPUSD","cot"),post.UNKNOWN)
        self.assertEqual(self.counts()["total"],0)

    def test_future_clocks_old_data_and_disabled_gate_rejected(self):
        self.assertEqual(self.deliver(enabled=False),post.UNKNOWN)
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            post.dispatch(self.core,self.research,symbol="EURUSD",
                          source="cot",read_at=READ,enabled=True)
        # Historical source is available for reading, but NEVER mislabel
        # its original FIRST-SEEN time by this postcommit scanner.
        old="2026-10-24T12:00:00Z"
        self.assertEqual(self.deliver(at=old),post.UNKNOWN)
        self.assertEqual(self.counts()["total"],0)

    def test_mismatched_name_or_directory_cannot_open_live(self):
        with tempfile.TemporaryDirectory(prefix="remura-not-c3b-") as root:
            fake_core=Path(root)/post.CORE_FILE
            with self.assertRaisesRegex(ValueError,
                                        "must_use_separate_temp_synthetic_core"):
                post.dispatch(fake_core,self.research,
                              symbol="EURUSD",source="cot",
                              read_at=READ,enabled=True,mode=post.MODE)
        wrong=self.core.parent/"remura-prices.sqlite3"
        with self.assertRaisesRegex(ValueError,"must_use_separate_temp"):
            post.dispatch(wrong,self.research,symbol="EURUSD",
                          source="cot",read_at=READ,enabled=True,
                          mode=post.MODE)

    def test_shadow_only_has_digest_not_raw_ohlc_and_no_auto_schedulers(self):
        self.assertEqual(self.deliver("XAUUSD","ctrader"),post.STAGED)
        db=sqlite3.connect(str(self.research))
        try:
            names={x[1] for x in db.execute(
                f"PRAGMA table_info({shadow.TABLE})").fetchall()}
            self.assertEqual(names,{
                "id","symbol","source","source_seen","core_committed",
                "sha256","staged_at","state","lease_token",
                "lease_deadline","resolved_at"})
            self.assertNotIn("payload",names)
            self.assertNotIn("price",names)
            self.assertNotIn("account",names)
        finally:db.close()
        self.assertEqual(self.counts()["total"],1)


if __name__=="__main__":
    unittest.main()
