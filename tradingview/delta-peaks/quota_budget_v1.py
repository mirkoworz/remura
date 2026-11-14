#!/usr/bin/env python3
# REMURA Free Quota Guard LAB v0.8.4 — aggiornamento 11/11/2026 18:03 CET
# Simulazione OFFLINE: non legge gli account, non crea servizi, nessun deploy.
"""Stima limiti gratuiti per il futuro gateway TradingView -> Cloudflare D1.

Limiti verificati documentazione ufficiale Cloudflare 11/11/2026:
Workers Free 100k requests/day; D1 Free 100k rows-written/day, 500MB
per database. 5M rows-read/day e CPU 10ms/request NON sono prevedibili
da una stima statica: restano obbligatori dashboard e test reale.
"""
from __future__ import annotations

import argparse
import json
import math

WORKERS_FREE_DAILY_REQUESTS = 100_000
D1_FREE_DAILY_WRITES = 100_000
D1_FREE_BYTES_PER_DB = 500_000_000
# 10% della quota di account come guardrail preliminare; non sono limiti Cloudflare.
MAX_FRACTION_DAILY = 0.10
# 65% del DB per lasciare spazio a indici, altri dati, variazioni di payload.
MAX_FRACTION_DB = 0.65
M5_BARS_PER_24H = 288


def budget(
    *,
    symbols: int = 1,
    heartbeat_enabled: bool = True,
    active_hours: float = 24.0,
    retention_days: int = 30,
    max_payload_bytes: int = 20_000,
    retries_multiplier: float = 1.10,
    db_overhead_multiplier: float = 1.40,
) -> dict:
    """Budget prudente per un singolo database D1, NON telemetria reale."""
    if type(symbols) is not int or symbols < 1 or symbols > 100:
        raise ValueError("symbols deve essere intero da 1 a 100")
    if type(retention_days) is not int or not 1 <= retention_days <= 365:
        raise ValueError("retention_days deve essere intero da 1 a 365")
    if not math.isfinite(active_hours) or not 0 < active_hours <= 24:
        raise ValueError("active_hours deve essere tra 0 e 24")
    if type(max_payload_bytes) is not int or not 1 <= max_payload_bytes <= 20_000:
        raise ValueError("max_payload_bytes deve essere 1–20.000")
    if not math.isfinite(retries_multiplier) or not 1 <= retries_multiplier <= 4:
        raise ValueError("retries_multiplier deve essere 1–4")
    if not math.isfinite(db_overhead_multiplier) or not 1 <= db_overhead_multiplier <= 3:
        raise ValueError("db_overhead_multiplier deve essere 1–3")
    bars_daily = math.ceil(active_hours * 60 / 5) * symbols
    # Con heartbeat attivo 1 sola chiamata per barra, anche con eventi multipli.
    # Senza heartbeat NON possiamo stimare gli eventi, né misurare i benchmark;
    # quindi il preflight non può essere considerato approvato.
    upper_daily_requests = math.ceil(bars_daily * retries_multiplier)
    upper_daily_writes = bars_daily  # INSERT OR IGNORE non duplica le righe.
    estimated_bytes = math.ceil(
        bars_daily * retention_days * max_payload_bytes * db_overhead_multiplier
    )
    caps = {
        "worker_daily_requests": int(WORKERS_FREE_DAILY_REQUESTS * MAX_FRACTION_DAILY),
        "d1_daily_writes": int(D1_FREE_DAILY_WRITES * MAX_FRACTION_DAILY),
        "d1_database_storage_bytes": int(D1_FREE_BYTES_PER_DB * MAX_FRACTION_DB),
    }
    fits_model = (
        heartbeat_enabled
        and upper_daily_requests <= caps["worker_daily_requests"]
        and upper_daily_writes <= caps["d1_daily_writes"]
        and estimated_bytes <= caps["d1_database_storage_bytes"]
    )
    return {
        "schema": "remura.tv.quota.model.v1",
        "version": "0.8.4-lab",
        "symbol_count": symbols,
        "timeframe_minutes": 5,
        "heartbeat_enabled": heartbeat_enabled,
        "retention_days": retention_days,
        "assumptions": {
            "active_hours": active_hours,
            "payload_bytes_max_per_event": max_payload_bytes,
            "retry_multiplier": retries_multiplier,
            "db_overhead_multiplier": db_overhead_multiplier,
            "realtime_signal_rate": "unknown; heartbeat model upper bound only",
        },
        "estimated_max": {
            "daily_bars": bars_daily,
            "daily_worker_requests_including_retry_allowance": upper_daily_requests,
            "daily_d1_writes_excluding_duplicates": upper_daily_writes,
            "storage_bytes_one_database": estimated_bytes,
        },
        "internal_guardrails": caps,
        "fits_internal_guardrails": fits_model,
        "cloudflare_account_usage_checked": False,
        "d1_rows_read_checked": False,
        "worker_cpu_checked": False,
        "cost_verified_zero": False,
        "meaning": "MODELLO PRUDENTE, NON PROVA DEL PIANO FREE O DEL CONSUMO REALE",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="REMURA: budget Cloudflare Free offline")
    ap.add_argument("--symbols", type=int, default=1)
    ap.add_argument("--active-hours", type=float, default=24)
    ap.add_argument("--retention-days", type=int, default=30)
    ap.add_argument("--payload-max", type=int, default=20_000)
    ap.add_argument("--no-heartbeat", action="store_true")
    args = ap.parse_args()
    print(json.dumps(budget(
        symbols=args.symbols, active_hours=args.active_hours,
        retention_days=args.retention_days, max_payload_bytes=args.payload_max,
        heartbeat_enabled=not args.no_heartbeat
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
