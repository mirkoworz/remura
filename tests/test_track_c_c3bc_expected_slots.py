"""C3b-c(b): independent schedule gaps before ANY source attempt.

Only synthetic/temp SQLite. No real provider, exchange hours, live scan
scheduler, background job or fake provider FIRST-SEEN. An expected future
slot is not a received market event. Three lab DBs remain independent.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import track_c_c3bc_attempt_denominator as den
import track_c_c3bc_expected_slots as slots
import track_c_c3b_durable_shadow as shadow
import track_c_c3b_postcommit_handoff as post
import test_track_c_c3bc_attempt_denominator as fixture

DUE="2026-11-09T12:00:00Z"
REGISTERED="2026-11-09T11:59:00Z"
SOON="2026-11-09T11:59:45Z"
GRACE="2026-11-09T12:00:05Z"
SETTLED="2026-11-09T12:00:31Z"
FUTURE="2026-11-09T12:01:00Z"


def expected(index):
    return hashlib.sha256(f"SYNTHETIC-SCAN-{index}".encode()).hexdigest()


class PreregisteredLabScheduleTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing C3b-c fixture's true synthetic CFTC collector,
        # cTrader price_store.ingest, shadow WAL and core ledger migrations.
        self.case=fixture.AttemptDenominatorOfflineTests(
            "test_complete_synthetic_denominator_for_two_markets_and_exclusions")
        self.case.setUp()
        self.core=self.case.core
        self.research=self.case.research
        self.schedule=Path(self.case.temp.name)/slots.FILE
        self.assertEqual(
            slots.prepare(self.core,self.research,self.schedule,mode=slots.MODE),
            "OFFLINE_SYNTHETIC_EXPECTED_SLOT_DB_ONLY")

    def tearDown(self):
        self.case.tearDown()

    def plan(self,index,symbol="EURUSD",source="cot",
             registered=REGISTERED,due=DUE):
        return slots.register(
            self.core,self.research,self.schedule,
            slot_id=expected(index),symbol=symbol,source=source,
            registered_at=registered,due_at=due,mode=slots.MODE)

    def audit(self,when=SETTLED):
        return slots.audit(self.core,self.research,self.schedule,
                           as_of=when,mode=slots.MODE)

    def test_pre_commit_crash_is_visible_as_expected_but_missing_scan(self):
        self.plan(1)
        # The simulated source never starts: ZERO core attempts, yet the
        # schedule remains committed independently in the third database.
        result=self.audit()
        self.assertEqual(result["registeredExpectedSlots"],1)
        self.assertEqual(result["settledDueSlots"],1)
        self.assertEqual(result["missingBeforeCoreAttempt"],1)
        self.assertEqual(result["startedInWindow"],0)
        self.assertFalse(result["completeRealDenominator"])
        self.assertFalse(result["everyLiveScanPreplanned"])
        self.assertFalse(result["clockIsIndependentOrSigned"])
        self.assertEqual(result["newProviderCalls"],0)

    def test_not_due_and_in_grace_must_not_count_as_proven_missing(self):
        self.plan(1)
        earlier=self.audit(SOON)
        self.assertEqual(earlier["futureNotYetDue"],1)
        self.assertEqual(earlier["missingBeforeCoreAttempt"],0)
        during=self.audit(GRACE)
        self.assertEqual(during["dueWithinGrace"],1)
        self.assertEqual(during["missingBeforeCoreAttempt"],0)
        later=self.audit()
        self.assertEqual(later["settledDueSlots"],1)
        self.assertEqual(later["missingBeforeCoreAttempt"],1)

    def test_full_instrumented_fixture_separates_scan_missing_and_proof_missing(self):
        cases=[("EURUSD","cot","CANDIDATE"),
               ("EURUSD","ctrader","CANDIDATE"),
               ("XAUUSD","cot","CANDIDATE"),
               ("XAUUSD","ctrader","CANDIDATE"),
               ("EURUSD","retail","EXCLUDED_UNKNOWN"),
               ("XAUUSD","retail","EXCLUDED_SOURCE_MISSING")]
        for i,(symbol,source,outcome) in enumerate(cases,1):
            self.plan(i,symbol,source)
            self.case.record(i,symbol,source,outcome)
        self.plan(7,"EURUSD","cot",due=FUTURE)
        for i,(symbol,source,_) in enumerate(cases[:2],1):
            self.assertEqual(
                self.case.link(i,symbol,source),
                "SYNTHETIC_ATTEMPT_STAGED_AND_LINKED_NOT_VERIFIED")
        out=self.audit()
        self.assertEqual(out["registeredExpectedSlots"],7)
        self.assertEqual(out["futureNotYetDue"],1)
        self.assertEqual(out["settledDueSlots"],6)
        self.assertEqual(out["missingBeforeCoreAttempt"],0)
        self.assertEqual(out["startedInWindow"],6)
        self.assertEqual(out["startedCandidates"],4)
        self.assertEqual(out["startedExcluded"],2)
        self.assertEqual(out["postCommitCandidateMissingOrUnknown"],2)
        self.assertEqual(out["researchMetadataStagedNotEvidence"],2)
        self.assertEqual(out["integrityBlockers"],0)
        self.assertFalse(out["realProspectiveObservations"])
        self.assertFalse(out["tradingEdgeEstablished"])

    def test_core_attempt_rolls_back_schedule_remains_gap(self):
        self.plan(1)
        db=sqlite3.connect(str(self.core))
        try:
            db.execute("BEGIN IMMEDIATE")
            den.record_core_attempt(
                db,self.core,self.research,attempt_id=expected(1),
                symbol="EURUSD",source="cot",scan_at=DUE,
                outcome="CANDIDATE",mode=den.MODE)
            db.rollback()  # simulate power loss before commit
        finally:db.close()
        out=self.audit()
        self.assertEqual(out["missingBeforeCoreAttempt"],1)
        self.assertEqual(out["startedInWindow"],0)

    def test_late_start_or_wrong_market_cannot_fill_schedule_gap(self):
        self.plan(1,due="2026-11-09T11:59:00Z",
                  registered="2026-11-09T11:58:00Z")
        self.case.record(1,when=DUE)
        out=self.audit()
        self.assertEqual(out["startedInWindow"],0)
        self.assertEqual(out["lateOrMisassignedAttempts"],1)
        self.assertGreater(out["integrityBlockers"],0)
        # Test independent mismatched attempt for a different planned slot.
        self.plan(2,"XAUUSD","cot")
        self.case.record(2,"EURUSD","ctrader")
        out=self.audit()
        self.assertEqual(out["lateOrMisassignedAttempts"],2)
        self.assertEqual(out["startedCandidates"],0)

    def test_unplanned_attempt_is_detected_without_claiming_plan_completeness(self):
        self.case.record(1)
        result=self.audit()
        self.assertEqual(result["registeredExpectedSlots"],0)
        self.assertEqual(result["unplannedCoreAttempts"],1)
        self.assertGreater(result["integrityBlockers"],0)
        self.assertFalse(result["everyLiveScanPreplanned"])

    def test_crash_before_schedule_registration_is_fundamentally_unknowable(self):
        # Zero plans and attempts is NOT evidence that the live scheduler
        # executed all expected ticks; absence cannot prove completeness.
        out=self.audit()
        self.assertEqual(out["registeredExpectedSlots"],0)
        self.assertEqual(out["missingBeforeCoreAttempt"],0)
        self.assertFalse(out["completeRealDenominator"])
        self.assertFalse(out["everyLiveScanPreplanned"])

    def test_duplicate_or_retroactive_schedule_registration_rejected(self):
        self.plan(1)
        with self.assertRaisesRegex(sqlite3.IntegrityError,"UNIQUE"):
            self.plan(1)
        with self.assertRaisesRegex(sqlite3.IntegrityError,"UNIQUE"):
            self.plan(2)  # same symbol/source/due with different slot ID
        with self.assertRaisesRegex(ValueError,"must_register_slot_before"):
            self.plan(3,registered=DUE,due=DUE)
        with self.assertRaisesRegex(ValueError,"must_register_slot_before"):
            self.plan(4,registered=SETTLED,due=DUE)
        self.assertEqual(self.audit()["registeredExpectedSlots"],1)

    def test_schedule_append_only_and_cannot_relabel_past_gaps(self):
        self.plan(1)
        db=sqlite3.connect(str(self.schedule))
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "immutable_expected_slot"):
                with db:
                    db.execute(f"UPDATE {slots.TABLE} "
                               "SET due_at='2099-01-01T00:00:00Z'")
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "immutable_expected_slot"):
                with db:
                    db.execute(f"DELETE FROM {slots.TABLE}")
        finally:db.close()
        self.assertEqual(self.audit()["missingBeforeCoreAttempt"],1)

    def test_retail_expected_but_no_parent_receipt_remains_gap(self):
        self.plan(1,"EURUSD","retail")
        out=self.audit()
        self.assertEqual(out["missingBeforeCoreAttempt"],1)
        self.case.record(1,"EURUSD","retail","EXCLUDED_UNKNOWN")
        out=self.audit()
        self.assertEqual(out["missingBeforeCoreAttempt"],0)
        self.assertEqual(out["startedExcluded"],1)
        self.assertFalse(out["retailParentReadVerified"])

    def test_shadow_locked_does_not_delete_independent_expected_schedule(self):
        self.plan(1)
        db=sqlite3.connect(str(self.research),timeout=.025)
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE c3b_schema_guard SET version=version")
            self.case.record(1)
            self.assertEqual(self.case.link(1),den.UNKNOWN)
            out=self.audit()
            self.assertEqual(out["startedInWindow"],1)
            self.assertEqual(out["postCommitCandidateMissingOrUnknown"],1)
        finally:
            db.rollback()
            db.close()

    def test_separate_planner_process_dies_after_registration(self):
        """Schedule survives a hard-stop before the source attempt begins."""
        program = """import os,sys
import track_c_c3bc_expected_slots as slots
core,research,schedule,identifier=sys.argv[1:]
status=slots.register(core,research,schedule,
    slot_id=identifier,symbol='EURUSD',source='cot',
    registered_at='2026-11-09T11:59:00Z',
    due_at='2026-11-09T12:00:00Z',mode=slots.MODE)
assert status=='EXPECTED_SYNTHETIC_SLOT_REGISTERED_NOT_OBSERVED'
os._exit(17)
"""
        env={"PYTHONPATH":str(ROOT/"scripts"),
             "PYTHONDONTWRITEBYTECODE":"1"}
        proc=subprocess.run([
            sys.executable,"-c",program,str(self.core),
            str(self.research),str(self.schedule),expected(1)],
            env=env,text=True,capture_output=True,timeout=15,check=False)
        self.assertEqual(proc.returncode,17)
        evidence=self.audit()
        self.assertEqual(evidence["registeredExpectedSlots"],1)
        self.assertEqual(evidence["missingBeforeCoreAttempt"],1)
        self.assertEqual(evidence["startedInWindow"],0)
        self.assertFalse(evidence["completeRealDenominator"])

    def test_future_slot_claimed_by_earlier_core_attempt_is_anomaly(self):
        self.plan(1,due=FUTURE)
        self.case.record(1,when=DUE)
        out=self.audit()
        self.assertEqual(out["futureNotYetDue"],1)
        self.assertEqual(out["startedInWindow"],0)
        self.assertGreater(out["integrityBlockers"],0)

    def test_mode_path_schema_and_capacity_guards(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline_schedule_mode"):
            slots.audit(self.core,self.research,self.schedule,as_of=SETTLED)
        with self.assertRaisesRegex(ValueError,"refuse_overwrite"):
            slots.prepare(self.core,self.research,self.schedule,mode=slots.MODE)
        with self.assertRaisesRegex(ValueError,"schedule_must_be_third"):
            slots.prepare(self.core,self.research,self.core,mode=slots.MODE)
        with self.assertRaisesRegex(ValueError,"only_pilot_market"):
            self.plan(1,"GBPUSD","cot")
        with self.assertRaises(ValueError):
            self.plan(1,registered="2026-11-09T12:00:01Z",due=DUE)
        from unittest.mock import patch
        with patch.object(slots,"MAX_SLOTS",0):
            with self.assertRaisesRegex(ValueError,"capacity_exceeded"):
                self.plan(2)
        self.assertEqual(self.audit()["registeredExpectedSlots"],0)


if __name__ == "__main__":
    unittest.main()
