#!/usr/bin/env python3
"""REMURA cTrader Open API: read-only historical M15 collection.

Uses Spotware's official ctrader-open-api SDK (Twisted/Protobuf). NO trading messages.
Requires a Spotware-approved application, OAuth token with scope=accounts, broker
account ID, and an outbound TCP connection. Secrets ONLY via environment variables.
The module is importable/testable without network or the cTrader SDK.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import sys

from price_feed import MARKETS, UTC, candle, market_document, iso, utcnow

INTERVAL_MS = 15 * 60 * 1000
MAX_LOOKBACK_DAYS = 45
TRENDBARS_RESPONSE_LIMIT = 350  # Fail closed for oversized single-day replies.


EVENT_PHASES = frozenset({
    "ProtoOAApplicationAuthRes",
    "ProtoOAGetAccountListByAccessTokenRes",
    "ProtoOAAccountAuthRes",
    "ProtoOASymbolsListRes",
    "ProtoOASymbolByIdRes",
    "ProtoOAGetTrendbarsRes",
    "ProtoOAErrorRes",
    "decode",
})
EVENT_ERROR_TYPES = frozenset({
    "AttributeError", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "OverflowError", "DecodeError", "EncodeError",
})


def safe_event_diagnostic(phase, exc):
    """Bounded diagnostic: never expose exception text, tokens or broker response."""
    kind = type(exc).__name__
    if kind not in EVENT_ERROR_TYPES:
        kind = "Exception"
    stage = phase if phase in EVENT_PHASES else "other"
    tb = exc.__traceback__
    line = 0
    # Use the innermost Python line number, never traceback text or file paths.
    while tb is not None:
        line = tb.tb_lineno
        tb = tb.tb_next
    return f"Risposta cTrader inattesa; fase={stage}; tipo={kind}; riga={line}."


def incomplete_trendbars_response(payload, limit=TRENDBARS_RESPONSE_LIMIT):
    """Detect truncated M15 responses across old and current Spotware SDKs.

    Older generated protobufs may not expose the newer optional hasMore field.
    The request deliberately omits count and uses a UTC-day interval (at most
    96 M15 bar opens), so 350 returned bars is abnormally large and unsafe.
    """
    bars = payload.trendbar
    return bool(getattr(payload, "hasMore", False)) or len(bars) >= limit


def configure_trendbars_request(request, account_id, symbol_id, period, start_ms, end_ms):
    """Build bounded historical request WITHOUT optional count.

    Spotware documents count as a limit backwards from toTimestamp; setting
    count=350 for a one-day M15 request returned older out-of-range candles.
    Rely on the required account/symbol and a validated <=24h UTC window.
    """
    if not 0 <= start_ms < end_ms or end_ms - start_ms > 86_400_000:
        raise ValueError("Intervallo storico cTrader non valido.")
    request.ctidTraderAccountId = account_id
    request.symbolId = symbol_id
    request.period = period
    request.fromTimestamp = start_ms
    request.toTimestamp = end_ms
    return request


def trendbar_inside_window(raw_bar, start_ms, end_ms, now):
    """Accept only M15 candles opened inside this requested UTC chunk and closed.

    cTrader may return the last `count` bars prior to toTimestamp even when
    fromTimestamp is provided. We never let those older bars contaminate a
    narrower requested window or include still-forming candles.
    """
    opened_ms = int(raw_bar.utcTimestampInMinutes) * 60_000
    now_ms = int(now.astimezone(UTC).timestamp() * 1000)
    return (start_ms <= opened_ms < end_ms and
            opened_ms + INTERVAL_MS <= now_ms)


def exact_symbols(light_symbols, requested, aliases=None):
    """Find ONE exact enabled broker name per REMURA code; never guess CFD aliases."""
    aliases = aliases or {}
    found, errors = {}, {}
    enabled = {}
    for row in light_symbols:
        if not getattr(row, "enabled", False):
            continue
        name = str(getattr(row, "symbolName", "")).strip()
        if not name:
            continue
        enabled.setdefault(name.upper(), []).append(row)
    for market in requested:
        broker_name = str(aliases.get(market, market))
        if not broker_name.strip():
            errors[market] = "Il ticker broker è vuoto."
            continue
        # Explicit mapping used verbatim. Standard FX names can match EUR/USD;
        # CFDs and indices require exact matching or manually verified alias.
        candidates = [broker_name.upper()]
        if market in MARKETS and len(market) == 6 and broker_name.upper() == market:
            candidates.append(market[:3] + "/" + market[3:])
        matches = []
        for name in candidates:
            matches = enabled.get(name, [])
            if matches:
                break
        if len(matches) != 1:
            errors[market] = "Ticker non disponibile o ambiguo: " + broker_name + ". Verifica il nome in cTrader."
            continue
        found[market] = matches[0]
    return found, errors


def convert_trendbar(bar, digits):
    """Convert documented relative OHLC and UTC-minute timestamp to REMURA OHLC."""
    digits = int(digits)
    if digits < 0 or digits > 10:
        raise ValueError("Precisione del simbolo non valida.")
    low = int(bar.low)
    high = low + int(bar.deltaHigh)
    op = low + int(bar.deltaOpen)
    close = low + int(bar.deltaClose)
    if not (low > 0 and low <= op <= high and low <= close <= high):
        raise ValueError("OHLC relativo cTrader non valido.")
    t = dt.datetime.fromtimestamp(int(bar.utcTimestampInMinutes) * 60, UTC)
    return candle(iso(t), round(op / 100000, digits),
                  round(high / 100000, digits),
                  round(low / 100000, digits),
                  round(close / 100000, digits))


def utc_chunks(now, lookback_days, chunk_hours=24):
    """Daily UTC request windows: no interval spans more than 24h."""
    if not 1 <= lookback_days <= MAX_LOOKBACK_DAYS:
        raise ValueError("lookback_days deve essere 1..45.")
    if chunk_hours != 24:
        raise ValueError("Usare finestre UTC di 24 ore per evitare limiti di backend.")
    end = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)
    start = end - dt.timedelta(days=lookback_days)
    chunks = []
    while start < end:
        following = min(end, start + dt.timedelta(hours=chunk_hours))
        chunks.append((int(start.timestamp() * 1000), int(following.timestamp() * 1000)))
        start = following
    return chunks


def settings_from_environment():
    names = ("CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN", "CTRADER_ACCOUNT_ID")
    missing = [k for k in names if not os.environ.get(k)]
    if missing:
        raise RuntimeError("Parametri cTrader assenti: " + ", ".join(missing) +
                           ". Non inviarli nella chat né inserirli nel repository.")
    env = os.environ.get("CTRADER_ENV", "demo").lower()
    if env not in ("demo", "live"):
        raise RuntimeError("CTRADER_ENV deve essere demo oppure live.")
    try:
        account_id = int(os.environ["CTRADER_ACCOUNT_ID"])
    except ValueError:
        raise RuntimeError("CTRADER_ACCOUNT_ID non valido.") from None
    if account_id <= 0:
        raise RuntimeError("CTRADER_ACCOUNT_ID non valido.")
    return {
        "client_id": os.environ["CTRADER_CLIENT_ID"],
        "secret": os.environ["CTRADER_CLIENT_SECRET"],
        "token": os.environ["CTRADER_ACCESS_TOKEN"],
        "account_id": account_id,
        "environment": env,
    }


def collect(config, requested, aliases, lookback_days, now=None):
    """Run one bounded session using the Spotware SDK; return a private JSON bundle.

    Every request is read-only and sequential. No balances/positions are requested.
    The Twisted reactor runs once per process; schedule one process per collection.
    """
    try:
        from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
        from ctrader_open_api.messages.OpenApiMessages_pb2 import (
            ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
            ProtoOAGetAccountListByAccessTokenReq, ProtoOAGetAccountListByAccessTokenRes,
            ProtoOAAccountAuthReq, ProtoOAAccountAuthRes,
            ProtoOASymbolsListReq, ProtoOASymbolsListRes,
            ProtoOASymbolByIdReq, ProtoOASymbolByIdRes,
            ProtoOAGetTrendbarsReq, ProtoOAGetTrendbarsRes,
            ProtoOAErrorRes,
        )
        from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod
        from twisted.internet import reactor
    except ImportError:
        raise RuntimeError("SDK mancante. Installa localmente: pip install ctrader-open-api") from None

    now = now or utcnow()
    host = EndPoints.PROTOBUF_DEMO_HOST if config["environment"] == "demo" else EndPoints.PROTOBUF_LIVE_HOST
    client = Client(host, EndPoints.PROTOBUF_PORT, TcpProtocol)
    chunks = utc_chunks(now, lookback_days)
    result = {"schema": "remura-price-v1", "generatedAt": iso(now),
              "purpose": "private-local-import", "intervalAlignment": "UTC",
              "markets": {}, "errors": {}}
    state = {"phase": "connect", "tasks": [], "index": 0, "bars": {},
             "names": {}, "digits": {}, "closed": False}

    def finish():
        if state["closed"]:
            return
        state["closed"] = True
        if reactor.running:
            reactor.stop()

    def problem(message):
        # Do not print raw failures/response bodies; they may contain secrets.
        result["errors"]["connection"] = message
        finish()

    def send(req):
        try:
            deferred = client.send(req)
            deferred.addErrback(lambda failure: problem("cTrader ha rifiutato una richiesta o la connessione."))
        except Exception:
            problem("Errore durante una richiesta cTrader.")

    def later():
        # ~3 requests/sec, below historical 5 req/sec official per connection.
        if state["index"] >= len(state["tasks"]):
            for market in requested:
                if market in result["errors"] or market not in state["names"]:
                    continue
                matched = state["names"][market]
                try:
                    raw = list(state["bars"].get(market, {}).values())
                    if not raw:
                        raise ValueError("Nessuna candela storica restituita da cTrader.")
                    result["markets"][market] = market_document(
                        market, "ctrader", str(matched.symbolName), raw, now
                    )
                except (ValueError, RuntimeError) as exc:
                    result["errors"][market] = str(exc)
            finish()
            return
        market, sid, digits, start_ms, end_ms = state["tasks"][state["index"]]
        state["pending"] = (market, sid, start_ms, end_ms)
        request = configure_trendbars_request(
            ProtoOAGetTrendbarsReq(), config["account_id"], sid,
            ProtoOATrendbarPeriod.Value("M15"), start_ms, end_ms
        )
        send(request)

    def event(client, message):
        if state["closed"]:
            return
        phase = "decode"
        try:
            payload = Protobuf.extract(message)
            phase = type(payload).__name__
            if isinstance(payload, ProtoOAErrorRes):
                problem("cTrader ha segnalato un errore API. Controlla autorizzazione, conto, simboli e limiti.")
            elif isinstance(payload, ProtoOAApplicationAuthRes):
                q = ProtoOAGetAccountListByAccessTokenReq()
                q.accessToken = config["token"]
                send(q)
            elif isinstance(payload, ProtoOAGetAccountListByAccessTokenRes):
                matches = [acc for acc in payload.ctidTraderAccount
                           if acc.ctidTraderAccountId == config["account_id"]]
                if len(matches) != 1 or bool(matches[0].isLive) != (config["environment"] == "live"):
                    problem("L'account indicato non è autorizzato dal token o non corrisponde all'ambiente.")
                    return
                q = ProtoOAAccountAuthReq()
                q.ctidTraderAccountId = config["account_id"]
                q.accessToken = config["token"]
                send(q)
            elif isinstance(payload, ProtoOAAccountAuthRes):
                q = ProtoOASymbolsListReq()
                q.ctidTraderAccountId = config["account_id"]
                q.includeArchivedSymbols = False
                send(q)
            elif isinstance(payload, ProtoOASymbolsListRes):
                selected, errors = exact_symbols(payload.symbol, requested, aliases)
                result["errors"].update(errors)
                state["names"] = selected
                if not selected:
                    finish()
                    return
                q = ProtoOASymbolByIdReq()
                q.ctidTraderAccountId = config["account_id"]
                q.symbolId.extend(sorted(set(row.symbolId for row in selected.values())))
                send(q)
            elif isinstance(payload, ProtoOASymbolByIdRes):
                details = {row.symbolId: row for row in payload.symbol}
                for market, light in state["names"].items():
                    full = details.get(light.symbolId)
                    if full is None:
                        result["errors"][market] = "cTrader non ha restituito dettagli e precisione del simbolo."
                        continue
                    state["digits"][market] = full.digits
                    state["bars"][market] = {}
                    for start_ms, end_ms in chunks:
                        state["tasks"].append((market, light.symbolId, full.digits, start_ms, end_ms))
                later()
            elif isinstance(payload, ProtoOAGetTrendbarsRes):
                if "pending" not in state:
                    return
                market, sid, start_ms, end_ms = state["pending"]
                if payload.ctidTraderAccountId != config["account_id"] or (
                    payload.HasField("symbolId") and payload.symbolId != sid
                ):
                    problem("Risposta cTrader non corrispondente alla richiesta.")
                    return
                if incomplete_trendbars_response(payload):
                    result["errors"][market] = "Dati incompleti: cTrader segnala altre candele per la finestra."
                elif market not in result["errors"]:
                    for raw_bar in payload.trendbar:
                        try:
                            if not trendbar_inside_window(raw_bar, start_ms, end_ms, now):
                                continue
                            bar = convert_trendbar(raw_bar, state["digits"][market])
                            state["bars"][market][bar["t"]] = bar
                        except (ValueError, OverflowError, TypeError):
                            result["errors"][market] = "Una candela cTrader è invalida."
                            break
                state["index"] += 1
                reactor.callLater(0.35, later)
        except Exception as exc:
            problem(safe_event_diagnostic(phase, exc))

    def connected(_):
        q = ProtoOAApplicationAuthReq()
        q.clientId = config["client_id"]
        q.clientSecret = config["secret"]
        send(q)

    def disconnected(_, reason):
        if not state["closed"]:
            problem("Connessione cTrader interrotta.")

    client.setConnectedCallback(connected)
    client.setDisconnectedCallback(disconnected)
    client.setMessageReceivedCallback(event)
    reactor.callLater(300, lambda: problem("Timeout della raccolta: dati incompleti."))
    client.startService()
    reactor.run()
    return result


def main():
    parser = argparse.ArgumentParser(description="cTrader read-only -> private REMURA price bundle")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD","XAUUSD","US500"])
    parser.add_argument("--days", type=int, default=14, help="Past UTC days (1..45).")
    parser.add_argument("--symbol-map", help="Private JSON file with exact broker symbol aliases.")
    parser.add_argument("--output", default="local/price-snapshot.json")
    args = parser.parse_args()
    if not 1 <= args.days <= MAX_LOOKBACK_DAYS:
        parser.error("--days must be 1..45")
    markets = list(dict.fromkeys(s.upper() for s in args.symbols))
    if not markets or any(s not in MARKETS for s in markets):
        parser.error("Only the 35 defined REMURA symbols are allowed.")
    aliases = json.loads(Path(args.symbol_map).read_text("utf-8")) if args.symbol_map else {}
    if not isinstance(aliases, dict) or any(k not in MARKETS for k in aliases):
        parser.error("Invalid private symbol mapping.")
    config = settings_from_environment()
    result = collect(config, markets, aliases, args.days)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    try:
        out.chmod(0o600)
    except OSError:
        pass
    print("REMURA cTrader: " + str(len(result["markets"])) + " / " + str(len(markets)) +
          " strumenti disponibili. File salvato LOCALMENTE in " + str(out) +
          ". Non pubblicare su GitHub.")
    for market, message in result["errors"].items():
        print(market + ": " + message, file=sys.stderr)
    return 0 if result["markets"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
