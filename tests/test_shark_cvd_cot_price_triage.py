"""REMURA Track B synthetic-only triple audit: COT + OHLC + CVD proxy.

An ORIGINAL source OHLC document is modified to contain a confirmed M15
bullish CLV*tick-volume proxy divergence near the REAL Squalincome signal
fixture clock. CVD is rerun on that same in-memory source before its atomic
private HMAC ledger insert; the COT+price linkage is separately recorded
by the authentic prospective bundle. No market-data API or LIVE access.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import json
import sqlite3
import unittest

from scripts import cvd_divergence as detector
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from scripts import shark_cvd_cot_price_triage as triple
from scripts import shark_cvd_ledger as cvd
from scripts import shark_cvd_source_lineage as lineage
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,NOW,OBSERVED,insert_history,iso
from test_shark_cvd_ledger import QUALITY,SECRET

UTC=timezone.utc


def source_with_verified_divergence(db,doc):
    source=json.loads(json.dumps(doc))
    bars=source["timeframes"]["M15"]
    for bar in bars:
        t=datetime.fromisoformat(bar["t"].replace("Z","+00:00"))
        if t.date()==OBSERVED.date() and t.hour==7 and t.minute==0:
            bar["l"]=0.998
        elif t.date()==OBSERVED.date() and t.hour==10 and t.minute==0:
            bar["l"]=0.995
    # Recompute ALL closed H1/H4 source frames from the *same* M15
    # snapshot; price-asof _source independently checks their rollups.
    for frame,seconds in (("H1",3600),("H4",14400)):
        groups={}
        for bar in bars:
            t=datetime.fromisoformat(bar["t"].replace("Z","+00:00"))
            opened=datetime.fromtimestamp(
                int(t.timestamp())//seconds*seconds,tz=UTC)
            groups.setdefault(opened,[]).append(bar)
        n=seconds//900
        result=[]
        for opened,group in sorted(groups.items()):
            if len(group)!=n:
                continue
            result.append({
                "t":iso(opened),"o":group[0]["o"],
                "h":max(x["h"] for x in group),
                "l":min(x["l"] for x in group),
                "c":group[-1]["c"],
                "v":sum(x["v"] for x in group),
            })
        source["timeframes"][frame]=result
    db.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
               (json.dumps(source),))
    db.commit()
    return source


def original_cvd_event(doc):
    market={
        "symbol":doc["symbol"],"provider":doc["provider"],
        "providerSymbol":doc["providerSymbol"],
        "frames":{"M15":[
            {**bar,"t":int(datetime.fromisoformat(
                bar["t"].replace("Z","+00:00")).timestamp()*1000)}
            for bar in doc["timeframes"]["M15"]
        ]},
    }
    report=detector.analyze(market,now=int(OBSERVED.timestamp()*1000))
    if report["status"]!="ok":
        raise AssertionError("detector did not verify synthetic source")
    qualified=[
        x for x in report["events"]
        if x["type"]=="bullish_regular"
        and x["first"]["pivotAt"].startswith("2026-11-04T07:00:00")
        and x["second"]["pivotAt"].startswith("2026-11-04T10:00:00")
    ]
    if len(qualified)!=1:
        raise AssertionError("expected one independently detected CVD pivot")
    return qualified[0]


class TripleCausalTriageTests(unittest.TestCase):
    def setUp(self):
        self.main,self.original=create()
        self.private=sqlite3.connect(":memory:")
        cvd.ensure_schema(self.private)
        self.doc=source_with_verified_divergence(self.main,self.original)
        self.event=original_cvd_event(self.doc)

    def tearDown(self):
        self.main.close()
        self.private.close()

    def _proof(self, *, prefix_enabled=False):
        witness.witness(self.main,clock=AT)
        with self.main:
            hid=insert_history(self.main)
            result=bundle.record(self.main,history_id=hid,
                                 observed_document=self.doc,clock=NOW,
                                 capture_cvd_prefix=prefix_enabled)
        self.assertEqual(result["state"],"BOTH_LOCAL_PROOFS_PRESENT")

    def _cvd(self,*,bound=True,secret=SECRET,now=OBSERVED,doc=None):
        return cvd.append(
            self.private,self.event,QUALITY,
            source_collected_at=iso(OBSERVED),
            hmac_secret=secret,now=now,
            source_document=(self.doc if doc is None else doc)
            if bound else None)

    def _triage(self,at=NOW+timedelta(seconds=5),secret=SECRET):
        a=self.main.total_changes
        b=self.private.total_changes
        report=triple.audit(
            self.main,self.private,as_of=iso(at),days=1,secret=secret)
        self.assertEqual(self.main.total_changes,a)
        self.assertEqual(self.private.total_changes,b)
        return report

    def _earlier_cvd(self,*,changed_source=None,detected=None):
        earlier=json.loads(json.dumps(self.doc))
        # CVD first sees M15 through 10:30 (close 10:45), whereas
        # Squalincome later sees an extra M15 (close 11:00).
        earlier["timeframes"]["M15"].pop()
        earlier["lastComplete"]=earlier["timeframes"]["M15"][-1]["t"]
        clock=detected or OBSERVED-timedelta(minutes=26)
        # Never smuggle later H1/H4 into the earlier CVD source document.
        for frame,span in (("H1",timedelta(hours=1)),
                           ("H4",timedelta(hours=4))):
            earlier["timeframes"][frame]=[
                bar for bar in earlier["timeframes"][frame]
                if datetime.fromisoformat(
                    bar["t"].replace("Z","+00:00"))+span<=clock]
        earlier_ev=original_cvd_event(earlier)
        self.assertEqual(earlier_ev["id"],self.event["id"])
        self.assertNotEqual(lineage._document_sha(earlier),
                            lineage._document_sha(self.doc))
        return cvd.append(
            self.private,earlier_ev,QUALITY,
            source_collected_at=iso(clock-timedelta(minutes=1)),
            hmac_secret=SECRET,now=clock,
            source_document=earlier if changed_source is None else changed_source)

    def test_earlier_snapshot_accepted_only_with_two_prospective_prefixes(self):
        self._proof(prefix_enabled=True)
        self._earlier_cvd()
        report=self._triage()
        self.assertEqual(report["exactSnapshotTriples"],0)
        self.assertTrue(report["earlierSnapshotPrefixProofsAvailable"])
        self.assertEqual(report["verifiedEarlierSnapshotTriples"],1)
        self.assertEqual(report["distinctSignalsWithEarlierCVD"],1)
        self.assertEqual(report["earlierSnapshotOrientations"],
                         {"SAME_TECHNICAL_DIRECTION":1})
        self.assertEqual(report["verifiedTriplesAnyTier"],1)
        self.assertFalse(report["earlierTierIsSameEntireOHLCSource"])
        self.assertFalse(report["tradingEdgeEstablished"])
        text=json.dumps(report)
        self.assertNotIn(self.doc["providerSymbol"],text)
        self.assertNotIn("0.995",text)

    def test_earlier_snapshot_no_original_main_prefix_is_not_negative_event(self):
        self._proof()
        self._earlier_cvd()
        report=self._triage()
        self.assertEqual(report["exactSnapshotTriples"],0)
        self.assertFalse(report["earlierSnapshotPrefixProofsAvailable"])
        self.assertIsNone(report["verifiedEarlierSnapshotTriples"])
        self.assertIsNone(report["verifiedTriplesAnyTier"])

    def test_earlier_snapshot_with_mutated_prior_m15_is_not_promoted(self):
        # Modify a prior M15 tick count and keep H1/H4 rollups
        # internally consistent BEFORE the genuine Squalincome proof.
        altered=self.doc["timeframes"]["M15"]
        target=next(x for x in altered if x["t"].endswith("T05:00:00Z"))
        target["v"]+=1
        for frame,span in (("H1",3600),("H4",14400)):
            t=datetime.fromisoformat(target["t"].replace("Z","+00:00"))
            bucket=int(t.timestamp())//span*span
            for x in self.doc["timeframes"][frame]:
                at=datetime.fromisoformat(x["t"].replace("Z","+00:00"))
                if int(at.timestamp())==bucket:
                    x["v"]+=1
        self.main.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                          (json.dumps(self.doc),))
        self.main.commit()
        self._proof(prefix_enabled=True)
        # Build the PREVIOUS source using the original volume in that bar.
        prior=json.loads(json.dumps(self.doc))
        for row in prior["timeframes"]["M15"]:
            if row["t"]==target["t"]:
                row["v"]-=1
        prior["timeframes"]["M15"].pop()
        prior["lastComplete"]=prior["timeframes"]["M15"][-1]["t"]
        for frame,span in (("H1",timedelta(hours=1)),
                           ("H4",timedelta(hours=4))):
            prior["timeframes"][frame]=[
                row for row in prior["timeframes"][frame]
                if datetime.fromisoformat(row["t"].replace("Z","+00:00"))
                +span<=OBSERVED-timedelta(minutes=26)]
        # Revert rollup volume on the historical source too.
        for frame,span in (("H1",3600),("H4",14400)):
            t=datetime.fromisoformat(target["t"].replace("Z","+00:00"))
            bucket=int(t.timestamp())//span*span
            for x in prior["timeframes"][frame]:
                at=datetime.fromisoformat(x["t"].replace("Z","+00:00"))
                if int(at.timestamp())==bucket:
                    x["v"]-=1
        ev=original_cvd_event(prior)
        cvd.append(self.private,ev,QUALITY,
                   source_collected_at=iso(
                       OBSERVED-timedelta(minutes=27)),
                   hmac_secret=SECRET,
                   now=OBSERVED-timedelta(minutes=26),
                   source_document=prior)
        report=self._triage()
        self.assertTrue(report["earlierSnapshotPrefixProofsAvailable"])
        self.assertEqual(report["exactSnapshotTriples"],0)
        self.assertEqual(report["verifiedEarlierSnapshotTriples"],0)

    def test_earlier_snapshot_does_not_invent_a_past_detection(self):
        self._proof(prefix_enabled=True)
        self._earlier_cvd(detected=OBSERVED+timedelta(minutes=1))
        report=self._triage(at=OBSERVED+timedelta(minutes=2))
        self.assertEqual(report["exactSnapshotTriples"],0)
        self.assertEqual(report["verifiedEarlierSnapshotTriples"],0)

    def test_same_original_snapshot_real_detector_and_cot_price_proofs(self):
        self._proof()
        self.assertTrue(self._cvd()["sourceDocumentBound"])
        result=self._triage()
        self.assertEqual(result["status"],
                         "EXACT_LOCAL_COT_PRICE_CVD_SOURCE_MATCHES_AUDITED_NOT_PREDICTIVE")
        self.assertEqual(result["validLocalCotPricePairs"],1)
        self.assertEqual(result["privateCvdEvents"],1)
        self.assertEqual(result["sourceBoundCvdEvents"],1)
        self.assertEqual(result["exactSnapshotTriples"],1)
        self.assertEqual(result["distinctSignalsWithExactCVD"],1)
        self.assertEqual(result["orientations"],{
            "SAME_TECHNICAL_DIRECTION":1})
        self.assertFalse(result["cvdAggressorFlowMeasured"])
        self.assertFalse(result["tradingEdgeEstablished"])
        self.assertFalse(result["crossDatabaseAtomicCommit"])
        self.assertEqual(result["institutionalPredictiveCohortsAdmissible"],0)
        self.assertEqual(result["brokerCalls"],0)
        text=json.dumps(result)
        self.assertNotIn(self.doc["providerSymbol"],text)
        self.assertNotIn(self.event["id"],text)
        self.assertNotIn(lineage._document_sha(self.doc),text)
        self.assertNotIn("0.995",text)

    def test_legacy_event_with_same_market_time_is_still_unknown(self):
        self._proof()
        self._cvd(bound=False)
        result=self._triage()
        self.assertEqual(result["status"],
                         "PRIVATE_CVD_DOCUMENT_BINDINGS_UNAVAILABLE")
        self.assertIsNone(result["exactSnapshotTriples"])
        self.assertEqual(result["privateCvdEvents"],1)

    def test_different_private_secret_cannot_fake_a_matching_source(self):
        self._proof()
        self._cvd()
        report=self._triage(secret=b"other-authorized-private-secret!!")
        self.assertEqual(report["exactSnapshotTriples"],0)
        self.assertEqual(report["sourceBoundCvdEvents"],1)

    def test_same_market_and_detection_but_different_document_is_unknown(self):
        self._proof()
        changed=json.loads(json.dumps(self.doc))
        # This H1 change leaves the exact M15 CVD event intact, but the
        # full source document is NOT the source of the price evidence.
        changed["timeframes"]["H1"][-1]["h"]+=0.001
        self._cvd(doc=changed)
        out=self._triage()
        self.assertEqual(out["validLocalCotPricePairs"],1)
        self.assertEqual(out["privateCvdEvents"],1)
        self.assertEqual(out["exactSnapshotTriples"],0)
        self.assertEqual(out["distinctSignalsWithExactCVD"],0)

    def test_future_cvd_event_is_invisible_in_earlier_asof_counts(self):
        self._proof()
        self._cvd(now=NOW+timedelta(seconds=30))
        before=self._triage(at=NOW+timedelta(seconds=5))
        self.assertEqual(before["validLocalCotPricePairs"],1)
        self.assertEqual(before["privateCvdEvents"],0)
        self.assertEqual(before["sourceBoundCvdEvents"],0)
        self.assertEqual(before["exactSnapshotTriples"],0)
        after=self._triage(at=NOW+timedelta(seconds=60))
        self.assertEqual(after["privateCvdEvents"],1)
        self.assertEqual(after["sourceBoundCvdEvents"],1)
        self.assertEqual(after["exactSnapshotTriples"],0)

    def test_later_event_cannot_create_an_earlier_signal(self):
        self._proof()
        self._cvd(now=OBSERVED+timedelta(seconds=20))
        result=self._triage()
        self.assertEqual(result["exactSnapshotTriples"],0)
        self.assertEqual(result["validLocalCotPricePairs"],1)

    def test_absent_cot_witness_must_keep_three_way_counts_zero(self):
        # Valid private CVD is never evidence that COT was seen before signal.
        with self.main:
            hid=insert_history(self.main)
            result=bundle.record(self.main,history_id=hid,
                                 observed_document=self.doc,clock=NOW)
        self.assertEqual(result["state"],"PARTIAL_LOCAL_PROOFS")
        self._cvd()
        report=self._triage()
        self.assertEqual(report["validLocalCotPricePairs"],0)
        self.assertEqual(report["exactSnapshotTriples"],0)

    def test_absent_private_event_is_not_a_synthetic_positive(self):
        self._proof()
        result=self._triage()
        self.assertEqual(result["status"],
                         "PRIVATE_CVD_DOCUMENT_BINDINGS_UNAVAILABLE")
        self.assertIsNone(result["exactSnapshotTriples"])

    def test_immutable_private_cvd_event_table_must_exist(self):
        self._proof()
        self._cvd()
        self.private.execute("DROP TRIGGER research_cvd_no_update")
        with self.assertRaisesRegex(ValueError,
                                    "private_cvd_event_triggers_missing"):
            self._triage()

    def test_missing_main_provenance_is_not_zero_negative_signal(self):
        empty=sqlite3.connect(":memory:")
        try:
            result=triple.audit(empty,self.private,as_of=iso(NOW),
                                secret=SECRET)
        finally:
            empty.close()
        self.assertEqual(result["status"],"COT_PRICE_PROOFS_UNAVAILABLE")
        self.assertIsNone(result["exactSnapshotTriples"])
        self.assertFalse(result["tradingEdgeEstablished"])

if __name__=="__main__":
    unittest.main()
