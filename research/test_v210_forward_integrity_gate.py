"""REMURA V21.0 NEW-ONLY tests: synthetic source, private ledger, M15 and mocked GitHub.

No network, secrets, broker, D1, public decisions, or real alpha.
"""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import unittest

from v209_private_decision_freezer import freeze_candidate
from v210_forward_integrity_gate import adjudicate, local_integrity
from v208_github_decision_witness import (
    ANCHOR_BRANCH, ANCHOR_WORKFLOW, REPOSITORY, REPOSITORY_ID, manifest_for,
)

UTC = timezone.utc
FREEZE=datetime(2026,11,23,4,36,tzinfo=UTC)
NOW=datetime(2026,11,23,7,0,tzinfo=UTC)
SOURCE=b'{"test_only":true,"raw_bytes_from_future_original_source":1}'
RUN_ID=45999123456
SHA="b"*40


def market():
    start=datetime(2026,11,23,3,15,tzinfo=UTC)
    rows=[]
    for i in range(12):
        moment=start+timedelta(minutes=15*i)
        price=1.1000 + i*0.0001
        rows.append({
            "t":moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "o":round(price,5), "h":round(price+0.0002,5),
            "l":round(price-0.0002,5), "c":round(price+0.0001,5),
        })
    return {"symbol":"EURUSD","provider":"ctrader",
            "providerSymbol":"SYNTHETIC_CTRADER_NOT_REAL",
            "timeframes":{"M15":rows}}


def packed():
    event={
        "schema":"remura-v209-local-cvd-observation-v1",
        "symbol":"FX:EURUSD",
        "event_close_utc":"2026-11-23T04:35:00Z",
        "received_at_utc":"2026-11-23T04:35:05Z",
        "source_event_sha256":hashlib.sha256(SOURCE).hexdigest(),
        "cvd_side":"LONG",
    }
    return freeze_candidate(event,market(),as_of=FREEZE,nonce="ad"*16)


class MockGithub:
    def __init__(self, ledger, *, bad_run=None, bad_manifest=None):
        self.calls=[]
        row=ledger["decisions"][0]
        m=manifest_for(row)
        digest=m["commitment_sha256"]
        self.run={
            "id":RUN_ID, "event":"push","status":"completed",
            "conclusion":"success", "head_branch":ANCHOR_BRANCH,
            "path":ANCHOR_WORKFLOW,"head_sha":SHA,
            "created_at":"2026-11-23T04:38:11Z",
            "repository":{"id":REPOSITORY_ID,"full_name":REPOSITORY},
        }
        self.manifest={
            "type":"file", "path":f"research/forward-anchors/{digest}.json",
            "encoding":"base64",
            "content":base64.b64encode(json.dumps(m).encode()).decode(),
        }
        if bad_run:
            self.run.update(bad_run)
        if bad_manifest:
            self.manifest.update(bad_manifest)

    def __call__(self, url):
        self.calls.append(url)
        if "/actions/runs/" in url:
            return copy.deepcopy(self.run)
        if "/contents/research/forward-anchors/" in url:
            return copy.deepcopy(self.manifest)
        raise AssertionError("unexpected network endpoint")


class V210Only(unittest.TestCase):
    def test_locally_binds_original_bytes_and_rule_no_network(self):
        l,m=packed()
        got=local_integrity(l,m,SOURCE,market(),as_of=NOW)
        self.assertEqual(got["status"],"LOCAL_ORIGINAL_SOURCE_AND_BASELINE_CONSISTENT")
        self.assertTrue(got["baseline_rule_and_timestamp_consistent"])
        self.assertFalse(got["github_first_seen_witness_verified"])
        self.assertFalse(got["broker_market_data_history_independently_authenticated"])
        self.assertFalse(got["cvd_direction_independently_derived_from_source"])
        self.assertFalse(got["scientific_alpha_established"])

    def test_offline_mode_never_queries_github_or_computes_returns(self):
        l,m=packed()
        def forbid(_):
            self.fail("offline mode must not touch network")
        got=adjudicate(l,m,SOURCE,market(),as_of=NOW,fetch_json=forbid)
        self.assertEqual(got["status"],"LOCAL_ONLY_NO_EXTERNAL_WITNESS_NO_OUTCOMES")
        self.assertNotIn("forward_windows",got)
        self.assertFalse(got["actual_forward_outcomes_evaluated"])

    def test_different_original_event_bytes_rejected_even_if_same_side(self):
        l,m=packed()
        with self.assertRaisesRegex(ValueError,"original_source_event_digest_mismatch"):
            local_integrity(l,m,SOURCE+b"x",market(),as_of=NOW)

    def test_aggregate_receipts_not_accepted_as_single_event_ledger(self):
        l,m=packed()
        l["decisions"]=[]
        with self.assertRaisesRegex(ValueError,"single_frozen_candidate"):
            local_integrity(l,m,SOURCE,market(),as_of=NOW)
        l,m=packed()
        l["decisions"]=l["decisions"]*12
        with self.assertRaisesRegex(ValueError,"single_frozen_candidate"):
            local_integrity(l,m,SOURCE,market(),as_of=NOW)

    def test_future_price_candles_are_not_part_of_original_frozen_snapshot(self):
        l,m=packed()
        row=l["decisions"][0]
        self.assertEqual(row["price_only_input_m15"][-1]["t"],
                         "2026-11-23T04:15:00Z")
        self.assertTrue(any(x["t"] == "2026-11-23T05:00:00Z"
                            for x in market()["timeframes"]["M15"]))
        out=local_integrity(l,m,SOURCE,market(),as_of=NOW)
        self.assertTrue(out["baseline_rule_and_timestamp_consistent"])

    def test_baseline_manipulated_and_rehashed_fails_original_rule(self):
        l,_=packed()
        l["decisions"][0]["price_only_side"]="SHORT"
        recalculated=manifest_for(l["decisions"][0])
        with self.assertRaisesRegex(ValueError,"does_not_follow_rule"):
            local_integrity(l,recalculated,SOURCE,market(),as_of=NOW)

    def test_locked_ohlc_manipulated_even_with_new_manifest_rejected(self):
        l,_=packed()
        l["decisions"][0]["price_only_input_m15"][1]["c"] += 0.0002
        recalculated=manifest_for(l["decisions"][0])
        with self.assertRaisesRegex(ValueError,"differs_from_local_price"):
            local_integrity(l,recalculated,SOURCE,market(),as_of=NOW)

    def test_source_digest_claim_changed_but_manifest_rehashed_rejected(self):
        l,_=packed()
        l["decisions"][0]["source_event_sha256"]="0"*64
        recalculated=manifest_for(l["decisions"][0])
        with self.assertRaisesRegex(ValueError,"digest_mismatch"):
            local_integrity(l,recalculated,SOURCE,market(),as_of=NOW)

    def test_manifest_rejects_edited_anchored_side_and_event(self):
        l,m=packed()
        l["decisions"][0]["cvd_side"]="SHORT"
        with self.assertRaisesRegex(ValueError,"differs_from_manifest"):
            local_integrity(l,m,SOURCE,market(),as_of=NOW)

    def test_later_local_database_revision_is_detected(self):
        l,m=packed()
        changed=market()
        changed["timeframes"]["M15"][3]["o"] += 0.00005
        with self.assertRaisesRegex(ValueError,"differs_from_local_price"):
            local_integrity(l,m,SOURCE,changed,as_of=NOW)

    def test_event_capture_late_or_future_timestamp_rejected(self):
        l,_=packed()
        l["decisions"][0]["frozen_at_utc"]="2026-11-23T05:30:00Z"
        l["decisions"][0]["recorded_at_utc"]="2026-11-23T05:30:00Z"
        l["decisions"][0]["price_only_known_at_utc"]="2026-11-23T05:30:00Z"
        with self.assertRaisesRegex(ValueError,"timing"):
            local_integrity(l,manifest_for(l["decisions"][0]),SOURCE,market(),as_of=NOW)
        l,_=packed()
        with self.assertRaisesRegex(ValueError,"timing"):
            local_integrity(l,manifest_for(l["decisions"][0]),SOURCE,market(),
                            as_of=datetime(2026,11,23,4,35,tzinfo=UTC))

    def test_missing_locked_price_or_unverified_source_flag_rejected(self):
        l,_=packed()
        l["decisions"][0]["price_only_input_m15"]=[]
        with self.assertRaisesRegex(ValueError,"missing_original_price"):
            local_integrity(l,manifest_for(l["decisions"][0]),SOURCE,market(),as_of=NOW)
        l,_=packed()
        l["decisions"][0]["cvd_source_authentication"]="TRADINGVIEW_SIGNED_TRUST_ME"
        with self.assertRaisesRegex(ValueError,"unexpected_source_rule"):
            local_integrity(l,manifest_for(l["decisions"][0]),SOURCE,market(),as_of=NOW)

    def test_bad_price_provider_or_history_missing_rejected(self):
        l,m=packed()
        p=market()
        p["provider"]="tradingview"
        with self.assertRaisesRegex(ValueError,"ctrader"):
            local_integrity(l,m,SOURCE,p,as_of=NOW)
        p=market()
        p["timeframes"]["M15"]=p["timeframes"]["M15"][7:]
        with self.assertRaisesRegex(ValueError,"not_enough_original"):
            local_integrity(l,m,SOURCE,p,as_of=NOW)

    def test_successful_mock_github_witness_keeps_unverified_source_fences(self):
        l,m=packed()
        l["decisions"][0]["anchor"]["workflow_run_id"]=RUN_ID
        f=MockGithub(l)
        report=adjudicate(l,m,SOURCE,market(),as_of=NOW,
                          github_readonly=True,fetch_json=f)
        self.assertEqual(len(f.calls),2)
        self.assertTrue(report["github_first_seen_witness_verified"])
        self.assertTrue(report["forward_price_window_coverage_checked"])
        self.assertFalse(report["actual_forward_outcomes_evaluated"])
        self.assertFalse(report["source_receipt_timestamp_independently_verified"])
        self.assertFalse(report["cvd_direction_independently_derived_from_source"])
        self.assertFalse(report["broker_market_data_history_independently_authenticated"])
        self.assertFalse(report["scientific_alpha_established"])
        self.assertEqual(report["forward_windows"]["60m"]["complete_matched_m15_windows"],1)
        self.assertIsNone(report["forward_windows"]["60m"]["net_pips"])

    def test_mock_github_failure_refuses_scorecard(self):
        l,m=packed()
        l["decisions"][0]["anchor"]["workflow_run_id"]=RUN_ID
        f=MockGithub(l,bad_run={"conclusion":"failure"})
        with self.assertRaisesRegex(ValueError,"untrusted_github_run"):
            adjudicate(l,m,SOURCE,market(),as_of=NOW,
                       github_readonly=True,fetch_json=f)

    def test_mock_github_witness_does_not_turn_assumed_costs_into_quotes(self):
        l,m=packed()
        l["decisions"][0]["anchor"]["workflow_run_id"]=RUN_ID
        f=MockGithub(l)
        rep=adjudicate(l,m,SOURCE,market(),as_of=NOW,
                       github_readonly=True,fetch_json=f,
                       costs={"spread_pips":1.0,"slippage_pips_per_side":0.5})
        self.assertFalse(rep["costs_are_observed_quotes"])
        self.assertEqual(rep["forward_windows"]["60m"]["metric_gate"],
                         "SAMPLE_TOO_SMALL_OR_CORRELATED")
        self.assertIsNone(rep["forward_windows"]["60m"]["paired_cvd_minus_price_only_net_pips"])

    def test_original_source_size_gate_blocks_empty_or_oversize(self):
        l,m=packed()
        for raw in (b"",b"x"*1_000_001):
            with self.subTest(n=len(raw)),self.assertRaisesRegex(ValueError,"real_original"):
                local_integrity(l,m,raw,market(),as_of=NOW)


if __name__=="__main__":
    unittest.main()
