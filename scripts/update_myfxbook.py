#!/usr/bin/env python3
"""REMURA: read public Myfxbook Community Outlook aggregates using private Actions secrets.
Save compact individual symbol histories. No credentials, account identifiers or API sessions are published.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

from myfxbook_store import update_collection

API = "https://www.myfxbook.com/api/"
ROOT = Path("data/myfxbook")
HIST = ROOT / "history"
MAX_DAYS = 30
MAX_POINTS = 2250  # 20m cadence x 30d ~= 2160 samples per symbol
TIMEOUT = 25

FX_PAIRS = (
    "EURUSD GBPUSD AUDUSD NZDUSD USDJPY USDCAD USDCHF EURGBP EURJPY "
    "EURCHF EURCAD EURAUD EURNZD GBPJPY GBPCHF GBPCAD GBPAUD GBPNZD "
    "AUDJPY AUDCAD AUDCHF AUDNZD NZDJPY NZDCAD NZDCHF CADJPY CADCHF CHFJPY"
).split()
ASSETS = ("XAUUSD", "XAGUSD", "US500", "NAS100", "US30", "US2000", "DXY")
SUPPORTED = set(FX_PAIRS) | set(ASSETS)


def api_json(endpoint, params):
    # Myfxbook's documented REST endpoints use URL parameters: never expose this URL in logs.
    url = API + endpoint + ".json?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "REMURA/0.7"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        result = json.loads(response.read(3_000_000).decode("utf-8"))
    if not isinstance(result, dict) or result.get("error"):
        raise ValueError("Invalid/unsuccessful Myfxbook API response")
    return result


def finite(v, minimum=None, maximum=None):
    try:
        if v is None or v == "":
            return None
        x = float(v)
        if not math.isfinite(x):
            return None
        if minimum is not None and x < minimum:
            return None
        if maximum is not None and x > maximum:
            return None
        return x
    except (ValueError, TypeError):
        return None


def integer(v):
    x = finite(v, 0)
    return int(x) if x is not None else None


def json_or(path, fallback):
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else fallback
    except (OSError, ValueError):
        return fallback


def parse_iso(value):
    try:
        stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def fetch_entries(email, password):
    token = None
    try:
        login = api_json("login", {"email": email, "password": password})
        token = login.get("session")
        if not isinstance(token, str) or not token:
            raise ValueError("Session unavailable")
        response = api_json("get-community-outlook", {"session": token})
        entries = response.get("symbols")
        if not isinstance(entries, list) or not entries:
            raise ValueError("No symbols returned")
        return entries
    finally:
        if token:
            try:
                api_json("logout", {"session": token})
            except Exception:
                pass


def snapshot(now, entry):
    obj = {
        "t": now,
        "lPct": finite(entry.get("longPercentage"), 0, 100),
        "sPct": finite(entry.get("shortPercentage"), 0, 100),
        "lLots": finite(entry.get("longVolume"), 0),
        "sLots": finite(entry.get("shortVolume"), 0),
        "lPos": integer(entry.get("longPositions")),
        "sPos": integer(entry.get("shortPositions")),
        "avgL": finite(entry.get("avgLongPrice"), 0),
        "avgS": finite(entry.get("avgShortPrice"), 0),
    }
    if obj["lPct"] is None or obj["sPct"] is None:
        return None
    return obj


def main():
    email = os.environ.get("MYFXBOOK_EMAIL", "").strip()
    password = os.environ.get("MYFXBOOK_PASSWORD", "")
    if not email or not password:
        print("No Myfxbook secrets configured; no data modified.")
        return 0
    try:
        entries = fetch_entries(email, password)
    except Exception:
        print("Myfxbook request failed. Previous data preserved.")
        return 1

    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    cutoff = now - dt.timedelta(days=MAX_DAYS)
    parsed = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        symbol = str(entry.get("name", "")).upper().replace("/", "").strip()
        if not (3 <= len(symbol) <= 12 and symbol.isalnum()):
            continue
        item = snapshot(stamp, entry)
        if item is not None:
            parsed[symbol] = item
    if not parsed:
        print("No valid Myfxbook data; previous data preserved.")
        return 1

    ROOT.mkdir(parents=True, exist_ok=True)
    legacy = json_or(ROOT / "history.json", {}).get("symbols", {})
    if not isinstance(legacy, dict):
        legacy = {}
    current = {
        "status": "ok",
        "source": "Myfxbook Community Outlook",
        "updatedAt": stamp,
        "symbols": parsed,
    }
    # History and latest share one advisory lock, with atomic file replacement.
    # Invalid existing history fails closed instead of resetting observations.
    updated = update_collection(
        ROOT, parsed, SUPPORTED, cutoff=cutoff, max_points=MAX_POINTS,
        legacy=legacy, latest=current,
    )
    print("Fetched", len(parsed), "Myfxbook symbols; updated",
          updated, "supported symbol histories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
