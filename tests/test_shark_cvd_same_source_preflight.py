"""Disposable synthetic-only preflight for a SAME-original price/CVD bridge.

No Oracle, live SQLite, cTrader API, real quotes/market performance or trades.
Synthetic original OHLC docs are created in memory via the existing collector
formatter. Test does NOT activate the existing CVD scan recorder.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import json
import unittest
from unittest.mock import patch

from scripts import price_feed
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_cvd_same_source_preflight as bridge
from scripts import shark_cvd_scan_coverage as scans
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_price_only_universe as universe

UTC=timezone.utc
SLOT=datetime(2026,11,9,11,0,0,tzinfo=UTC)
AT=SLOT+timedelta(minutes=1,seconds=10)
SECRET="PRIVATE_SYNTHETIC_BROKER_MAPPING_DO_NOT_EXPORT"


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def original_document(symbol):
    bars=[]
    for i in range(160):
        time=SLOT-timedelta(minutes=(160-i)*15)
        op=1.1+i*0.0001
        bars.append({"t":stamp(time),"o":op,
                     "h":op+0.0004,"l":op-0.0002,
                     "c":op+0.0002,"v":100+i%3})
    return price_feed.market_document(
        symbol,"ctrader",SECRET,bars,AT)


def inputs(*,pilot=("EURUSD","XAUUSD"),one_missing=False):
    docs={s:original_document(s) for s in pilot}
    rows=[]
    for symbol in protocol.FROZEN_UNIVERSE:
        if symbol in docs and not (one_missing and symbol=="EURUSD"):
            state="PRICE_CONTEXT_READY"
            quality="verified"
            freshness="recent"
            closed=stamp(SLOT)
            side=1
            digest=lineage._document_sha(docs[symbol])
            complete=1
            pstate="confirmed"
        else:
            state="PRICE_UNIVERSE_NOT_RECORDED"
            quality="missing"
            freshness="missing"
            closed=None
            side=0
            digest=None
            complete=0
            pstate=None
        rows.append((
            symbol,stamp(SLOT),
            stamp(SLOT+timedelta(minutes=1)),
            stamp(SLOT+timedelta(minutes=1,seconds=2)),
            state,quality,freshness,closed,side,pstate,
            side,side,side,digest,complete,universe.ALGORITHM
        ))
    if one_missing:
        docs.pop("EURUSD",None)
    return rows,docs


def update_row(rows,symbol,idx,value):
    found=[]
    for row in rows:
        item=list(row)
        if item[0]==symbol:
            item[idx]=value
        found.append(tuple(item))
    return found


class SameOriginalPreflightTests(unittest.TestCase):

    def test_two_valid_original_pilot_docs_full34_denominator_not_activated(self):
        rows,docs=inputs()
        backup=copy.deepcopy(docs)
        out=bridge.prepare(rows,docs,clock=AT)
        self.assertEqual(docs,backup)
        self.assertEqual(out["status"],"ORIGINAL_DOCUMENT_PREFLIGHT_ONLY_NOT_ACTIVE")
        self.assertEqual(out["fullPriceOnlyDenominator"],34)
        self.assertEqual(out["fullPriceOnlyCandidateCount"],2)
        self.assertEqual(out["fullPriceOnlyExplicitUnknownCount"],32)
        self.assertEqual(out["twoPilotMarketsOnly"],2)
        self.assertEqual(out["marketsNotSupportedByExistingCvdRecorder"],32)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],2)
        self.assertEqual(out["pilotOriginalSourceUnavailable"],0)
        self.assertEqual(out["pilotOutsideAllowedCvdClock"],0)
        self.assertEqual(out["extraBrokerRequestsMade"],0)
        self.assertEqual(out["sqliteReadsOrWritesMade"],0)
        self.assertFalse(out["cvdDetectorEvaluated"])
        self.assertFalse(out["cvdScanAttemptsRecorded"])
        self.assertFalse(out["enabledInProduction"])
        self.assertFalse(out["researchMayBeEnabled"])
        self.assertFalse(out["tradingOrNotificationsAuthorized"])
        self.assertFalse(out["statisticalInstitutionalEdgeEstablished"])
        self.assertEqual(out["protocolSha256"],protocol.FROZEN_PROTOCOL_SHA256)
        public=json.dumps(out)
        self.assertNotIn(SECRET,public)
        self.assertNotIn("EURUSD",public)
        self.assertNotIn("XAUUSD",public)
        self.assertNotIn("1.1",public)
        self.assertNotIn("hmac",public.lower())

    def test_cvd_missing_source_does_not_backfill_or_refetch(self):
        rows,docs=inputs(pilot=("EURUSD",))
        out=bridge.prepare(rows,docs,clock=AT)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],1)
        self.assertEqual(out["pilotOriginalSourceUnavailable"],1)
        self.assertFalse(out["missingOrZeroNewCvdEventProvesNegative"])
        self.assertFalse(out["researchMayBeEnabled"])

    def test_explicit_unknown_price_cell_keeps_denominator(self):
        rows,docs=inputs(one_missing=True)
        out=bridge.prepare(rows,docs,clock=AT)
        self.assertEqual(out["fullPriceOnlyDenominator"],34)
        self.assertEqual(out["fullPriceOnlyCandidateCount"],1)
        self.assertEqual(out["fullPriceOnlyExplicitUnknownCount"],33)
        self.assertEqual(out["pilotOriginalSourceUnavailable"],1)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],1)

    def test_mismatched_original_document_cannot_be_replaced_after_price_scan(self):
        rows,docs=inputs()
        docs=copy.deepcopy(docs)
        docs["EURUSD"]["providerSymbol"]="AFTER_SCAN_REPLACEMENT"
        with self.assertRaisesRegex(ValueError,
                                     "price_document_race_or_missing_source_digest"):
            bridge.prepare(rows,docs,clock=AT)
        self.assertNotIn("AFTER_SCAN_REPLACEMENT",
                         json.dumps(bridge.prepare(rows,inputs()[1],clock=AT)))

    def test_price_only_sha_tampering_fails_closed(self):
        rows,docs=inputs()
        rows=update_row(rows,"EURUSD",13,"f"*64)
        with self.assertRaisesRegex(ValueError,
                                     "price_document_race_or_missing_source_digest"):
            bridge.prepare(rows,docs,clock=AT)

    def test_wrong_ohlc_close_and_provider_identity_fails_closed(self):
        for changed in (
            {"symbol":"GBPUSD"}, {"provider":"demo"},
            {"sourceTimeframe":"H1"},{"timezone":"Europe/Rome"},
            {"providerSymbol":""},
        ):
            with self.subTest(changed=changed):
                rows,docs=inputs()
                docs["EURUSD"].update(changed)
                with self.assertRaisesRegex(ValueError,
                                             "original_source_identity_mismatch"):
                    bridge.prepare(rows,docs,clock=AT)
        rows,docs=inputs()
        docs["EURUSD"]["lastComplete"]=stamp(SLOT)
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock=AT)
        rows,docs=inputs()
        docs["EURUSD"]["timeframes"]["M15"]=[]
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock=AT)

    def test_same_original_document_but_late_current_window_is_unknown(self):
        rows,docs=inputs()
        late=SLOT+timedelta(minutes=3,seconds=20)
        rows=update_row(rows,"EURUSD",2,stamp(late))
        rows=update_row(rows,"XAUUSD",2,stamp(late))
        rows=update_row(rows,"EURUSD",3,stamp(late+timedelta(seconds=2)))
        rows=update_row(rows,"XAUUSD",3,stamp(late+timedelta(seconds=2)))
        out=bridge.prepare(rows,docs,clock=late+timedelta(seconds=5))
        self.assertEqual(out["pilotOutsideAllowedCvdClock"],2)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],0)
        self.assertFalse(out["researchMayBeEnabled"])

    def test_tick_volume_incomplete_is_not_cvd_ready(self):
        rows,docs=inputs()
        rows=update_row(rows,"EURUSD",14,0)
        out=bridge.prepare(rows,docs,clock=AT)
        self.assertEqual(out["pilotIncompleteTickVolume"],1)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],1)
        self.assertFalse(out["cvdDetectorEvaluated"])

    def test_extra_pilot_doc_with_placeholder_cannot_fabricate_price(self):
        rows,docs=inputs()
        row=next(x for x in rows if x[0]=="EURUSD")
        bad=list(row)
        bad[4]="PRICE_UNIVERSE_NOT_RECORDED"
        bad[5]=bad[6]="missing"
        bad[7]=None
        bad[8]=bad[10]=bad[11]=bad[12]=0
        bad[9]=None
        bad[13]=None
        bad[14]=0
        rows=[tuple(bad) if x[0]=="EURUSD" else x for x in rows]
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock=AT)

    def test_no_full_market_denominator_ambiguity(self):
        rows,docs=inputs()
        for bad in (rows[:33],rows+[rows[0]],
                    [r for r in rows if r[0]!="EURUSD"]):
            with self.assertRaises(ValueError):
                bridge.prepare(bad,docs,clock=AT)
        rows,docs=inputs()
        rows=update_row(rows,"EURUSD",0,"GER30")
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock=AT)
        with self.assertRaisesRegex(ValueError,
                                     "nonpilot_source_documents_not_allowed"):
            bridge.prepare(inputs()[0],{**docs,"USDCHF":{}},clock=AT)

    def test_cannot_run_before_prospective_start_or_with_untrusted_clock(self):
        rows,docs=inputs()
        with self.assertRaisesRegex(ValueError,"prospective_study_has_not_started"):
            bridge.prepare(rows,docs,clock=datetime(2026,11,6,11,1,tzinfo=UTC))
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock=datetime(2026,11,9,11,1))
        with self.assertRaises(ValueError):
            bridge.prepare(rows,docs,clock="2026-11-09T11:01:10Z")
        with patch.dict(protocol.PROTOCOL,{"stopAtr":3.25}):
            with self.assertRaisesRegex(ValueError,"frozen_preregistration"):
                bridge.prepare(rows,docs,clock=AT)

    def test_no_network_database_or_filesystem_operations(self):
        rows,docs=inputs()
        with patch("sqlite3.connect",side_effect=AssertionError("sqlite_access")):
            with patch("urllib.request.urlopen",side_effect=AssertionError("http_access")):
                with patch("builtins.open",side_effect=AssertionError("fs_access")):
                    out=bridge.prepare(rows,docs,clock=AT)
        self.assertEqual(out["pilotOriginalSourcesReadyForFutureTest"],2)
        self.assertFalse(out["networkOrFilesystemIOPerformed"])

    def test_production_entrypoints_not_wired_to_private_preflight(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        for path in ("scripts/signals_monitor.py","scripts/private_server.py"):
            with self.subTest(entrypoint=path):
                source=(root/path).read_text()
                self.assertNotIn("shark_cvd_same_source_preflight",source)
                self.assertNotIn("shark_cvd_full_denominator_audit",source)


if __name__=="__main__":
    unittest.main()
