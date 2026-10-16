#!/usr/bin/env python3
"""Collect Myfxbook Community Outlook snapshots with GitHub Actions secrets.
No credentials or session IDs are ever written to the repository.
Only community aggregates, never personal account details.
"""
import datetime as dt
import json
import math
import os
import pathlib
import sys
import urllib.parse
import urllib.request

BASE = "https://www.myfxbook.com/api/"
OUTPUT = pathlib.Path("data/myfxbook")
MAX_SAMPLES_PER_SYMBOL = 1100
MAX_AGE_DAYS = 45
TIMEOUT_SECONDS = 25


def get_json(endpoint: str, params: dict) -> dict:
    url = BASE + endpoint + ".json?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "REMURA/0.6"})
    # Never print HTTP exceptions: request URLs for login can contain credentials.
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result = json.loads(response.read(3_000_000).decode("utf-8"))
    if not isinstance(result, dict) or result.get("error"):
        raise ValueError("API response unsuccessful")
    return result


def finite(value, low=None, high=None):
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        if low is not None and number < low:
            return None
        if high is not None and number > high:
            return None
        return number
    except (TypeError, ValueError):
        return None


def integer(value):
    n = finite(value, 0)
    return int(n) if n is not None else None


def read_json(path, fallback):
    try:
        with path.open("r", encoding="utf-8") as f:
            content = json.load(f)
        return content if isinstance(content, dict) else fallback
    except (OSError, ValueError):
        return fallback


def main():
    email = os.environ.get("MYFXBOOK_EMAIL", "").strip()
    password = os.environ.get("MYFXBOOK_PASSWORD", "")
    if not email or not password:
        print("Myfxbook secrets absent: no request made and no data changed.")
        return 0

    session = None
    try:
        response = get_json("login", {"email": email, "password": password})
        session = response.get("session")
        if not isinstance(session, str) or not session:
            raise ValueError("No API session received")
        response = get_json("get-community-outlook", {"session": session})
        entries = response.get("symbols")
        if not isinstance(entries, list) or not entries:
            raise ValueError("No Community Outlook symbols available")
    except Exception:
        print("Myfxbook authentication or Community Outlook request failed; no data overwritten.")
        return 1
    finally:
        if session:
            try:
                get_json("logout", {"session": session})
            except Exception:
                pass

    now = dt.datetime.now(dt.timezone.utc)
    timestamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    cutoff = now - dt.timedelta(days=MAX_AGE_DAYS)
    latest_symbols = {}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    history_file = OUTPUT / "history.json"
    old = read_json(history_file, {"version": 1, "symbols": {}})
    historical = old.get("symbols")
    if not isinstance(historical, dict):
        historical = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        symbol = str(entry.get("name", "")).upper().replace("/", "").strip()
        if not (3 <= len(symbol) <= 12 and symbol.isalnum()):
            continue
        record = {
            "t": timestamp,
            "lPct": finite(entry.get("longPercentage"), 0, 100),
            "sPct": finite(entry.get("shortPercentage"), 0, 100),
            "lLots": finite(entry.get("longVolume"), 0),
            "sLots": finite(entry.get("shortVolume"), 0),
            "lPos": integer(entry.get("longPositions")),
            "sPos": integer(entry.get("shortPositions")),
            "avgL": finite(entry.get("avgLongPrice"), 0),
            "avgS": finite(entry.get("avgShortPrice"), 0),
        }
        if record["lPct"] is None or record["sPct"] is None:
            continue
        latest_symbols[symbol] = record
        existing = historical.get(symbol, [])
        if not isinstance(existing, list):
            existing = []
        clean = []
        for item in existing:
            if not isinstance(item, dict) or not isinstance(item.get("t"), str):
                continue
            try:
                date = dt.datetime.fromisoformat(item["t"].replace("Z", "+00:00"))
                if date >= cutoff:
                    clean.append(item)
            except ValueError:
                pass
        clean.append(record)
        historical[symbol] = clean[-MAX_SAMPLES_PER_SYMBOL:]

    if not latest_symbols:
        print("No usable sentiment records returned; previous snapshots preserved.")
        return 1
    current = {"status": "ok", "source": "Myfxbook Community Outlook",
               "updatedAt": timestamp, "symbols": latest_symbols}
    archive = {"version": 1, "source": "Myfxbook Community Outlook",
               "sampling": "scheduled approximately hourly",
               "symbols": historical}
    (OUTPUT / "latest.json").write_text(json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    history_file.write_text(json.dumps(archive, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("Updated Community Outlook snapshots for", len(latest_symbols), "symbols.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
