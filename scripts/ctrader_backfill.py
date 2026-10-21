#!/usr/bin/env python3
"""REMURA: safe, manually triggered, incremental cTrader history backfill.

Discover exact enabled instruments, then load ONE small batch of missing markets.
Does not change REMURA_SYMBOLS, schedules, credentials, or trading permissions.
Run as the dedicated remura user with the private environment file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from ctrader_feed import collect, settings_from_environment, MAX_LOOKBACK_DAYS
from ctrader_tokens import access_token
from price_feed import MARKETS
from price_store import connect, symbols_available
from private_server import collect_once
from ctrader_lock import collection_guard

DEFAULT_DB = "/opt/remura/private/remura-prices.sqlite3"


def next_batch(available, existing, batch_size):
    """Only exact enabled catalog matches not already present in SQLite."""
    if not 1 <= batch_size <= 3:
        raise ValueError("Dimensione gruppo consentita: 1..3.")
    return sorted((set(available) & MARKETS) - set(existing))[:batch_size]


def private_aliases(db_path):
    """Reuse manually reviewed exact broker aliases, if configured."""
    path = Path(db_path).resolve().parent / "ctrader-symbols.json"
    if not path.is_file():
        return {}
    if path.stat().st_size > 16_384:
        raise ValueError("File alias troppo grande.")
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict) or any(
        k not in MARKETS or not isinstance(v, str) or not v.strip() or len(v) > 100
        for k, v in value.items()
    ):
        raise ValueError("File alias non valido.")
    return value


def load_plan(db_path, batch_size):
    """One read-only broker catalog request and one local SQLite inspection."""
    with collection_guard(db_path):
        token = access_token(db_path)
        if not token:
            raise RuntimeError("Autorizzazione cTrader mancante.")
        os.environ["CTRADER_ACCESS_TOKEN"] = token
        config = settings_from_environment()
        discovery = collect(
            config, sorted(MARKETS), private_aliases(db_path), 1, discover_only=True
        )
    catalog = discovery.get("catalog")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("available"), dict):
        raise RuntimeError("Catalogo cTrader non disponibile.")
    available = catalog["available"]
    db = connect(db_path)
    try:
        existing = symbols_available(db)
    finally:
        db.close()
    waiting = sorted((set(available) & MARKETS) - set(existing))
    return {
        "available": len(available),
        "existing": len(set(existing) & set(available)),
        "waiting": len(waiting),
        "next": next_batch(available, existing, batch_size),
        "unmatched": catalog.get("unmatched", []),
    }


def run_all_missing(db_path, days, batch_size, pause_seconds, max_batches=12, sleeper=time.sleep):
    """One bounded, resumable run. Stop on first error; next run skips saved data."""
    if not 60 <= pause_seconds <= 1800 or not 1 <= max_batches <= 12:
        raise ValueError("Limiti di esecuzione non validi.")
    for n in range(max_batches):
        try:
            plan = load_plan(db_path, batch_size)
        except (RuntimeError, ValueError, OSError, TypeError, json.JSONDecodeError, TimeoutError):
            print("ERRORE: scoperta cTrader non disponibile. Arresto sicuro.", flush=True)
            return 1
        print("GRUPPO", n + 1, "DA CARICARE:", ", ".join(plan["next"]) or "nessuno", flush=True)
        if not plan["next"]:
            print("COMPLETATO: nessun mercato disponibile mancante.", flush=True)
            return 0
        report = collect_once(db_path, plan["next"], days=days)
        print("SALVATI:", report.get("saved", {}), "ERRORI:", report.get("errors", {}), flush=True)
        if set(report.get("saved", {})) != set(plan["next"]) or report.get("errors"):
            print("INTERROTTO: dati incompleti. Controllare prima di riprendere.", flush=True)
            return 1
        if n + 1 < max_batches:
            print("PAUSA:", pause_seconds, "secondi.", flush=True)
            sleeper(pause_seconds)
    # Fail closed; use a new run to discover whether additional markets remain.
    print("LIMITE GRUPPI RAGGIUNTO: verifica il database prima di ripartire.", flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="REMURA cTrader: load one small batch of missing market histories.")
    parser.add_argument("--database", default=DEFAULT_DB)
    parser.add_argument("--days", type=int, default=21)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="Actually fetch and save.")
    parser.add_argument("--all-missing", action="store_true", help="Process all missing markets sequentially in batches of at most three.")
    parser.add_argument("--pause-seconds", type=int, default=180)
    args = parser.parse_args(argv)
    if not 1 <= args.days <= min(30, MAX_LOOKBACK_DAYS):
        parser.error("--days deve essere tra 1 e 30.")
    if not 1 <= args.batch_size <= 3:
        parser.error("--batch-size deve essere tra 1 e 3.")

    if args.all_missing and not args.apply:
        parser.error("--all-missing richiede --apply.")
    if not 60 <= args.pause_seconds <= 1800:
        parser.error("--pause-seconds deve essere tra 60 e 1800.")
    db_path = str(Path(args.database).expanduser().resolve())
    if args.all_missing:
        return run_all_missing(db_path, args.days, args.batch_size, args.pause_seconds)
    try:
        plan = load_plan(db_path, args.batch_size)
    except (RuntimeError, ValueError, OSError, TypeError, json.JSONDecodeError):
        print("ERRORE: impossibile preparare il catalogo privato cTrader.")
        return 1

    print("DISPONIBILI:", plan["available"])
    print("GIA SALVATI:", plan["existing"])
    print("ANCORA DA CARICARE:", plan["waiting"])
    print("PROSSIMO GRUPPO:", ", ".join(plan["next"]) or "nessuno")
    print("DA VERIFICARE:", ", ".join(plan["unmatched"]) or "nessuno")
    if not args.apply:
        print("ANTEPRIMA: nessuno storico scaricato. Usa --apply per un solo gruppo.")
        return 0
    if not plan["next"]:
        print("NESSUN NUOVO MERCATO DA CARICARE.")
        return 0

    try:
        result = collect_once(db_path, plan["next"], days=args.days)
    except (RuntimeError, ValueError, OSError, TypeError):
        print("ERRORE: raccolta non completata.")
        return 1
    print("STORICI NEL DATABASE:", result.get("saved", {}))
    print("ERRORI:", result.get("errors", {}))
    success = set(result.get("saved", {}))
    return 0 if success == set(plan["next"]) and not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
