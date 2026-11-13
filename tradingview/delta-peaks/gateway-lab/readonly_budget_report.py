# REMURA INFRA BUDGET REPORT v0.1 — aggiornamento 13/11/2026, ore 10:08 CET
# Aggregatore locale delle sole metriche pubblicabili, nessuna API né credenziale.
"""Summarize three read-only Cloudflare audits for the GitHub Actions step summary.

Empty/missing data is UNKNOWN, never zero. Estimates do NOT prove exact billing.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys

KEY_PATTERN = re.compile(r"^[A-Z0-9_]+$")
VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.,:%;=-]+$")
STATUS_KEYS = {
    "d1": ("REMURA_CF_ACCOUNT_QUOTA", {"OK", "WARNING", "CRITICAL", "UNKNOWN_NO_GRAPHQL_DATA"}),
    "workers": ("REMURA_CF_WORKERS_USAGE", {"OK", "WARNING", "CRITICAL", "UNKNOWN_NO_DATA"}),
    "storage": ("REMURA_D1_TEST_STORAGE", {"OK", "WARNING", "CRITICAL"}),
}
ALLOWED_FIELDS = {
    "D1_ACCOUNT_ROWS_READ_ESTIMATE", "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE",
    "D1_FREE_READ_LIMIT", "D1_FREE_WRITE_LIMIT",
    "WORKERS_ACCOUNT_REQUESTS_ESTIMATE", "WORKERS_ACCOUNT_ERRORS_ESTIMATE",
    "WORKERS_ACCOUNT_SCRIPT_COUNT", "WORKERS_MAX_REPORTED_CPU_P99_US",
    "WORKERS_FREE_DAILY_REQUEST_LIMIT",
    "REMURA_D1_TEST_STORAGE_BYTES", "REMURA_D1_TEST_STORAGE_LIMIT_BYTES",
    "REMURA_D1_TEST_STORAGE_PERCENT",
}


def filtered_fields(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, val = line.strip().split("=", 1)
        if key not in ALLOWED_FIELDS and key not in {v[0] for v in STATUS_KEYS.values()}:
            continue
        if not KEY_PATTERN.fullmatch(key) or not VALUE_PATTERN.fullmatch(val):
            raise ValueError("report_bad_known_field")
        if key in values:
            raise ValueError("report_duplicate_known_field")
        values[key] = val
    return values


def category_status(fields: dict[str, str], category: str) -> str:
    key, accepted = STATUS_KEYS[category]
    status = fields.get(key)
    return status if status in accepted else "UNKNOWN"


def display_number(fields: dict[str, str], key: str) -> str:
    value = fields.get(key)
    if value is None:
        return "non disponibile"
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        return "non disponibile"
    return value


def build_report(d1_text: str, workers_text: str, storage_text: str,
                 day_utc: str) -> str:
    reports = {
        "d1": filtered_fields(d1_text),
        "workers": filtered_fields(workers_text),
        "storage": filtered_fields(storage_text),
    }
    d1 = reports["d1"]
    workers = reports["workers"]
    storage = reports["storage"]

    # Suppress counters for any status not backed by successful, complete metrics.
    if category_status(d1, "d1") not in ("OK", "WARNING", "CRITICAL"):
        d1 = {}
    if category_status(workers, "workers") not in ("OK", "WARNING", "CRITICAL"):
        workers = {}
    if category_status(storage, "storage") not in ("OK", "WARNING", "CRITICAL"):
        storage = {}

    def row(label: str, status: str, value: str, limit: str) -> str:
        return f"| {label} | {status} | {value} | {limit} |"

    lines = [
        "## REMURA · controllo infrastruttura read-only",
        "",
        f"**Giorno UTC:** {day_utc} · **PR #102 DRAFT** · nessun deploy, write o webhook",
        "",
        "| Metrica | Stato | Valore | Limite Free di riferimento |",
        "|---|---|---:|---:|",
        row("D1 account: righe lette (stima)", category_status(reports["d1"], "d1"),
            display_number(d1, "D1_ACCOUNT_ROWS_READ_ESTIMATE"), "5.000.000/giorno"),
        row("D1 account: righe scritte (stima)", category_status(reports["d1"], "d1"),
            display_number(d1, "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE"), "100.000/giorno"),
        row("Workers account: richieste (stima)", category_status(reports["workers"], "workers"),
            display_number(workers, "WORKERS_ACCOUNT_REQUESTS_ESTIMATE"), "100.000/giorno"),
        row("Workers account: errori (stima)", category_status(reports["workers"], "workers"),
            display_number(workers, "WORKERS_ACCOUNT_ERRORS_ESTIMATE"), "n/a"),
        row("D1 TEST: dimensione file", category_status(reports["storage"], "storage"),
            display_number(storage, "REMURA_D1_TEST_STORAGE_BYTES") + " byte",
            "500.000.000 byte"),
        "",
        "**Nota:** metriche GraphQL adattive/stimate e potenzialmente ritardate; "
        "il test D1 misura solo il database TEST. "
        "Non sono contatori di fatturazione esatti e non includono una "
        "verifica dei costi effettivi, del piano attivo o dell'uso CPU aggregato.",
        "",
        "**Gateway pubblico:** l'ultima sonda da GitHub ha restituito 403/403; "
        "stato di ingestione non verificabile da quella sonda. "
        "La CI verde non autorizza l'attivazione dei webhook.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("REMURA_BUDGET_REPORT=ERROR:bad_arguments")
        return 2
    paths = [Path(p) for p in argv[1:]]
    try:
        d1, workers, storage = [path.read_text(encoding="utf-8") for path in paths]
        from datetime import datetime, timezone
        text = build_report(d1, workers, storage, datetime.now(timezone.utc).date().isoformat())
        output_path = os.getenv("GITHUB_STEP_SUMMARY")
        if not output_path:
            raise ValueError("github_summary_missing")
        with open(output_path, "a", encoding="utf-8") as writer:
            writer.write(text)
    except (OSError, ValueError):
        print("REMURA_BUDGET_REPORT=ERROR:safe_summary_failed")
        return 1
    print("REMURA_BUDGET_REPORT=GENERATED_NO_SECRETS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
