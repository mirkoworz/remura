"""Track B OFFLINE: cTrader child -> price_store merge -> observer HANDOFF preflight.

The existing production architecture uses 3 distinct stages:
  1. ctrader_feed.collect() builds remura-price-v1 (generatedAt is set
     BEFORE broker requests; it is NOT cTrader response receipt time).
  2. private_server.collect_once() reads a private child temp JSON and
     price_store.ingest() MERGES historical M15, then regenerates H1/H4.
  3. signals_monitor._scan_once() opens prices in a later DB connection.
Thus the broker child document need NOT equal the merged stored document.

This module simulates an ephemeral, in-memory handoff with explicit UTC local
timestamps and exact 33 closed M15 overlap between child and merged source.
It can detect accidental post-ingest revision by checking the entire merged
SHA again at the scan; it CANNOT certify when real cTrader data were received,
that a receipt was recorded at the time, or keep a token across processes.
Never use it to backfill an institutional signal, prove a trading edge or
activate collector/VM. Zero DB writes, network calls, orders or alerts.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import math

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as study
from scripts import shark_market_regime_context as regime

SCHEMA = "remura-track-b-ctrader-local-ingest-scan-handoff-preflight-v1"
STEP = timedelta(minutes=15)
LAST_M15 = 33
MAX_CHILD_DURATION = timedelta(minutes=12)
MAX_INGEST_DURATION = timedelta(minutes=2)
MAX_SCAN_AGE = timedelta(minutes=3)
MAX_SOURCE_BARS = 4320


def _identity(doc, *, symbol):
    if (type(doc) is not dict or doc.get("symbol") != symbol
            or doc.get("provider") != "ctrader"
            or doc.get("sourceTimeframe") != "M15"
            or doc.get("timezone") != "UTC"
            or type(doc.get("providerSymbol")) is not str
            or not doc["providerSymbol"].strip()
            or type(doc.get("timeframes")) is not dict):
        raise ValueError("source_mapping_unverifiable")
    rows = doc["timeframes"].get("M15")
    if type(rows) is not list or not LAST_M15 <= len(rows) <= MAX_SOURCE_BARS:
        raise ValueError("original_m15_window_missing")
    out = []
    prior = None
    for b in rows[-LAST_M15:]:
        if type(b) is not dict:
            raise ValueError("invalid_closed_m15")
        started = witness._parse(b.get("t"))
        if (int(started.timestamp()) % 900 or
                prior is not None and started - prior != STEP):
            raise ValueError("noncontiguous_original_m15")
        vals = [b.get(k) for k in ("o", "h", "l", "c")]
        if (not all(type(x) in (float, int) and
                    math.isfinite(x) and x > 0 for x in vals)
                or vals[1] < max(vals[0], vals[3])
                or vals[2] > min(vals[0], vals[3])
                or vals[1] < vals[2]):
            raise ValueError("invalid_original_ohlc")
        volume = b.get("v")
        if volume is not None and (
                type(volume) is not int
                or not 0 <= volume <= 9007199254740991):
            raise ValueError("invalid_original_tick_volume")
        out.append((started, tuple(vals), volume))
        prior = started
    if witness._parse(doc.get("lastComplete")) != out[-1][0]:
        raise ValueError("last_complete_is_not_last_open")
    return out


def stage(child_export, stored_document, *, symbol, parent_read_at,
          ingest_finished_at, staged_at):
    """Local candidate only; all timestamps are caller-provided UTC clocks.

    Must run with the original child JSON and the freshly merged SQLite
    price document in memory at ingestion; **not** in a later backtest.
    A future implementation must ensure this is actually called there,
    with an append-only source receipt recorded in the SAME ingest write.
    """
    if study.protocol_sha256() != study.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_study_changed")
    if type(symbol) is not str or symbol not in study.FROZEN_UNIVERSE:
        raise ValueError("outside_research_universe")
    if (type(child_export) is not dict
            or child_export.get("schema") != "remura-price-v1"
            or type(child_export.get("markets")) is not dict
            or symbol not in child_export["markets"]):
        raise ValueError("original_child_export_required")
    if any(type(x) is not datetime for x in
           (parent_read_at, ingest_finished_at, staged_at)):
        raise ValueError("explicit_actual_local_utc_clocks_required")
    received = witness._clock(parent_read_at)
    committed = witness._clock(ingest_finished_at)
    staged = witness._clock(staged_at)
    generated = witness._parse(child_export.get("generatedAt"))
    started = witness._parse(study.START)
    if (not started <= generated <= received <= committed <= staged
            or received - generated > MAX_CHILD_DURATION
            or committed - received > MAX_INGEST_DURATION):
        raise ValueError("noncausal_process_handoff_clocks")
    original = child_export["markets"][symbol]
    child_bars = _identity(original, symbol=symbol)
    saved_bars = _identity(stored_document, symbol=symbol)
    if original["providerSymbol"] != stored_document["providerSymbol"]:
        raise ValueError("broker_mapping_changed_between_processes")
    # The merged document may have additional older M15 bars. Its LAST
    # 33 must still precisely reproduce the child window. Matching SHA
    # of the *whole* child market would be wrong: price_store.ingest
    # regenerates H1/H4 and may add older M15 history.
    if child_bars != saved_bars:
        raise ValueError("child_to_merged_last33_candles_changed")
    closed = saved_bars[-1][0] + STEP
    if (generated < closed or received < closed or
            staged - closed < timedelta(0) or
            staged - closed > MAX_SCAN_AGE):
        raise ValueError("unclosed_or_stale_at_handoff")
    return {
        "schema": SCHEMA,
        "symbol": symbol,
        "mergedSha256": regime._digest(stored_document),
        "childSha256": regime._digest(original),
        "parentReadAtUtc": witness._iso(received),
        "ingestFinishedAtUtc": witness._iso(committed),
        "stagedAtUtc": witness._iso(staged),
        "closedAtUtc": witness._iso(closed),
        # THIS IS ONLY A TRANSIENT AND SELF-REPORTED IN-PROCESS CONTRACT.
        # Never serialize to a public API or claim it was persisted.
        "immutableIngestReceiptRecorded": False,
        "firstSeenBrokerResponseVerified": False,
    }


def check_scan(handoff, current_document, *, scan_at):
    """Reject later source changes or stale/non-causal scan observations."""
    if type(handoff) is not dict or handoff.get("schema") != SCHEMA:
        raise ValueError("transient_original_handoff_required")
    if (type(handoff.get("symbol")) is not str
            or handoff["symbol"] not in study.FROZEN_UNIVERSE
            or handoff.get("immutableIngestReceiptRecorded") is not False
            or handoff.get("firstSeenBrokerResponseVerified") is not False):
        raise ValueError("handoff_integrity_flags_invalid")
    scan = witness._clock(scan_at)
    staged = witness._parse(handoff.get("stagedAtUtc"))
    receipt = witness._parse(handoff.get("parentReadAtUtc"))
    recorded = witness._parse(handoff.get("ingestFinishedAtUtc"))
    close = witness._parse(handoff.get("closedAtUtc"))
    if (not close <= receipt <= recorded <= staged <= scan
            or scan - close > MAX_SCAN_AGE):
        raise ValueError("scan_cannot_join_stale_or_future_receipt")
    if (type(current_document) is not dict or
            regime._digest(current_document) != handoff.get("mergedSha256")):
        raise ValueError("original_price_store_revised_after_handoff")
    # Reuse the SAME strict prospective 33 closed-M15 classifier. No PnL.
    classified = regime.classify({
        "symbol": handoff["symbol"],
        "observedAtUtc": witness._iso(scan),
        "firstRecordedAtUtc": witness._iso(recorded),
        "sourceReceivedAtUtc": witness._iso(receipt),
        "originalDocumentSha256": handoff["mergedSha256"],
        "document": current_document,
    }, as_of=witness._iso(scan))
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_MATCHED_MERGED_SOURCE_ONLY_NOT_PERSISTED",
        "regimeCandidate": classified["state"],
        "childAndMergedLast33MatchedAtLocalStage": True,
        "fullMergedDocumentUnchangedAtScan": True,
        "actualBrokerResponseReceiptVerified": False,
        "persistentFirstSeenIngestReceiptExists": False,
        "collectorAndObserverSameProcessOrTransaction": False,
        "cotAndRetailProofsIncluded": False,
        "cvdProxyConfirmationIncluded": False,
        "independentTrustedTimeOrSource": False,
        "backfilledHistoricalEvidenceAllowed": False,
        "statisticalEdgeEstablished": False,
        "liveCollectorIntegrationEnabled": False,
        "ordersOrNotificationsEnabled": False,
        "brokerCalls": 0,
        "writes": 0,
    }
