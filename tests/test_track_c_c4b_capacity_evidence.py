"""Track C4b(a) synthetic resource snapshots; no real services or network."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import track_c_c4b_capacity_evidence as gate

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)

def clock(dt):
    return dt.isoformat().replace("+00:00", "Z")

def sample(mins=0, ram=50, disk=30, swap=0, load=.25, uptime=1000):
    return {
        "schema": "remura-resources-v1", "sampledAt": clock(NOW + timedelta(minutes=mins)),
        "memory": {"total": 100_000, "used": int(ram * 1000),
                   "swapTotal": 100_000, "swapUsed": swap},
        "cpu": {"logical": 2, "load1": load},
        "disk": {"total": 10_000_000_000, "used": int(disk * 100_000_000)},
        "uptimeSeconds": uptime,
    }

def files(at=NOW):
    return {"sampledAt": clock(at), **{k: 1_000 for k in gate.FILE_KEYS}}

class ResourceEvidenceOffline(unittest.TestCase):
    def audit(self, snapshots=(), file_manifest=None):
        return gate.evaluate(snapshots, observed_at=clock(NOW),
                             file_manifest=file_manifest, mode=gate.MODE)

    def test_empty_and_missing_manifest_are_not_zero_consumption(self):
        x = self.audit()
        self.assertEqual(x["state"], "UNKNOWN_NO_RUNTIME_SAMPLE")
        self.assertEqual(x["pressure"], "UNKNOWN")
        self.assertEqual(x["sqliteWalInventory"], "UNKNOWN_NO_SQLITE_WAL_INVENTORY")
        self.assertIsNone(x["maxRamUsedPct"])
        self.assertIsNone(x["sqliteWalBackupSuppliedBytes"])
        self.assertEqual(x["newProviderCalls"], 0)

    def test_single_fresh_sample_is_not_continuity_and_never_go(self):
        x = self.audit([sample()])
        self.assertEqual(x["state"], "SINGLE_SAMPLE_NO_CONTINUITY_PROOF")
        self.assertEqual(x["maxRamUsedPct"], 50)
        self.assertEqual(x["maxDiskUsedPct"], 30)
        self.assertEqual(x["pressure"], "ONLY_SAMPLED_RESOURCE_HEADROOM_NOT_A_GO")
        self.assertEqual(x["operationalDecision"], "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION")

    def test_two_ordered_samples_only_unattested_runtime(self):
        x = self.audit([sample(mins=-2, uptime=880), sample(mins=0, uptime=1000)], files())
        self.assertEqual(x["state"], "MULTIPLE_SAMPLES_UNATTESTED_RUNTIME")
        self.assertEqual(x["sqliteWalInventory"], "SUPPLIED_UNATTESTED_FILE_SIZE_COUNTERS_ONLY")
        self.assertEqual(x["sqliteWalBackupSuppliedBytes"], 7000)
        self.assertFalse(x["backupRestoreTestVerified"])
        self.assertFalse(x["oracleBillingVerified"])

    def test_stale_historical_sample_not_current_measurement(self):
        x = self.audit([sample(mins=-60)])
        self.assertEqual(x["state"], "UNKNOWN_STALE_SAMPLE")
        self.assertEqual(x["pressure"], "UNKNOWN")
        self.assertEqual(x["validFreshSamples"], 0)

    def test_future_clock_and_bad_timezone_fail_closed(self):
        bad = sample(mins=1)
        x = self.audit([bad])
        self.assertEqual(x["invalidSamples"], 1)
        bad = sample()
        bad["sampledAt"] = "2026-11-09T13:00:00+01:00"
        self.assertEqual(self.audit([bad])["state"], "UNKNOWN_INVALID_SAMPLE")

    def test_ram_disk_pressure_swap_and_high_load_are_cautions(self):
        for change in ({"ram": 85}, {"disk": 82}, {"swap": 10}, {"load": 1.8}):
            with self.subTest(change=change):
                x = self.audit([sample(**change)])
                self.assertEqual(x["pressure"], "RESEARCH_PRESSURE_ALERT")
                self.assertFalse(x["cpuLoadIsUsagePercent"])

    def test_restart_and_reversed_clocks_not_continuity(self):
        x = self.audit([sample(mins=-2, uptime=1000), sample(uptime=1)])
        self.assertEqual(x["state"], "UNKNOWN_CLOCK_OR_RESTART")
        x = self.audit([sample(mins=0, uptime=1000), sample(mins=-2, uptime=900)])
        self.assertEqual(x["state"], "UNKNOWN_CLOCK_OR_RESTART")

    def test_invalid_or_missing_dimensions_never_safe(self):
        cases = []
        a = sample(); a["memory"]["total"] = None; cases.append(a)
        a = sample(); a["disk"]["used"] = -1; cases.append(a)
        a = sample(); a["cpu"]["load1"] = float("nan"); cases.append(a)
        a = sample(); a["memory"]["used"] = a["memory"]["total"] + 1; cases.append(a)
        a = sample(); a["memory"]["used"] = True; cases.append(a)
        for item in cases:
            with self.subTest(case=item):
                self.assertEqual(self.audit([item])["pressure"], "UNKNOWN")

    def test_no_payload_account_or_secrets_in_untrusted_snapshot(self):
        a = sample(); a["token"] = "NOT_FOR_OUTPUT"
        x = self.audit([a])
        self.assertEqual(x["state"], "UNKNOWN_INVALID_SAMPLE")
        self.assertNotIn("NOT_FOR_OUTPUT", repr(x))
        self.assertNotIn("EURUSD", repr(x))

    def test_manifest_missing_invalid_stale_and_size_guard(self):
        self.assertEqual(self.audit([sample()], files(NOW-timedelta(hours=1)))["sqliteWalInventory"],
                         "UNKNOWN_INVALID_OR_STALE_SQLITE_WAL_INVENTORY")
        wrong = files(); wrong["coreDbBytes"] = "1000"
        self.assertEqual(self.audit([sample()], wrong)["sqliteWalBackupSuppliedBytes"], None)
        wrong = files(); wrong["path"] = "/opt/remura/private"
        self.assertEqual(self.audit([sample()], wrong)["sqliteWalBackupSuppliedBytes"], None)

    def test_explicit_mode_and_bounded_list(self):
        with self.assertRaisesRegex(ValueError, "explicit_offline"):
            gate.evaluate([], observed_at=clock(NOW))
        with self.assertRaisesRegex(ValueError, "bounded_sanitized"):
            self.audit([sample()] * 9)

    def test_no_go_even_for_perfect_synthetic_measurements(self):
        x = self.audit([sample(mins=-1, uptime=940), sample(mins=0, uptime=1000)], files())
        self.assertEqual(x["operationalDecision"], "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION")
        for k in ("oracleBillingVerified", "firestoreBillingVerified", "githubUsageBillingVerified",
                  "backupRestoreTestVerified", "coreSurvivalOnLiveVerified", "realFirstSeenVerified"):
            self.assertFalse(x[k])

if __name__ == "__main__":
    unittest.main()
