#!/usr/bin/env python3
"""REMURA Filone B V21.6 LAB — exact TWO-date official CFTC source fetch.

The default CLI makes ZERO HTTP requests, no files, no secrets, no trades.
An explicit operator opt-in is mandatory to perform exactly TWO public CFTC
HTTPS GET requests (one official TFF, one official Disaggregated). No retries.
Output is public CFTC-only JSON compatible with the existing strict offline
public/private parity pipeline. Not an authenticated historic first-seen clock.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
import urllib.request

from cot_public_official_audit import (
    CONFIG, COMMON, HOST, MAX_BYTES, extract,
)
from cot_intelligence_parity import EXPECTED

VERSION = "B_V21_6_LAB"
SCHEMA = "remura-cot-intelligence-snapshot-v1"
DATES = ("2026-11-10", "2026-11-17")
MAX_EXPECTED = 28
MAX_PER_DATASET = {"tff": 22, "disagg": 6}
CONFIRM = "ALLOW_2_PUBLIC_CFTC_GETS_NO_PRIVATE_DATA"


def official_query(dataset: str) -> str:
    if dataset not in CONFIG:
        raise ValueError("UNKNOWN_OFFICIAL_CFTC_DATASET")
    source = CONFIG[dataset]
    # Exact two report dates, not 70 weeks of unnecessary traffic or files.
    dates = ",".join("'" + day + "T00:00:00'" for day in DATES)
    codes = ",".join("'" + code + "'" for code in source["codes"])
    params = {
        "$select": ",".join(COMMON + source["cols"]),
        "$where": ("report_date_as_yyyy_mm_dd IN (" + dates + ")"
                    " AND cftc_contract_market_code IN (" + codes + ")"),
        "$order": "report_date_as_yyyy_mm_dd DESC,cftc_contract_market_code ASC",
        "$limit": str(MAX_PER_DATASET[dataset] + 1),
    }
    return HOST + "/resource/" + source["id"] + ".json?" + urllib.parse.urlencode(params)


class _DenyRedirects(urllib.request.HTTPRedirectHandler):
    """3xx must not trigger a hidden extra GET beyond the authorized budget."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("OFFICIAL_CFTC_REDIRECT_REJECTED_NO_EXTRA_GET")


def read_once(dataset: str, *, opener=None) -> list[dict]:
    url = official_query(dataset)
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "REMURA-2-date-CFTC-public-only-lab-v21.6/1.0",
    })
    # This request is counted once. Disable HTTP redirects and environment
    # proxy configuration; a 3xx never permits another GET or another host.
    if opener is None:
        opener = urllib.request.build_opener(
            _DenyRedirects, urllib.request.ProxyHandler({})
        ).open
    with opener(req, timeout=20) as response:
        if getattr(response, "status", 200) != 200:
            raise ValueError("OFFICIAL_CFTC_NOT_HTTP_200")
        if hasattr(response, "geturl") and response.geturl() != url:
            raise ValueError("OFFICIAL_CFTC_RESPONSE_URL_CHANGED")
        raw = response.read(MAX_BYTES + 1)
    if not 1 <= len(raw) <= MAX_BYTES:
        raise ValueError("OFFICIAL_CFTC_RESPONSE_EMPTY_OR_TOO_LARGE")
    result = json.loads(raw.decode("utf-8"))
    if type(result) is not list:
        raise ValueError("OFFICIAL_CFTC_NOT_A_LIST")
    return result


def assemble(*, now: dt.datetime, fetch=read_once) -> dict:
    if now.tzinfo is None or now.utcoffset() != dt.timedelta(0):
        raise ValueError("UTC_NOW_REQUIRED")
    if now.date() < dt.date.fromisoformat(DATES[-1]):
        raise ValueError("BEFORE_LAST_OFFICIAL_REPORT_DATE")
    # Exactly TWO public GETs if fetch==read_once.
    tff_raw = fetch("tff")
    disagg_raw = fetch("disagg")
    rows = extract("tff", tff_raw, now) + extract("disagg", disagg_raw, now)
    expect = {(ds, code, day) for ds, codes in EXPECTED.items()
              for code in codes for day in DATES}
    actual = [(r["dataset"], r["code"], r["report_date"]) for r in rows]
    if len(actual) != MAX_EXPECTED or len(set(actual)) != MAX_EXPECTED or set(actual) != expect:
        raise ValueError("OFFICIAL_TWO_DATE_14_CONTRACTS_EACH_NOT_COMPLETE")
    rows.sort(key=lambda r: (r["dataset"], r["code"], r["report_date"]))
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("utf-8")
    return {
        "schema": SCHEMA,
        "source": "official_public_cftc_socrata",
        "captureClock": "public_api_read_at_not_official_publication",
        "readAtUtc": now.isoformat().replace("+00:00", "Z"),
        "datasetIds": {k: CONFIG[k]["id"] for k in ("tff", "disagg")},
        "reportDates": list(DATES),
        "sourceReference": {
            "tff": "https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if",
            "disagg": "https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy"
        },
        "dataSha256": hashlib.sha256(raw).hexdigest(),
        "rows": rows,
        "rowCount": len(rows),
        "truncated": False,
        "historicFirstSeenAttested": False,
        "officialReleaseTimestampAttested": False,
        "publicDataMayHaveBeenRevisedAfterPrivateCapture": True,
        "publicApiRequests": 2,
        "privateProviderOrBrokerCalls": 0,
        "ordersOrSignalsEnabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--confirmation", help="Explicit public CFTC opt-in phrase")
    a = p.parse_args(argv)
    if a.confirmation is None:
        print(json.dumps({
            "schema": "remura-b-v216-public-two-date-acquisition-plan",
            "version": VERSION, "status": "PUBLIC_CFTC_FETCH_NOT_AUTHORIZED",
            "reportDates": list(DATES), "expectedRows": MAX_EXPECTED,
            "maxPublicGetRequestsIfAuthorized": 2,
            "actualPublicGetRequests": 0, "privateCalls": 0,
            "filesWritten": 0,
        }, sort_keys=True))
        return 0
    if a.confirmation != CONFIRM:
        p.error("Explicit exact confirmation required; no request sent")
    try:
        result = assemble(now=dt.datetime.now(dt.timezone.utc))
    except (ValueError, TypeError, KeyError, UnicodeError, OSError, TimeoutError,
            json.JSONDecodeError):
        # Fail closed without exposing response bodies or provider secrets.
        print("REMURA_B_OFFICIAL_CFTC_TWO_DATE_FETCH_FAILED", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
