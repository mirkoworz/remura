"""Track B offline-only prospective market-regime context from ORIGINAL M15.

This is an ancillary descriptive analysis, NOT a change to the frozen
2026-11-09 CVD incremental study, and not a COT, order-flow or trade signal.
A genuine future caller would have to preserve each immutable same-source
price witness at observation time. SHA and operator-supplied timestamps here
are LOCAL consistency checks, not external clock/source authentication.

Never reload today's prices to label yesterday's observation. No database,
filesystem, HTTP, broker, trading, scheduler, signals or notifications.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import hashlib
import json
import math
import re

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as study

SCHEMA = "remura-track-b-prospective-price-regime-context-v1"
WINDOW_BARS = 33                   # 32 consecutive M15 close-to-close moves
STEP = timedelta(minutes=15)
MAX_RECEIPT_AGE = timedelta(minutes=3)
MAX_RECORD_DELAY = timedelta(seconds=120)
MAX_RECORDS = 10000
MAX_M15 = 4320
# Fixed descriptive buckets; NOT learned from, or tuned to, trade outcomes.
LATERAL_MAX = 0.30
DIRECTIONAL_MIN = 0.60
STATES = ("DIRECTIONAL_UP", "DIRECTIONAL_DOWN", "LATERAL", "MIXED")


def _digest(document):
    """Same canonical price-document SHA convention as price-asof evidence."""
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(raw) > 4_000_000:
        raise ValueError("source_document_too_large")
    return hashlib.sha256(raw).hexdigest()


def _finite(v):
    return type(v) in (int, float) and math.isfinite(v) and v > 0


def _validated(row, now):
    if type(row) is not dict or type(row.get("document")) is not dict:
        raise ValueError("original_source_required")
    symbol = row.get("symbol")
    if type(symbol) is not str or symbol not in study.FROZEN_UNIVERSE:
        raise ValueError("outside_frozen_market_universe")
    doc = row["document"]
    if (doc.get("symbol") != symbol or doc.get("provider") != "ctrader"
            or doc.get("timezone") != "UTC"
            or doc.get("sourceTimeframe") != "M15"
            or type(doc.get("providerSymbol")) is not str
            or not doc["providerSymbol"].strip()
            or type(doc.get("timeframes")) is not dict):
        raise ValueError("source_identity_mismatch")
    frames = doc["timeframes"]
    if type(frames.get("M15")) is not list or not (
            WINDOW_BARS <= len(frames["M15"]) <= MAX_M15):
        raise ValueError("missing_bounded_m15_history")
    try:
        observed = witness._parse(row.get("observedAtUtc"))
        recorded = witness._parse(row.get("firstRecordedAtUtc"))
        received = witness._parse(row.get("sourceReceivedAtUtc"))
    except ValueError as exc:
        raise ValueError("invalid_observation_clocks") from exc
    start = witness._parse(study.START)
    if (min(observed, recorded, received) < start
            or not received <= recorded <= observed <= now
            or recorded - received > MAX_RECORD_DELAY):
        raise ValueError("future_backdated_or_unwitnessed_source")
    expected_sha = row.get("originalDocumentSha256")
    if (type(expected_sha) is not str
            or re.fullmatch("[0-9a-f]{64}", expected_sha) is None
            or _digest(doc) != expected_sha):
        raise ValueError("original_document_sha_mismatch")
    bars = frames["M15"][-WINDOW_BARS:]
    closes = []
    last_open = None
    for bar in bars:
        if type(bar) is not dict:
            raise ValueError("invalid_m15_bar")
        try:
            opened = witness._parse(bar.get("t"))
        except ValueError as exc:
            raise ValueError("invalid_m15_time") from exc
        if (opened.minute % 15 or opened.second or opened.microsecond
                or (last_open is not None and opened-last_open != STEP)):
            raise ValueError("missing_or_misaligned_m15")
        o, h, l, c = [bar.get(x) for x in ("o", "h", "l", "c")]
        if (not all(_finite(x) for x in (o, h, l, c))
                or h < max(o, c) or l > min(o, c) or h < l):
            raise ValueError("invalid_m15_ohlc")
        closes.append(c)
        last_open = opened
    if witness._parse(doc.get("lastComplete")) != last_open:
        raise ValueError("last_complete_open_mismatch")
    last_closed = last_open + STEP
    if (not last_closed <= received <= recorded <= observed
            or observed-last_closed > MAX_RECEIPT_AGE):
        raise ValueError("last_closed_not_fresh_and_observed")
    return closes


def classify(row, *, as_of):
    """Classify ONE explicitly observed original source; no future candles.

    Efficiency ratio ER = abs(net 32-step close move) / gross absolute path.
    ER is a PRICE geometry measure, not estimated predictive probability.
    """
    if study.protocol_sha256() != study.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_cvd_protocol_changed")
    closes = _validated(row, witness._parse(as_of))
    distances = [abs(b-a) for a, b in zip(closes, closes[1:])]
    path = sum(distances)
    if not path or not math.isfinite(path):
        raise ValueError("zero_or_nonfinite_path_unknown")
    ratio = min(1.0, abs(closes[-1]-closes[0]) / path)
    if ratio >= DIRECTIONAL_MIN:
        state = ("DIRECTIONAL_UP" if closes[-1] > closes[0]
                 else "DIRECTIONAL_DOWN")
    elif ratio <= LATERAL_MAX:
        state = "LATERAL"
    else:
        state = "MIXED"
    return {
        "state": state,
        "efficiencyRatio": round(ratio, 6),
        "onlyClosedM15FromOriginalSource": True,
        "externalSourceAndClockAttested": False,
        "actualMarketReturnOrPnLEstimated": False,
    }


def audit(records, *, as_of):
    """Privacy-preserving denominator; duplicates are quarantined wholesale.

    Missing or invalid original evidence is UNKNOWN, NEVER lateral. The
    original 34-market universe is not implied by a sparse input list.
    """
    if type(records) is not list or len(records) > MAX_RECORDS:
        raise ValueError("invalid_regime_records")
    seen = Counter()
    for row in records:
        if type(row) is dict:
            key = (row.get("symbol"), row.get("observedAtUtc"))
            if all(type(x) is str for x in key):
                seen[key] += 1
    states = Counter()
    excluded = Counter()
    for row in records:
        if type(row) is dict:
            key = (row.get("symbol"), row.get("observedAtUtc"))
            if all(type(x) is str for x in key) and seen[key] != 1:
                excluded["ambiguous_duplicate_observation"] += 1
                continue
        try:
            label = classify(row, as_of=as_of)["state"]
            states[label] += 1
        except (ValueError, TypeError, KeyError, OverflowError):
            excluded["unknown_unverified_or_missing_original"] += 1
    known = sum(states.values())
    if known + sum(excluded.values()) != len(records):
        raise ValueError("classification_denominator_mismatch")
    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_REGIME_CANDIDATES_ONLY_NO_OUTCOMES",
        "frozenCvdProtocolSha256": study.protocol_sha256(),
        "prospectiveStartUtc": study.START,
        "observationsReceived": len(records),
        "locallyClassified": known,
        "unknownOrRejected": sum(excluded.values()),
        "exclusions": dict(sorted(excluded.items())),
        "regimes": {name: states[name] for name in STATES},
        "marketUniverseCount": len(study.FROZEN_UNIVERSE),
        "sparseRecordsDoNotProve34MarketCoverage": True,
        "sameSourceHashAndTimesOnlyLocallyChecked": True,
        "originalEvidenceExternallyAttested": False,
        "h1H4ConsistencyNotCertifiedByThisM15Audit": True,
        "regimesNotOptimizedOnOutcomes": True,
        "cotWeekClusterDependenceRemains": True,
        "independentOutOfSample": False,
        "statisticalEdgeEstablished": False,
        "profitProbabilityEstimated": False,
        "marketTradeAuthorization": False,
        "liveSignalsOrNotificationsAuthorized": False,
        "brokerCalls": 0,
        "writes": 0,
    }
