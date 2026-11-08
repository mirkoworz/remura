"""C4b(e): test fictional historical trends, not the private real measurements."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import track_c_c4be_historic_trend as m

NOW = datetime(2026,11,8,12,0,tzinfo=timezone.utc)


def ts(t):
    return t.isoformat().replace("+00:00","Z")


def record(i, *, rows=100, ram=25.0, disk=10.0, saved=None):
    at = datetime(2026,11,3+i,14,30,tzinfo=timezone.utc)
    return {
        "runId": 10000+i, "jobId": 90000+i, "jobConclusion": "success",
        "sampleAtUtc": ts(at),
        "ramUsedPercent": ram, "diskUsedPercent": disk,
        "backupStatus": "NON_VERIFICATO_DA_QUESTO_TEST",
        "timingState": "PRONTA", "timingRows": rows,
        "timingPlanned": rows*5, "timingSaved": rows*5 if saved is None else saved,
        "timingMedianMs": 15_000+i*100, "timingMaximumMs": 25_000+i*100,
        "lastIngestUtc": ts(at-timedelta(minutes=1)),
    }


class ExistingRunsOffline(unittest.TestCase):
    def check(self, rows, **opts):
        return m.summarize(rows,observed_at_utc=ts(NOW),mode=m.MODE,**opts)

    def test_three_old_runs_are_not_current_proof(self):
        x=self.check([record(1,rows=110),record(2,rows=196),record(3,rows=256)])
        self.assertEqual(x["historicalSuccessfulRunsCompared"],3)
        self.assertEqual(x["state"],"HISTORICAL_UNATTESTED_COMPARISON_ONLY")
        self.assertTrue(x["anyRetainedWindowAtCap256"])
        self.assertEqual(x["latestRetainedBatchRows"],256)
        self.assertFalse(x["currentVpsCapacityVerified"])
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_256_is_cap_not_full_schedule_certificate(self):
        x=self.check([record(3,rows=256)])
        self.assertFalse(x["eightDistinctBatchSlotsVerified"])
        self.assertFalse(x["completeBatchScheduleVerified"])
        self.assertFalse(x["perSymbolCommitProven"])
        self.assertEqual(x["latestSavedSymbolsInRetainedRows"],1280)

    def test_equal_saved_planned_does_not_mean_market_freshness(self):
        x=self.check([record(2,rows=196)])
        self.assertEqual(x["latestPlannedSymbolsInRetainedRows"],980)
        self.assertEqual(x["latestSavedSymbolsInRetainedRows"],980)
        self.assertFalse(x["offhostBackupRestoreVerified"])
        self.assertFalse(x["billFreeVerified"])

    def test_partial_save_can_be_recorded_without_false_go(self):
        x=self.check([record(1, saved=300)])
        self.assertEqual(x["latestSavedSymbolsInRetainedRows"],300)
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_empty_means_unknown_not_zero(self):
        x=self.check([])
        self.assertEqual(x["state"],"UNKNOWN_NO_HISTORICAL_RUNS")
        self.assertIsNone(x["historicalMaximumRamUsedPct"])
        self.assertIsNone(x["anyRetainedWindowAtCap256"])

    def test_duplicate_run_or_job_fails_closed(self):
        a,b=record(1),record(2)
        b["runId"]=a["runId"]
        self.assertTrue(self.check([a,b])["state"].startswith("UNKNOWN_"))
        b=record(2);b["jobId"]=a["jobId"]
        self.assertTrue(self.check([a,b])["state"].startswith("UNKNOWN_"))

    def test_out_of_order_clock_fails_closed(self):
        self.assertEqual(self.check([record(2),record(1)])["state"],
                         "UNKNOWN_INVALID_OR_CONFLICTING_HISTORICAL_RUNS")

    def test_future_or_inconsistent_ingest_clock_fails_closed(self):
        a=record(1)
        a["lastIngestUtc"]=ts(datetime(2026,11,8,13,tzinfo=timezone.utc))
        self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))
        a=record(1)
        a["lastIngestUtc"]=ts(datetime(2026,11,3,1,tzinfo=timezone.utc))
        self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))

    def test_negative_nan_or_more_than_100_percent_not_accepted(self):
        for v in (-1,101,float("nan"),True):
            with self.subTest(v=v):
                a=record(1);a["ramUsedPercent"]=v
                self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))

    def test_forged_backup_proof_rejected(self):
        a=record(1);a["backupStatus"]="VERIFIED"
        self.assertEqual(self.check([a])["state"],
                         "UNKNOWN_INVALID_OR_CONFLICTING_HISTORICAL_RUNS")

    def test_bad_synthetic_timing_or_rising_counter_rejected(self):
        a=record(1,rows=300)
        self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))
        a=record(1);a["timingSaved"]=999
        self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))
        a=record(1);a["timingMedianMs"]=10000000
        self.assertTrue(self.check([a])["state"].startswith("UNKNOWN_"))

    def test_input_schema_rejects_secret_and_does_not_echo(self):
        a=record(1);a["PASSWORD"]="DO_NOT_SHARE"
        x=self.check([a])
        self.assertTrue(x["state"].startswith("UNKNOWN_"))
        self.assertNotIn("DO_NOT_SHARE",repr(x))
        self.assertNotIn("account",repr(x))

    def test_explicit_mode_and_max_count(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            m.summarize([],observed_at_utc=ts(NOW))
        with self.assertRaisesRegex(ValueError,"bounded_historical"):
            self.check([record(1)]*9)

    def test_newest_even_hypothetically_recent_is_unverified(self):
        a=record(3)
        at=NOW-timedelta(seconds=10)
        a["sampleAtUtc"]=ts(at)
        a["lastIngestUtc"]=ts(at-timedelta(seconds=2))
        x=self.check([a])
        self.assertEqual(x["lastLogAgeSeconds"],10)
        self.assertFalse(x["sourceAuthenticityVerified"])
        self.assertFalse(x["currentVpsCapacityVerified"])
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_zero_network_activity_and_no_live_release(self):
        x=self.check([record(1)])
        self.assertEqual(x["newVpsRequests"],0)
        self.assertEqual(x["newProviderCalls"],0)
        self.assertEqual(x["operationalDecision"],m.NO_GO)

if __name__=="__main__":unittest.main()
