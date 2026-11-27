"""REMURA v1.65 synthetic-only read-only preflight; no VPS/DB/billing."""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "deploy" / "oracle"
sys.path.insert(0, str(DIR))
import v165_readonly_preflight_fixture as m


class V165ReadonlyPreflightFixtureTests(unittest.TestCase):
    def scenario(self, **changes):
        snap = m.fake_snapshot()
        for name, value in changes.items():
            if name in m.SIZE_FIELDS:
                snap["sizes"][name] = value
            else:
                snap[name] = value
        return m.assess_mock(snap)

    def test_default_mock_is_plausible_but_never_go(self):
        r = self.scenario()
        self.assertEqual(r["classification"],
                         "MOCK_CAPACITY_PLAUSIBLE_NOT_LIVE_PROOF")
        self.assertEqual(r["operationalDecision"], m.NO_GO)
        self.assertTrue(r["fakeDiskAboveReserve"])

    def test_nobody_mistakes_fake_for_live(self):
        r = self.scenario()
        for key in ("actualLiveInstalledShaVerified",
                    "actualOracleFreeCapacityMeasured",
                    "actualOracleBillingChecked",
                    "realTailscalePolicyChecked",
                    "actualCIPushMainVerified",
                    "realBackupOrRestorePerformed", "realVpsContacted",
                    "actualPrivateEvidenceCollected",
                    "databaseOpened", "productionWritePerformed",
                    "releaseAuthorized", "researchC5Enabled"):
            self.assertIs(r[key], False, key)

    def test_twelve_true_evidences_remain_missing(self):
        r = self.scenario()
        self.assertEqual(r["requiredRealEvidenceGates"], 12)
        self.assertEqual(r["missingRealEvidenceGates"], 12)

    def test_reserve_uses_wal_and_shm_not_only_db(self):
        r = self.scenario()
        expected = 4 * (16 + 2 + 1) * m.MIB + 3 * 2 * m.MIB + 512 * m.MIB
        self.assertEqual(r["fakeReserveBytes"], expected)

    def test_insufficient_fake_space_blocks(self):
        r = self.scenario(freeBytes=300*m.MIB)
        self.assertEqual(r["classification"], "STOP_FAKE_DISK_HEADROOM")

    def test_exact_reserve_does_not_count_as_free(self):
        reserve = self.scenario()["fakeReserveBytes"]
        r = self.scenario(freeBytes=reserve)
        self.assertFalse(r["fakeDiskAboveReserve"])
        self.assertEqual(r["classification"], "STOP_FAKE_DISK_HEADROOM")

    def test_missing_disk_measurement_is_unknown(self):
        r = self.scenario(freeBytes=None)
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")
        self.assertIsNone(r["fakeDiskAboveReserve"])
        self.assertIsNotNone(r["fakeReserveBytes"])

    def test_missing_db_measurement_is_unknown_no_reserve(self):
        r = self.scenario(dbBytes=None)
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")
        self.assertIsNone(r["fakeReserveBytes"])

    def test_missing_wal_measurement_is_not_silently_zero(self):
        r = self.scenario(walBytes=None)
        self.assertIsNone(r["fakeReserveBytes"])
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_missing_shm_measurement_is_not_silently_zero(self):
        r = self.scenario(shmBytes=None)
        self.assertIsNone(r["fakeReserveBytes"])
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_missing_inode_measurement_is_unknown(self):
        r = self.scenario(freeInodes=None)
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_low_inodes_are_blocking(self):
        r = self.scenario(freeInodes=m.REQUIRED_FREE_INODES-1)
        self.assertEqual(r["classification"], "STOP_FAKE_INODE_HEADROOM")
        self.assertFalse(r["fakeInodesAboveReserve"])

    def test_exactly_required_inodes_is_not_unknown(self):
        r = self.scenario(freeInodes=m.REQUIRED_FREE_INODES)
        self.assertTrue(r["fakeInodesAboveReserve"])

    def test_sha_mismatch_stops_before_capacity_plausibility(self):
        r = self.scenario(fakeInstalled="FAKE_MISMATCH",freeBytes=0)
        self.assertEqual(r["classification"], "STOP_FAKE_SHA_MISMATCH")

    def test_updater_sha_mismatch_stops(self):
        r = self.scenario(fakeUpdater="FAKE_MISMATCH")
        self.assertEqual(r["classification"], "STOP_FAKE_SHA_MISMATCH")

    def test_public_ingress_stops(self):
        r = self.scenario(fakeIngress="FAKE_PUBLIC")
        self.assertEqual(r["classification"], "STOP_FAKE_PUBLIC_INGRESS")

    def test_billing_risk_stops(self):
        r = self.scenario(fakeBilling="FAKE_BILLING_RISK")
        self.assertEqual(r["classification"], "STOP_FAKE_BILLING_RISK")

    def test_not_proven_ci_stops(self):
        r = self.scenario(fakeCi="FAKE_CI_UNVERIFIED")
        self.assertEqual(r["classification"], "STOP_FAKE_CI_UNVERIFIED")

    def test_unknown_ci_is_unknown_not_green(self):
        r = self.scenario(fakeCi="UNKNOWN")
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_unknown_billing_is_unknown(self):
        r = self.scenario(fakeBilling="UNKNOWN")
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_unknown_ingress_is_unknown(self):
        r = self.scenario(fakeIngress="UNKNOWN")
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_missing_age_is_unknown(self):
        r = self.scenario(metadataAgeSeconds=None)
        self.assertEqual(r["classification"], "UNKNOWN_NO_REAL_EVIDENCE")

    def test_stale_metadata_stops(self):
        r = self.scenario(metadataAgeSeconds=m.MAX_META_AGE_SECONDS+1)
        self.assertEqual(r["classification"], "STOP_FAKE_METADATA_STALE")

    def test_age_exactly_at_limit_is_not_stale(self):
        r = self.scenario(metadataAgeSeconds=m.MAX_META_AGE_SECONDS)
        self.assertEqual(r["classification"],
                         "MOCK_CAPACITY_PLAUSIBLE_NOT_LIVE_PROOF")

    def test_negative_and_bool_metrics_rejected(self):
        for metric in m.SIZE_FIELDS:
            for bad in (-1, True, False, 1.1, "500"):
                with self.subTest(metric=metric,bad=bad):
                    with self.assertRaisesRegex(m.MockPreflightError,
                                                "STOP_INVALID_BOUNDED_NUMBER"):
                        self.scenario(**{metric:bad})

    def test_required_nonzero_db_and_candidate(self):
        for metric in ("dbBytes","candidateBytes"):
            with self.subTest(metric=metric):
                with self.assertRaisesRegex(m.MockPreflightError,
                                            "STOP_INVALID_BOUNDED_NUMBER"):
                    self.scenario(**{metric:0})

    def test_unreasonably_large_values_rejected(self):
        invalid={
            "dbBytes":m.MAX_DATA_BYTES+1,
            "walBytes":m.MAX_DATA_BYTES+1,
            "shmBytes":m.MAX_DATA_BYTES+1,
            "candidateBytes":m.MAX_CANDIDATE_BYTES+1,
            "freeBytes":m.MAX_FREE_BYTES+1,
            "freeInodes":m.MAX_INODES+1,
        }
        for metric,bad in invalid.items():
            with self.subTest(metric=metric):
                with self.assertRaisesRegex(m.MockPreflightError,
                                            "STOP_INVALID_BOUNDED_NUMBER"):
                    self.scenario(**{metric:bad})

    def test_unknown_size_field_rejected_not_printed(self):
        snap=m.fake_snapshot()
        snap["sizes"]["privatePath"]="/opt/anything"
        with self.assertRaisesRegex(m.MockPreflightError,"STOP_STRICT_SIZE_FIELDS"):
            m.assess_mock(snap)

    def test_extra_input_field_rejected(self):
        snap=m.fake_snapshot()
        snap["token"]="FAKE"
        with self.assertRaisesRegex(m.MockPreflightError,"STOP_STRICT_FIXTURE_FIELDS"):
            m.assess_mock(snap)

    def test_missing_field_rejected(self):
        snap=m.fake_snapshot()
        del snap["fakeUpdater"]
        with self.assertRaisesRegex(m.MockPreflightError,"STOP_STRICT_FIXTURE_FIELDS"):
            m.assess_mock(snap)

    def test_wrong_input_type_rejected(self):
        for bad in (None,True,{},[],0, "FAKE"):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaisesRegex(m.MockPreflightError,
                                            "STOP_STRICT_FIXTURE_FIELDS"):
                    m.assess_mock(bad)

    def test_wrong_mode_rejected(self):
        for mode in ("LIVE","READONLY_LIVE",None,True,0,""):
            with self.subTest(mode=mode):
                snap=m.fake_snapshot()
                snap["mode"]=mode
                with self.assertRaisesRegex(m.MockPreflightError,
                                            "STOP_OFFLINE_FIXTURE_ONLY"):
                    m.assess_mock(snap)

    def test_bad_identity_type_or_unrecognized_value_rejected(self):
        for bad in (True,0,None,{}, "SHA_FROM_GITHUB", "V164"):
            with self.subTest(bad=bad):
                snap=m.fake_snapshot()
                snap["fakeInstalled"]=bad
                with self.assertRaisesRegex(m.MockPreflightError,
                                            "STOP_INVALID_FAKEINSTALLED"):
                    m.assess_mock(snap)

    def test_bad_fake_ci_type_rejected(self):
        snap=m.fake_snapshot()
        snap["fakeCi"]=True
        with self.assertRaisesRegex(m.MockPreflightError,
                                    "STOP_INVALID_FAKECI"):
            m.assess_mock(snap)

    def test_no_private_values_appear_in_report(self):
        output=json.dumps(self.scenario(),sort_keys=True)
        for forbidden in ("installedSha", "127.0.0.1", "accountId",
                          "apiKey", "/opt/", "privateKey", "secret"):
            self.assertNotIn(forbidden,output)

    def test_repeated_input_deterministic(self):
        a=m.fake_snapshot()
        self.assertEqual(m.assess_mock(a),m.assess_mock(copy.deepcopy(a)))

    def test_module_cannot_open_files_or_connect_services(self):
        source=(DIR/"v165_readonly_preflight_fixture.py").read_text()
        imports={x.name.partition(".")[0]
                 for node in ast.walk(ast.parse(source))
                 if isinstance(node,ast.Import) for x in node.names}
        self.assertTrue(imports.isdisjoint({
            "os","pathlib","subprocess","socket","sqlite3","urllib",
            "requests","shutil","fcntl","datetime","time"
        }))
        for forbidden in ("systemctl", "urlopen(", "connect(", "open(",
                          "/opt/remura", "statvfs(", "lstat(", "scandir("):
            self.assertNotIn(forbidden,source)
        for flag in ("--apply","--live","--host","--path","--json",
                     "--database","--target","--deploy","--restore"):
            self.assertNotIn('add_argument("'+flag+'"',source)

    def test_only_offline_cli_accepts_fixture(self):
        cmd=[sys.executable,str(DIR/"v165_readonly_preflight_fixture.py")]
        p=subprocess.run(cmd+["--check-synthetic-readonly"],cwd=ROOT,
                         check=True,timeout=12,capture_output=True,text=True)
        report=json.loads(p.stdout)
        self.assertEqual(report["requiredRealEvidenceGates"],12)
        self.assertEqual(report["missingRealEvidenceGates"],12)
        self.assertEqual(report["operationalDecision"],m.NO_GO)
        x=subprocess.run(cmd+["--apply"],cwd=ROOT,timeout=12,
                         capture_output=True,text=True)
        self.assertNotEqual(x.returncode,0)


if __name__=="__main__":
    unittest.main()
