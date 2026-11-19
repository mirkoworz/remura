"""Track C3c-b: real-shaped GitHub run metadata versus scheduled CRON.

Observed November 7 example came from read-only GitHub Actions metadata.
All records are sanitized, historical exemplars; test does NOT query
GitHub/market services. No secret, account, quote or broker input.
Batch telemetry is written to a disposable database using REMURA's
original opt-in batch_timing.record function, then read via mode=ro.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import batch_timing
import track_c_c3c_execution_evidence as audit

START="2026-11-07T00:00:00Z"
END="2026-11-07T22:00:00Z"
NOW="2026-11-07T22:00:00Z"
UTC=timezone.utc

# Public GitHub Actions run metadata observed on 2026-11-07.
OBSERVED=[
    (42317620575,"2026-11-07T00:20:28Z"),
    (42346155111,"2026-11-07T06:15:03Z"),
    (42376425017,"2026-11-07T13:19:26Z"),
    (42399603442,"2026-11-07T18:06:31Z"),
    (42417221728,"2026-11-07T21:43:39Z"),
]


def action(ident,when,event="schedule",conclusion="success",attempt=1):
    return {
        "id":ident,
        "workflow_path":".github/workflows/myfxbook.yml",
        "event":event,
        "head_branch":"main",
        "created_at":when,
        "run_started_at":when,
        "status":"completed",
        "conclusion":conclusion,
        "run_attempt":attempt,
    }


def sample():
    return [action(*item) for item in OBSERVED]


class C3cExecutionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-c3c-runtime-")
        self.path=Path(self.tmp.name)/audit.BATCH_FILE

    def tearDown(self):
        self.tmp.cleanup()

    def github(self,rows=None,**kw):
        options={"window_start":START,"window_end":END,
                 "observed_at":NOW,"mode":audit.MODE}
        options.update(kw)
        return audit.reconcile_github_runs(sample() if rows is None else rows,
                                           **options)

    def record(self, *, minute,planned,saved,state,elapsed=10):
        t=datetime(2026,11,7,21,minute,0,tzinfo=UTC)
        start=t
        returned=start+timedelta(seconds=elapsed)
        finished=returned+timedelta(seconds=5)
        with sqlite3.connect(str(self.path)):
            pass
        batch_timing.record(
            self.path,started=start,ingest_returned=returned,
            finished=finished,scheduled_markets=planned,
            saved_markets=saved,slot=1+minute//15,
            post_scan_state=state,
            post_scan_finished=returned+timedelta(seconds=2)
                               if state!="not_run" else None,
        )

    def inspect(self,**kw):
        return audit.inspect_batch_timing(
            self.path,observed_at=NOW,mode=audit.MODE,**kw)

    def test_five_observed_real_git_hub_runs_not_sixty_six_confirmed_ticks(self):
        proof=self.github()
        self.assertEqual(proof["nominalCronSlots"],66)
        self.assertEqual(proof["observedScheduledRuns"],5)
        self.assertEqual(proof["completedSuccessRuns"],5)
        self.assertEqual(proof["completedFailedOrCancelledRuns"],0)
        self.assertEqual(proof["temporallyCompatibleRunsNotSlotProof"],5)
        self.assertEqual(proof["observedRunsWithoutCompatibleNominalSlot"],0)
        # Critical: never claim that absent GitHub run rows are proven
        # skipped cron ticks. Run creation cannot be tied to specific slot.
        self.assertEqual(proof["provenSkippedCronSlots"],0)
        self.assertEqual(proof["nominalSlotsWithoutProvenRunIdentity"],66)
        self.assertFalse(proof["runToCronSlotIdentityProvable"])
        self.assertFalse(proof["apiPaginationAndRunHistoryCompleteProven"])
        self.assertFalse(proof["actionsSucceededMeansFreshMyfxbook"])
        self.assertFalse(proof["liveRuntimeObservedByThisTest"])
        self.assertEqual(proof["newExternalApiCalls"],0)

    def test_empty_api_page_does_not_prove_66_missed_slots(self):
        result=self.github(rows=[])
        self.assertEqual(result["nominalCronSlots"],66)
        self.assertEqual(result["observedScheduledRuns"],0)
        self.assertEqual(result["provenSkippedCronSlots"],0)
        self.assertFalse(result["workflowEnabledThroughoutWindowProven"])

    def test_manual_dispatch_and_other_workflows_do_not_fill_schedule(self):
        records=[
            action(1,"2026-11-07T21:27:00Z",event="workflow_dispatch"),
            {**action(2,"2026-11-07T21:27:00Z"),
             "workflow_path":".github/workflows/price-checks.yml"},
            {**action(3,"2026-11-07T21:27:00Z"),
             "head_branch":"research/track-c-beta-prospective-20261107"},
        ]
        result=self.github(rows=records)
        self.assertEqual(result["otherEventOrWorkflowRowsIgnored"],3)
        self.assertEqual(result["observedScheduledRuns"],0)

    def test_failed_and_pending_runs_not_conflated_with_data_freshness(self):
        queued=action(11,"2026-11-07T21:47:30Z")
        queued.update({"status":"in_progress","conclusion":None,
                       "run_started_at":None})
        fail=action(10,"2026-11-07T21:43:39Z",conclusion="failure")
        result=self.github(rows=[queued,fail])
        self.assertEqual(result["observedScheduledRuns"],2)
        self.assertEqual(result["completedFailedOrCancelledRuns"],1)
        self.assertEqual(result["uncompletedRuns"],1)
        self.assertEqual(result["completedSuccessRuns"],0)
        self.assertFalse(result["marketDataProviderPublicationVerified"])

    def test_same_run_retries_are_one_execution_record(self):
        base=action(100,"2026-11-07T21:43:39Z",
                    conclusion="failure",attempt=1)
        retry=action(100,"2026-11-07T21:43:39Z",
                     conclusion="success",attempt=2)
        result=self.github(rows=[base,retry])
        self.assertEqual(result["observedScheduledRuns"],1)
        self.assertEqual(result["completedSuccessRuns"],1)

    def test_identical_attempt_conflicting_metadata_rejected(self):
        a=action(5,"2026-11-07T21:43:39Z",conclusion="failure")
        b=action(5,"2026-11-07T21:43:39Z",conclusion="success")
        with self.assertRaisesRegex(ValueError,"conflicting_same_attempt"):
            self.github(rows=[a,b])

    def test_future_and_noncausal_start_times_are_rejected(self):
        bad=action(1,"2026-11-08T01:00:00Z")
        with self.assertRaisesRegex(ValueError,"future_actions_run"):
            self.github(rows=[bad])
        bad=action(1,"2026-11-07T21:43:39Z")
        bad["run_started_at"]="2026-11-07T21:00:00Z"
        with self.assertRaisesRegex(ValueError,"actions_start_precedes"):
            self.github(rows=[bad])

    def test_secret_like_extra_fields_are_rejected_not_exported(self):
        payload=action(1,"2026-11-07T21:43:39Z")
        payload["MYFXBOOK_PASSWORD"]="synthetic-secret"
        with self.assertRaisesRegex(ValueError,"unexpected_actions_metadata_shape"):
            self.github(rows=[payload])
        output=json.dumps(self.github())
        for forbidden in ("MYFXBOOK_PASSWORD","EURUSD","account","lLots",
                          "42417221728","21:43:39"):
            self.assertNotIn(forbidden,output)

    def test_bound_and_utc_validation_require_explicit_mode(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            self.github(mode=None)
        with self.assertRaisesRegex(ValueError,"utc_only"):
            self.github(window_start="2026-11-07T00:00:00+01:00")
        with self.assertRaisesRegex(ValueError,"bounded_completed"):
            self.github(window_start="2026-11-05T00:00:00Z")
        with self.assertRaisesRegex(ValueError,"bounded_actions_metadata"):
            self.github(rows=sample()*31)

    def test_optional_batch_telemetry_absent_is_unknown_not_no_batches(self):
        summary=self.inspect()
        self.assertEqual(summary["state"],"UNKNOWN_NO_TELEMETRY")
        self.assertIsNone(summary["batchRowsObserved"])
        self.assertFalse(summary["allRuntimeBatchesObserved"])
        self.assertFalse(summary["perSymbolCommitWitnessed"])
        self.assertFalse(self.path.exists())

    def test_actual_batch_timing_schema_measures_aggregates_not_broker_candles(self):
        self.record(minute=0,planned=5,saved=4,state="ok")
        self.record(minute=15,planned=5,saved=0,state="failed")
        self.record(minute=30,planned=4,saved=2,state="not_run")
        report=self.inspect()
        self.assertEqual(report["batchRowsObserved"],3)
        self.assertEqual(report["scheduledSymbolsInObservedBatches"],14)
        self.assertEqual(report["savedSymbolsInObservedBatches"],6)
        self.assertEqual(report["zeroSavedBatches"],1)
        self.assertEqual(report["failedPostIngestScans"],1)
        self.assertEqual(report["postIngestNotRun"],1)
        self.assertFalse(report["perSymbolCommitWitnessed"])
        self.assertFalse(report["allRuntimeBatchesObserved"])
        self.assertFalse(report["actualMarketOHLCInspected"])
        self.assertEqual(report["newExternalApiCalls"],0)

    def test_invalid_telemetry_clock_does_not_become_a_valid_sample(self):
        self.record(minute=0,planned=4,saved=4,state="ok")
        with sqlite3.connect(str(self.path)) as db:
            db.execute(
                "UPDATE remura_batch_timing "
                "SET finished_utc='2026-11-07T20:00:00+00:00'")
        result=self.inspect()
        self.assertEqual(result["state"],
                         "UNKNOWN_INVALID_OR_UNAVAILABLE_TELEMETRY")
        self.assertIsNone(result["batchRowsObserved"])

    def test_unprepared_sqlite_and_live_path_are_not_read(self):
        with sqlite3.connect(str(self.path)):
            pass
        result=self.inspect()
        self.assertEqual(result["state"],
                         "UNKNOWN_INVALID_OR_UNAVAILABLE_TELEMETRY")
        with self.assertRaisesRegex(ValueError,"only_disposable_batch_timing"):
            audit.inspect_batch_timing(
                Path("/opt/remura/market.sqlite3"),
                observed_at=NOW,mode=audit.MODE)

    def test_batch_scan_result_is_upper_bound_not_source_first_seen(self):
        self.record(minute=0,planned=5,saved=5,state="ok")
        result=self.inspect()
        self.assertEqual(result["state"],
                         "OFFLINE_TEMP_COPY_OF_EXISTING_BATCH_TELEMETRY")
        self.assertFalse(result["perSymbolCommitWitnessed"])
        self.assertFalse(result["actualMarketOHLCInspected"])
        self.assertIsNotNone(result["latestBatchFinishedAt"])


if __name__=="__main__":
    unittest.main()
