#!/usr/bin/env python3
"""REMURA Track D0.7 CSV quality auditor, offline, standard library only.

Read an exported TradingView CSV. Output aggregated audit statistics to stdout.
Do NOT publish raw provider data; this script does not submit any HTTP requests
or create orders/alerts. Not a profitability/forward-testing estimator.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys

REQUIRED = {
    "quality": "QUALITA_5M_COMPLETA",
    "continuity": "CONTINUITA_PRECEDENTE_5M",
    "raw_delta": "DELTA_5M_GREZZO_COMPLETO",
    "reliable_delta": "DELTA_5M_CONTINUO_VERIFICATO",
    "bull": "EVENTO_STUDIO_RIALZISTA",
    "bear": "EVENTO_STUDIO_RIBASSISTA",
}
NATIVE = {"open": "CVD (Apertura)", "close": "CVD (Chiudi)"}


def col_lookup(headers, name):
    """Exact first; otherwise disambiguated exported indicator title suffix."""
    if name in headers:
        return name
    matches = [h for h in headers if h.startswith(name + ".") or h.startswith(name + " ")]
    if len(matches) == 1:
        return matches[0]
    return None


def number(value):
    value = str(value or "").strip()
    if not value or value.lower() in ("na", "nan", "null"):
        return None
    try:
        val = Decimal(value)
        return val if val.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def binary(value):
    val = number(value)
    return int(val) if val in (Decimal(0), Decimal(1)) else None


def audit_rows(rows, headers):
    cols = {key: col_lookup(headers, name) for key, name in REQUIRED.items()}
    missing = [name for key, name in REQUIRED.items() if cols[key] is None]
    if missing:
        raise ValueError("D0.7 export missing required columns: " + ", ".join(missing))
    natives = {key: col_lookup(headers, name) for key, name in NATIVE.items()}
    have_native = all(natives.values())

    out = {
        "scope": "RESEARCH_ONLY / FX:EURUSD M5 / D0.7",
        "data_source": "user_exported_tradingview_csv",
        "records": 0,
        "complete_5m": 0,
        "incomplete_5m": 0,
        "unknown_quality": 0,
        "complete_with_verified_continuity": 0,
        "complete_but_context_unverified": 0,
        "reliable_delta_count": 0,
        "context_flag_inconsistencies": 0,
        "study_bullish_events": 0,
        "study_bearish_events": 0,
        "events_on_unverified_context": 0,
        "has_native_cvd_ohlc": have_native,
        "numeric_comparisons_contiguous": 0,
        "exact_delta_matches_contiguous": 0,
        "sign_disagreements_contiguous": 0,
        "note": "Indicator replication and event counts only; NO statistical edge or trade instruction.",
    }
    total_error = Decimal(0)
    for row in rows:
        out["records"] += 1
        qual = binary(row.get(cols["quality"], ""))
        cont = binary(row.get(cols["continuity"], ""))
        raw = number(row.get(cols["raw_delta"], ""))
        reliable = number(row.get(cols["reliable_delta"], ""))
        if qual == 1:
            out["complete_5m"] += 1
            if cont == 1:
                out["complete_with_verified_continuity"] += 1
            elif cont == 0:
                out["complete_but_context_unverified"] += 1
            else:
                out["context_flag_inconsistencies"] += 1
        elif qual == 0:
            out["incomplete_5m"] += 1
        else:
            out["unknown_quality"] += 1

        if reliable is not None:
            out["reliable_delta_count"] += 1
            if qual != 1 or cont != 1 or raw != reliable:
                out["context_flag_inconsistencies"] += 1
        if cont == 1 and qual != 1:
            out["context_flag_inconsistencies"] += 1

        bull = binary(row.get(cols["bull"], "")) == 1
        bear = binary(row.get(cols["bear"], "")) == 1
        out["study_bullish_events"] += int(bull)
        out["study_bearish_events"] += int(bear)
        if (bull or bear) and (qual != 1 or cont != 1):
            out["events_on_unverified_context"] += 1

        if have_native and qual == 1 and cont == 1 and reliable is not None:
            a = number(row.get(natives["open"], ""))
            b = number(row.get(natives["close"], ""))
            if a is not None and b is not None:
                native_delta = b - a
                out["numeric_comparisons_contiguous"] += 1
                out["exact_delta_matches_contiguous"] += int(native_delta == reliable)
                out["sign_disagreements_contiguous"] += int((native_delta > 0) != (reliable > 0) and native_delta != 0 and reliable != 0)
                total_error += abs(native_delta - reliable)
    n = out["numeric_comparisons_contiguous"]
    out["mae_contiguous"] = str(total_error / n) if n else None
    out["exact_match_pct_contiguous"] = (
        round(100 * out["exact_delta_matches_contiguous"] / n, 4) if n else None
    )
    out["quality_coverage_pct"] = (
        round(100 * out["complete_5m"] / out["records"], 4)
        if out["records"] else None
    )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_file", type=Path, help="Local TradingView export. Never upload raw data to GitHub.")
    ns = ap.parse_args(argv)
    with ns.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            ap.error("CSV has no header")
        try:
            result = audit_rows(reader, reader.fieldnames)
        except ValueError as error:
            ap.error(str(error))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
