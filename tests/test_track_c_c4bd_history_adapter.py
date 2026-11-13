"""C4b(d) synthetic fixtures matching private diagnostic OUTPUT FORMAT only."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import track_c_c4bd_history_adapter as mod

# Fictional test percentages only. Private GitHub logs NEVER in public repo.
NOW = "2026-11-08T12:45:00Z"
BASE = "2026-11-03T14:24:19.1138784Z"


def line(key, value, at=BASE):
    return f"{at} {key}={value}"


def sample():
    return [line("VPS_RAM_USATA_PERCENTO", "32.5"),
            line("VPS_DISCO_USATO_PERCENTO", "12.5"),
            line("BACKUP_SQLITE", "NON_VERIFICATO_DA_QUESTO_TEST")]


class HistoryTest(unittest.TestCase):
    def check(self, lines=None, **opts):
        p = {"run_id": 100, "job_id": 500, "job_conclusion": "success",
             "checked_at_utc": NOW, "mode": mod.MODE}
        p.update(opts)
        return mod.inspect_redacted_lines(sample() if lines is None else lines, **p)

    def test_historical_lines_not_current(self):
        x = self.check()
        self.assertEqual(x["state"], "HISTORICAL_PAST_RUN_NOT_CURRENT_VPS_EVIDENCE")
        self.assertEqual(x["ramUsedPercentObserved"], 32.5)
        self.assertEqual(x["diskUsedPercentObserved"], 12.5)
        self.assertFalse(x["vpsCurrentHeadroomVerified"])
        self.assertEqual(x["operationalDecision"], mod.NO_GO)

    def test_backup_explicitly_not_verified(self):
        x = self.check()
        self.assertEqual(x["backupSqliteEvidence"], "DIAGNOSTIC_SPECIFICALLY_DID_NOT_VERIFY_BACKUP")
        self.assertFalse(x["offhostBackupAndRestoreVerified"])

    def test_missing_backup_is_unknown(self):
        self.assertEqual(self.check(sample()[:2])["backupSqliteEvidence"],
                         "UNKNOWN_NO_RESTORE_EVIDENCE")

    def test_missing_one_resource_unknown(self):
        x = self.check(sample()[:1])
        self.assertEqual(x["state"], "UNKNOWN_MISSING_RESOURCE_MEASUREMENT")
        self.assertIsNone(x["ramUsedPercentObserved"])

    def test_unexpected_private_content_rejected_and_not_echoed(self):
        x = self.check(sample() + ["TOKEN_PASSWORD=do-not-leak"])
        self.assertEqual(x["state"], "UNKNOWN_UNEXPECTED_LOG_CONTENT")
        self.assertNotIn("do-not-leak", repr(x))

    def test_forged_backup_success_rejected(self):
        x = self.check(sample()[:-1] + [line("BACKUP_SQLITE", "VERIFIED")])
        self.assertEqual(x["state"], "UNKNOWN_UNEXPECTED_LOG_CONTENT")

    def test_duplicates_rejected(self):
        x = self.check(sample() + [line("VPS_RAM_USATA_PERCENTO", "24.3")])
        self.assertEqual(x["state"], "UNKNOWN_DUPLICATE_OR_MALFORMED_MEASUREMENT")

    def test_bad_percent_values_fail_closed(self):
        for val in ["101", "-1", "NaN", "nan", "1e2"]:
            with self.subTest(value=val):
                x = self.check([line("VPS_RAM_USATA_PERCENTO", val), sample()[1]])
                self.assertTrue(x["state"].startswith("UNKNOWN_"))

    def test_bad_mode_and_run_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "strict_bounded"):
            self.check(run_id=True)
        with self.assertRaisesRegex(ValueError, "explicit_offline"):
            self.check(mode="LIVE")

    def test_failed_job_not_success(self):
        x = self.check(job_conclusion="failure")
        self.assertEqual(x["state"], "UNKNOWN_DIAGNOSTIC_JOB_NOT_SUCCESSFUL")

    def test_empty_or_too_many_lines(self):
        self.assertEqual(self.check([])["state"], "UNKNOWN_NO_REDACTED_LINES")
        with self.assertRaisesRegex(ValueError, "strict_bounded"):
            self.check(sample()*5)

    def test_non_comparable_clocks(self):
        rows = [sample()[0], line("VPS_DISCO_USATO_PERCENTO", "12.5",
                                  "2026-11-03T13:14:19Z")]
        self.assertEqual(self.check(rows)["state"], "UNKNOWN_NONCOMPARABLE_TIMESTAMPS")

    def test_future_timestamp_not_current(self):
        rows = [line("VPS_RAM_USATA_PERCENTO", "32.5", "2026-11-09T14:24:19Z"),
                sample()[1]]
        self.assertEqual(self.check(rows)["state"], "UNKNOWN_FUTURE_LOG_CLOCK")

    def test_recent_claim_is_not_attestation(self):
        at = "2026-11-08T12:42:00Z"
        rows = [line("VPS_RAM_USATA_PERCENTO", "32.5", at),
                line("VPS_DISCO_USATO_PERCENTO", "12.5", at)]
        x = self.check(rows)
        self.assertEqual(x["state"], "TIMESTAMP_RECENT_BUT_UNAUTHENTICATED_AND_INCOMPLETE")
        self.assertFalse(x["sourceLogAuthenticityVerified"])
        self.assertFalse(x["vpsCurrentHeadroomVerified"])
        self.assertFalse(x["oracleBillingVerified"])
        self.assertEqual(x["operationalDecision"], mod.NO_GO)

    def test_historical_pressure_flag_without_research_activation(self):
        x = self.check([line("VPS_RAM_USATA_PERCENTO", "85"),
                        line("VPS_DISCO_USATO_PERCENTO", "12")])
        self.assertEqual(x["historicPressureClassification"], "HISTORICAL_THRESHOLD_EXCEEDED")
        self.assertEqual(x["newVpsRequests"], 0)
        self.assertEqual(x["newProviderCalls"], 0)
        self.assertFalse(x["researchLiveEnabled"])

if __name__ == "__main__":
    unittest.main()
