#!/usr/bin/env python3
"""Track D0.7: offline descriptive event study of an exported TradingView CSV.

NO trading, forecasting, data downloads, alerts or statistical significance claim.
Event is known only at the CLOSE of its confirmed 5-minute bar. A forward
outcome is measured from that close to close after +12/+48/+288 future bars
only if every intervening 5-minute timestamp is present and the target bar
is confirmed. Does not silently bridge weekends/gaps or count live candles.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from zoneinfo import ZoneInfo

PIP = Decimal("0.0001")
BAR_SECONDS = 300
HORIZONS = { "1h": 12, "4h": 48, "24h": 288 }
REQUIRED = ("time", "close", "QUALITA_5M_COMPLETA",
            "CONTINUITA_PRECEDENTE_5M", "SEGMENTO_ELIGIBILE_STUDIO",
            "EVENTO_STUDIO_RIALZISTA", "EVENTO_STUDIO_RIBASSISTA")


def decimal_or_none(value):
    try:
        s = str(value or "").strip()
        if not s:
            return None
        d = Decimal(s)
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def flag(value):
    v = decimal_or_none(value)
    return int(v) if v in (Decimal(0), Decimal(1)) else None


def outcome_audit(rows):
    rows = list(rows)
    if not rows:
        raise ValueError("Empty CSV")
    missing = [c for c in REQUIRED if c not in rows[0]]
    if missing:
        raise ValueError("Missing D0.7 columns: " + ", ".join(missing))
    by_time = {}
    times = []
    for r in rows:
        t = int(r["time"])
        if t in by_time or (times and t < times[-1]):
            raise ValueError("Duplicate or unordered timestamp")
        by_time[t] = r
        times.append(t)

    results = []
    invalid_events = []
    timezone = ZoneInfo("Europe/Rome")
    for r in rows:
        side = 1 if flag(r["EVENTO_STUDIO_RIALZISTA"]) == 1 else (
            -1 if flag(r["EVENTO_STUDIO_RIBASSISTA"]) == 1 else 0)
        if side == 0:
            continue
        t = int(r["time"])
        base = decimal_or_none(r["close"])
        ready = (base is not None and flag(r["QUALITA_5M_COMPLETA"]) == 1
                 and flag(r["CONTINUITA_PRECEDENTE_5M"]) == 1
                 and flag(r["SEGMENTO_ELIGIBILE_STUDIO"]) == 1)
        signal_time = datetime.fromtimestamp(t + BAR_SECONDS, timezone).isoformat()
        if not ready:
            invalid_events.append({"confirmed_at_italy": signal_time,
                                   "reason": "Incomplete/invalid quality, continuity or eligibility"})
            continue
        rec = {"confirmed_at_italy": signal_time, "side": "ST+" if side > 0 else "ST-",
               "confirmation_close": str(base)}
        for name, steps in HORIZONS.items():
            target = by_time.get(t + steps * BAR_SECONDS)
            intact = all(t + step * BAR_SECONDS in by_time
                         for step in range(1, steps + 1))
            future_price = (decimal_or_none(target.get("close")) if target else None)
            target_closed = target is not None and flag(target.get("QUALITA_5M_COMPLETA")) is not None
            if not intact or future_price is None or not target_closed:
                rec[name + "_pips"] = None
                rec[name + "_reason"] = ("gap_or_not_available" if not intact
                                        else "unclosed_or_no_price")
            else:
                # Directional movement before spreads, slippage or commissions.
                pip_move = (future_price - base) / PIP * side
                rec[name + "_pips"] = float(pip_move)
                rec[name + "_reason"] = "observed"
        results.append(rec)

    stats = {}
    for name in HORIZONS:
        observations = [x[name + "_pips"] for x in results if x[name + "_pips"] is not None]
        stats[name] = {
            "observed": len(observations),
            "unobserved": len(results) - len(observations),
            "directionally_positive": sum(v > 0 for v in observations),
            "mean_pips": round(sum(observations) / len(observations), 4) if observations else None
        }
    return {
        "scope": "EXPLORATORY_ONLY_D07_FX_EURUSD_5M",
        "total_csv_bars": len(rows),
        "study_events_eligible": len(results),
        "study_bullish": sum(x["side"] == "ST+" for x in results),
        "study_bearish": sum(x["side"] == "ST-" for x in results),
        "study_events_rejected": invalid_events,
        "horizons": stats,
        "events": results,
        "warning": ("No edge demonstrated; in-sample overlapping signals, no "
                    "price-only baseline, spreads, execution or out-of-sample testing.")
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    args = parser.parse_args(argv)
    with args.input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        result = outcome_audit(reader)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
