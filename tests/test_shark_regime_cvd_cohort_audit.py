"""Synthetic-only tests of exact-source regime/CVD cohort reconciliation.

All source documents and future timestamps are invented fixtures. No PnL,
actual CFTC receipts or broker information is authenticated by these tests.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import unittest

from scripts import shark_regime_cvd_cohort_audit as mat
from scripts import shark_market_regime_context as regime
from scripts import shark_cvd_incremental_protocol as study

UTC = timezone.utc
OBS = "2026-11-09T10:01:00Z"
ASOF = "2026-11-16T12:00:00Z"
TRAIN = "2026-11-11T00:00:00Z"
VALIDATION = "2026-11-13T00:00:00Z"
SECRET = "PRIVATE_SYNTHETIC_BROKER_NAME"


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def original(symbol="EURUSD",kind="up",opened=None):
    opened = opened or datetime(2026,11,9,9,45,tzinfo=UTC)
    closes=[100.0]
    for i in range(1,33):
        inc = (0.01 if kind=="up" else
               -0.01 if kind=="down" else
               (0.01 if i%2 else -0.01))
        closes.append(round(closes[-1]+inc,8))
    bars=[]
    for i,c in enumerate(closes):
        o=closes[i-1] if i else c
        bars.append({"t":iso(opened-timedelta(minutes=15*(32-i))),
                     "o":o,"h":max(o,c)+.001,
                     "l":min(o,c)-.001,"c":c,"v":100})
    return {"symbol":symbol,"provider":"ctrader",
            "providerSymbol":SECRET,"timezone":"UTC",
            "sourceTimeframe":"M15","lastComplete":bars[-1]["t"],
            "timeframes":{"M15":bars,"H1":[],"H4":[]}}


def case(symbol="EURUSD",kind="up",cvd="BULLISH_CONFIRMED",
         observed=OBS,report="2026-11-03", **mod):
    dt=datetime.fromisoformat(observed.replace("Z","+00:00"))
    closed=dt.replace(minute=0,second=0,microsecond=0)
    # The test observations are always HH:01, with the previous M15
    # ending at HH:00, and no source was received after observation.
    doc=original(symbol,kind,closed-timedelta(minutes=15))
    digest=regime._digest(doc)
    received=iso(closed+timedelta(seconds=20))
    first=iso(closed+timedelta(seconds=40))
    observed=iso(closed+timedelta(minutes=1))
    legs=study.expected_cot_legs(symbol)
    core={
        "schema":study.INPUT_SCHEMA,
        "symbol":symbol,"direction":1,
        "observedAtUtc":observed,
        "firstRecordedAtUtc":first,
        "cotFirstSeenAtUtc":"2026-11-06T20:00:00Z",
        "cotReportDate":report,"cotFirstSeenVerified":True,
        "cotDataset":legs[0][0],
        "cotMappedLegWitnesses":[
            {"dataset":ds,"code":code,"reportDate":report,
             "firstSeenAtUtc":"2026-11-06T20:00:00Z"}
            for ds,code in legs],
        "priceWitnessAtUtc":received,
        "priceOriginalSha256":digest,
        "m15ClosedAtUtc":iso(closed),
        "priceQualityVerified":True,"provider":"ctrader",
        "priceFrame":"M15",
        "retailFirstSeenAtUtc":iso(closed),
        "retailQualityVerified":True,
        "cvdScanCoverage":"FULL_PROSPECTIVE",
        "cvdScanWitnessAtUtc":iso(closed+timedelta(seconds=45)),
        "cvdAlgorithm":study.CVD_VERSION,
        "cvdQualityVerified":True,
        "cvdOriginalClosedBarsVerified":True,
        "cvdSourceWitnessSha256":digest,
        "cvdFullMarketUniverseAtObservation":True,
        "cvdResult":cvd,
        "cvdConfirmedAtUtc":iso(closed+timedelta(seconds=42)),
        "secret":"DO_NOT_EXPOSE_THIS",
    }
    reg={
        "symbol":symbol,"observedAtUtc":observed,
        "firstRecordedAtUtc":first,
        "sourceReceivedAtUtc":received,
        "originalDocumentSha256":digest,
        "document":doc,
    }
    out={"core":core,"regime":reg,"imaginaryPnlBps":999999}
    for path, changes in mod.items():
        if path == "core":
            out["core"].update(changes)
        if path == "regime":
            out["regime"].update(changes)
    return out


def go(cases, **kwargs):
    defaults={"as_of":ASOF,"train_end":TRAIN,"validation_end":VALIDATION,
              "expected_protocol_sha256":study.FROZEN_PROTOCOL_SHA256}
    defaults.update(kwargs)
    return mat.audit(cases,**defaults)


def cells(out,fold="train",state="DIRECTIONAL_UP"):
    return out["folds"][fold]["regimes"][state]


class RegimeCvdCohortTests(unittest.TestCase):
    def test_exact_same_snapshot_classifies_cvd_and_regime(self):
        out=go([case()])
        self.assertEqual(out["coreAdmitted"],1)
        self.assertEqual(cells(out)["candidates"],1)
        self.assertEqual(cells(out)["cvd"]["ALIGNED_CANDIDATE"],1)
        self.assertEqual(cells(out)["distinctCotReportWeeks"],1)
        self.assertEqual(cells(out)["descriptiveGate"],
                         "INSUFFICIENT_COHORTS_OR_WEEKS")
        self.assertFalse(out["riskAdjustedPnLCalculated"])
        self.assertFalse(out["independentOutOfSampleValidated"])
        self.assertFalse(out["statisticalEdgeEstablished"])
        self.assertFalse(out["tradingOrNotificationsAuthorized"])
        self.assertEqual(out["protocolSha256"],study.FROZEN_PROTOCOL_SHA256)
        self.assertNotIn(SECRET,json.dumps(out))
        self.assertNotIn("DO_NOT_EXPOSE_THIS",json.dumps(out))
        self.assertNotIn("999999",json.dumps(out))

    def test_missing_regime_stays_unknown_without_removing_core_candidate(self):
        r=case()
        r["regime"]=None
        out=go([r])
        self.assertEqual(out["coreAdmitted"],1)
        self.assertEqual(cells(out,state="UNKNOWN")["candidates"],1)
        self.assertEqual(cells(out,state="UNKNOWN")["cvd"]
                         ["ALIGNED_CANDIDATE"],1)
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["missing_original_regime_witness"],1)

    def test_retrospective_or_different_original_price_cannot_be_paired(self):
        changed=case()
        changed["regime"]["document"]["timeframes"]["M15"][0]["c"]+=.001
        out=go([changed])
        self.assertEqual(cells(out,state="UNKNOWN")["candidates"],1)
        self.assertEqual(cells(out)["candidates"],0)
        wrong_receipt=case()
        wrong_receipt["regime"]["sourceReceivedAtUtc"]="2026-11-09T10:00:25Z"
        out=go([wrong_receipt])
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["different_original_price_receipt"],1)
        future=case()
        future["regime"]["observedAtUtc"]="2026-11-09T10:16:00Z"
        out=go([future])
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["different_original_decision"],1)

    def test_cvd_source_mismatch_and_missing_full_scan_not_negative(self):
        diff=case(cvd="NO_CONFIRMED_DIVERGENCE",
                  core={"cvdSourceWitnessSha256":"b"*64})
        missing=case("XAUUSD",kind="lateral",cvd="NO_CONFIRMED_DIVERGENCE",
                     core={"cvdScanCoverage":"PARTIAL"})
        out=go([diff,missing])
        self.assertEqual(cells(out)["cvd"]["UNKNOWN"],1)
        self.assertEqual(cells(out,state="LATERAL")["cvd"]["UNKNOWN"],1)
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["different_cvd_original_price_sha"],1)
        self.assertTrue(out["cvdUnknownNotNegative"])

    def test_cross_fold_cot_week_quarantined_all_markets(self):
        early=case()
        # Same COT report, other market after 2h embargo, with 24h
        # nominal horizon matured. The shared week cannot enter both folds.
        late=case("XAUUSD",observed="2026-11-11T10:01:00Z")
        # Do not accidentally put the synthetic second observation into the
        # validation PURGE window: that would not test week contamination.
        self.assertEqual(mat._fold(study._time("2026-11-11T10:01:00Z"),
                                   study._time(TRAIN),
                                   study._time(VALIDATION),
                                   study._time(ASOF)), "validation")
        out=go([early,late])
        self.assertEqual(out["coreAdmitted"],2)
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["cot_week_crosses_folds"],2)
        self.assertEqual(sum(f["candidates"] for f in out["folds"].values()),0)

    def test_train_validation_embargo_and_nominal_horizon(self):
        # 24h outcome horizon + 2h embargo crosses the train boundary.
        near=case(observed="2026-11-10T01:01:00Z")
        out=go([near])
        self.assertEqual(out["coreAdmitted"],1)
        self.assertEqual(out["foldExclusionsAndMissingProvenance"]
                         ["embargo_or_nominal_24h_not_elapsed"],1)
        self.assertEqual(sum(f["candidates"] for f in out["folds"].values()),0)

    def test_duplicate_core_quarantined_both_and_bad_cot_rejected(self):
        first=case()
        second=copy.deepcopy(first)
        second["core"]["cvdResult"]="NO_CONFIRMED_DIVERGENCE"
        bogus=case("XAUUSD",core={"cotFirstSeenAtUtc":"2026-11-12T12:00:00Z"})
        out=go([first,second,bogus])
        self.assertEqual(out["coreAdmitted"],0)
        self.assertEqual(out["coreExcluded"],3)
        self.assertEqual(out["coreExclusions"]
                         ["ambiguous_duplicate_observation"],2)
        self.assertEqual(sum(f["candidates"] for f in out["folds"].values()),0)
        self.assertEqual(out,go([bogus,second,first]))

    def test_no_profit_optimization_on_same_regime_matrix(self):
        a=case(cvd="NO_CONFIRMED_DIVERGENCE")
        b=copy.deepcopy(a)
        b["imaginaryPnlBps"]=-12345678
        b["imaginaryOutcome"]="LOSS"
        self.assertEqual(go([a]),go([b]))
        self.assertTrue(go([a])["notRealized24hOutcomes"])

    def test_empty_and_bad_split_fail_closed(self):
        out=go([])
        self.assertEqual(out["received"],0)
        self.assertEqual(out["coreAdmitted"],0)
        self.assertFalse(out["splitsExternallyPreRegistered"])
        with self.assertRaisesRegex(ValueError,
                                     "invalid_chronological_split_boundaries"):
            go([case()],train_end=VALIDATION,validation_end=TRAIN)
        with self.assertRaisesRegex(ValueError,"frozen_protocol_mismatch"):
            go([case()],expected_protocol_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"invalid_paired_coverage_records"):
            go([case()]*(mat.MAX_ROWS+1))


if __name__=="__main__":
    unittest.main()
