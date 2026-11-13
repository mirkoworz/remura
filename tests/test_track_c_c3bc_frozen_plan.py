"""C3b-c(c): immutable synthetic plan detects lost slot registration.

The plan is an offline TEST artifact; Monday 12:00 COT is a hypothetical
poll, NOT the CFTC official release. M15 and 30-minute test polls do not
establish a market session or Myfxbook update SLA. No provider requests.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import track_c_c3bc_frozen_plan as plan
import track_c_c3bc_expected_slots as slots
import track_c_c3bc_attempt_denominator as den
import track_c_c3b_durable_shadow as shadow
import test_track_c_c3bc_attempt_denominator as fixture

CREATED="2026-11-09T11:59:00Z"
START="2026-11-09T12:00:00Z"
END="2026-11-09T13:00:00Z"
NOW="2026-11-09T12:00:31Z"
BEFORE="2026-11-09T11:59:30Z"
GRACE="2026-11-09T12:00:15Z"


class FrozenPlanSourceCadenceTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.AttemptDenominatorOfflineTests(
            "test_complete_synthetic_denominator_for_two_markets_and_exclusions")
        self.case.setUp()
        self.core=self.case.core
        self.research=self.case.research
        self.schedule=Path(self.case.temp.name)/slots.FILE
        slots.prepare(self.core,self.research,self.schedule,mode=slots.MODE)
        self.assertEqual(
            plan.prepare(self.core,self.research,self.schedule,mode=plan.MODE),
            "SYNTHETIC_POLICY_SCHEMA_ONLY_NO_PLAN_YET")

    def tearDown(self):
        self.case.tearDown()

    def commit(self,created=CREATED,start=START,end=END):
        return plan.commit_plan(self.core,self.research,self.schedule,
            created_at=created,start_at=start,end_at=end,mode=plan.MODE)

    def events(self):
        return plan.expected_ids(self.core,self.research,
                                 self.schedule,mode=plan.MODE)

    def report(self,when=NOW):
        return plan.audit(self.core,self.research,self.schedule,
                          as_of=when,mode=plan.MODE)

    def register(self,event,when=CREATED):
        return plan.register_planned(
            self.core,self.research,self.schedule,
            slot_id=event[0],registered_at=when,mode=plan.MODE)

    def core_attempt(self,event,*,outcome="CANDIDATE"):
        ident,symbol,source,due=event
        if source=="retail":
            outcome="EXCLUDED_UNKNOWN"
        db=sqlite3.connect(str(self.core))
        try:
            with db:
                db.execute("UPDATE cot_reports SET oi=oi WHERE "
                           "dataset='tff' AND code='099741'")
                den.record_core_attempt(
                    db,self.core,self.research,attempt_id=ident,
                    symbol=symbol,source=source,scan_at=due,
                    outcome=outcome,mode=den.MODE)
        finally:
            db.close()

    def test_policy_reconstructs_distinct_synthetic_cadences_without_slots(self):
        identifier=self.commit()
        self.assertEqual(len(identifier),64)
        occurrences=self.events()
        self.assertEqual(len(occurrences),14)
        by_source={name:sum(r[2]==name for r in occurrences)
                   for name in ("cot","ctrader","retail")}
        self.assertEqual(by_source,{"cot":2,"ctrader":8,"retail":4})
        self.assertEqual(
            sum("2026-11-09T12:00:00Z"==r[3] for r in occurrences),6)
        out=self.report()
        self.assertEqual(out["planExpectedSlots"],14)
        self.assertEqual(out["registeredSlots"],0)
        self.assertEqual(out["planSettledDue"],6)
        self.assertEqual(out["missingSlotRegistrations"],6)
        self.assertEqual(out["registeredButNoCoreAttempt"],0)
        self.assertEqual(out["totalKnownPreAttemptGaps"],6)
        self.assertEqual(out["postCommitResearchUnknown"],0)
        self.assertFalse(out["liveSchedulerEmissionVerified"])
        self.assertFalse(out["officialProviderPublicationVerified"])
        self.assertFalse(out["completeLiveDenominatorProven"])
        self.assertEqual(out["newProviderApiCalls"],0)

    def test_separate_plan_process_hard_crash_before_first_slot(self):
        code="""import os,sys
import track_c_c3bc_frozen_plan as p
core,research,schedule=sys.argv[1:]
x=p.commit_plan(core,research,schedule,
    created_at='2026-11-09T11:59:00Z',
    start_at='2026-11-09T12:00:00Z',
    end_at='2026-11-09T13:00:00Z',mode=p.MODE)
assert len(x)==64
os._exit(17)
"""
        env={"PYTHONPATH":str(ROOT/"scripts"),
             "PYTHONDONTWRITEBYTECODE":"1"}
        child=subprocess.run(
            [sys.executable,"-c",code,str(self.core),str(self.research),
             str(self.schedule)],env=env,capture_output=True,text=True,
            timeout=15,check=False)
        self.assertEqual(child.returncode,17)
        out=self.report()
        self.assertEqual(out["planExpectedSlots"],14)
        self.assertEqual(out["missingSlotRegistrations"],6)
        self.assertEqual(out["registeredSlots"],0)
        self.assertFalse(out["planClockIndependentlyAuthenticated"])

    def test_missing_plan_is_a_blocker_not_evidence_of_no_scans(self):
        with self.assertRaisesRegex(ValueError,"exact_one_committed_plan"):
            self.report()
        with self.assertRaisesRegex(ValueError,"exact_one_committed_plan"):
            self.events()

    def test_plan_registered_scans_and_core_gaps_distinguish_two_failures(self):
        self.commit()
        due=[r for r in self.events() if r[3]==START]
        self.assertEqual(len(due),6)
        for event in due[:3]:
            self.register(event)
        self.core_attempt(due[0])
        out=self.report()
        self.assertEqual(out["missingSlotRegistrations"],3)
        self.assertEqual(out["registeredButNoCoreAttempt"],2)
        self.assertEqual(out["totalKnownPreAttemptGaps"],5)
        self.assertEqual(out["postCommitResearchUnknown"],1)
        self.assertEqual(out["integrityBlockers"],0)
        self.assertFalse(out["completeLiveDenominatorProven"])

    def test_releasing_all_synthetic_slots_does_not_prove_trading_or_retail(self):
        self.commit()
        for event in self.events():
            self.register(event)
        out=self.report()
        self.assertEqual(out["registeredSlots"],14)
        self.assertEqual(out["planExpectedSlots"],14)
        self.assertEqual(out["missingSlotRegistrations"],0)
        self.assertEqual(out["registeredButNoCoreAttempt"],6)
        self.assertFalse(out["realRetailFirstSeenVerified"])
        self.assertFalse(out["realMarketSessionScheduleVerified"])
        self.assertFalse(out["actualProspectiveData"])

    def test_not_yet_due_and_grace_are_not_misclassified_as_gaps(self):
        self.commit()
        before=self.report(BEFORE)
        self.assertEqual(before["planSettledDue"],0)
        self.assertEqual(before["missingSlotRegistrations"],0)
        during=self.report(GRACE)
        self.assertEqual(during["planSettledDue"],0)
        self.assertEqual(during["planWithinGrace"],6)
        self.assertEqual(during["totalKnownPreAttemptGaps"],0)

    def test_only_ids_derived_from_original_plan_are_accepted(self):
        self.commit()
        with self.assertRaisesRegex(ValueError,"slot_not_derived"):
            plan.register_planned(self.core,self.research,self.schedule,
                slot_id="0"*64,registered_at=CREATED,mode=plan.MODE)
        event=self.events()[0]
        self.assertEqual(self.register(event),
                         "EXPECTED_SYNTHETIC_SLOT_REGISTERED_NOT_OBSERVED")
        with self.assertRaisesRegex(sqlite3.IntegrityError,"UNIQUE"):
            self.register(event)
        self.assertEqual(self.report()["registeredSlots"],1)

    def test_plan_creation_must_precede_due_and_schema_is_explicit(self):
        with self.assertRaisesRegex(ValueError,"plan_would_be_created_too_late"):
            self.commit(created=START)
        with self.assertRaisesRegex(ValueError,"fixed_monday_utc"):
            self.commit(start="2026-11-10T12:00:00Z",
                        end="2026-11-10T13:00:00Z")
        self.commit()
        with self.assertRaisesRegex(ValueError,"only_one_explicit_plan"):
            self.commit()
        self.assertEqual(self.report()["planExpectedSlots"],14)

    def test_historical_policy_drift_blocks_reconstruction(self):
        self.commit()
        with patch.object(plan,"SOURCES",(("ctrader","changed",300),)):
            with self.assertRaisesRegex(ValueError,"frozen_synthetic_policy"):
                self.report()
        self.assertEqual(self.report()["planExpectedSlots"],14)

    def test_cannot_rewrite_or_delete_frozen_plan(self):
        self.commit()
        db=sqlite3.connect(str(self.schedule))
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                        "immutable_frozen_plan"):
                with db:
                    db.execute(
                        f"UPDATE {plan.TABLE} SET expected_slots=0")
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                        "immutable_frozen_plan"):
                with db:
                    db.execute(f"DELETE FROM {plan.TABLE}")
        finally:
            db.close()
        self.assertEqual(self.report()["planExpectedSlots"],14)

    def test_unplanned_slot_registration_is_visible(self):
        self.commit()
        slots.register(self.core,self.research,self.schedule,
                       slot_id="e"*64,symbol="XAUUSD",source="cot",
                       registered_at=CREATED,due_at=START,mode=slots.MODE)
        out=self.report()
        self.assertEqual(out["unexpectedRegisteredSlots"],1)
        self.assertGreater(out["integrityBlockers"],0)
        self.assertEqual(out["missingSlotRegistrations"],6)

    def test_scope_and_temp_guards_remain_default_off(self):
        with self.assertRaisesRegex(ValueError,"explicit_synthetic_frozen"):
            plan.prepare(self.core,self.research,self.schedule)
        self.commit()
        for expected_negative in (
                "completeLiveDenominatorProven",
                "liveEnabled","realRetailFirstSeenVerified",
                "planClockIndependentlyAuthenticated"):
            self.assertFalse(self.report()[expected_negative])
        self.assertEqual(self.report()["newProviderApiCalls"],0)


if __name__=="__main__":
    unittest.main()
