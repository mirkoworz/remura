"""Track C3c-a: verify ACTUAL source owner schedule by static AST and YAML.

All fixtures operate in disposable temporary directories. No importing
private_server, opening any provider, GitHub/Oracle runtime probe, broker,
trading, secrets, cron or live source mutations.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import track_c_c3c_scheduler_source_contract as audit

SOURCE_PATHS=(
    "scripts/private_server.py",
    ".github/workflows/myfxbook.yml",
    "scripts/track_c_c3bc_frozen_plan.py",
)


class ActualSourceScheduleContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="remura-c3c-static-")
        self.root=Path(self.temp.name)
        for relative in SOURCE_PATHS:
            src=ROOT/relative
            dst=self.root/relative
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)

    def tearDown(self):
        self.temp.cleanup()

    def scan(self,*,root=None,mode=audit.MODE):
        return audit.inspect(root=self.root if root is None else root,
                             mode=mode)

    def change(self,relative,old,new):
        path=self.root/relative
        value=path.read_text(encoding="utf-8")
        if value.count(old)!=1:
            raise AssertionError("source fixture anchor must be unique "+old)
        path.write_text(value.replace(old,new),encoding="utf-8")

    def test_true_repository_schedule_differs_from_frozen_lab_policy(self):
        result=self.scan()
        self.assertEqual(result["status"],
                         "OFFLINE_SOURCE_REPOSITORY_CADENCE_AUDITED")
        cadence=result["cadences"]
        self.assertEqual(cadence["cotCoreSecondsAfterCompletion"],21600)
        self.assertEqual(cadence["ctraderBatchQuarterSeconds"],900)
        self.assertEqual(cadence["ctraderAfterQuarterGraceSeconds"],90)
        self.assertEqual(cadence["privateRetailCycleSeconds"],1200)
        self.assertEqual(cadence["myfxbookActionsCronUtc"],
                         "7,27,47 * * * *")
        self.assertEqual(len(result["approvedSourceSemanticsSha256"]),64)
        self.assertFalse(result["liveCadenceEqualsFrozenLabPlan"])
        self.assertFalse(result["liveScanTimesReconstructibleExactly"])
        self.assertFalse(result["perSymbolM15EveryQuarterProven"])
        self.assertFalse(result["githubCronRunsOnTimeProven"])
        self.assertFalse(result["actualRuntimeConfigurationVerified"])
        self.assertTrue(result["collectorDefaultsStillOff"])
        self.assertEqual(result["newProviderCalls"],0)

    def test_frozen_lab_weekly_cot_is_not_six_hour_core_cot(self):
        data=self.scan()
        self.assertEqual(data["cadences"]["cotCoreSecondsAfterCompletion"],6*3600)
        self.assertFalse(data["cotReportPublishedAtPoll"])

    def test_two_distinct_retail_paths_not_conflated(self):
        data=self.scan()
        self.assertEqual(data["cadences"]["privateRetailCycleSeconds"],20*60)
        self.assertEqual(data["cadences"]["myfxbookActionsCronUtc"],
                         "7,27,47 * * * *")
        self.assertFalse(data["retailProviderUpdatedAtPoll"])

    def test_source_drift_core_cot_interval_fails_closed(self):
        self.change("scripts/private_server.py",
                    "stop.wait(6*3600)","stop.wait(4*3600)")
        with self.assertRaisesRegex(ValueError,"scheduler_source_drift_cot"):
            self.scan()

    def test_source_drift_ctrader_batch_cadence_fails_closed(self):
        self.change("scripts/private_server.py",
                    "stop.wait(seconds_to_next_quarter())",
                    "stop.wait(600)")
        with self.assertRaisesRegex(ValueError,"scheduler_source_drift_ctrader"):
            self.scan()

    def test_source_drift_ctrader_grace_fails_closed(self):
        self.change("scripts/private_server.py",
                    "quarter+90","quarter+60")
        with self.assertRaisesRegex(ValueError,"scheduler_source_drift_ctrader"):
            self.scan()

    def test_source_drift_private_retail_interval_fails_closed(self):
        self.change("scripts/private_server.py",
                    "stop.wait(next_cycle(20*60,90))",
                    "stop.wait(next_cycle(30*60,90))")
        with self.assertRaisesRegex(ValueError,"scheduler_source_drift_vps"):
            self.scan()

    def test_source_drift_github_retail_cron_fails_closed(self):
        self.change(".github/workflows/myfxbook.yml",
                    "7,27,47 * * * *","0,20,40 * * * *")
        with self.assertRaisesRegex(ValueError,"myfxbook_actions_cron"):
            self.scan()

    def test_default_off_retail_toggle_cannot_be_silently_changed(self):
        self.change("scripts/private_server.py",
                    'os.environ.get("REMURA_RETAIL_ENABLED","0")',
                    'os.environ.get("REMURA_RETAIL_ENABLED","1")')
        with self.assertRaisesRegex(ValueError,
                                    "scheduler_enablement_contract_drift"):
            self.scan()

    def test_frozen_plan_drift_requires_new_explicit_review(self):
        self.change("scripts/track_c_c3bc_frozen_plan.py",
                    '("retail","30m-synthetic-poll",1800)',
                    '("retail","20m-synthetic-poll",1200)')
        with self.assertRaisesRegex(ValueError,"unreviewed_lab_policy_changed"):
            self.scan()

    def test_missing_schedule_source_is_unknown_not_fabricated(self):
        (self.root/".github/workflows/myfxbook.yml").unlink()
        with self.assertRaisesRegex(ValueError,
                                    "scheduler_source_file_missing"):
            self.scan()

    def test_explicit_lab_mode_and_no_default_live_work(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            self.scan(mode=None)
        safe=self.scan()
        self.assertFalse(safe["liveEnabled"])
        self.assertFalse(safe["providerDataFreshnessGuaranteed"])
        self.assertFalse(safe["externalCostsVerified"])


if __name__=="__main__":
    unittest.main()
