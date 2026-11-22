# REMURA new tests: pinned, real EURUSD repository history only.
# No repetition of the 34-file Myfxbook audit and no network/provider calls.
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from myfxbook_pinned_real_replay_v02_lab import (
    PINNED_BLOB_SHA1,PINNED_SYMBOL,ROOT,ReplayError,replay,
)

class PinnedRealReplayTests(unittest.TestCase):
    def test_01_actual_repo_archive_identity_is_pinned(self):
        r=replay(decision_utc="2026-11-22T01:36:15Z")
        self.assertEqual(r["archive_git_blob_sha1"],PINNED_BLOB_SHA1)
        self.assertEqual(r["symbol"],PINNED_SYMBOL)
        self.assertEqual(r["snapshot_latest_utc"],"2026-11-22T01:36:15Z")
        self.assertEqual(r["record"]["t"],r["snapshot_latest_utc"])

    def test_02_before_earliest_archive_is_unknown_not_zero(self):
        r=replay(decision_utc="2026-10-01T00:00:00Z")
        self.assertEqual(r["status"],"UNKNOWN_NO_PRIOR_REPOSITORY_RECORD")
        self.assertIsNone(r["record"])

    def test_03_earlier_decision_never_uses_22_nov_snapshot(self):
        r=replay(decision_utc="2026-11-20T12:00:00Z")
        self.assertEqual(r["status"],"REPOSITORY_REPLAY_UNATTESTED")
        self.assertEqual(r["record"]["t"],"2026-11-20T11:18:32Z")
        self.assertNotEqual(r["record"]["t"],r["snapshot_latest_utc"])

    def test_04_decision_at_exact_record_local_clock_includes_only_that_record(self):
        r=replay(decision_utc="2026-11-20T11:18:32Z")
        self.assertEqual(r["record"]["t"],"2026-11-20T11:18:32Z")

    def test_05_decision_one_second_before_record_excludes_future_record(self):
        r=replay(decision_utc="2026-11-20T11:18:31Z")
        self.assertLess(r["record"]["t"],"2026-11-20T11:18:32Z")

    def test_06_not_a_provider_or_first_seen_attestation(self):
        r=replay(decision_utc="2026-11-22T01:36:15Z")
        for key in ("recorded_time_is_independent_first_seen",
                    "provider_publication_time_verified",
                    "source_available_at_decision_verified",
                    "spot_futures_mapping_verified",
                    "institutional_exposure_established",
                    "tradingview_holdout_scientific_admission",
                    "alpha_established","data_mutated"):
            self.assertIs(r[key],False)
        self.assertEqual(r["external_calls"],0)

    def test_07_future_decision_still_does_not_upgrade_attestation(self):
        r=replay(decision_utc="2026-11-30T01:00:00Z")
        self.assertEqual(r["record"]["t"],"2026-11-22T01:36:15Z")
        self.assertFalse(r["source_available_at_decision_verified"])

    def test_08_malformed_or_non_utc_decision_rejected(self):
        for s in ("2026-11-22T01:36:15+00:00","2026-11-22T02:36:15+01:00",
                  "2026-11-22T25:00:00Z",None):
            with self.assertRaises(ReplayError):
                replay(decision_utc=s)

    def test_09_mutated_file_fails_pinned_digest_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"history").mkdir()
            shutil.copyfile(ROOT/"latest.json",root/"latest.json")
            data=(ROOT/"history"/"EURUSD.json").read_bytes()
            (root/"history"/"EURUSD.json").write_bytes(data+b" ")
            with self.assertRaisesRegex(ReplayError,"pinned_git_blob_changed"):
                replay(decision_utc="2026-11-22T01:36:15Z",archive_root=root)

    def test_10_mutated_latest_fails_pinned_digest_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"history").mkdir()
            shutil.copyfile(ROOT/"history"/"EURUSD.json",root/"history"/"EURUSD.json")
            (root/"latest.json").write_bytes((ROOT/"latest.json").read_bytes()+b"\n")
            with self.assertRaisesRegex(ReplayError,"pinned_git_blob_changed"):
                replay(decision_utc="2026-11-22T01:36:15Z",archive_root=root)

    def test_11_real_archive_was_not_modified_by_replay(self):
        before=(ROOT/"history"/"EURUSD.json").read_bytes()
        replay(decision_utc="2026-11-20T12:00:00Z")
        self.assertEqual((ROOT/"history"/"EURUSD.json").read_bytes(),before)

    def test_12_no_trade_or_institutional_decision_output(self):
        r=replay(decision_utc="2026-11-21T12:00:00Z")
        self.assertTrue(set(r["record"])=={
            "t","lPct","sPct","lLots","sLots","lPos","sPos","avgL","avgS"})
        self.assertNotIn("buy",r)
        self.assertNotIn("predicted_direction",r)
        self.assertFalse(r["alpha_established"])

if __name__=="__main__":
    unittest.main()
