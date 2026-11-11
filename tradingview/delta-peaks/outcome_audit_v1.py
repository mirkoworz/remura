#!/usr/bin/env python3
# REMURA TELEMETRY LAB v0.8.3 — aggiornamento 11/11/2026 18:01 CET
# Valutazione PROSPETTICA OFFLINE, zero accesso rete, zero ordini.
"""Misura esiti ER/RT M5 a 3/6/12 barre SOLO con dati ricevuti in tempo.

Formato input JSONL:
    {"received_at_ms": 1800000002000, "payload": { ... snapshot TradingView ... }}
o export D1:
    {"received_at_ms": 1800000002000, "raw_json": "{...}"}

ATTENZIONE: senza heartbeat per tutte le barre M5, gli esiti restano MISSING,
non vengono interpolati. Nessuna efficacia statistica è dimostrata da questo tool.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import statistics
import sys
from pathlib import Path

from validate_telemetry_v1 import InvalidTelemetry, validate_payload

TF_MS = 300_000
HORIZONS = (3, 6, 12)
RETESTS = {
    "retest_day1": ("RT_DAY1", "day1"),
    "retest_day2": ("RT_DAY2", "day2"),
    "retest_day3": ("RT_DAY3", "day3"),
    "retest_previous_day": ("RT_PREVIOUS_DAY", "previous_day"),
}
ER = {"er_positive": "ER_POS", "er_negative": "ER_NEG"}
MIN_ATR_MOVE = 0.1  # fissato prima di osservare i risultati


def session_id(bar_close_ms: int) -> tuple[str, int]:
    """Sessioni UTC fisse 00-08, 08-16, 16-24, preregistrate, non ricalibrate."""
    t = datetime.fromtimestamp(bar_close_ms / 1000, tz=timezone.utc)
    return (t.strftime("%Y-%m-%d"), t.hour // 8)


def cohorts_for(p: dict) -> list[tuple[str, str | None]]:
    """Il singolo bar-event rimane UNA sola osservazione aggregata."""
    e = p["events"]
    out: list[tuple[str, str | None]] = []
    for flag, label in ER.items():
        if e[flag]:
            out.append((label, None))
    for flag, (label, price_field) in RETESTS.items():
        if e[flag]:
            out.append((label, price_field))
    if e["peak"] and not e["er_positive"] and not e["er_negative"]:
        out.append(("PEAK_ONLY", None))
    if e["day_level_action"] != "NONE":
        out.append(("DAY_" + e["day_level_action"], None))
    return out


def _decode_record(record: object) -> tuple[dict, int | None]:
    if not isinstance(record, dict):
        raise InvalidTelemetry("record_non_object")
    if "payload" in record:
        if set(record) != {"payload", "received_at_ms"}:
            raise InvalidTelemetry("wrapper_fields")
        p = record["payload"]
        received = record["received_at_ms"]
    elif "raw_json" in record:
        if set(record) != {"raw_json", "received_at_ms"}:
            raise InvalidTelemetry("d1_export_fields")
        p = json.loads(record["raw_json"])
        received = record["received_at_ms"]
    else:
        # Una riga solo payload è valida per diagnostica, NON prospettica.
        p, received = record, None
    if received is not None and type(received) is not int:
        raise InvalidTelemetry("received_ms_not_int")
    return p, received


def load_records(records: list[object]) -> tuple[dict[int, dict], dict]:
    audit = Counter({
        "input_rows": len(records),
        "invalid": 0,
        "duplicates": 0,
        "conflicted_bars": 0,
        "missing_receipt": 0,
        "late_receipt": 0,
        "accepted_snapshots": 0,
    })
    bars: dict[int, dict] = {}
    event_keys: set[str] = set()
    for record in records:
        try:
            p, received = _decode_record(record)
            result = validate_payload(p, received_ms=received)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            audit["invalid"] += 1
            continue
        key = result["event_key"]
        if key in event_keys:
            audit["duplicates"] += 1
            continue
        event_keys.add(key)
        close_ms = p["bar_close_ms"]
        if close_ms in bars:
            # Collisione stesso timestamp con snapshot differente: quarantena.
            bars[close_ms]["conflicted"] = True
            audit["conflicted_bars"] += 1
            continue
        timely = bool(result.get("timely_for_prospective", False))
        if received is None:
            audit["missing_receipt"] += 1
        elif not timely:
            audit["late_receipt"] += 1
        bars[close_ms] = {"payload": p, "timely": timely, "conflicted": False}
        audit["accepted_snapshots"] += 1
    return bars, dict(audit)


def _evaluate(bars: dict[int, dict], t0: int, h: int) -> tuple[dict | None, str | None]:
    origin = bars[t0]
    if origin["conflicted"]:
        return None, "CONFLICTED_ORIGIN"
    if not origin["timely"]:
        return None, "NOT_PROSPECTIVE"
    p = origin["payload"]
    atr = p["ohlc"]["atr14"]
    if atr is None or atr <= 0:
        return None, "ATR_UNAVAILABLE"
    future = []
    for i in range(1, h + 1):
        bar = bars.get(t0 + i * TF_MS)
        if bar is None:
            return None, "MISSING_BAR"
        if bar["conflicted"] or not bar["timely"]:
            return None, "UNVERIFIED_FUTURE_BAR"
        if bar["payload"]["quality"]["daily_anchor"] != p["quality"]["daily_anchor"]:
            return None, "ANCHOR_CHANGED"
        future.append(bar["payload"])
    at_h = future[-1]
    close_t0 = p["ohlc"]["close"]
    close_h = at_h["ohlc"]["close"]
    return {
        "return_atr": (close_h - close_t0) / atr,
        "mfe_up_atr": (max(x["ohlc"]["high"] for x in future) - close_t0) / atr,
        "mae_down_atr": (min(x["ohlc"]["low"] for x in future) - close_t0) / atr,
        "close_h": close_h,
    }, None


def _retest_label(p: dict, future_close: float, field: str) -> str:
    price = p["levels"][field]
    before = p["ohlc"]["prev_close"]
    atr = p["ohlc"]["atr14"]
    if price is None or before is None or atr is None or atr <= 0:
        return "INDEFINITO"
    side_before = before - price
    after = future_close - price
    if side_before == 0:
        return "INDEFINITO"
    if side_before * after > 0 and abs(after) >= MIN_ATR_MOVE * atr:
        return "RIFIUTO"
    if side_before * after < 0 and abs(after) >= MIN_ATR_MOVE * atr:
        return "ROTTURA"
    return "INDEFINITO"


def _contrarian_label(cohort: str, ret_atr: float) -> str | None:
    if cohort == "ER_POS":
        return ("INVERSIONE" if ret_atr <= -MIN_ATR_MOVE else
                "CONTINUAZIONE" if ret_atr >= MIN_ATR_MOVE else "INDEFINITO")
    if cohort == "ER_NEG":
        return ("INVERSIONE" if ret_atr >= MIN_ATR_MOVE else
                "CONTINUAZIONE" if ret_atr <= -MIN_ATR_MOVE else "INDEFINITO")
    return None


def _level_alive_at_h(p: dict, end: dict, field: str | None) -> bool | None:
    if field is None:
        return None
    origin = p["level_origin_ms"].get(field)
    if origin is None:
        return None
    if field == "previous_day":
        return origin == end["level_origin_ms"]["previous_day"]
    return origin in (end["level_origin_ms"][f] for f in ("day1", "day2", "day3"))


def _summary(rows: list[dict], attempted: Counter, missing: Counter,
             baselines: dict, h: int) -> dict:
    by_cohort: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)
    result = {}
    for cohort, count in sorted(attempted.items()):
        if cohort[1] != h:
            continue
        name = cohort[0]
        group = by_cohort[name]
        returns = [r["return_atr"] for r in group]
        labels = Counter(r["label"] for r in group if r["label"] is not None)
        base_vals: list[float] = []
        matched_counts = 0
        for r in group:
            matches = baselines.get((h, r["utc_session"]), [])
            if matches:
                matched_counts += 1
                base_vals.extend(matches)
        result[name] = {
            "events_attempted": count,
            "outcomes_complete": len(group),
            "outcomes_missing": count - len(group),
            "missing_reasons": {
                k[2]: v for k, v in sorted(missing.items())
                if k[0] == name and k[1] == h
            },
            "median_signed_return_atr": (round(statistics.median(returns), 6)
                                          if returns else None),
            "labels": dict(sorted(labels.items())),
            "matched_baseline_event_count": matched_counts,
            "matched_baseline_mean_return_atr": (
                round(statistics.mean(base_vals), 6) if base_vals else None
            ),
            "benchmark_status": "COMPARABILE" if matched_counts == len(group) and
                                len(group) > 0 else "INSUFFICIENTE",
        }
    return result


def evaluate(records: list[object]) -> dict:
    bars, audit = load_records(records)
    times = sorted(bars)
    attempts = Counter()
    missing: Counter = Counter()
    detail: list[dict] = []
    # Benchmark: solo HEARTBEAT privo di eventi, stessa data e fascia UTC.
    baselines: dict[tuple[int, tuple[str, int]], list[float]] = defaultdict(list)
    for t0 in times:
        bar = bars[t0]
        p = bar["payload"]
        if p["event_type"] != "HEARTBEAT" or bar["conflicted"]:
            continue
        for h in HORIZONS:
            out, err = _evaluate(bars, t0, h)
            if err is None:
                baselines[(h, session_id(t0))].append(out["return_atr"])

    for t0 in times:
        bar = bars[t0]
        p = bar["payload"]
        cohorts = cohorts_for(p)
        if not cohorts:
            continue
        for h in HORIZONS:
            out, err = _evaluate(bars, t0, h)
            for cohort, field in [("ANY_EVENT", None), *cohorts]:
                attempts[(cohort, h)] += 1
                if err is not None:
                    missing[(cohort, h, err)] += 1
                    continue
                label = (_retest_label(p, out["close_h"], field)
                         if field is not None else
                         _contrarian_label(cohort, out["return_atr"]))
                detail.append({
                    "bar_close_ms": t0,
                    "horizon_bars": h,
                    "horizon_minutes": h * 5,
                    "cohort": cohort,
                    "utc_session": session_id(t0),
                    "return_atr": round(out["return_atr"], 8),
                    "mfe_up_atr": round(out["mfe_up_atr"], 8),
                    "mae_down_atr": round(out["mae_down_atr"], 8),
                    "label": label,
                    "level_origin_ms": (
                        p["level_origin_ms"].get(field) if field else None
                    ),
                    "level_survives_at_h": (
                        _level_alive_at_h(p, bars[t0 + h * TF_MS]["payload"], field)
                        if field else None
                    ),
                })
    by_h = {str(h): _summary([r for r in detail if r["horizon_bars"] == h],
                              attempts, missing, baselines, h) for h in HORIZONS}
    return {
        "schema": "remura.tv.outcomes.lab.v1",
        "version": "0.8.3-lab",
        "mode": "OFFLINE_DESCRIPTIVE_NO_TRADING",
        "source": "TRADINGVIEW_FXCM_ESTIMATED_NOT_CME",
        "audit": audit,
        "heartbeat_bars": sum(1 for v in bars.values()
                              if v["payload"]["event_type"] == "HEARTBEAT"),
        "sessions_utc": "00-08,08-16,16-24",
        "horizons_bars": list(HORIZONS),
        "event_outcomes": by_h,
        "records": detail,
        "not_proof_of_edge": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="REMURA ER/RT: esiti prospettici offline")
    ap.add_argument("jsonl", help="Export JSONL con received_at_ms e payload/raw_json")
    ap.add_argument("--output", help="Salva risultati JSON (non invia alla rete)")
    args = ap.parse_args()
    rows = []
    for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    result = evaluate(rows)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    # Non interpretare file vuoto o errori come esito positivo.
    if result["audit"]["invalid"] > 0:
        print("ATTENZIONE: record invalidi nel dataset", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
