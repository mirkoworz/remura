"""Track C3b-c denominator: crash gap, no-replay and conservative UNKNOWN.

Only synthetic CFTC/ctrader fixtures. No real collector research hook,
no Myfxbook read, no live migration, no provider network or trading.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import cot_monitor as cot
import price_store
import track_c_c3b_durable_shadow as shadow
import track_c_c3b_postcommit_handoff as post
import track_c_c3bc_attempt_denominator as den
from test_track_c_c3b_postcommit_handoff import feed,price_bundle,NOW,READ


def aid(index):
    return hashlib.sha256(f"SYNTHETIC-SCAN-{index}".encode()).hexdigest()


class AttemptDenominatorOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="remura-c3b-")
        root=Path(self.temp.name)
        self.core=root/post.CORE_FILE
        self.research=root/shadow.FILE
        self.out=cot.collect_once(self.core,NOW,fetch=lambda dataset,now:feed(dataset))
        self.assertEqual(self.out["errors"],{})
        db=price_store.connect(self.core)
        try:
            for sym in ("EURUSD","XAUUSD"):
                self.assertIn(sym,price_store.ingest(
                    db,price_bundle(sym),now=NOW)["saved"])
        finally:db.close()
        shadow.prepare(self.research,mode=shadow.MODE)
        den.prepare_core(self.core,self.research,mode=den.MODE)
        den.prepare_research(self.core,self.research,mode=den.MODE)

    def tearDown(self):
        self.temp.cleanup()

    def record(self,index,symbol="EURUSD",source="cot",
               outcome="CANDIDATE",when=READ):
        db=sqlite3.connect(str(self.core))
        try:
            with db:
                # Intentionally simulate a source update AND the attempt
                # in the SAME transaction, without calling LIVE collector.
                db.execute("UPDATE cot_reports SET oi=oi WHERE "
                           "dataset='tff' AND code='099741'")
                result=den.record_core_attempt(
                    db,self.core,self.research,attempt_id=aid(index),
                    symbol=symbol,source=source,scan_at=when,
                    outcome=outcome,mode=den.MODE)
            self.assertEqual(result,
                             "SYNTHETIC_CORE_ATTEMPT_SAME_TRANSACTION")
        finally:db.close()

    def report(self):
        return den.audit(self.core,self.research,mode=den.MODE)

    def link(self,index,symbol="EURUSD",source="cot",when=READ):
        return den.link_after_stage(
            self.core,self.research,attempt_id=aid(index),
            symbol=symbol,source=source,read_at=when,mode=den.MODE)

    def test_complete_synthetic_denominator_for_two_markets_and_exclusions(self):
        cases=[
            ("EURUSD","cot","CANDIDATE"),
            ("EURUSD","ctrader","CANDIDATE"),
            ("XAUUSD","cot","CANDIDATE"),
            ("XAUUSD","ctrader","CANDIDATE"),
            ("EURUSD","retail","EXCLUDED_UNKNOWN"),
            ("XAUUSD","retail","EXCLUDED_SOURCE_MISSING"),
            ("XAUUSD","cot","EXCLUDED_NOT_DUE"),
        ]
        for i,(symbol,source,outcome) in enumerate(cases,1):
            self.record(i,symbol,source,outcome)
        before=self.report()
        self.assertEqual(before["instrumentedAttemptCount"],7)
        self.assertEqual(before["candidateCount"],4)
        self.assertEqual(before["excludedCount"],3)
        self.assertEqual(before["missingOrUnknownCount"],4)
        for i,(symbol,source,_) in enumerate(cases[:4],1):
            self.assertEqual(
                self.link(i,symbol,source),
                "SYNTHETIC_ATTEMPT_STAGED_AND_LINKED_NOT_VERIFIED"
            )
        result=self.report()
        self.assertEqual(result["instrumentedAttemptCount"],7)
        self.assertEqual(result["candidateCount"]+result["excludedCount"],7)
        self.assertEqual(result["stagedResearchMetadataCount"],4)
        self.assertEqual(result["missingOrUnknownCount"],0)
        self.assertEqual(result["integrityBlockerCount"],0)
        self.assertFalse(result["denominatorIsCompleteForLiveScans"])
        self.assertFalse(result["realMarketReceiptVerified"])
        self.assertFalse(result["retailOriginalParentReadLinked"])
        self.assertFalse(result["actualOutOfSampleObservations"])
        self.assertFalse(result["realEdgeEstablished"])
        self.assertEqual(result["researchSuccessesProven"],0)
        self.assertEqual(result["newApiCalls"],0)

    def test_crash_between_source_commit_and_dispatch_counts_missing(self):
        self.record(1)
        self.record(2,"XAUUSD","ctrader")
        # The committed source and its CORE scan ledger survive; the
        # research process never started for one attempt.
        self.assertEqual(self.link(1),den.link_after_stage.__doc__ and
                         "SYNTHETIC_ATTEMPT_STAGED_AND_LINKED_NOT_VERIFIED")
        result=self.report()
        self.assertEqual(result["instrumentedAttemptCount"],2)
        self.assertEqual(result["candidateCount"],2)
        self.assertEqual(result["stagedResearchMetadataCount"],1)
        self.assertEqual(result["missingOrUnknownCount"],1)
        # No implicit replay during auditing, even on a second invocation.
        self.assertEqual(self.report(),result)

    def test_crash_between_shadow_stage_and_link_is_conservative_missing(self):
        self.record(1)
        self.assertEqual(post.dispatch(
            self.core,self.research,symbol="EURUSD",source="cot",
            read_at=READ,enabled=True,mode=post.MODE),post.STAGED)
        report=self.report()
        self.assertEqual(report["stagedResearchMetadataCount"],0)
        self.assertEqual(report["missingOrUnknownCount"],1)
        self.assertEqual(report["unlinkedShadowJobs"],1)
        # Duplicate stage must NOT silently repair/relabel provenance.
        self.assertEqual(self.link(1),den.UNKNOWN)
        self.assertEqual(self.report()["missingOrUnknownCount"],1)

    def test_same_core_transaction_rolls_back_source_and_attempt(self):
        db=sqlite3.connect(str(self.core))
        baseline=db.execute("SELECT oi FROM cot_reports "
            "WHERE dataset='tff' AND code='099741' "
            "AND report_date='2026-11-03'").fetchone()[0]
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                        "synthetic_force_rollback"):
                with db:
                    db.execute("UPDATE cot_reports SET oi=oi+77 "
                        "WHERE dataset='tff' AND code='099741' "
                        "AND report_date='2026-11-03'")
                    den.record_core_attempt(
                        db,self.core,self.research,attempt_id=aid(1),
                        symbol="EURUSD",source="cot",
                        scan_at=READ,outcome="CANDIDATE",mode=den.MODE)
                    db.execute("""CREATE TEMP TRIGGER synthetic_abort
                        BEFORE INSERT ON cot_reports
                        BEGIN SELECT RAISE(ABORT,'synthetic_force_rollback'); END""")
                    db.execute("INSERT INTO cot_reports VALUES "
                        "('tff','099741','2026-11-10',1,1,1,1,1)")
            self.assertEqual(db.execute("SELECT oi FROM cot_reports "
                "WHERE dataset='tff' AND code='099741' "
                "AND report_date='2026-11-03'").fetchone()[0],baseline)
            self.assertEqual(db.execute(
                f"SELECT count(*) FROM {den.CORE_TABLE}").fetchone()[0],0)
        finally:
            db.close()
        self.assertEqual(self.report()["instrumentedAttemptCount"],0)

    def test_dedup_and_core_attempt_identity_are_immutable(self):
        self.record(1)
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                     "UNIQUE constraint failed"):
            self.record(1)
        db=sqlite3.connect(str(self.core))
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "immutable_scan_denominator"):
                with db:
                    db.execute(f"UPDATE {den.CORE_TABLE} "
                               "SET outcome='EXCLUDED_UNKNOWN'")
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "immutable_scan_denominator"):
                with db:
                    db.execute(f"DELETE FROM {den.CORE_TABLE}")
        finally:db.close()
        self.assertEqual(self.report()["instrumentedAttemptCount"],1)

    def test_retail_cannot_be_falsely_marked_candidate_or_linked(self):
        db=sqlite3.connect(str(self.core))
        try:
            with self.assertRaisesRegex(ValueError,"source_attempt_not_eligible"):
                with db:
                    den.record_core_attempt(
                        db,self.core,self.research,attempt_id=aid(10),
                        symbol="EURUSD",source="retail",
                        scan_at=READ,outcome="CANDIDATE",mode=den.MODE)
        finally:db.close()
        self.record(11,"EURUSD","retail","EXCLUDED_UNKNOWN")
        self.assertEqual(self.link(11,"EURUSD","retail"),den.UNKNOWN)
        self.assertEqual(self.report()["candidateCount"],0)
        self.assertEqual(self.report()["excludedCount"],1)

    def test_research_locked_is_unknown_without_core_rollback(self):
        self.record(1)
        lock=sqlite3.connect(str(self.research),timeout=.025)
        try:
            lock.execute("BEGIN IMMEDIATE")
            lock.execute("UPDATE c3b_schema_guard SET version=version")
            self.assertEqual(self.link(1),den.UNKNOWN)
            self.assertEqual(self.report()["missingOrUnknownCount"],1)
            # Core is still writable despite shadow lock.
            self.record(2,"XAUUSD","cot")
        finally:
            lock.rollback()
            lock.close()
        self.assertEqual(self.report()["instrumentedAttemptCount"],2)
        self.assertEqual(self.report()["missingOrUnknownCount"],2)

    def test_revision_after_delivery_rejected_by_read_only_audit(self):
        self.record(1)
        self.assertNotEqual(self.link(1),den.UNKNOWN)
        db=sqlite3.connect(str(self.core))
        try:
            with db:
                db.execute("UPDATE cot_reports SET first_long=first_long+1 "
                           "WHERE dataset='tff' AND code='099741' "
                           "AND report_date='2026-11-03'")
        finally:db.close()
        result=self.report()
        self.assertEqual(result["stagedResearchMetadataCount"],0)
        self.assertEqual(result["missingOrUnknownCount"],1)
        self.assertGreater(result["integrityBlockerCount"],0)

    def test_stale_scan_id_cannot_be_backfilled_after_window(self):
        self.record(1,when="2026-11-09T11:57:00Z")
        self.assertEqual(self.link(1),den.UNKNOWN)
        self.assertEqual(self.report()["missingOrUnknownCount"],1)

    def test_schema_modes_and_live_path_are_refused(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline_denominator"):
            den.audit(self.core,self.research)
        with tempfile.TemporaryDirectory(prefix="nonremura-") as root:
            with self.assertRaises(ValueError):
                den.prepare_core(Path(root)/"remura.sqlite",
                                 self.research,mode=den.MODE)
        db=sqlite3.connect(str(self.core))
        try:
            with self.assertRaisesRegex(ValueError,"core_same_transaction_required"):
                den.record_core_attempt(
                    db,self.core,self.research,attempt_id=aid(1),
                    symbol="EURUSD",source="cot",scan_at=READ,
                    outcome="CANDIDATE",mode=den.MODE)
        finally:db.close()
        self.assertEqual(self.report()["instrumentedAttemptCount"],0)


if __name__=="__main__":
    unittest.main()
