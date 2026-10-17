#!/usr/bin/env python3
"""Optional IG Client Sentiment collector for REMURA.

Uses the authenticated, documented /clientsentiment REST endpoint.
No credentials, account data or tokens are saved. Only percent snapshots
stay in local private storage and are never published to the repository.
"""
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = {
    "demo": "https://demo-api.ig.com/gateway/deal",
    "live": "https://api.ig.com/gateway/deal",
}
OUTPUT = Path(os.environ.get("REMURA_IG_OUTPUT", str(Path(__file__).resolve().parents[1] / "private" / "ig" / "latest.json"))).expanduser().resolve()
TIMEOUT = 25
FX = ("EURUSD GBPUSD AUDUSD NZDUSD USDJPY USDCAD USDCHF EURGBP EURJPY "
      "EURCHF EURCAD EURAUD EURNZD GBPJPY GBPCHF GBPCAD GBPAUD GBPNZD "
      "AUDJPY AUDCAD AUDCHF AUDNZD NZDJPY NZDCAD NZDCHF CADJPY CADCHF CHFJPY").split()
# IG uses market group IDs (not trading EPICs). Extra instruments are
# attempted but only displayed if IG actually returns verified percentages.
MARKET_IDS = {symbol: symbol for symbol in FX}
MARKET_IDS.update({"XAUUSD": "GOLD", "XAGUSD": "SILVER",
                   "US500": "SP500", "NAS100": "NASDAQ", "US30": "DOW"})


def finite_percent(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= 100 else None


def parse_sentiments(payload, timestamp):
    """Reject partial, unknown, zero-zero and inconsistent IG percentages."""
    rows = payload.get("clientSentiments") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Invalid IG sentiment response")
    reverse = {market.upper(): symbol for symbol, market in MARKET_IDS.items()}
    parsed = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        market = str(row.get("marketId", "")).strip().upper()
        symbol = reverse.get(market)
        if not symbol:
            continue
        long_pct = finite_percent(row.get("longPositionPercentage"))
        short_pct = finite_percent(row.get("shortPositionPercentage"))
        if long_pct is None or short_pct is None or abs(long_pct + short_pct - 100) > 1:
            continue
        parsed[symbol] = {
            "t": timestamp,
            "lPct": long_pct,
            "sPct": short_pct,
            "marketId": market,
            "metric": "client_positions",
        }
    return parsed


def request_json(url, headers, body=None):
    request = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode("utf-8"),
        headers=headers, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = response.read(2_000_000)
        result = json.loads(data.decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Unexpected IG JSON response")
        return result, response.headers


def collect(api_key, identifier, password, environment):
    base = BASE[environment]
    headers = {"X-IG-API-KEY": api_key, "VERSION": "2",
               "Accept": "application/json", "Content-Type": "application/json"}
    session, session_headers = request_json(
        base + "/session", headers,
        {"identifier": identifier, "password": password, "encryptedPassword": False})
    cst = session_headers.get("CST")
    xst = session_headers.get("X-SECURITY-TOKEN")
    if not cst or not xst:
        raise ValueError("IG login returned no session tokens")
    auth = {**headers, "VERSION": "1", "CST": cst, "X-SECURITY-TOKEN": xst}
    ids = ",".join(dict.fromkeys(MARKET_IDS.values()))
    url = base + "/clientsentiment?" + urllib.parse.urlencode({"marketIds": ids})
    # There is no trading endpoint here: read-only sentiment collection.
    data, _ = request_json(url, auth)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    symbols = parse_sentiments(data, stamp)
    if not symbols:
        raise ValueError("IG returned no supported, valid market percentages")
    return {"status": "ok", "source": "IG Client Sentiment",
            "metric": "client_positions", "environment": environment,
            "updatedAt": stamp, "symbols": symbols}


def main():
    api_key = os.environ.get("IG_API_KEY", "").strip()
    identifier = os.environ.get("IG_IDENTIFIER", "").strip()
    password = os.environ.get("IG_PASSWORD", "")
    environment = os.environ.get("IG_ENV", "demo").strip().lower()
    if not all((api_key, identifier, password)):
        print("IG not configured; retaining previously collected data.")
        return 0
    if environment not in BASE:
        print("IG_ENV must be 'demo' or 'live'.")
        return 1
    if os.environ.get("IG_PUBLISH_AGGREGATES", "").lower() != "true":
        print("IG publication disabled; set IG_PUBLISH_AGGREGATES=true only if permitted.")
        return 0
    try:
        result = collect(api_key, identifier, password, environment)
    except Exception:
        # Do not log exception bodies: provider responses can include details.
        print("IG sentiment fetch failed; previous data preserved.")
        return 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False,
                                 separators=(",", ":")) + "\n", encoding="utf-8")
    print("IG sentiment: updated", len(result["symbols"]), "verified market groups.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
