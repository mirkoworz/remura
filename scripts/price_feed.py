#!/usr/bin/env python3
"""REMURA private OHLC collector.

No dependency outside Python 3.11 stdlib. API credentials are read from environment,
never from JS, committed JSON, CLI arguments, or GitHub Pages.
Supported inputs: Twelve Data (15min), OANDA v20 practice/live (M15), local OHLC CSV.
Only fully closed M15 bars are retained. H1/H4 are aggregated from *contiguous*
UTC M15 bars; missing bars invalidate that hour/4-hour bucket.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UTC = dt.timezone.utc
STEP = dt.timedelta(minutes=15)
MARKETS_FX = [
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF",
    "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
    "NZDJPY", "NZDCAD", "NZDCHF", "CADJPY", "CADCHF", "CHFJPY",
]
MARKETS_OTHER = ["XAUUSD", "XAGUSD", "US500", "NAS100", "US30", "US2000", "DXY",
                 "GER30", "USOIL", "UKOIL"]
MARKETS = set(MARKETS_FX + MARKETS_OTHER)


def utcnow() -> dt.datetime:
    return dt.datetime.now(UTC)


def parse_time(value: str) -> dt.datetime:
    s = str(value).strip().replace("Z", "+00:00").replace(" ", "T")
    parsed = dt.datetime.fromisoformat(s)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)  # only accepted for explicit UTC inputs
    return parsed.astimezone(UTC).replace(microsecond=0)


def iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def float_price(value: object) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("OHLC prices must be positive finite numbers")
    return result


def candle(t: str, o: object, h: object, l: object, c: object) -> dict:
    start = parse_time(t)
    if start.second or start.minute % 15:
        raise ValueError("Unaligned M15 timestamp")
    values = tuple(float_price(x) for x in (o, h, l, c))
    if values[1] < max(values[0], values[3]) or values[2] > min(values[0], values[3]) or values[1] < values[2]:
        raise ValueError("Invalid OHLC high/low")
    return dict(t=iso(start), o=values[0], h=values[1], l=values[2], c=values[3])


def http_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "REMURA-Private-Price-Engine/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Intentionally avoid dumping provider responses, URLs, credentials or tokens.
        raise RuntimeError(f"Source rejected request (HTTP {exc.code}). Check symbol, access, rate limit or subscription.") from None
    except urllib.error.URLError:
        raise RuntimeError("Price provider unreachable") from None


def default_ticker(provider: str, symbol: str, aliases: dict) -> str:
    if symbol in aliases:
        override = aliases[symbol]
        if not isinstance(override, str) or not override.strip():
            raise ValueError("Symbol alias must be a nonempty string")
        return override.strip()
    # FX/spot metals only. Index/CFD symbols must be confirmed with the actual provider/account.
    if symbol in MARKETS_OTHER and symbol not in ("XAUUSD", "XAGUSD"):
        raise ValueError(f"{symbol}: no verified {provider} ticker. Add a symbol override in your PRIVATE mapping file.")
    if provider == "mt5":
        return symbol  # Broker-specific symbols require an explicit private alias.
    if provider == "oanda":
        return f"{symbol[:3]}_{symbol[3:]}"
    return f"{symbol[:3]}/{symbol[3:]}"


def twelve_data(symbol: str, mapped: str, count: int) -> list[dict]:
    key = os.environ.get("TWELVE_DATA_API_KEY")
    if not key:
        raise RuntimeError("Set TWELVE_DATA_API_KEY in the local environment (not in the repository).")
    args = urllib.parse.urlencode({
        "symbol": mapped, "interval": "15min", "outputsize": count,
        "format": "JSON", "timezone": "UTC", "apikey": key
    })
    payload = http_json("https://api.twelvedata.com/time_series?" + args)
    if payload.get("status") == "error" or not isinstance(payload.get("values"), list):
        raise RuntimeError(f"{symbol}: provider did not return a candle series. Check permitted instrument and API quota.")
    bars = []
    for item in payload["values"]:
        try:
            bars.append(candle(item["datetime"], item["open"], item["high"], item["low"], item["close"]))
        except (KeyError, TypeError, ValueError):
            continue
    return bars


def oanda(symbol: str, mapped: str, count: int, environment: str) -> list[dict]:
    token = os.environ.get("OANDA_API_TOKEN")
    if not token:
        raise RuntimeError("Set OANDA_API_TOKEN in the local environment (not in the repository).")
    host = "api-fxpractice.oanda.com" if environment == "practice" else "api-fxtrade.oanda.com"
    query = urllib.parse.urlencode({"granularity": "M15", "price": "M", "count": count, "smooth": "false"})
    url = "https://" + host + "/v3/instruments/" + urllib.parse.quote(mapped, safe="_") + "/candles?" + query
    payload = http_json(url, {"Authorization": "Bearer " + token})
    if not isinstance(payload.get("candles"), list):
        raise RuntimeError(f"{symbol}: OANDA returned no candles.")
    bars = []
    for item in payload["candles"]:
        if item.get("complete") is not True:
            continue
        data = item.get("mid") or {}
        try:
            bars.append(candle(item["time"], data["o"], data["h"], data["l"], data["c"]))
        except (KeyError, TypeError, ValueError):
            continue
    return bars



def mt5_prices(symbol: str, mapped: str, count: int, terminal: str | None = None) -> list[dict]:
    """Read-only OHLC from an already connected local MetaTrader 5 terminal.

    No password, login, balances, orders, or trade permissions are used.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        raise RuntimeError("MetaTrader5 is not installed; on Windows run: py -m pip install MetaTrader5") from None
    path = terminal or os.environ.get("REMURA_MT5_TERMINAL")
    try:
        ready = mt5.initialize(path, timeout=15000) if path else mt5.initialize(timeout=15000)
    except Exception:
        raise RuntimeError("MT5 terminal initialization failed.") from None
    if not ready:
        raise RuntimeError("MT5 terminal unavailable. Run MT5 on Windows with an active logged-in broker session.")
    try:
        if mt5.symbol_info(mapped) is None or not mt5.symbol_select(mapped, True):
            raise RuntimeError(f"{symbol}: ticker '{mapped}' not provided by MT5 broker; add private --symbol-map.")
        # Zero is the potentially incomplete current candle. Fetch and exclude by UTC close time.
        rates = mt5.copy_rates_from_pos(mapped, mt5.TIMEFRAME_M15, 0, count + 1)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"{symbol}: no M15 history in MT5; inspect the terminal's Max. bars in chart.")
        bars = []
        for row in rates:
            try:
                timestamp = iso(dt.datetime.fromtimestamp(int(row["time"]), UTC))
                bars.append(candle(timestamp, float(row["open"]), float(row["high"]),
                                   float(row["low"]), float(row["close"])))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        return bars
    finally:
        mt5.shutdown()


def csv_input(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"Missing CSV file: {path}")
    content = path.read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV needs headers: datetime,open,high,low,close")
    bars = []
    for row in reader:
        fields = {str(k).strip().lower(): v for k,v in row.items() if k}
        stamp = fields.get("datetime") or fields.get("timestamp") or fields.get("t")
        if not stamp and fields.get("date"):
            stamp = fields["date"] + " " + fields.get("time", "00:00:00")
        if not stamp:
            raise ValueError("CSV requires datetime/timestamp/t or date+time in UTC.")
        try:
            bars.append(candle(stamp, fields["open"], fields["high"], fields["low"], fields["close"]))
        except (KeyError, ValueError, TypeError):
            continue
    return bars


def closed_m15(bars: list[dict], now: dt.datetime) -> list[dict]:
    keyed = {}
    for bar in bars:
        start = parse_time(bar["t"])
        if start + STEP <= now:
            keyed[bar["t"]] = bar
    return [keyed[k] for k in sorted(keyed)]


def rollup(rows: list[dict], hours: int, now: dt.datetime) -> list[dict]:
    """Aggregate only complete and exactly contiguous UTC-aligned M15 buckets."""
    n = hours * 4
    buckets: dict[dt.datetime, list[dict]] = {}
    for r in rows:
        t = parse_time(r["t"])
        bucket = t.replace(hour=(t.hour // hours) * hours, minute=0, second=0, microsecond=0)
        buckets.setdefault(bucket, []).append(r)
    result = []
    for t, items in sorted(buckets.items()):
        items.sort(key=lambda x: x["t"])
        if t + dt.timedelta(hours=hours) > now or len(items) != n:
            continue
        if any(parse_time(item["t"]) != t + STEP*i for i,item in enumerate(items)):
            continue
        result.append({"t": iso(t), "o": items[0]["o"], "h": max(x["h"] for x in items),
                       "l": min(x["l"] for x in items), "c": items[-1]["c"]})
    return result


def market_document(symbol: str, provider: str, mapped: str, raw: list[dict], now: dt.datetime) -> dict:
    m15 = closed_m15(raw, now)
    if not m15:
        raise RuntimeError(f"{symbol}: no complete 15-minute observations")
    return {
        "symbol": symbol, "provider": provider, "providerSymbol": mapped,
        "sourceTimeframe": "M15", "timezone": "UTC",
        "timeframes": {
            "M15": m15[-4000:],
            "H1": rollup(m15, 1, now)[-800:],
            "H4": rollup(m15, 4, now)[-250:],
        },
        "lastComplete": m15[-1]["t"],
        "note": "Market source quotes may differ from CFTC futures, broker CFDs or TradingView. H1/H4 use UTC bucket alignment."
    }


def make_bundle(args, symbols: list[str], aliases: dict, now: dt.datetime | None = None) -> dict:
    now = now or utcnow()
    result = {"schema": "remura-price-v1", "generatedAt": iso(now), "purpose": "private-local-import",
              "intervalAlignment": "UTC", "markets": {}, "errors": {}}
    for index, symbol in enumerate(symbols):
        if index and args.provider == "twelve":
            time.sleep(args.delay)
        try:
            if symbol not in MARKETS:
                raise ValueError(f"Unknown Remura symbol: {symbol}")
            mapped = "user CSV" if args.provider == "csv" else default_ticker(args.provider, symbol, aliases)
            if args.provider == "twelve":
                bars = twelve_data(symbol, mapped, args.count)
            elif args.provider == "oanda":
                bars = oanda(symbol, mapped, args.count, args.oanda_environment)
            elif args.provider == "mt5":
                bars = mt5_prices(symbol, mapped, args.count, args.mt5_terminal)
            elif args.provider == "csv":
                if not args.csv:
                    raise ValueError("CSV mode requires --csv path.")
                bars = csv_input(Path(args.csv))
            else:
                raise ValueError("Unsupported provider")
            result["markets"][symbol] = market_document(symbol, args.provider, mapped, bars, now)
            print(f"{symbol}: {len(result['markets'][symbol]['timeframes']['M15'])} M15, "
                  f"{len(result['markets'][symbol]['timeframes']['H1'])} H1, "
                  f"{len(result['markets'][symbol]['timeframes']['H4'])} H4", file=sys.stderr)
        except (ValueError, RuntimeError) as exc:
            result["errors"][symbol] = str(exc)
            print(f"{symbol}: {exc}", file=sys.stderr)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Private OHLC export for REMURA; NEVER commit generated JSON.")
    p.add_argument("--provider", choices=["twelve", "oanda", "mt5", "csv"], required=True)
    p.add_argument("--symbols", nargs="+", default=["EURUSD", "XAUUSD", "US500"], help="Any subset of the 38 REMURA symbols")
    p.add_argument("--count", type=int, default=2400, help="Number of M15 bars: 100..5000")
    p.add_argument("--delay", type=float, default=9.0, help="Seconds between Twelve Data calls (default 9s to respect Basic 8 credits/min)")
    p.add_argument("--oanda-environment", choices=["practice", "live"], default="practice")
    p.add_argument("--symbol-map", help="Private JSON mapping of REMURA symbols to broker/provider tickers")
    p.add_argument("--csv", help="Private CSV with UTC OHLC M15 bars")
    p.add_argument("--mt5-terminal", help="Optional Windows path to terminal64.exe. Defaults to installed terminal autodetection.")
    p.add_argument("--output", default="local/price-snapshot.json", help="Local file for Safari import, never committed")
    args = p.parse_args()
    if not 100 <= args.count <= 5000:
        p.error("--count must be 100..5000")
    if not 0 <= args.delay <= 180:
        p.error("--delay must be 0..180 seconds")
    symbols = [s.upper() for s in args.symbols]
    if args.provider == "csv" and len(symbols) != 1:
        p.error("CSV import needs exactly one symbol")
    aliases = {}
    if args.symbol_map:
        aliases = json.loads(Path(args.symbol_map).read_text(encoding="utf-8"))
        if not isinstance(aliases, dict):
            p.error("--symbol-map must contain a JSON object")
    result = make_bundle(args, symbols, aliases)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    try:
        out.chmod(0o600)
    except OSError:
        pass
    print(f"Saved locally: {out} (OK: {len(result['markets'])}/{len(symbols)}). "
          "Do not commit/upload this file to a public repo.", file=sys.stderr)
    return 0 if result["markets"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
