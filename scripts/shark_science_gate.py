"""REMURA Track B: conservative as-of research gate for evidence provenance.

Pure offline utility. It never fetches market data, writes databases, predicts
returns, generates orders, or enables notifications. All times are UTC.
The CVD branch is a CLV x cTrader tick-volume PROXY, never aggressor delta.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

SCHEMA = "remura-shark-asof-gate-v1"
CVD_VERSION = "cvd-divergence-proxy-m15-v1"
UTC = timezone.utc
MAX_AGE = {"cot": timedelta(days=14), "retail": timedelta(hours=3),
           "M15": timedelta(minutes=90), "H1": timedelta(minutes=120),
           "H4": timedelta(hours=8), "cvd": timedelta(minutes=90)}


def _utc(value):
    """Reject naive/local/ambiguous times rather than assuming an offset."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("utc_z_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("non_utc")
    return parsed


def _side(value):
    if type(value) is not int or value not in (-1, 0, 1):
        raise ValueError("invalid_side")
    return value


def _missing(reason):
    return {"status": "excluded", "side": 0, "reason": reason}


def _cot(data, asof):
    if not isinstance(data, dict):
        return _missing("cot_missing")
    try:
        if (data.get("dataset") not in ("tff", "disagg")
                or data.get("publicationVerified") is not True
                or data.get("marketMappingVerified") is not True
                or data.get("mappingType") not in ("direct_futures", "derived_fx_cross")):
            return _missing("cot_lineage_unverified")
        side = _side(data.get("side"))
        report = date.fromisoformat(data["reportDate"])
        released = _utc(data["publishedAt"])
        available = _utc(data["availableAt"])
        if not (report <= released.date() and released <= available <= asof):
            return _missing("cot_not_known_asof")
        if asof - released > MAX_AGE["cot"]:
            return _missing("cot_stale")
        return {"status": "valid", "side": side, "reason": "official_weekly_futures_context"}
    except (ValueError, TypeError, KeyError, OverflowError):
        return _missing("cot_invalid")


def _retail(data, asof):
    if not isinstance(data, dict):
        return _missing("retail_missing")
    try:
        if data.get("provider") not in ("myfxbook", "capital"):
            return _missing("retail_source_unverified")
        side = _side(data.get("side"))
        sampled = _utc(data["sampledAt"])
        available = _utc(data["availableAt"])
        if not sampled <= available <= asof:
            return _missing("retail_not_known_asof")
        if asof - sampled > MAX_AGE["retail"]:
            return _missing("retail_stale")
        return {"status": "valid", "side": side, "reason": "retail_sample_not_institutional"}
    except (ValueError, TypeError, KeyError, OverflowError):
        return _missing("retail_invalid")


def _price(data, asof):
    if not isinstance(data, dict):
        return _missing("price_missing")
    try:
        if data.get("provider") != "ctrader":
            return _missing("price_provider_unverified")
        if data.get("qualityVerified") is not True:
            return _missing("price_quality_unverified")
        states = data.get("frameStatus")
        if not isinstance(states, dict) or any(states.get(tf) != "ready"
                                               for tf in ("M15", "H1", "H4")):
            return _missing("price_h1_or_other_frame_not_ready")
        side = _side(data.get("side"))
        available = _utc(data["availableAt"])
        if available > asof:
            return _missing("price_not_known_asof")
        for tf in ("M15", "H1", "H4"):
            closed = _utc(data["closedAt"][tf])
            if closed > available or asof - closed > MAX_AGE[tf]:
                return _missing("price_" + tf.lower() + "_stale_or_future")
        return {"status": "valid", "side": side, "reason": "closed_ctrader_bars_verified"}
    except (ValueError, TypeError, KeyError, OverflowError):
        return _missing("price_invalid")


def _cvd(data, asof):
    if not isinstance(data, dict):
        return _missing("cvd_missing")
    try:
        if (data.get("algorithm") != CVD_VERSION
                or data.get("state") != "confirmed_technical_not_trade_signal"
                or data.get("dataQualityVerified") is not True):
            return _missing("cvd_proxy_unverified")
        value = data.get("side")
        if value not in ("bullish", "bearish"):
            return _missing("cvd_side_invalid")
        confirmed = _utc(data["confirmedAt"])
        collected = _utc(data["collectedAt"])
        detected = _utc(data["detectedAt"])
        if not confirmed <= collected <= detected <= asof:
            return _missing("cvd_unavailable_at_decision")
        if asof - confirmed > MAX_AGE["cvd"]:
            return _missing("cvd_stale")
        return {"status": "valid", "side": 1 if value == "bullish" else -1,
                "reason": "clv_tick_volume_proxy_not_aggressor_delta"}
    except (ValueError, TypeError, KeyError, OverflowError):
        return _missing("cvd_invalid")


def evaluate(snapshot, *, as_of):
    """As-of check for distinct evidence channels. No tuned score or trade edge."""
    at = _utc(as_of)
    if not isinstance(snapshot, dict):
        raise ValueError("invalid_snapshot")
    channels = {"cot": _cot(snapshot.get("cot"), at),
                "retail": _retail(snapshot.get("retail"), at),
                "price": _price(snapshot.get("price"), at),
                "cvdProxy": _cvd(snapshot.get("cvdProxy"), at)}
    valid = {k: v for k, v in channels.items() if v["status"] == "valid"}
    cot, price = channels["cot"], channels["price"]
    aligned = (cot["status"] == price["status"] == "valid" and
               cot["side"] in (-1, 1) and cot["side"] == price["side"])
    conflict = (cot["status"] == price["status"] == "valid" and
                cot["side"] * price["side"] == -1)
    if aligned:
        verdict = "CONFERMA PARZIALE"
    elif valid:
        verdict = "DA OSSERVARE"
    else:
        verdict = "NESSUN SEGNALE VALIDATO"
    # Retail and CVD never become a proof of an institutional transaction.
    # CVD shares OHLC-derived CLV with the price arm: no independence assumed.
    return {
        "schema": SCHEMA, "asOf": as_of,
        "verdict": verdict, "qualityGate": "PASS" if price["status"] == "valid" else "BLOCK",
        "contextPriceAligned": aligned, "contextPriceConflict": conflict,
        "channels": channels,
        "excluded": [k for k, v in channels.items() if v["status"] != "valid"],
        "researchOnly": True, "institutionalAttribution": "NOT_PROVEN",
        "empiricalEdge": "NOT_ESTABLISHED", "probability": None,
        "orderEnabled": False, "notificationEnabled": False,
        "limitations": [
            "COT: weekly delayed release, not intraday orderflow.",
            "Retail: distinct retail sample, not institutional flow.",
            "CVD: CLV x cTrader tick volume proxy, mechanically price-linked.",
            "This gate checks information availability, not predictive value or PnL."
        ],
    }
