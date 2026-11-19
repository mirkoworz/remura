"""Synthetic no-network safety tests for future Oracle lab one-shot co-load."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from scripts import shark_oracle_cvd_coload_gate as gate


def valid():
    return {
        "schema":"remura-synthetic-dual-db-coload-v1",
        "status":"GITHUB_SYNTHETIC_ONLY_ORACLE_NO_GO",
        "priceMarketsIngested":34,"cvdPilotScans":2,
        "cvdMarketsNotCovered":32,"syntheticRestoreBothSqlites":True,
        "crossDatabaseAtomicSnapshot":False,
        "realOracleCpuQuotaMeasured":False,
        "realOracleP95P99LockMeasured":False,
        "actualCollectorBrokerRequestsMade":0,
        "liveIngestInterferenceCertified":False,
        "releaseAuthorized":False,"tradingEdgeProven":False,
        "jointProcessCpuSeconds":0.166,
        "jointProcessWallSeconds":0.193,
        "rssBeforeMiB":32.72,"rssAfterMiB":35.96,
    }


def input_of(doc):
    return gate.CHILD_PREFIX + json.dumps(doc,sort_keys=True)


class OracleIsolatedCvdColoadTests(unittest.TestCase):
    def test_synthetic_redacted_report_is_accepted_but_never_promoted_to_go(self):
        parsed=gate._parse_child(input_of(valid()))
        self.assertIs(parsed["releaseAuthorized"],False)
        self.assertEqual(parsed["cvdMarketsNotCovered"],32)
        self.assertFalse(parsed["crossDatabaseAtomicSnapshot"])

    def test_all_false_or_unknown_certifications_must_stay_unproven(self):
        base=valid()
        for field in ("crossDatabaseAtomicSnapshot",
                      "realOracleCpuQuotaMeasured",
                      "realOracleP95P99LockMeasured",
                      "liveIngestInterferenceCertified",
                      "releaseAuthorized","tradingEdgeProven"):
            with self.subTest(field=field):
                wrong=copy.deepcopy(base)
                wrong[field]=True
                with self.assertRaisesRegex(ValueError,"unexpected_synthetic_claims"):
                    gate._parse_child(input_of(wrong))

    def test_denominator_missing_broker_calls_and_fake_restore_fail(self):
        for field,value in (("priceMarketsIngested",33),
                            ("cvdPilotScans",34),
                            ("cvdMarketsNotCovered",0),
                            ("actualCollectorBrokerRequestsMade",1),
                            ("syntheticRestoreBothSqlites",False),
                            ("status","LIVE_ENABLED")):
            with self.subTest(field=field):
                d=valid()
                d[field]=value
                with self.assertRaises(ValueError):
                    gate._parse_child(input_of(d))

    def test_bounded_types_and_duplicate_reports(self):
        for field,value in (("jointProcessCpuSeconds",-1),
                            ("jointProcessWallSeconds",0),
                            ("jointProcessWallSeconds",1000),
                            ("rssAfterMiB",130),
                            ("rssBeforeMiB",float("nan")),
                            ("cvdPilotScans",True)):
            with self.subTest(field=field):
                d=valid()
                d[field]=value
                with self.assertRaises(ValueError):
                    gate._parse_child(input_of(d))
        raw=input_of(valid())
        for bad in ("",raw+"\n"+raw,raw+"x"*10000,
                    gate.CHILD_PREFIX+"not-json"):
            with self.assertRaises(ValueError):
                gate._parse_child(bad)

    def test_guard_blocks_production_path_without_starting_child(self):
        with patch.object(gate.safety,"ROOT",Path("/opt/remura")):
            with patch.object(gate.subprocess,"Popen",
                              side_effect=AssertionError("child_was_launched")):
                with self.assertRaisesRegex(RuntimeError,"staging_checkout"):
                    gate.run()

    def test_guard_blocks_root_and_low_free_disk_without_spawn(self):
        with patch.object(gate.safety,"ROOT",Path("/tmp/trusted-synthetic-lab")):
            with patch.object(gate.safety.os,"geteuid",return_value=0):
                with patch.object(gate.subprocess,"Popen",
                                  side_effect=AssertionError("child_was_launched")):
                    with self.assertRaisesRegex(RuntimeError,"as_root"):
                        gate.run()

    def test_refuses_existing_live_service_even_under_tmp(self):
        with patch.object(gate.safety,"guard_host",return_value=None):
            with patch.object(gate.os.path,"lexists",return_value=True):
                with patch.object(gate.subprocess,"Popen",
                                  side_effect=AssertionError("child_was_launched")):
                    with self.assertRaisesRegex(RuntimeError,
                                                 "live_host_footprint"):
                        gate.run()

    def test_refuses_unconfirmed_lab_even_with_no_live_footprint(self):
        with patch.object(gate.safety,"guard_host",return_value=None):
            with patch.object(gate.os.path,"lexists",return_value=False):
                with patch.dict(gate.os.environ,{},clear=True):
                    with patch.object(gate.subprocess,"Popen",
                                      side_effect=AssertionError("child_was_launched")):
                        with self.assertRaisesRegex(RuntimeError,
                                                     "isolated_lab_attestation"):
                            gate.run()

    def test_command_is_only_existing_synthetic_suite(self):
        cmd=gate._command()
        self.assertEqual(cmd[1:5],["-B","-m","unittest","discover"])
        self.assertEqual(cmd[-3:-1],
                         ["-p","test_shark_cvd_coload_rehearsal.py"])
        self.assertNotIn("ssh"," ".join(cmd).lower())
        self.assertNotIn("curl"," ".join(cmd).lower())
        self.assertNotIn("pytest"," ".join(cmd).lower())

    def test_cli_requires_explicit_mode_and_self_check_has_no_host_access(self):
        self.assertEqual(gate.main(["invalid"]),2)
        with patch.object(gate.safety,"guard_host",
                          side_effect=AssertionError("host_guard_triggered")):
            self.assertEqual(gate.main(["--self-check"]),0)
        with patch.object(gate,"run",
                          side_effect=RuntimeError("explicit_only")):
            with self.assertRaisesRegex(RuntimeError,"explicit_only"):
                gate.main(["--run"])


if __name__=="__main__":
    unittest.main()
