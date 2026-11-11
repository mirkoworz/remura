#!/usr/bin/env python3
# REMURA v0.8.1 TELEMETRY — validatore OFFLINE del payload (no rete).
# Aggiornamento: 11/11/2026 16:18 CET.
# Dati FXCM classificati: NON esecuzioni istituzionali CME.
"""Valida JSON e JSONL TradingView senza attivare webhook o operazioni live.

Uso: python3 tradingview/delta-peaks/validate_telemetry_v1.py eventi.jsonl
     cat eventi.jsonl | python3 tradingview/delta-peaks/validate_telemetry_v1.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


SCHEMA = "remura.tv.flow.v1"
SOURCE = "TRADINGVIEW_INTRABAR_ESTIMATE"
VERSION = "0.8.1-lab"
LEVEL_NAMES = ("day1", "day2", "day3", "previous_day", "week",
               "current_month", "previous_month")
RETEST_NAMES = ("retest_day1", "retest_day2", "retest_day3",
                "retest_previous_day")
EVENT_FLAGS = ("peak", "er_positive", "er_negative")
MAX_BYTES = 20_000
MAX_PROSPECTIVE_LAG_MS = 120_000  # Regola preregistrata: entro 2 minuti.


class InvalidTelemetry(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise InvalidTelemetry(reason)


def fields(value: object, names: tuple[str, ...], label: str) -> dict:
    require(isinstance(value, dict), f"{label}: oggetto JSON obbligatorio")
    missing = set(names).difference(value)
    require(not missing, f"{label}: chiavi mancanti: {sorted(missing)}")
    return value


def numeric(value: object, label: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    require(type(value) in (float, int) and math.isfinite(value),
            f"{label}: numero finito" + (" oppure null" if nullable else ""))


def timestamp(value: object, label: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    require(type(value) is int and value > 1_000_000_000_000,
            f"{label}: Unix millis positivo")


def validate_payload(
    payload: object,
    *,
    received_ms: int | None = None,
    expected_symbol: str | None = "FXCM:EURUSD",
    expected_timeframe: str | None = "5",
) -> dict:
    """Valida lo snapshot e calcola identità/deliverability. Non salva nulla."""
    top = (
        "schema", "source", "indicator", "version", "event_type",
        "symbol", "feed", "timeframe", "bar_open_ms", "bar_close_ms",
        "sent_clock_ms", "confirmed", "realtime", "ohlc",
        "delta_intrabar", "effort", "signed_result_atr", "efficiency",
        "footprint", "levels", "level_scores", "level_origin_ms",
        "events", "quality",
    )
    p = fields(payload, top, "payload")
    encoded = json.dumps(p, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    require(len(encoded.encode("utf-8")) <= MAX_BYTES, "payload oltre 20 KB")
    require(p["schema"] == SCHEMA, "schema differente")
    require(p["source"] == SOURCE, "fonte differente")
    require(p["indicator"] == "REMURA_ALL_IN_ONE_PREMIUM", "indicatore differente")
    require(p["version"] == VERSION, "versione differente")
    require(p["event_type"] in ("BAR_EVENT", "HEARTBEAT"), "tipo evento sconosciuto")
    require(type(p["symbol"]) is str and 1 <= len(p["symbol"]) <= 80, "simbolo non valido")
    require(type(p["feed"]) is str and 1 <= len(p["feed"]) <= 40, "feed non valido")
    require(type(p["timeframe"]) is str and bool(p["timeframe"]), "timeframe non valido")
    if expected_symbol is not None:
        require(p["symbol"] == expected_symbol, "simbolo fuori dal pilota")
    if expected_timeframe is not None:
        require(p["timeframe"] == expected_timeframe, "timeframe fuori dal pilota")
    require(p["confirmed"] is True and p["realtime"] is True,
            "prospettico: barra non confermata o non realtime")

    for name in ("bar_open_ms", "bar_close_ms", "sent_clock_ms"):
        timestamp(p[name], name)
    require(0 < p["bar_close_ms"] - p["bar_open_ms"] <= 600_000,
            "durata candela non plausibile")

    o = fields(p["ohlc"], ("open", "high", "low", "close",
                           "prev_close", "atr14"), "ohlc")
    for name in ("open", "high", "low", "close"):
        numeric(o[name], "ohlc." + name)
    numeric(o["prev_close"], "ohlc.prev_close", nullable=True)
    numeric(o["atr14"], "ohlc.atr14", nullable=True)
    require(o["low"] <= o["open"] <= o["high"] and
            o["low"] <= o["close"] <= o["high"], "OHLC incoerente")
    require(o["atr14"] is None or o["atr14"] >= 0, "ATR negativo")
    for name in ("delta_intrabar", "effort", "signed_result_atr", "efficiency"):
        numeric(p[name], name, nullable=True)
    require(p["effort"] is None or p["effort"] >= 0, "effort negativo")

    fpkeys = ("available", "buy", "sell", "delta", "total", "delta_pct",
              "poc", "vah", "val", "imb_buy_rows", "imb_sell_rows")
    fp = fields(p["footprint"], fpkeys, "footprint")
    require(type(fp["available"]) is bool, "footprint.available bool")
    for name in fpkeys[1:]:
        numeric(fp[name], "footprint." + name, nullable=True)
    if not fp["available"]:
        require(all(fp[k] is None for k in fpkeys[1:]),
                "footprint N/D deve utilizzare null, non zero")
    else:
        require(fp["total"] is not None, "footprint presente senza totale")
        for name in ("imb_buy_rows", "imb_sell_rows"):
            require(fp[name] is None or
                    (type(fp[name]) is int and fp[name] >= 0),
                    f"{name}: conteggio intero non negativo")
    lv = fields(p["levels"], LEVEL_NAMES, "levels")
    ids = fields(p["level_origin_ms"], LEVEL_NAMES, "level_origin_ms")
    for name in LEVEL_NAMES:
        numeric(lv[name], "levels." + name, nullable=True)
        timestamp(ids[name], "level_origin_ms." + name, nullable=True)
        require((lv[name] is None) == (ids[name] is None),
                f"{name}: livello e origine non coerenti")
    scores = fields(p["level_scores"], ("day1", "day2", "day3"), "level_scores")
    for name in ("day1", "day2", "day3"):
        numeric(scores[name], "level_scores." + name, nullable=True)
        require((scores[name] is None) == (lv[name] is None),
                "score del livello non coerente")

    evkeys = EVENT_FLAGS + ("day_level_action", "day_level_rank",
                           "evicted_day_price", "evicted_day_origin_ms") + RETEST_NAMES
    ev = fields(p["events"], evkeys, "events")
    for flag in EVENT_FLAGS + RETEST_NAMES:
        require(type(ev[flag]) is bool, f"events.{flag}: bool")
    require(ev["day_level_action"] in ("NONE", "ADDED", "REPLACED"),
            "day_level_action non valido")
    require(ev["day_level_rank"] is None or
            (type(ev["day_level_rank"]) is int and 1 <= ev["day_level_rank"] <= 3),
            "day_level_rank non valido")
    numeric(ev["evicted_day_price"], "evicted_day_price", nullable=True)
    timestamp(ev["evicted_day_origin_ms"], "evicted_day_origin_ms", nullable=True)
    changed = ev["day_level_action"] != "NONE"
    require(changed == (ev["day_level_rank"] is not None),
            "action/rank incoerenti")
    require(not ev["er_positive"] or ev["peak"], "ER+ senza picco")
    require(not ev["er_negative"] or ev["peak"], "ER- senza picco")
    require(not (ev["er_positive"] and ev["er_negative"]), "ER+ e ER- simultanei")
    has_event = changed or any(ev[k] for k in EVENT_FLAGS + RETEST_NAMES)
    require((p["event_type"] == "BAR_EVENT") == has_event,
            "BAR_EVENT/HEARTBEAT non coerente con flags")

    q = fields(p["quality"], ("bar_closed", "source_type",
                              "has_intrabar_delta", "has_footprint",
                              "freshness_ms", "daily_anchor", "lower_tf"), "quality")
    require(q["bar_closed"] is True, "quality: barra aperta")
    require(q["source_type"] == "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS",
            "tipologia fonte diversa")
    require(q["has_footprint"] is fp["available"], "quality footprint incoerente")
    require(q["has_intrabar_delta"] is (p["delta_intrabar"] is not None),
            "quality delta incoerente")
    require(q["daily_anchor"] in ("HL2", "POC FOOTPRINT"), "anchor invalido")
    require(type(q["lower_tf"]) is str and bool(q["lower_tf"]), "lower_tf invalido")
    require(type(q["freshness_ms"]) is int, "freshness_ms invalido")

    key = "|".join((p["symbol"], p["timeframe"],
                    str(p["bar_close_ms"]), p["version"], p["event_type"]))
    result = {"event_key": key, "event": p["event_type"], "valid": True}
    if received_ms is not None:
        timestamp(received_ms, "received_ms")
        lag = received_ms - p["bar_close_ms"]
        # Evento in futuro: orologio nettamente incoerente.
        require(lag >= -120_000, "bar_close troppo nel futuro")
        result["lag_ms"] = lag
        result["timely_for_prospective"] = 0 <= lag <= MAX_PROSPECTIVE_LAG_MS
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="REMURA LAB: valida JSON/JSONL offline")
    parser.add_argument("file", nargs="?", help="JSONL/JSON; assente = stdin")
    a = parser.parse_args(argv)
    data = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
    try:
        text = data.strip()
        require(bool(text), "nessun dato")
        records = ([json.loads(text)] if text.startswith("{") and "\n" not in text
                   else [json.loads(line) for line in text.splitlines() if line.strip()])
        seen: set[str] = set()
        for index, record in enumerate(records, start=1):
            output = validate_payload(record)
            key = output["event_key"]
            require(key not in seen, f"riga {index}: duplicato {key}")
            seen.add(key)
        print(f"OK: {len(seen)} payload validi, 0 duplicati")
        return 0
    except (InvalidTelemetry, ValueError, json.JSONDecodeError) as exc:
        print(f"RIFIUTATO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
