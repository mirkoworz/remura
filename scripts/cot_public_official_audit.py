#!/usr/bin/env python3
"""REMURA Filone B v20.9 LAB: one-shot, public CFTC API read for research.

Exactly TWO HTTPS GETs (one TFF, one Disaggregated), no retries/fallback,
no credentials, no private DB, no writes except stdout redirected by caller.
This audit does NOT populate cot_first_seen and never claims historical as-of.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
import urllib.parse
import urllib.request

HOST = "https://publicreporting.cftc.gov"
CONFIG = {
    "tff": {
        "id": "gpe5-46if",
        "codes": ("099741", "096742", "097741", "232741", "090741", "092741", "112741",
                  "13874A", "209742", "124603", "098662"),
        "cols": ("asset_mgr_positions_long", "asset_mgr_positions_short",
                 "lev_money_positions_long", "lev_money_positions_short")
    },
    "disagg": {
        "id": "72hh-3qpy",
        "codes": ("088691", "084691", "067651"),
        "cols": ("m_money_positions_long_all", "m_money_positions_short_all",
                 "prod_merc_positions_long", "prod_merc_positions_short")
    }
}
COMMON = ("report_date_as_yyyy_mm_dd", "cftc_contract_market_code", "open_interest_all")
MAX_BYTES = 5_000_000
MAX_ROWS = 1500


def query(dataset: str, now: dt.datetime, weeks: int = 70) -> str:
    if dataset not in CONFIG or type(weeks) is not int or not 60 <= weeks <= 76:
        raise ValueError("INVALID_PUBLIC_CFTC_QUERY")
    if now.tzinfo is None or now.utcoffset() != dt.timedelta(0):
        raise ValueError("NOW_MUST_BE_UTC")
    config = CONFIG[dataset]
    cutoff = (now - dt.timedelta(weeks=weeks)).date().isoformat() + "T00:00:00"
    codes = ",".join("'" + code + "'" for code in config["codes"])
    where = "report_date_as_yyyy_mm_dd >= '" + cutoff + "' AND cftc_contract_market_code IN (" + codes + ")"
    params = {
        "$select": ",".join(COMMON + config["cols"]), "$where": where,
        "$order": "report_date_as_yyyy_mm_dd DESC", "$limit": str(MAX_ROWS)
    }
    return HOST + "/resource/" + config["id"] + ".json?" + urllib.parse.urlencode(params)


def _as_number(x):
    if type(x) not in (str, int, float) or not str(x).strip():
        raise ValueError("BAD_PUBLIC_CFTC_NUMBER")
    value = float(x)
    if not math.isfinite(value) or value < 0 or value > 1e11:
        raise ValueError("BAD_PUBLIC_CFTC_NUMBER")
    return value


def extract(dataset: str, incoming: list, now: dt.datetime):
    if type(incoming) is not list or len(incoming) >= MAX_ROWS:
        raise ValueError("PUBLIC_CFTC_EMPTY_OR_TRUNCATED")
    cfg = CONFIG[dataset]
    rows, seen = [], {}
    for item in incoming:
        if not isinstance(item, dict):
            raise ValueError("INVALID_PUBLIC_CFTC_ROW")
        code = str(item.get("cftc_contract_market_code", "")).upper()
        if code not in cfg["codes"]:
            raise ValueError("CFTC_UNEXPECTED_CONTRACT")
        day = str(item.get("report_date_as_yyyy_mm_dd", ""))[:10]
        try:
            parsed = dt.date.fromisoformat(day)
        except ValueError:
            raise ValueError("INVALID_PUBLIC_CFTC_DATE") from None
        if parsed > now.date() or parsed.isoformat() != day:
            raise ValueError("PUBLIC_CFTC_FUTURE_REPORT")
        oi = _as_number(item.get("open_interest_all"))
        vals = [_as_number(item.get(name)) for name in cfg["cols"]]
        if oi <= 0 or any(n > 2*oi for n in vals):
            raise ValueError("INVALID_PUBLIC_CFTC_POSITION")
        key = (dataset, code, day)
        signature = (oi, *vals)
        if key in seen:
            if seen[key] != signature:
                raise ValueError("CONFLICTING_PUBLIC_CFTC_DUPLICATE")
            continue
        seen[key] = signature
        rows.append({
            "dataset":dataset, "code":code, "report_date":day,
            "oi":oi, "first_long":vals[0], "first_short":vals[1],
            "second_long":vals[2], "second_short":vals[3],
            "first_seen_at":None
        })
    if not rows:
        raise ValueError("PUBLIC_CFTC_EMPTY_OR_TRUNCATED")
    return rows


def fetch_once(dataset: str, now: dt.datetime, opener=urllib.request.urlopen):
    url = query(dataset, now)
    request = urllib.request.Request(url, headers={
        "Accept":"application/json",
        "User-Agent":"REMURA-Filone-B-public-CFTC-audit/1.0"
    })
    with opener(request, timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("PUBLIC_CFTC_RESPONSE_OVER_MAX_BYTES")
    items = json.loads(raw.decode("utf-8"))
    return extract(dataset, items, now)


def build_snapshot(now: dt.datetime | None = None, fetch=fetch_once):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None or now.utcoffset() != dt.timedelta(0):
        raise ValueError("NOW_MUST_BE_UTC")
    # Exactly two official public queries; no retries, no third parties.
    tff = fetch("tff", now)
    disagg = fetch("disagg", now)
    rows = tff + disagg
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {
        "schema":"remura-cot-intelligence-snapshot-v1",
        "source":"official_public_cftc_socrata",
        "captureClock":"public_api_read_at_not_official_publication",
        "readAtUtc":now.isoformat().replace("+00:00", "Z"),
        "datasetIds":{"tff":"gpe5-46if","disagg":"72hh-3qpy"},
        "sourceLinks":{
            "tff":"https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if",
            "disagg":"https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy"
        },
        "dataSha256":hashlib.sha256(raw).hexdigest(),
        "rows":rows,"rowCount":len(rows),"truncated":False
    }


if __name__ == "__main__":
    try:
        output = build_snapshot()
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    except (OSError, TimeoutError, ValueError, TypeError, KeyError, UnicodeError,
            json.JSONDecodeError) as error:
        print("REMURA_CFTC_PUBLIC_AUDIT_UNAVAILABLE: "+type(error).__name__+": "+str(error),
              file=sys.stderr)
        sys.exit(2)
