"""ONLY NEW V20.4 tests: frozen real 12/12 proof + synthetic LOCAL price coverage."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from v204_private_cvd_price_coverage import (
    assess, checked_m15, next_entry_after_max_receipt, read_local_price_db,
    receipt_window, REAL_RUN,
)

ROOT=Path(__file__).resolve().parent
PROOF_PATH=ROOT/"real-proofs/REMURA-V203-CVD-TEST-RECEIPTS-20261123.json"
UTC=timezone.utc
ASOF=datetime(2026,11,23,7,0,tzinfo=UTC)
START=datetime(2026,11,23,4,45,tzinfo=UTC)


def proof():
    return json.loads(PROOF_PATH.read_text(encoding="utf-8"))


def prices(n=8, *, gap=None, provider="ctrader"):
    rows=[]
    for i in range(n):
        t=START+timedelta(minutes=15*i)
        if t==gap:
            continue
        rows.append({"t":t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "o":1.1,"h":1.101,"l":1.099,"c":1.1001})
    return {"symbol":"EURUSD","provider":provider,"providerSymbol":"FP Markets EURUSD personal",
            "timeframes":{"M15":rows}}


class V204VerifiedRealReceiptWithPrivatePriceTests(unittest.TestCase):
    def test_actual_public_proof_is_same_completed_owner_run(self):
        e=receipt_window(proof())
        self.assertEqual(e["max_lag"],15510)
        self.assertEqual(e["start"],1795408200000)
        self.assertEqual(e["end"],1795411500000)

    def test_missing_price_never_claims_return_or_signal(self):
        d=assess(proof(),None,as_of=ASOF)
        self.assertEqual(d["status"],"PRICE_NOT_PROVIDED")
        self.assertEqual(d["cvd_receipts_verified_requested_window"],12)
        self.assertEqual(d["m15_cohorts_unique_not_12_independent_trades"],4)
        self.assertFalse(d["directional_outcomes_computed"])
        self.assertFalse(d["statistical_alpha_established"])
        self.assertEqual(d["horizons"]["60m"]["complete_unique_m15_price_cohorts"],0)

    def test_synthetic_full_closed_one_hour_is_coverage_not_profit(self):
        d=assess(proof(),prices(8),as_of=ASOF)
        self.assertEqual(d["horizons"]["60m"]["complete_unique_m15_price_cohorts"],4)
        self.assertEqual(d["horizons"]["60m"]["closed_but_price_missing_unique_cohorts"],0)
        self.assertEqual(d["horizons"]["4h"]["not_yet_mature_unique_cohorts"],4)
        self.assertEqual(d["horizons"]["24h"]["not_yet_mature_unique_cohorts"],4)
        self.assertFalse(d["directional_outcomes_computed"])
        self.assertNotIn("FP Markets",json.dumps(d))
        self.assertNotIn("1.101",json.dumps(d))

    def test_gap_never_filled(self):
        d=assess(proof(),prices(8,gap=START+timedelta(minutes=15)),as_of=ASOF)
        self.assertEqual(d["horizons"]["60m"]["closed_but_price_missing_unique_cohorts"],2)
        self.assertEqual(d["horizons"]["60m"]["complete_unique_m15_price_cohorts"],2)

    def test_unclosed_future_bars_not_used(self):
        d=assess(proof(),prices(30),as_of=ASOF)
        self.assertEqual(d["horizons"]["60m"]["complete_unique_m15_price_cohorts"],4)
        self.assertEqual(d["horizons"]["4h"]["complete_unique_m15_price_cohorts"],0)
        self.assertEqual(d["horizons"]["24h"]["complete_unique_m15_price_cohorts"],0)

    def test_tampering_with_real_provenance_rejected(self):
        for mutation in ("source","coverage","alpha","dataset"):
            p=proof()
            if mutation=="source":
                p["provenance"]["github_workflow_run"]="https://example.com/fake"
            elif mutation=="coverage":
                p["result"]["valid_unique_bars"]=11
            elif mutation=="alpha":
                p["result"]["radar"]["verdict"]="BUY_NOW"
            else:
                p["result"]["collection"]["target"]="PRODUCTION_DB"
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                receipt_window(p)

    def test_invalid_ohlc_and_non_ctrader_fail(self):
        with self.assertRaisesRegex(ValueError,"ctrader"):
            checked_m15(prices(provider="fiction"),ASOF)
        bad=prices()
        bad["timeframes"]["M15"][0]["h"]=1.0
        with self.assertRaisesRegex(ValueError,"extremes"):
            checked_m15(bad,ASOF)
        missing=prices()
        missing["timeframes"]["M15"].pop(0)
        missing["timeframes"]["M15"].append(copy.deepcopy(missing["timeframes"]["M15"][0]))
        with self.assertRaises(ValueError):
            checked_m15(missing,ASOF)

    def test_conservative_entry_strictly_after_max_receipt(self):
        # M5 close 04:30:00, last observed possible receipt at 04:30:15.510.
        self.assertEqual(next_entry_after_max_receipt(1795408200000,15510),1795409100000)
        # Exact on M15 boundary still chooses the NEXT full M15 candle.
        self.assertEqual(next_entry_after_max_receipt(1795408200000,0),1795409100000)

    def test_read_only_sqlite_never_exposes_private_broker(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"price.db"
            with sqlite3.connect(p) as db:
                db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY,payload TEXT NOT NULL)")
                db.execute("INSERT INTO prices VALUES(?,?)",("EURUSD",json.dumps(prices())))
            before=p.read_bytes()
            doc=read_local_price_db(p)
            report=assess(proof(),doc,as_of=ASOF)
            self.assertEqual(before,p.read_bytes())
            self.assertEqual(report["horizons"]["60m"]["complete_unique_m15_price_cohorts"],4)
            self.assertNotIn("FP Markets",json.dumps(report))
            self.assertFalse(report["price_values_or_broker_ids_exported"])


if __name__=="__main__":
    unittest.main()
