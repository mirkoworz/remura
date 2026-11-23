"""REMURA V20.9: only NEW tests using synthetic data, no Mac/Cloudflare/market calls."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from v209_private_decision_freezer import (
    BASELINE_RULE, EVENT_SCHEMA, freeze_candidate, store_private_pair,
)
from v208_github_decision_witness import commitment
from v207_forward_cvd_evaluation import _decisions

UTC = timezone.utc
NOW = datetime(2026,11,23,4,36,0,tzinfo=UTC)
FIRST = datetime(2026,11,23,3,15,0,tzinfo=UTC)
NONCE = "ab" * 16


def event(**changes):
    doc={
        "schema":EVENT_SCHEMA,
        "symbol":"FX:EURUSD",
        "event_close_utc":"2026-11-23T04:35:00Z",
        "received_at_utc":"2026-11-23T04:35:10Z",
        "source_event_sha256":"a"*64,
        "cvd_side":"LONG",
    }
    doc.update(changes)
    return doc


def market(closes=None, *, provider="ctrader", gap=None, extra=None):
    vals=closes or [1.1000,1.1001,1.1002,1.1003,1.1004]
    bars=[]
    for i,cl in enumerate(vals):
        start=FIRST+timedelta(minutes=15*i)
        if start==gap:
            continue
        bars.append({
            "t":start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "o":cl,"h":cl+0.0002,"l":cl-0.0002,"c":cl,
        })
    if extra is not None:
        bars.append(extra)
    return {"symbol":"EURUSD","provider":provider,
            "providerSymbol":"SYNTHETIC_BROKER_NOT_REAL",
            "timeframes":{"M15":bars}}


def freeze(e=None,m=None,*,as_of=NOW):
    return freeze_candidate(e or event(),m or market(),as_of=as_of,nonce=NONCE)


class V209NewOnly(unittest.TestCase):
    def test_momentum_long_frozen_same_instant_as_cvd(self):
        ledger,manifest=freeze()
        row=ledger["decisions"][0]
        self.assertEqual(row["cvd_side"],"LONG")
        self.assertEqual(row["price_only_side"],"LONG")
        self.assertEqual(row["price_only_rule"],BASELINE_RULE)
        self.assertEqual(row["frozen_at_utc"],"2026-11-23T04:36:00Z")
        self.assertEqual(row["price_only_known_at_utc"],row["frozen_at_utc"])
        self.assertEqual(row["observations_count"],1)
        self.assertEqual(len(row["price_only_input_m15"]),5)
        self.assertEqual(set(manifest),{"schema","commitment_sha256"})

    def test_short_and_flat_baselines_are_deterministic(self):
        d,_=freeze(m=market([1.1004,1.1003,1.1002,1.1001,1.1000]))
        self.assertEqual(d["decisions"][0]["price_only_side"],"SHORT")
        d,_=freeze(m=market([1.1000,1.1003,1.1002,1.1004,1.1000]))
        self.assertEqual(d["decisions"][0]["price_only_side"],"FLAT")

    def test_cvd_side_never_derived_from_prices(self):
        d,_=freeze(e=event(cvd_side="SHORT"))
        self.assertEqual(d["decisions"][0]["cvd_side"],"SHORT")
        self.assertEqual(d["decisions"][0]["price_only_side"],"LONG")
        self.assertEqual(d["decisions"][0]["cvd_source_authentication"],"LOCAL_ASSERTION_UNVERIFIED")

    def test_no_m15_future_peeking_even_when_future_row_in_payload(self):
        normal,_=freeze()
        next_row={
            "t":"2026-11-23T04:30:00Z","o":2.0,"h":2.0003,"l":1.999,"c":2.0,
        }
        doc=market(extra=next_row)
        with_future,_=freeze(m=doc)
        self.assertEqual(
            normal["decisions"][0]["price_only_input_m15"],
            with_future["decisions"][0]["price_only_input_m15"],
        )

    def test_price_gap_or_insufficient_history_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"gap"):
            freeze(m=market(gap=FIRST+timedelta(minutes=30)))
        with self.assertRaisesRegex(ValueError,"five_closed"):
            freeze(m=market([1.1,1.1002,1.1003,1.1004]))

    def test_stale_m15_rejected_even_with_recent_cvd(self):
        doc=market()
        # Last full bar now ends 04:30. Move all 5 bars one hour earlier.
        for r in doc["timeframes"]["M15"]:
            t=datetime.strptime(r["t"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            r["t"]=(t-timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.assertRaisesRegex(ValueError,"stale_m15"):
            freeze(m=doc)

    def test_stale_m5_event_cannot_be_backfilled(self):
        with self.assertRaisesRegex(ValueError,"stale_event"):
            freeze(e=event(event_close_utc="2026-11-23T04:20:00Z",
                           received_at_utc="2026-11-23T04:22:00Z"))

    def test_future_or_unsorted_receipt_and_non_aligned_event_rejected(self):
        for e in (
            event(received_at_utc="2026-11-23T04:40:00Z"),
            event(received_at_utc="2026-11-23T04:29:00Z"),
            event(event_close_utc="2026-11-23T04:34:00Z"),
        ):
            with self.subTest(e=e),self.assertRaises(ValueError):
                freeze(e=e)

    def test_bad_schema_digest_side_and_provider_rejected(self):
        for e in (
            event(symbol="XAUUSD"),
            event(source_event_sha256="zz"),
            event(cvd_side="BUY_NOW"),
            event(schema="old"),
        ):
            with self.subTest(e=e),self.assertRaises(ValueError):
                freeze(e=e)
        with self.assertRaisesRegex(ValueError,"ctrader"):
            freeze(m=market(provider="csv"))

    def test_hash_only_witness_cannot_expose_nonce_side_broker(self):
        ledger,manifest=freeze()
        text=json.dumps(manifest)
        self.assertEqual(manifest["commitment_sha256"],commitment(ledger["decisions"][0]))
        for secret in ("SYNTHETIC_BROKER_NOT_REAL",NONCE,"LONG","FX:EURUSD","decision_id"):
            self.assertNotIn(secret,text)
        self.assertEqual(len(manifest["commitment_sha256"]),64)

    def test_changing_direction_or_price_snapshot_invalidates_hash(self):
        ledger,m=freeze()
        for key,value in (
            ("cvd_side","SHORT"),
            ("price_only_side","FLAT"),
            ("price_only_known_at_utc","2026-11-23T04:35:59Z"),
        ):
            another=copy.deepcopy(ledger["decisions"][0])
            another[key]=value
            with self.subTest(key=key):
                self.assertNotEqual(commitment(another),m["commitment_sha256"])
        another=copy.deepcopy(ledger["decisions"][0])
        another["price_only_input_m15"][-1]["c"] += 0.001
        self.assertNotEqual(commitment(another),m["commitment_sha256"])

    def test_compatible_with_v207_when_future_verified_anchor_added(self):
        ledger,m=freeze()
        ledger["decisions"][0]["anchor"]={
            "kind":"github_commit",
            "workflow_run_id":123456789,
            "sha":"b"*40,
            "committed_at_utc":"2026-11-23T04:39:00Z",
        }
        self.assertEqual(commitment(ledger["decisions"][0]),m["commitment_sha256"])
        ds=_decisions(ledger,datetime(2026,11,23,5,0,tzinfo=UTC))
        self.assertEqual(ds[0]["entry"],
                         int(datetime(2026,11,23,4,45,tzinfo=UTC).timestamp()*1000))

    def test_write_two_files_securely_outside_repository_only(self):
        ledger,m=freeze()
        with tempfile.TemporaryDirectory() as parent:
            folder=Path(parent)/"secured"
            result=store_private_pair(ledger,m,folder)
            self.assertEqual(result["files_created"],2)
            self.assertFalse(result["github_witness_verified"])
            saved=sorted(folder.iterdir())
            self.assertEqual(len(saved),2)
            for path in saved:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            priv=[p for p in saved if p.name.endswith(".private.json")][0]
            self.assertEqual(json.loads(priv.read_text())["decisions"][0]["cvd_side"],"LONG")
            public=[p for p in saved if p.name.endswith(".hash-only.json")][0]
            self.assertEqual(json.loads(public.read_text()),m)
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)

    def test_repeat_same_event_does_not_overwrite_or_replace_files(self):
        ledger,m=freeze()
        with tempfile.TemporaryDirectory() as parent:
            folder=Path(parent)/"private"
            store_private_pair(ledger,m,folder)
            old={p.name:p.read_bytes() for p in folder.iterdir()}
            with self.assertRaisesRegex(ValueError,"already_frozen"):
                store_private_pair(ledger,m,folder)
            self.assertEqual(old,{p.name:p.read_bytes() for p in folder.iterdir()})

    def test_public_repository_dir_guard_never_writes(self):
        ledger,m=freeze()
        from v209_private_decision_freezer import REPOSITORY_ROOT
        with self.assertRaisesRegex(ValueError,"outside_public_repository"):
            store_private_pair(ledger,m,REPOSITORY_ROOT/"research"/"accidental_public_decisions")

    def test_mismatched_manifest_refused_without_writes(self):
        ledger,m=freeze()
        with tempfile.TemporaryDirectory() as parent:
            m["commitment_sha256"]="f"*64
            with self.assertRaisesRegex(ValueError,"mismatched"):
                store_private_pair(ledger,m,Path(parent))
            self.assertEqual(list(Path(parent).iterdir()),[])


if __name__=="__main__":
    unittest.main()
