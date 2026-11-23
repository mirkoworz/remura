#!/usr/bin/env python3
"""REMURA V20.2: one-shot official ECB DAILY FX reference price witness.

Free public institutional reference data, NOT tradable execution quotes, ticks,
M5/M15/H1/H4, or a CVD/alpha result. No credentials, external dependencies,
D1, Cloudflare, Firestore, broker access, or automatic long-running scheduling.
The capture timestamp is measured AFTER reading ECB XML; never fabricate
historical first-seen or treat the reference DATE as the publication time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

UTC = timezone.utc
ROME = ZoneInfo("Europe/Rome")
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CURRENCIES = ("EUR", "USD", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD")
PAIRS = (
    "EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
    "GBPUSD", "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
    "AUDUSD", "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
    "NZDUSD", "NZDJPY", "NZDCAD", "NZDCHF",
    "USDJPY", "USDCAD", "USDCHF",
    "CADJPY", "CADCHF", "CHFJPY"
)
MAX_BYTES = 120_000
MAX_AGE_DAYS = 7


def iso(t: datetime) -> str:
    if t.tzinfo is None:
        raise ValueError("Timezone required")
    return t.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def tag(e: ET.Element) -> str:
    return e.tag.rsplit("}", 1)[-1]


def parse_rates(xml: bytes) -> tuple[date, dict[str, Decimal]]:
    if not isinstance(xml, bytes) or not 0 < len(xml) <= MAX_BYTES:
        raise ValueError("Invalid or oversized official XML payload")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError("ECB XML parse failure") from exc
    if tag(root) != "Envelope":
        raise ValueError("Unexpected ECB envelope")
    dates = [x for x in root.iter() if tag(x) == "Cube" and "time" in x.attrib]
    if len(dates) != 1:
        raise ValueError("Expected exactly one daily reference date")
    stamp = dates[0].attrib["time"]
    try:
        d = date.fromisoformat(stamp)
    except ValueError as exc:
        raise ValueError("Invalid ECB reference date") from exc
    if d.isoformat() != stamp:
        raise ValueError("Noncanonical reference date")
    rates = {"EUR": Decimal("1")}
    for x in dates[0]:
        if tag(x) != "Cube" or set(x.attrib) != {"currency", "rate"}:
            raise ValueError("Unexpected ECB daily row")
        c = x.attrib["currency"]
        if c not in CURRENCIES or c == "EUR":
            continue
        if c in rates:
            raise ValueError("Duplicate ECB quote")
        try:
            n = Decimal(x.attrib["rate"])
        except InvalidOperation as exc:
            raise ValueError("Invalid ECB quote") from exc
        if not n.is_finite() or n <= 0:
            raise ValueError("Nonpositive or nonfinite ECB quote")
        rates[c] = n
    if set(rates) != set(CURRENCIES):
        raise ValueError("Required major ECB reference currencies missing")
    return d, rates


def witness(xml: bytes, observed_at: datetime) -> dict:
    if observed_at.tzinfo is None:
        raise ValueError("Observed-at timestamp must be timezone aware")
    now = observed_at.astimezone(UTC)
    refdate, rates = parse_rates(xml)
    if refdate > now.date():
        raise ValueError("Future-dated reference rate")
    age_days = (now.date() - refdate).days
    if age_days > MAX_AGE_DAYS:
        raise ValueError("Stale ECB reference beyond seven calendar days")
    pairs = {}
    for pair in PAIRS:
        base, quote = pair[:3], pair[3:]
        # Rates are units of each quoted currency per 1 EUR.
        cross = rates[quote] / rates[base]
        pairs[pair] = str(cross.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP))
    if len(pairs) != 28:
        raise ValueError("Incomplete 28-pair universe")
    return {
        "schema": "remura-ecb-daily-reference-witness-v202",
        "source": "European Central Bank official daily EUR reference rates",
        "source_url": ECB_URL,
        "raw_xml_sha256": hashlib.sha256(xml).hexdigest(),
        "reference_date": refdate.isoformat(),
        "observed_at_utc": iso(now),
        "observed_at_rome": observed_at.astimezone(ROME).isoformat(timespec="seconds"),
        "eligible_for_future_decisions_only_after_utc": iso(now),
        "days_behind_observation_date": age_days,
        "reference_date_is_not_publication_timestamp": True,
        "first_seen_independently_attested": False,
        "intraday_candles_or_tradeable_price": False,
        "independent_daily_fx_context_only": True,
        "forward_60m_h4_24h_alpha_calculated": False,
        "new_23_nov_reference_observed": refdate >= date(2026, 11, 23),
        "currencies": list(CURRENCIES),
        "derived_pairs": pairs,
    }


def get_once() -> bytes:
    request = urllib.request.Request(
        ECB_URL,
        headers={"Accept": "application/xml,text/xml", "User-Agent": "REMURA-research-ECB-daily-reference/1.0"}
    )
    # No automatic retry, no external accounts, no user-specific inputs.
    with urllib.request.urlopen(request, timeout=16) as response:
        if not response.geturl().startswith("https://www.ecb.europa.eu/"):
            raise ValueError("Unexpected non-ECB redirect")
        raw = response.read(MAX_BYTES + 1)
    return raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--live-official", action="store_true",
                        help="One GET to the official public ECB XML, without API key")
    source.add_argument("--offline-xml", type=Path,
                        help="Parse existing local XML with NO HTTP (tests/replay)")
    args = ap.parse_args()
    raw = get_once() if args.live_official else args.offline_xml.read_bytes()
    result = witness(raw, datetime.now(UTC))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
