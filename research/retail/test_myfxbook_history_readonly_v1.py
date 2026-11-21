"""REMURA Retail Observatory v0.1 LAB — 10 new-only offline audit cases."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import os

from myfxbook_history_readonly_v1 import audit, SOURCE
NOW = "2026-11-21T22:55:00Z"
SAMPLE = {
    "t": "2026-11-21T21:43:42Z",
    "lPct": 79.0, "sPct": 21.0,
    "lLots": 226.16, "sLots": 60.04,
    "lPos": 972, "sPos": 365, "avgL": 112.7242, "avgS": 106.7566
}

def generate(root):
    root.mkdir(parents=True)
    (root / "history").mkdir()
    latest = {"status":"ok","source":SOURCE,"updatedAt":SAMPLE["t"],"symbols":{"CADJPY":SAMPLE}}
    hist={"symbol":"CADJPY","source":SOURCE,
          "sampling":"observed at recorded timestamps (not guaranteed 20m)",
          "records":[dict(SAMPLE)]}
    (root / "latest.json").write_text(json.dumps(latest),encoding="utf-8")
    (root / "history"/"CADJPY.json").write_text(json.dumps(hist),encoding="utf-8")
    return latest,hist

def write(root, latest, hist):
    (root/"latest.json").write_text(json.dumps(latest),encoding="utf-8")
    (root/"history"/"CADJPY.json").write_text(json.dumps(hist),encoding="utf-8")

class RetailReadOnlyAudit(TestCase):
    def in_dir(self, fn):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/"myfxbook"
            latest,hist=generate(root)
            return fn(root,latest,hist)

    def test_01_real_repository_histories_are_consistent_without_provenance_claim(self):
        root = Path(__file__).resolve().parents[2] / "data" / "myfxbook"
        latest=json.loads((root/"latest.json").read_text(encoding="utf-8"))
        now=(datetime.fromisoformat(latest["updatedAt"].replace("Z","+00:00"))+
             timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result=audit(root,now_utc=now)
        self.assertEqual(result["status"], "REPOSITORY_HISTORY_PARTIAL_LEGACY_UNATTESTED",result)
        self.assertEqual(result["historical_only_legacy_series"],4)
        self.assertEqual(result["current_series"],30)
        self.assertGreaterEqual(result["symbols_in_latest"],1)
        self.assertGreaterEqual(result["series_checked"],1)
        self.assertGreaterEqual(result["records_checked"],result["series_checked"])
        self.assertFalse(result["external_source_first_seen_verified"])
        self.assertFalse(result["retail_is_institutional"])
        self.assertEqual(result["provider_calls"],0)
        self.assertFalse(result["data_modified"])

    def test_02_consistent_synthetic_file_without_false_external_attestation(self):
        def run(root,latest,hist):
            r=audit(root,now_utc=NOW)
            self.assertEqual(r["status"],"REPOSITORY_HISTORY_STRUCTURALLY_CONSISTENT_UNATTESTED")
            self.assertEqual(r["series_checked"],1)
            self.assertFalse(r["holdout_causal_admission"])
        self.in_dir(run)

    def test_03_duplicate_json_keys_denied(self):
        def run(root,latest,hist):
            text='{"status":"ok","status":"ok","source":"'+SOURCE+'","updatedAt":"'+SAMPLE["t"]+'","symbols":{}}'
            (root/"latest.json").write_text(text,encoding="utf-8")
            self.assertEqual(audit(root,now_utc=NOW)["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_04_history_timestamp_regression_denied(self):
        def run(root,latest,hist):
            previous=dict(SAMPLE,t="2026-11-21T20:00:00Z")
            hist["records"]=[dict(SAMPLE),previous]
            write(root,latest,hist)
            self.assertEqual(audit(root,now_utc=NOW)["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_05_latest_history_split_brain_rejected(self):
        def run(root,latest,hist):
            hist["records"][-1]["lPct"]=1.0
            write(root,latest,hist)
            self.assertEqual(audit(root,now_utc=NOW)["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_06_unknown_extra_source_field_denied(self):
        def run(root,latest,hist):
            hist["records"][-1]["fake_provenance_verified"]=True
            write(root,latest,hist)
            self.assertEqual(audit(root,now_utc=NOW)["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_07_future_snapshot_is_not_retroactively_accepted(self):
        def run(root,latest,hist):
            self.assertEqual(audit(root,now_utc="2026-11-21T21:00:00Z")["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_08_absent_histories_do_not_prove_zero_activity(self):
        def run(root,latest,hist):
            (root/"history"/"CADJPY.json").unlink()
            r=audit(root,now_utc=NOW)
            self.assertEqual(r["status"],"UNVERIFIED_OR_INCOMPLETE")
            self.assertIsNone(r["records_checked"])
        self.in_dir(run)

    def test_09_symlinked_history_not_followed(self):
        def run(root,latest,hist):
            target=root/"history"/"CADJPY.json"
            target.unlink()
            target.symlink_to(root/"latest.json")
            self.assertEqual(audit(root,now_utc=NOW)["status"],"UNVERIFIED_OR_INCOMPLETE")
        self.in_dir(run)

    def test_11_legacy_only_series_does_not_count_as_current(self):
        def run(root,latest,hist):
            legacy_row=dict(SAMPLE,t="2026-10-22T01:38:06Z")
            legacy={"symbol":"US500","source":SOURCE,
                    "sampling":"observed approximately every 20 minutes",
                    "records":[legacy_row]}
            (root/"history"/"US500.json").write_text(json.dumps(legacy),encoding="utf-8")
            r=audit(root,now_utc=NOW)
            self.assertEqual(r["status"],"REPOSITORY_HISTORY_PARTIAL_LEGACY_UNATTESTED")
            self.assertEqual(r["historical_only_legacy_series"],1)
            self.assertEqual(r["current_series"],1)
            self.assertFalse(r["holdout_causal_admission"])
        self.in_dir(run)

    def test_10_staleness_is_reported_separately_from_a_valid_file(self):
        def run(root,latest,hist):
            r=audit(root,now_utc="2026-11-22T12:00:00Z")
            self.assertEqual(r["status"],"REPOSITORY_HISTORY_STRUCTURALLY_CONSISTENT_UNATTESTED")
            self.assertFalse(r["latest_snapshot_is_fresh_2h"])
            self.assertFalse(r["external_source_first_seen_verified"])
        self.in_dir(run)
