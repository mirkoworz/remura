#!/usr/bin/env python3
"""REMURA D0.8 private CSV snapshot ledger (offline, standard library only).

Tracks original CSV SHA-256, received-at timestamp, last confirmed candle,
new vs backfilled study candidates and historical row revisions. No prices
or provider CSV are stored in the ledger. This is provenance, NOT a realtime
market feed, a verified signal service, or statistical evidence of alpha.

First import MUST use --baseline: all its events are historical regardless
of their timestamp. Subsequent imports count an event as NEW_ON_NEW_BAR
only if its confirmation close is after the previous confirmed watermark;
otherwise a first-seen event is BACKFILL_OR_RECALCULATION. Neither class is
proof of real-time detection. A timely export is only a weak audit clue.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
MODEL = "remura_fx_price_vs_cvd_d0.8"
CUTOFF = datetime.fromisoformat("2026-11-10T12:25:00+01:00").timestamp()
PINE_SHA = "4160994d14240ab2af5eff0c67d00c95671d7567"
FIELDS = (
    "time", "close", "QUALITA_5M_COMPLETA",
    "CONTINUITA_PRECEDENTE_5M", "SEGMENTO_ELIGIBILE_STUDIO",
    "BASELINE_PREZZO_RIALZISTA", "BASELINE_PREZZO_RIBASSISTA",
    "EVENTO_STUDIO_RIALZISTA", "EVENTO_STUDIO_RIBASSISTA",
)


def number(raw):
    try:
        v = Decimal(str(raw or "").strip())
        return v if v.is_finite() else None
    except (ValueError, InvalidOperation):
        return None


def flag(raw):
    v = number(raw)
    return int(v) if v in (0, 1) else None


def canonical(raw):
    v = number(raw)
    return str(v.normalize()) if v is not None else str(raw or "").strip()


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, ROME).isoformat()


def csv_digest_and_rows(path, received_epoch):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes, events = {}, {}
    last_time, watermark = None, None
    row_count = confirmed_count = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [col for col in FIELDS if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Missing D0.8 CSV fields: " + ", ".join(missing))
        for row in reader:
            row_count += 1
            try:
                t = int(row["time"])
            except (ValueError, TypeError):
                raise ValueError("Invalid CSV timestamp") from None
            if last_time is not None and t <= last_time:
                raise ValueError("CSV has duplicate or unordered timestamps")
            last_time = t
            quality = flag(row["QUALITA_5M_COMPLETA"])
            if quality is None:
                continue  # ignore the currently forming / unknown last bar
            bar_close = t + 300
            if bar_close > received_epoch:
                raise ValueError("CSV claims a confirmed candle after recorded receipt time")
            confirmed_count += 1
            watermark = bar_close
            canonical_row = "|".join(canonical(row[field]) for field in FIELDS)
            hashes[str(t)] = hashlib.sha256(canonical_row.encode()).hexdigest()
            complete_context = (
                quality == 1
                and flag(row["CONTINUITA_PRECEDENTE_5M"]) == 1
                and flag(row["SEGMENTO_ELIGIBILE_STUDIO"]) == 1
                and number(row["close"]) is not None
            )
            for side, price_field, cvd_field in (
                ("bull", "BASELINE_PREZZO_RIALZISTA", "EVENTO_STUDIO_RIALZISTA"),
                ("bear", "BASELINE_PREZZO_RIBASSISTA", "EVENTO_STUDIO_RIBASSISTA"),
            ):
                if flag(row[cvd_field]) == 1 and flag(row[price_field]) != 1:
                    raise ValueError("CVD event without price-only candidate at " + str(t))
                if flag(row[price_field]) != 1:
                    continue
                if not complete_context:
                    raise ValueError("Unqualified price event at " + str(t))
                events[str(t) + ":" + side] = {
                    "close_epoch": bar_close,
                    "has_cvd": flag(row[cvd_field]) == 1,
                }
    if confirmed_count == 0:
        raise ValueError("No confirmed candles found")
    return digest, hashes, events, watermark, row_count, confirmed_count


def ingest(csv_path, ledger_path, received_at, *, baseline=False):
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("--received-at must be timezone-aware")
    received_epoch = received_at.timestamp()
    if received_epoch < CUTOFF:
        raise ValueError("Snapshot receipt cannot precede the frozen experiment cutoff")
    repo_root = Path(__file__).resolve().parents[2]
    out = ledger_path.expanduser().resolve()
    if out == repo_root or repo_root in out.parents:
        raise ValueError("Private ledger must be OUTSIDE the GitHub repository")
    exists = out.exists()
    if baseline == exists:
        raise ValueError("Use --baseline only for first import; omit it for later imports")
    digest, hashes, events, watermark, rows, confirmed = csv_digest_and_rows(
        csv_path, received_epoch
    )
    if exists:
        ledger = json.loads(out.read_text(encoding="utf-8"))
        if ledger.get("schema") != 1 or ledger.get("model") != MODEL or ledger.get("pine_blob_sha") != PINE_SHA:
            raise ValueError("Ledger model/frozen Pine SHA mismatch")
        if received_epoch < ledger["last_received_epoch"]:
            raise ValueError("Received-at must not be earlier than prior import")
        if digest in ledger["seen_csv_hashes"]:
            return {"status": "duplicate_unchanged", "csv_sha256": digest,
                    "snapshots_recorded": len(ledger["snapshots"])}
        if watermark < ledger["latest_confirmed_close_epoch"]:
            raise ValueError("Stale snapshot cannot roll back confirmed watermark")
    else:
        ledger = {
            "schema": 1,
            "model": MODEL,
            "pine_blob_sha": PINE_SHA,
            "cutoff": iso(CUTOFF),
            "last_received_epoch": 0,
            "latest_confirmed_close_epoch": 0,
            "seen_csv_hashes": [],
            "first_seen_events": {},
            "row_hashes": {},
            "snapshots": [],
            "disclaimer": "User-attested receipt; reconstructed CSV does not prove live observation.",
        }

    previous_max = ledger["latest_confirmed_close_epoch"]
    old_hashes = ledger["row_hashes"]
    changed_rows = [t for t, h in hashes.items() if t in old_hashes and old_hashes[t] != h]
    counts = {
        "historical_at_baseline": 0,
        "new_on_new_bar": 0,
        "backfill_or_recalculation": 0,
        "new_on_new_bar_timely_15m": 0,
    }
    for key, event in events.items():
        if key in ledger["first_seen_events"]:
            # Check if a prior event changed from price-only to CVD-selected;
            # this is retrospective instability, never a fresh CVD signal.
            if event["has_cvd"] != ledger["first_seen_events"][key]["has_cvd"]:
                changed_rows.append(key.split(":")[0])
            continue
        close_t = event["close_epoch"]
        if baseline:
            classification = "historical_at_baseline"
        elif close_t <= previous_max:
            classification = "backfill_or_recalculation"
        else:
            classification = "new_on_new_bar"
        counts[classification] += 1
        timely = (
            classification == "new_on_new_bar"
            and 0 <= received_epoch - close_t <= 900
        )
        if timely:
            counts["new_on_new_bar_timely_15m"] += 1
        ledger["first_seen_events"][key] = {
            "confirmation_epoch": close_t,
            "first_received_at": received_at.isoformat(),
            "has_cvd": event["has_cvd"],
            "classification": classification,
            "timely_15m": timely,
        }

    ledger["row_hashes"].update(hashes)
    ledger["seen_csv_hashes"].append(digest)
    ledger["last_received_epoch"] = received_epoch
    ledger["latest_confirmed_close_epoch"] = max(previous_max, watermark)
    snapshot = {
        "received_at": received_at.isoformat(),
        "csv_sha256": digest,
        "confirmed_rows": confirmed,
        "rows_total": rows,
        "max_confirmed_close": iso(watermark),
        "overlapping_rows_changed": len(set(changed_rows)),
        "changed_row_open_times_sample": [iso(int(t)) for t in sorted(set(changed_rows), key=int)[:5]],
        "new_event_classes": counts,
        "new_study_events_total": sum(v for k, v in counts.items() if k in (
            "historical_at_baseline", "new_on_new_bar", "backfill_or_recalculation"
        )),
    }
    ledger["snapshots"].append(snapshot)

    out.parent.mkdir(parents=True, exist_ok=True)
    # Create atomically; failed or interrupted jobs never truncate prior ledger.
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=out.parent, prefix=".remura_d08_",
            suffix=".tmp", delete=False
        ) as f:
            temp = Path(f.name)
            json.dump(ledger, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(temp, out)
    finally:
        if temp and temp.exists():
            temp.unlink()
    return {
        "status": "recorded_baseline" if baseline else "recorded_incremental",
        "snapshot": snapshot,
        "ledger_private_path": str(out),
        "note": "No proof of real-time signals or profits; first-seen is a snapshot observation.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv_file", type=Path)
    p.add_argument("--ledger", required=True, type=Path,
                   help="Private JSON file outside GitHub repository")
    p.add_argument("--received-at", required=True,
                   help="Recorded receipt ISO8601 with timezone, e.g. 2026-11-10T13:10:00+01:00")
    p.add_argument("--baseline", action="store_true",
                   help="Mandatory first import; categorizes all existing events as historical")
    ns = p.parse_args(argv)
    try:
        dt = datetime.fromisoformat(ns.received_at)
        result = ingest(ns.csv_file, ns.ledger, dt, baseline=ns.baseline)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        p.error(str(e))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
