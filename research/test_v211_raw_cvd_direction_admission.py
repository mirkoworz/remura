"""REMURA V21.1: NEW synthetic-only closed-M5 source-derived CVD direction tests."""
from __future__ import annotations

import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

from v211_raw_cvd_direction_admission import (
    RAW_SCHEMA, RULE, SOURCE_FAMILY, adjudicate_raw, classify_raw,
    event_from_raw, freeze_raw,
)
from v209_private_decision_freezer import store_private_pair
from v208_github_decision_witness import (
    REPOSITORY_ID, REPOSITORY, ANCHOR_BRANCH, ANCHOR_WORKFLOW, manifest_for,
)
from v207_forward_cvd_evaluation import _decisions

UTC=timezone.utc
FREEZE=datetime(2026,11,23,4,36,tzinfo=UTC)
NOW=datetime(2026,11,23,7,0,tzinfo=UTC)
RECEIVED="2026-11-23T04:35:05Z"
SHA="e"*40
RUN=45999123456
NONCE="ab"*16


def source_doc(*, first="100.125", last="105.125", **changes):
    d={
        "schema":RAW_SCHEMA, "symbol":"FX:EURUSD", "timeframe":"M5",
        "source_family":SOURCE_FAMILY,
        "prior_close_utc":"2026-11-23T04:30:00Z",
        "event_close_utc":"2026-11-23T04:35:00Z",
        "prior_cvd":first,"event_cvd":last,
    }
    d.update(changes)
    return d


def raw(*, first="100.125", last="105.125", **changes):
    return json.dumps(source_doc(first=first,last=last,**changes),
                      sort_keys=True,separators=(",",":")).encode("utf-8")


def prices():
    start=datetime(2026,11,23,3,15,tzinfo=UTC)
    rows=[]
    for i in range(12):
        t=start+timedelta(minutes=15*i)
        price=1.1000+i*0.0001
        rows.append({
            "t":t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "o":round(price,5),"h":round(price+0.0002,5),
            "l":round(price-0.0002,5),"c":round(price+0.0001,5)
        })
    return {"symbol":"EURUSD","provider":"ctrader",
            "providerSymbol":"SYNTHETIC_CTRADER_ONLY",
            "timeframes":{"M15":rows}}


def freeze(b=None,p=None,*,when=FREEZE):
    return freeze_raw(b if b is not None else raw(),RECEIVED,p or prices(),
                      as_of=when,nonce=NONCE)


class FakeGithub:
    def __init__(self, ledger):
        self.urls=[]
        manifest=manifest_for(ledger["decisions"][0])
        digest=manifest["commitment_sha256"]
        self.response={
            "run":{"id":RUN,"event":"push","status":"completed",
                   "conclusion":"success","head_sha":SHA,
                   "head_branch":ANCHOR_BRANCH,"path":ANCHOR_WORKFLOW,
                   "created_at":"2026-11-23T04:39:00Z",
                   "repository":{"id":REPOSITORY_ID,"full_name":REPOSITORY}},
            "file":{"type":"file","path":f"research/forward-anchors/{digest}.json",
                    "encoding":"base64","content":base64.b64encode(
                        json.dumps(manifest).encode()).decode()}
        }
    def __call__(self,url):
        self.urls.append(url)
        return copy.deepcopy(self.response["run" if "/actions/runs/" in url else "file"])


class NewV211Tests(unittest.TestCase):
    def test_long_from_last_minus_prior_decimal(self):
        self.assertEqual(classify_raw(raw()),("LONG","2026-11-23T04:35:00Z","5.000"))

    def test_short_from_negative_cvd_difference(self):
        self.assertEqual(classify_raw(raw(first="90.5",last="-10.5"))[0],"SHORT")

    def test_flat_when_cvd_unchanged(self):
        self.assertEqual(classify_raw(raw(first="19.25",last="19.25"))[0],"FLAT")

    def test_deterministic_high_precision_no_floating_threshold_rewrite(self):
        self.assertEqual(classify_raw(raw(first="1.000000",last="1.000001"))[0],"LONG")
        self.assertEqual(classify_raw(raw(first="1.000001",last="1.000000"))[0],"SHORT")

    def test_numeric_floats_or_bad_decimal_strings_fail(self):
        for value in (3.2,0,None,"NaN","3e2",".1","000.1","+3","1.1234567","-",
                      "1000000000000"," 7"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                classify_raw(raw(last=value))

    def test_duplicate_json_fields_cannot_override_symbol_or_cvd(self):
        malformed=b'{"schema":"remura-v211-closed-m5-cvd-pair-v1","schema":"evil"}'
        with self.assertRaisesRegex(ValueError,"duplicate_source_json_key"):
            classify_raw(malformed)

    def test_unknown_old_aggregate_receipts_are_not_directional_signals(self):
        old=json.dumps({"schema":"remura-v203-tradingview-test-receipt-real-proof",
                        "result":{"valid_unique_bars":12,"scientific_admission":False}}).encode()
        with self.assertRaisesRegex(ValueError,"unknown_original_source_contract"):
            classify_raw(old)

    def test_unknown_extra_source_side_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"unknown_original_source_contract"):
            classify_raw(raw(cvd_side="LONG"))

    def test_missing_or_unclosed_adjacent_m5_is_rejected(self):
        for fields in (
            {"event_close_utc":"2026-11-23T04:40:00Z"},
            {"prior_close_utc":"2026-11-23T04:25:00Z"},
            {"event_close_utc":"2026-11-23T04:34:00Z"},
        ):
            with self.subTest(fields=fields),self.assertRaisesRegex(ValueError,"not_two_consecutive"):
                classify_raw(raw(**fields))

    def test_source_family_symbol_and_timeframe_are_strict(self):
        for change in (
            {"symbol":"XAUUSD"},
            {"timeframe":"M1"},
            {"source_family":"EXECUTED_EXCHANGE_VOLUME_TRUST_ME"},
            {"schema":"unknown"},
        ):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,"wrong_cvd"):
                classify_raw(raw(**change))

    def test_future_or_old_receipt_cannot_be_reconstructed(self):
        s=raw()
        with self.assertRaisesRegex(ValueError,"future_or_backdated"):
            event_from_raw(s,"2026-11-23T04:34:50Z",as_of=FREEZE)
        with self.assertRaisesRegex(ValueError,"future_or_backdated"):
            event_from_raw(s,"2026-11-23T04:40:00Z",as_of=FREEZE)
        with self.assertRaisesRegex(ValueError,"cannot_backfill"):
            event_from_raw(s,RECEIVED,as_of=FREEZE+timedelta(hours=1))

    def test_closed_pair_must_be_past_current_freeze(self):
        s=raw()
        with self.assertRaisesRegex(ValueError,"future_or_backdated"):
            event_from_raw(s,RECEIVED,as_of=datetime(2026,11,23,4,34,tzinfo=UTC))

    def test_freezer_produces_private_derived_direction_and_opaque_manifest(self):
        ledger,m=freeze()
        row=ledger["decisions"][0]
        self.assertEqual(row["cvd_side"],"LONG")
        self.assertEqual(row["source_raw_schema"],RAW_SCHEMA)
        self.assertEqual(row["source_direction_rule"],RULE)
        self.assertEqual(row["source_self_reported_cvd_difference"],"5.000")
        self.assertFalse(row["source_origin_is_authenticated"])
        self.assertEqual(row["source_event_sha256"],hashlib.sha256(raw()).hexdigest())
        self.assertEqual(set(m),{"schema","commitment_sha256"})
        for forbidden in ("LONG","100.125","105.125",NONCE,"SYNTHETIC_CTRADER_ONLY"):
            self.assertNotIn(forbidden,json.dumps(m))

    def test_hash_binding_includes_derived_delta_metadata_and_raw_digest(self):
        ledger,m=freeze()
        row=copy.deepcopy(ledger["decisions"][0])
        row["source_self_reported_cvd_difference"]="99.0"
        self.assertNotEqual(manifest_for(row),m)
        row=copy.deepcopy(ledger["decisions"][0])
        row["source_direction_rule"]="AFTER_THE_FACT"
        self.assertNotEqual(manifest_for(row),m)

    def test_wrong_locked_side_with_rehashed_manifest_fails_raw_comparison(self):
        ledger,m=freeze()
        ledger["decisions"][0]["cvd_side"]="SHORT"
        with self.assertRaisesRegex(ValueError,"locked_direction_differs"):
            adjudicate_raw(ledger,manifest_for(ledger["decisions"][0]),raw(),prices(),as_of=NOW)

    def test_changed_raw_pair_original_bytes_fails_even_if_direction_same(self):
        ledger,m=freeze()
        with self.assertRaisesRegex(ValueError,"locked_direction_differs|digest_mismatch"):
            adjudicate_raw(ledger,m,raw(first="100.125",last="106.125"),prices(),as_of=NOW)

    def test_same_side_but_changed_ohcl_baseline_fails_older_integrity_gate(self):
        ledger,m=freeze()
        bad=prices()
        bad["timeframes"]["M15"][3]["o"] += 0.00001
        with self.assertRaisesRegex(ValueError,"locked_ohlc_differs"):
            adjudicate_raw(ledger,m,raw(),bad,as_of=NOW)

    def test_good_raw_offline_source_derivation_does_not_claim_identity_or_alpha(self):
        ledger,m=freeze()
        def forbid(_):
            self.fail("GitHub GET without opt-in")
        result=adjudicate_raw(ledger,m,raw(),prices(),as_of=NOW,fetch_json=forbid)
        self.assertEqual(result["status"],"LOCAL_ONLY_NO_EXTERNAL_WITNESS_NO_OUTCOMES")
        self.assertTrue(result["cvd_direction_deterministically_recomputed_from_raw_pair"])
        self.assertFalse(result["cvd_origin_independently_authenticated"])
        self.assertFalse(result["raw_first_seen_timestamp_independently_authenticated"])
        self.assertFalse(result["institutional_trading_flow_claimed"])
        self.assertFalse(result["scientific_alpha_established"])
        self.assertFalse(result["actual_forward_outcomes_evaluated"])

    def test_opt_in_github_mock_witness_still_not_a_real_signal(self):
        ledger,m=freeze()
        ledger["decisions"][0]["anchor"]["workflow_run_id"]=RUN
        f=FakeGithub(ledger)
        result=adjudicate_raw(ledger,m,raw(),prices(),as_of=NOW,
                              github_readonly=True,fetch_json=f)
        self.assertEqual(len(f.urls),2)
        self.assertTrue(result["github_first_seen_witness_verified"])
        self.assertTrue(result["cvd_direction_deterministically_recomputed_from_raw_pair"])
        self.assertFalse(result["cvd_origin_independently_authenticated"])
        self.assertFalse(result["scientific_alpha_established"])

    def test_private_store_never_publishes_nonce_decision_or_raw_bytes(self):
        ledger,m=freeze()
        with tempfile.TemporaryDirectory() as base:
            folder=Path(base)/"private"
            report=store_private_pair(ledger,m,folder)
            self.assertEqual(report["files_created"],2)
            self.assertFalse(report["public_manifest_uploaded"])
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)
            private_files=list(folder.glob("*.private.json"))
            self.assertEqual(len(private_files),1)
            self.assertEqual(stat.S_IMODE(private_files[0].stat().st_mode),0o600)
            self.assertNotIn("100.125",json.dumps(m))
            with self.assertRaisesRegex(ValueError,"already_frozen"):
                store_private_pair(ledger,m,folder)

    def test_ledger_can_only_be_assessed_after_future_anchor_timestamp(self):
        ledger,m=freeze()
        ledger["decisions"][0]["anchor"]={
            "kind":"github_commit","workflow_run_id":RUN,
            "sha":SHA,"committed_at_utc":"2026-11-23T04:39:00Z",
        }
        accepted=_decisions(ledger,datetime(2026,11,23,5,0,tzinfo=UTC))
        self.assertEqual(len(accepted),1)
        self.assertEqual(accepted[0]["entry"],
                         int(datetime(2026,11,23,4,45,tzinfo=UTC).timestamp()*1000))


if __name__=="__main__":
    unittest.main()
