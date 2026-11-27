"""Offline adversarial fixture for prospective M15 price-regime context.

All bars, times and symbols in this suite are SYNTHETIC; not market evidence.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import unittest

from scripts import shark_market_regime_context as m
from scripts import shark_cvd_incremental_protocol as protocol

UTC = timezone.utc
LAST_OPEN = datetime(2026, 11, 9, 9, 45, tzinfo=UTC)
OBSERVED = "2026-11-09T10:01:00Z"
AS_OF = "2026-11-09T11:00:00Z"
SECRET = "FAKE_PRIVATE_BROKER_DO_NOT_LEAK"


def _utc(value):
    return value.isoformat().replace("+00:00", "Z")


def original(kind="up", symbol="EURUSD"):
    closes = [100.0]
    for i in range(1, 33):
        if kind == "up":
            inc = 0.01
        elif kind == "down":
            inc = -0.01
        elif kind == "lateral":
            inc = 0.01 if i % 2 else -0.01
        elif kind == "mixed":
            inc = -0.01 if i % 4 == 0 else 0.01
        elif kind == "zero":
            inc = 0.0
        else:
            raise ValueError("unknown_fixture")
        closes.append(round(closes[-1] + inc, 8))
    bars = []
    for i, c in enumerate(closes):
        opened = LAST_OPEN - timedelta(minutes=15*(32-i))
        o = closes[i-1] if i else c
        bars.append({"t": _utc(opened), "o": o,
                     "h": max(o,c)+0.001, "l": min(o,c)-0.001,
                     "c": c, "v": 100})
    return {"symbol": symbol, "provider": "ctrader",
            "providerSymbol": SECRET, "timezone": "UTC",
            "sourceTimeframe": "M15", "lastComplete": bars[-1]["t"],
            "timeframes": {"M15": bars, "H1": [], "H4": []}}


def row(kind="up", symbol="EURUSD", **overrides):
    doc = original(kind,symbol)
    payload = {
        "symbol": symbol, "observedAtUtc": OBSERVED,
        "firstRecordedAtUtc": "2026-11-09T10:00:40Z",
        "sourceReceivedAtUtc": "2026-11-09T10:00:20Z",
        "originalDocumentSha256": m._digest(doc),
        "document": doc,
        "fakeOutcomeBps": 2000000,
        "fakeInstitutionalTrade": True,
    }
    payload.update(overrides)
    return payload


class MarketRegimeContextTests(unittest.TestCase):
    def test_fixed_asof_regimes_on_synthetic_original_m15(self):
        expected = {
            "up": "DIRECTIONAL_UP",
            "down": "DIRECTIONAL_DOWN",
            "lateral": "LATERAL",
            "mixed": "MIXED",
        }
        for kind, state in expected.items():
            with self.subTest(kind=kind):
                result = m.classify(row(kind),as_of=AS_OF)
                self.assertEqual(result["state"],state)
                self.assertFalse(result["externalSourceAndClockAttested"])
                self.assertFalse(result["actualMarketReturnOrPnLEstimated"])
        self.assertEqual(m.classify(row("up"),as_of=AS_OF)
                         ["efficiencyRatio"],1.0)
        self.assertEqual(m.classify(row("mixed"),as_of=AS_OF)
                         ["efficiencyRatio"],0.5)
        self.assertEqual(m.WINDOW_BARS,33)
        self.assertEqual((m.LATERAL_MAX,m.DIRECTIONAL_MIN),(0.3,0.6))
        self.assertEqual(protocol.protocol_sha256(),
                         protocol.FROZEN_PROTOCOL_SHA256)

    def test_true_zero_path_not_assumed_lateral(self):
        with self.assertRaisesRegex(ValueError,
                                     "zero_or_nonfinite_path_unknown"):
            m.classify(row("zero"),as_of=AS_OF)
        result = m.audit([row("zero")],as_of=AS_OF)
        self.assertEqual(result["locallyClassified"],0)
        self.assertEqual(result["unknownOrRejected"],1)

    def test_changed_original_document_not_rebound_after_observation(self):
        candidate = row()
        candidate["document"]["timeframes"]["M15"][0]["c"] += .0001
        with self.assertRaisesRegex(ValueError,"original_document_sha_mismatch"):
            m.classify(candidate,as_of=AS_OF)
        self.assertEqual(m.audit([candidate],as_of=AS_OF)["regimes"]["LATERAL"],0)

    def test_future_or_unclosed_bar_rejected_not_masked_by_last_33(self):
        future = row()
        future["document"]["timeframes"]["M15"].append({
            "t": "2026-11-09T10:00:00Z", "o": 100.0,
            "h": 100.01, "l": 99.99, "c": 100.0})
        future["document"]["lastComplete"] = "2026-11-09T10:00:00Z"
        future["originalDocumentSha256"] = m._digest(future["document"])
        with self.assertRaisesRegex(ValueError,"last_closed_not_fresh"):
            m.classify(future,as_of=AS_OF)

    def test_gap_order_future_source_and_stale_are_unknown(self):
        cases = []
        gap = row()
        gap["document"]["timeframes"]["M15"][-3]["t"] = (
            "2026-11-09T09:00:00Z")
        gap["originalDocumentSha256"] = m._digest(gap["document"])
        cases.append(gap)
        late = row(sourceReceivedAtUtc="2026-11-09T10:02:00Z")
        cases.append(late)
        stale = row(observedAtUtc="2026-11-09T10:07:00Z",
                    firstRecordedAtUtc="2026-11-09T10:06:40Z",
                    sourceReceivedAtUtc="2026-11-09T10:06:00Z")
        cases.append(stale)
        prestart = row(observedAtUtc="2026-11-08T10:01:00Z",
                       firstRecordedAtUtc="2026-11-08T10:00:40Z",
                       sourceReceivedAtUtc="2026-11-08T10:00:20Z")
        cases.append(prestart)
        no_source = row(document=None)
        cases.append(no_source)
        r = m.audit(cases, as_of=AS_OF)
        self.assertEqual(r["unknownOrRejected"],len(cases))
        self.assertEqual(r["locallyClassified"],0)
        self.assertEqual(sum(r["regimes"].values()),0)

    def test_duplicates_quarantined_regardless_input_order(self):
        a = row("up")
        b = row("down")
        valid_other = row("lateral",symbol="XAUUSD")
        r = m.audit([a,b,valid_other],as_of=AS_OF)
        reverse = m.audit([valid_other,b,a],as_of=AS_OF)
        self.assertEqual(r,reverse)
        self.assertEqual(r["locallyClassified"],1)
        self.assertEqual(r["unknownOrRejected"],2)
        self.assertEqual(r["exclusions"]["ambiguous_duplicate_observation"],2)
        self.assertEqual(r["regimes"]["DIRECTIONAL_UP"],0)

    def test_34_market_universe_not_equated_to_two_source_coverage(self):
        a = row("up",symbol="EURUSD")
        b = row("lateral",symbol="XAUUSD")
        r = m.audit([a,b],as_of=AS_OF)
        self.assertEqual(r["marketUniverseCount"],34)
        self.assertEqual(r["observationsReceived"],2)
        self.assertEqual(r["locallyClassified"],2)
        self.assertTrue(r["sparseRecordsDoNotProve34MarketCoverage"])
        self.assertFalse(r["statisticalEdgeEstablished"])
        self.assertFalse(r["independentOutOfSample"])
        serialized = json.dumps(r)
        self.assertNotIn(SECRET,serialized)
        self.assertNotIn("2000000",serialized)
        self.assertNotIn("EURUSD",serialized)
        self.assertNotIn("XAUUSD",serialized)
        self.assertFalse(r["liveSignalsOrNotificationsAuthorized"])
        self.assertEqual((r["brokerCalls"],r["writes"]),(0,0))

    def test_unknown_schema_non_utc_cot_and_wrong_provider_fail(self):
        invalids = [None,{},123,[],row(symbol="FAKE"),
                    row(sourceReceivedAtUtc="2026-11-09T10:00:20+01:00")]
        # +01:00 is not UTC, not a local time silently converted to UTC.
        invalids.append(row(document=dict(original(),provider="not_ctrader")))
        invalids.append(row(observedAtUtc="2026-11-09T12:00:00Z"))
        r = m.audit(invalids,as_of=AS_OF)
        self.assertEqual(r["locallyClassified"],0)
        self.assertEqual(r["unknownOrRejected"],len(invalids))
        with self.assertRaisesRegex(ValueError,"invalid_regime_records"):
            m.audit([row()]*(m.MAX_RECORDS+1),as_of=AS_OF)

    def test_future_outcomes_or_retrospective_improvements_do_not_affect_label(self):
        a = row()
        b = copy.deepcopy(a)
        b["fakeOutcomeBps"] = -999999999.0
        b["fakeInstitutionalTrade"] = False
        self.assertEqual(m.classify(a,as_of=AS_OF),m.classify(b,as_of=AS_OF))
        self.assertEqual(m.audit([a],as_of=AS_OF),
                         m.audit([b],as_of=AS_OF))


if __name__ == "__main__":
    unittest.main()
