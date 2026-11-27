"""Track B OFFLINE: zero-I/O preflight for reuse of ORIGINAL price snapshots.

NOT a CVD recorder, background task, broker client or production adapter.
Accepts only the already-created 34-row FULL price-only research batch and
the SAME two in-memory market documents produced by the original collector.
No re-fetch, no COT filtering, no SQLite, no HMAC secret needed, no detector
execution, no persistent output, no speculative missing data backfill.

The last two markets are a CURRENTLY LIMITED PILOT, not a representative 34
market CVD denominator. A passing preflight never authorizes a live deployment.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import hmac

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_cvd_scan_coverage as scan
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_price_only_compact as compact

SCHEMA = "remura-track-b-same-original-cvd-bridge-preflight-v1"
FROZEN_PILOT = frozenset(("EURUSD","XAUUSD"))
MAX_PILOT_DOCS = 2
MAX_ORIGINAL_M15 = 4320


def prepare(price_rows, pilot_documents, *, clock):
    """Fail closed if research capture could mistake later data for original.

    The only prospective caller may pass a single UTC clock, the 34 already
    prepared price-only cells and at most two ORIGINAL in-memory documents.
    This function never starts a scan or performs a write. The normal
    production path does not import it.

    Output deliberately has no source/identity hashes, prices, account
    fields, broker symbols, COT versions, files, event data or order hints.
    """
    if (protocol.protocol_sha256()!=protocol.FROZEN_PROTOCOL_SHA256 or
            set(scan.PILOT)!=FROZEN_PILOT or
            len(scan.PILOT)!=MAX_PILOT_DOCS or
            not FROZEN_PILOT.issubset(protocol.FROZEN_UNIVERSE)):
        raise ValueError("frozen_preregistration_or_pilot_changed")
    if type(clock) is not datetime:
        raise ValueError("explicit_utc_research_clock_required")
    now=witness._clock(clock)
    start=witness._parse(protocol.START)
    if now < start:
        raise ValueError("prospective_study_has_not_started")
    if type(price_rows) not in (tuple,list) or len(price_rows)!=34:
        raise ValueError("exact_34_price_cells_required")
    if type(pilot_documents) is not dict or len(pilot_documents)>MAX_PILOT_DOCS:
        raise ValueError("pilot_documents_scope_invalid")
    if not set(pilot_documents).issubset(FROZEN_PILOT):
        raise ValueError("nonpilot_source_documents_not_allowed")

    # Reuse the ORIGINAL compact batch preparation contract, which checks
    # 34 distinct markets, exact slot, allowed states and original receipt
    # times. No COT reader, no price loader, no database and no API call.
    checked=compact.prepare_batch(price_rows,full=True,clock=now)
    slot=witness._parse(checked["slot"])
    if slot<start:
        raise ValueError("backdated_full_scan_slot")
    if checked["marketCount"]!=len(protocol.FROZEN_UNIVERSE):
        raise ValueError("frozen_universe_count_mismatch")
    by_symbol={}
    for row in price_rows:
        by_symbol[row[0]]=row
    if set(by_symbol)!=set(protocol.FROZEN_UNIVERSE):
        raise ValueError("original_34_catalog_mismatch")
    counts=Counter()
    for symbol in ("EURUSD","XAUUSD"):
        row=by_symbol[symbol]
        doc=pilot_documents.get(symbol)
        if doc is None:
            # Price-only may have attested a cell, but no ORIGINAL M15 doc
            # survives for a causal CVD scan; cannot re-fetch it now.
            counts["SOURCE_NOT_AVAILABLE"]+=1
            continue
        if (type(doc) is not dict or
                doc.get("symbol")!=symbol or
                doc.get("provider")!="ctrader" or
                doc.get("timezone")!="UTC" or
                doc.get("sourceTimeframe")!="M15" or
                type(doc.get("providerSymbol")) is not str or
                not doc["providerSymbol"].strip() or
                type(doc.get("timeframes")) is not dict or
                any(type(doc["timeframes"].get(frame)) is not list
                    for frame in ("M15","H1","H4"))):
            raise ValueError("original_source_identity_mismatch")
        bars=doc["timeframes"]["M15"]
        if not 1<=len(bars)<=MAX_ORIGINAL_M15 or type(bars[-1]) is not dict:
            raise ValueError("unbounded_or_absent_m15_document")
        if (witness._parse(doc.get("lastComplete"))!=
                witness._parse(bars[-1].get("t"))):
            raise ValueError("original_last_complete_inconsistent")
        closed=witness._parse(doc["lastComplete"])+scan.STEP
        if closed!=slot:
            raise ValueError("not_same_original_m15_slot")
        # The compact price-only source hash is the SAME canonical document
        # digest as the CVD HMAC input. Caller must NOT supply a revised,
        # updated or reloaded doc after the price classification.
        original_sha=row[13]
        if (type(original_sha) is not str or
                not compact.HEX.fullmatch(original_sha) or
                not hmac.compare_digest(
                    lineage._document_sha(doc),original_sha)):
            raise ValueError("price_document_race_or_missing_source_digest")
        if row[4]=="PRICE_UNIVERSE_NOT_RECORDED":
            raise ValueError("placeholder_cannot_have_original_document")
        seen=witness._parse(row[2])
        if (not closed<=seen<=now<=closed+scan.GRACE or
                now-seen>timedelta(seconds=30)):
            # A too-late attempt is UNKNOWN, never forged as a valid scan.
            counts["OUTSIDE_PROSPECTIVE_CVD_CLOCK"]+=1
            continue
        if row[14]!=1:
            counts["TICK_VOLUME_INCOMPLETE"]+=1
            continue
        # This is only an opportunity to CALL the existing detector once.
        # We intentionally do NOT do it, and do not fabricate a negative.
        counts["PILOT_SOURCE_READY_FOR_ISOLATED_FUTURE_TEST"]+=1
    return {
        "schema":SCHEMA,
        "status":"ORIGINAL_DOCUMENT_PREFLIGHT_ONLY_NOT_ACTIVE",
        "prospectiveStartUtc":protocol.START,
        "protocolSha256":protocol.FROZEN_PROTOCOL_SHA256,
        "fullPriceOnlyDenominator":len(protocol.FROZEN_UNIVERSE),
        "fullPriceOnlyCandidateCount":checked["candidateCount"],
        "fullPriceOnlyExplicitUnknownCount":checked["unknownCount"],
        "twoPilotMarketsOnly":MAX_PILOT_DOCS,
        "marketsNotSupportedByExistingCvdRecorder":
            len(protocol.FROZEN_UNIVERSE)-MAX_PILOT_DOCS,
        "pilotOriginalSourcesReadyForFutureTest":
            counts["PILOT_SOURCE_READY_FOR_ISOLATED_FUTURE_TEST"],
        "pilotOriginalSourceUnavailable":counts["SOURCE_NOT_AVAILABLE"],
        "pilotOutsideAllowedCvdClock":counts["OUTSIDE_PROSPECTIVE_CVD_CLOCK"],
        "pilotIncompleteTickVolume":counts["TICK_VOLUME_INCOMPLETE"],
        "providedPilotHashesCheckedAgainstOriginalPriceRows":True,
        "unknownPilotSourcesAreNotCrossChecked":True,
        "cOTFilteringApplied":False,
        "retailSourceJoined":False,
        "cvdDetectorEvaluated":False,
        "cvdScanAttemptsRecorded":False,
        "missingOrZeroNewCvdEventProvesNegative":False,
        "crossDatabaseAtomicityEstablished":False,
        "independentBrokerFirstSeenProved":False,
        "futureOutcomeNetOfExecutionCostsVerified":False,
        "extraBrokerRequestsMade":0,
        "sqliteReadsOrWritesMade":0,
        "networkOrFilesystemIOPerformed":False,
        "cloudCostIntroduced":False,
        "enabledInProduction":False,
        "researchMayBeEnabled":False,
        "tradingOrNotificationsAuthorized":False,
        "statisticalInstitutionalEdgeEstablished":False,
    }
