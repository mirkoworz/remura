"""V20.8 NEW-ONLY offline tests: mock GitHub replies; synthetic private choices only."""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
import json
import unittest

from v208_github_decision_witness import (
    ANCHOR_BRANCH, ANCHOR_WORKFLOW, COMMITMENT_SCHEMA, REPOSITORY,
    REPOSITORY_ID, commitment, manifest_for, witness_ledger,
    verified_evaluation,
)

UTC = timezone.utc
ASOF = datetime(2026, 11, 23, 7, 0, tzinfo=UTC)
GIT_SHA = "b" * 40
RUN_ID = 45199912345


def decision():
    return {
        "decision_id": "synthetic_future_00001",
        "event_close_utc": "2026-11-23T04:30:00Z",
        "received_at_utc": "2026-11-23T04:30:14Z",
        "recorded_at_utc": "2026-11-23T04:31:00Z",
        "frozen_at_utc": "2026-11-23T04:32:00Z",
        "price_only_known_at_utc": "2026-11-23T04:31:30Z",
        "cvd_side": "LONG",
        "price_only_side": "FLAT",
        "observations_count": 1,
        "decision_nonce": "0123456789abcdef" * 2,
        "anchor": {"kind": "github_commit", "workflow_run_id": RUN_ID},
    }


def ledger(row=None):
    return {
        "schema": "remura-v207-prospective-decision-ledger-v1",
        "symbol": "EURUSD", "signal_family": "CVD_PROXY_M5",
        "decisions": [row or decision()],
    }


def github_run(*, created="2026-11-23T04:38:11Z"):
    return {"id": RUN_ID, "status": "completed",
            "conclusion": "success", "event": "push",
            "head_branch": ANCHOR_BRANCH, "path": ANCHOR_WORKFLOW,
            "head_sha": GIT_SHA, "created_at": created,
            "repository": {"id": REPOSITORY_ID, "full_name": REPOSITORY}}


def manifest_response(row):
    digest = commitment(row)
    path = f"research/forward-anchors/{digest}.json"
    return {
        "type": "file", "path": path, "encoding": "base64",
        "content": base64.b64encode(json.dumps(manifest_for(row)).encode()).decode(),
    }


class MockGetter:
    def __init__(self, row, *, run=None, manifest=None):
        self.urls = []
        self.run = github_run() if run is None else run
        self.manifest = manifest_response(row) if manifest is None else manifest

    def __call__(self, url):
        self.urls.append(url)
        if "/actions/runs/" in url:
            return copy.deepcopy(self.run)
        if "/contents/research/forward-anchors/" in url:
            return copy.deepcopy(self.manifest)
        raise AssertionError("unexpected network endpoint")


def synthetic_prices():
    rows = []
    start = datetime(2026, 11, 23, 4, 45, tzinfo=UTC)
    for i in range(8):
        t = start + timedelta(minutes=15*i)
        rows.append({"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "o": 1.1000, "h": 1.1003, "l": 1.0999, "c": 1.1002})
    return {"symbol": "EURUSD", "provider": "ctrader",
            "providerSymbol": "SYNTHETIC_ONLY", "timeframes": {"M15": rows}}


class V208NewOnly(unittest.TestCase):
    def test_no_real_ledger_never_triggers_git_api_or_alpha(self):
        def forbid(_):
            self.fail("unexpected_network")
        r = verified_evaluation(None, None, as_of=ASOF, fetch_json=forbid)
        self.assertFalse(r["github_hash_only_witness_verified"])
        self.assertFalse(r["scientific_alpha_established"])
        self.assertEqual(r["unique_m15_decisions"], 0)

    def test_manifest_contains_only_blinded_hash_not_private_data(self):
        d = decision()
        m = manifest_for(d)
        self.assertEqual(set(m), {"schema", "commitment_sha256"})
        self.assertEqual(m["schema"], COMMITMENT_SCHEMA)
        dumped = json.dumps(m)
        for item in ("EURUSD","LONG","decision_id","synthetic_future_","012345"):
            self.assertNotIn(item, dumped)
        self.assertEqual(len(m["commitment_sha256"]),64)

    def test_server_run_timestamp_overrides_user_claimed_commit_time(self):
        d = decision()
        d["anchor"]["committed_at_utc"] = "2026-11-23T04:00:00Z"
        f = MockGetter(d)
        witnessed = witness_ledger(ledger(d), as_of=ASOF, fetch_json=f)
        self.assertEqual(witnessed["decisions"][0]["anchor"]["committed_at_utc"],
                         "2026-11-23T04:38:11Z")
        self.assertEqual(witnessed["decisions"][0]["anchor"]["sha"], GIT_SHA)
        self.assertEqual(len(f.urls), 2)
        self.assertTrue(f.urls[0].endswith(str(RUN_ID)))
        self.assertIn(f"?ref={GIT_SHA}", f.urls[1])

    def test_verified_commitment_is_not_cvd_feed_proof_or_alpha(self):
        d = decision()
        f = MockGetter(d)
        r = verified_evaluation(ledger(d), synthetic_prices(), as_of=ASOF, fetch_json=f)
        self.assertEqual(r["unique_m15_decisions"],1)
        self.assertTrue(r["github_hash_only_witness_verified"])
        self.assertFalse(r["underlying_cvd_receipt_provenance_independently_verified"])
        self.assertFalse(r["independent_price_feed_authenticity_externally_verified"])
        self.assertFalse(r["scientific_alpha_established"])
        self.assertEqual(r["horizons"]["60m"]["complete_matched_m15_windows"],1)

    def test_mutating_side_after_manifest_is_refused(self):
        initial = decision()
        altered = copy.deepcopy(initial)
        altered["cvd_side"] = "SHORT"
        with self.assertRaisesRegex(ValueError, "wrong_immutable|does_not_match"):
            witness_ledger(ledger(altered), as_of=ASOF,
                           fetch_json=MockGetter(initial))

    def test_mutating_baseline_or_timestamp_after_manifest_is_refused(self):
        initial = decision()
        for key, value in (("price_only_side","SHORT"),
                           ("recorded_at_utc","2026-11-23T04:31:13Z")):
            altered = copy.deepcopy(initial)
            altered[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,"wrong_immutable|does_not_match"):
                witness_ledger(ledger(altered), as_of=ASOF,
                               fetch_json=MockGetter(initial))

    def test_bad_nonce_and_missing_nonce_rejected_locally(self):
        for bad in ("","00","zz"*16, None):
            d = decision()
            d["decision_nonce"] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError,"nonce"):
                commitment(d)

    def test_wrong_historical_git_path_or_manifest_hash_refused(self):
        d = decision()
        m = manifest_response(d)
        m["path"] = "README.md"
        with self.assertRaisesRegex(ValueError,"wrong_immutable"):
            witness_ledger(ledger(d), as_of=ASOF,
                           fetch_json=MockGetter(d,manifest=m))
        m = manifest_response(d)
        m["content"] = base64.b64encode(b'{"schema":"wrong","commitment_sha256":"deadbeef"}').decode()
        with self.assertRaisesRegex(ValueError,"wrong_immutable|does_not_match"):
            witness_ledger(ledger(d), as_of=ASOF,
                           fetch_json=MockGetter(d,manifest=m))

    def test_wrong_repo_branch_workflow_or_event_is_refused(self):
        d = decision()
        for key,bad in (("head_branch","main"),
                        ("path",".github/workflows/other.yml"),
                        ("event","workflow_dispatch"),
                        ("conclusion","failure")):
            run=github_run()
            run[key]=bad
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "untrusted"):
                witness_ledger(ledger(d), as_of=ASOF,
                               fetch_json=MockGetter(d,run=run))
        run=github_run()
        run["repository"]["id"]=0
        with self.assertRaisesRegex(ValueError,"repository"):
            witness_ledger(ledger(d), as_of=ASOF,
                           fetch_json=MockGetter(d,run=run))

    def test_future_or_stale_remote_witness_refused(self):
        d=decision()
        for now in ("2026-11-24T09:00:00Z","2026-11-23T05:04:00Z"):
            run=github_run(created=now)
            with self.subTest(now=now), self.assertRaises(ValueError):
                witness_ledger(ledger(d), as_of=ASOF,
                               fetch_json=MockGetter(d,run=run))

    def test_claimed_sha_mismatch_refused(self):
        d=decision()
        d["anchor"]["sha"]="a"*40
        with self.assertRaisesRegex(ValueError,"claimed_sha"):
            witness_ledger(ledger(d), as_of=ASOF, fetch_json=MockGetter(d))

    def test_request_budget_limited_before_remote_io(self):
        d=decision()
        j=ledger(d)
        j["decisions"]=[copy.deepcopy(d) for _ in range(6)]
        def forbid(_):
            self.fail("no remote traffic on overbudget ledger")
        with self.assertRaisesRegex(ValueError,"too_many"):
            witness_ledger(j, as_of=ASOF, fetch_json=forbid)
        with self.assertRaisesRegex(ValueError,"missing_or_too_many"):
            witness_ledger(ledger().__class__({"schema":ledger()["schema"],
                          "decisions":[]}), as_of=ASOF, fetch_json=forbid)

    def test_no_private_row_or_nonce_leaks_into_github_urls(self):
        d=decision()
        f=MockGetter(d)
        witness_ledger(ledger(d), as_of=ASOF, fetch_json=f)
        sent="\n".join(f.urls)
        for word in ("EURUSD","LONG","synthetic_future","0123456789"):
            self.assertNotIn(word,sent)
        self.assertIn("api.github.com",sent)


if __name__ == "__main__":
    unittest.main()
