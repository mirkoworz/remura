#!/usr/bin/env python3
"""REMURA D0.8: compare CVD-selected price pivots with price-only pivots.

This is a DESCRIPTIVE, offline event study, not evidence of profitability.
Groups are nested: CVD-selected is a strict subset of all price candidates.
Therefore the relevant comparison is selected vs REJECTED, not two
independent strategies. No p-values, trading orders, calls or secrets.

Usage:
  python experiments/tradingview/compare_d08_baseline.py "FX_EURUSD, 5.csv"
  python experiments/tradingview/compare_d08_baseline.py "FX_EURUSD, 5.csv" \
      --prospective-from 2026-11-11T08:00:00+01:00

Only use --prospective-from with the independently logged D0.8 activation
time; do not select a cutoff after inspecting performance.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

PIP = Decimal("0.0001")
STEP = 300
HORIZONS = {"1h": 12, "4h": 48, "24h": 288}
COLS = (
    "time", "close", "QUALITA_5M_COMPLETA",
    "CONTINUITA_PRECEDENTE_5M", "SEGMENTO_ELIGIBILE_STUDIO",
    "EVENTO_STUDIO_RIALZISTA", "EVENTO_STUDIO_RIBASSISTA",
    "BASELINE_PREZZO_RIALZISTA", "BASELINE_PREZZO_RIBASSISTA",
)
ROME = ZoneInfo("Europe/Rome")


def number(x):
    try:
        val = Decimal(str(x or "").strip())
        return val if val.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def flag(x):
    val = number(x)
    return int(val) if val in (Decimal(0), Decimal(1)) else None


def summarize(events):
    out = {"events": len(events),
           "bull": sum(x["side"] == "bull" for x in events),
           "bear": sum(x["side"] == "bear" for x in events),
           "distinct_days_italy": len(set(x["italian_day"] for x in events)),
           "horizons": {}}
    for label, bars in HORIZONS.items():
        usable = [x["outcomes"][label] for x in events
                  if x["outcomes"][label] is not None]
        # Events a few minutes apart can have highly overlapping outcomes;
        # record overlap instead of calling such events independent.
        ordered_times = sorted(x["time"] for x in events)
        overlapping = sum(
            right - left < bars * STEP
            for left, right in zip(ordered_times, ordered_times[1:])
        )
        out["horizons"][label] = {
            "observable": len(usable),
            "censored": len(events) - len(usable),
            "favorable": sum(x > 0 for x in usable),
            "mean_pips": round(mean(usable), 4) if usable else None,
            "median_pips": round(median(usable), 4) if usable else None,
            "adjacent_event_windows_overlap": overlapping,
        }
    return out


def evaluate(rows, prospective_from=None):
    rows = list(rows)
    if not rows:
        raise ValueError("CSV vuoto")
    missing = [name for name in COLS if name not in rows[0]]
    if missing:
        raise ValueError("CSV D0.8: colonne mancanti: " + ", ".join(missing))
    if prospective_from is not None and prospective_from.tzinfo is None:
        raise ValueError("Il cutoff prospettico richiede un fuso orario esplicito")

    by_time = {}
    previous = None
    for r in rows:
        try:
            t = int(r["time"])
        except (ValueError, TypeError, KeyError):
            raise ValueError("Timestamp non valido nel CSV") from None
        if t in by_time or (previous is not None and t <= previous):
            raise ValueError("Timestamp duplicati o non ordinati")
        by_time[t] = r
        previous = t

    groups = {"price_all": [], "cvd_selected": [], "price_rejected_by_cvd": []}
    problems = {"quality_mask_rejected": 0,
                "dual_direction_ambiguous": 0,
                "cvd_not_subset_of_price": 0}
    cutoff = prospective_from.timestamp() if prospective_from else None

    for row in rows:
        t = int(row["time"])
        if cutoff is not None and t + STEP < cutoff:
            continue  # signal available only at confirmation bar CLOSE

        p_bull = flag(row["BASELINE_PREZZO_RIALZISTA"]) == 1
        p_bear = flag(row["BASELINE_PREZZO_RIBASSISTA"]) == 1
        c_bull = flag(row["EVENTO_STUDIO_RIALZISTA"]) == 1
        c_bear = flag(row["EVENTO_STUDIO_RIBASSISTA"]) == 1
        if (c_bull and not p_bull) or (c_bear and not p_bear):
            problems["cvd_not_subset_of_price"] += 1
            continue
        if not p_bull and not p_bear:
            continue
        if p_bull and p_bear:
            problems["dual_direction_ambiguous"] += 1
            continue

        ready = (flag(row["QUALITA_5M_COMPLETA"]) == 1
                 and flag(row["CONTINUITA_PRECEDENTE_5M"]) == 1
                 and flag(row["SEGMENTO_ELIGIBILE_STUDIO"]) == 1
                 and number(row["close"]) is not None)
        if not ready:
            problems["quality_mask_rejected"] += 1
            continue

        side = "bull" if p_bull else "bear"
        is_cvd = c_bull if p_bull else c_bear
        origin = number(row["close"])
        event = {
            "time": t,
            "italian_day": datetime.fromtimestamp(t + STEP, ROME).date().isoformat(),
            "side": side,
            "outcomes": {},
        }
        for label, n in HORIZONS.items():
            # Every forward 5m bar must exist, have a usable close, and be
            # CONFIRMED (quality flag 0/1; na = still forming). Volume
            # completeness of future bars is deliberately NOT used to
            # select outcomes: only a valid close price is required.
            future = [by_time.get(t + STEP * k) for k in range(1, n + 1)]
            observable = all(
                x is not None and number(x.get("close")) is not None
                and flag(x.get("QUALITA_5M_COMPLETA")) is not None
                for x in future
            )
            if not observable:
                event["outcomes"][label] = None
            else:
                change = (number(future[-1]["close"]) - origin) / PIP
                event["outcomes"][label] = float(change if p_bull else -change)
        groups["price_all"].append(event)
        groups["cvd_selected" if is_cvd else "price_rejected_by_cvd"].append(event)

    stats = {name: summarize(events) for name, events in groups.items()}
    incremental = {}
    for horizon in HORIZONS:
        picked = stats["cvd_selected"]["horizons"][horizon]
        rejected = stats["price_rejected_by_cvd"]["horizons"][horizon]
        incremental[horizon] = (
            round(picked["mean_pips"] - rejected["mean_pips"], 4)
            if picked["mean_pips"] is not None and rejected["mean_pips"] is not None
            else None
        )

    return {
        "model": "remura_fx_price_vs_cvd_d0.8",
        "data": "FX:EURUSD 5m TradingView user CSV",
        "mode": "PROSPECTIVE_CUTOFF_SUPPLIED" if cutoff is not None else "EXPLORATORY_HISTORICAL",
        "prospective_from": prospective_from.isoformat() if prospective_from else None,
        "total_rows": len(rows),
        "quality_problems": problems,
        "cohorts": stats,
        "mean_cvd_minus_rejected_pips": incremental,
        "limitations": [
            "CVD-selected is a subset of price candidates, not an independent system",
            "Outcomes may overlap and cluster by trading day",
            "Forward movement is before spreads, slippage, execution constraints",
            "Price-only benchmark shares the same 1m coverage gate for fair selection",
            "Historical results are descriptive and cannot establish an edge",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path, help="CSV originale TradingView D0.8 (solo locale)")
    parser.add_argument("--prospective-from", help="ISO8601 con offset, fissato all'attivazione, es. 2026-11-11T08:00:00+01:00")
    args = parser.parse_args(argv)
    start = datetime.fromisoformat(args.prospective_from) if args.prospective_from else None
    with args.csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        output = evaluate(csv.DictReader(f), prospective_from=start)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
