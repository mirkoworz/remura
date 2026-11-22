# REMURA COT — global integrity v0.4 LAB / Mac handoff
**22 novembre 2026, Europe/Rome. SOLO LAB, nessuna modifica Oracle/collector.**

## New evidence
- Branch `research/cot-integrity-global-v04-lab-20261122`.
- Nuovo read-only `research/cot/cot_global_integrity_v04_lab.py`;
  verifiche globali per DB SQLite effimero v0.3 con opt-in `synthetic=True`,
  senza percorsi verso filesystem operativi, Oracle o Cloudflare.
- Nuovi 12 test `research/cot/test_cot_global_integrity_v04_lab.py`.
  [GitHub Actions 45002593074](https://github.com/mirkoworz/remura/actions/runs/45002593074)
  **12/12 PASS**, esito SUCCESS e marker log
  `REMURA_COT_GLOBAL_INTEGRITY_V04=12_12_PASS`.
- Il controllo legge **tutti** gli eventi di acquisizione, le versioni e i
  current heads del fixture. Recalcola hash di evento/versione, verifica
  record in envelope, cardinalità, timestamp, fonte dichiarata, versioni
  contigue e orari crescenti, puntatore all'ultima revisione, trigger
  append-only e foreign keys.
- Nuova capacità oltre `as_of()`: trova un current_head **mancante**, uno
  stale head e un evento di un altro mercato con contenuto non coerente.
  Fixture vuoto produce `UNKNOWN_EMPTY_FIXTURE`, NON un falso positivo di
  dati attestati. Alterazioni simulate -> `QUARANTINE_FIXTURE_INTEGRITY_FAILURE`.
- Nessuna ripetizione dei test COT v0.1 (20), v0.2 (16), v0.3 (15) o
  backup/Oracle/custodia Mac.

## Limiti obbligatori
- La diagnostica è su **DB sintetico**, non misura l'integrità reale Oracle.
- Un database modificabile dal proprietario può essere ricalcolato e riscritto
  da un soggetto privilegiato: trigger e SHA locali non sono prova esterna.
- Nessun nuovo timestamp indipendente, fonte CFTC verificata dal provider,
  crash/failover fisico o mapping futures/spot certificato.
- Protezioni v0.2/v0.3 e verifiche offline non implicano migrazione live.

## Next gate con Codex Mac, NON AUTORIZZATO
Coordinare branch/versione custodia prima di qualsiasi piano di migrazione:
schema append-only additivo e atomico, audit globale in sola lettura,
recovery persistente, backup/revert, fonte e ricezione attestabili, controllo
Free e regressioni nuove. Non modificare `scripts/cot_monitor.py` operativo,
servizio Oracle, autoupdater, package v1.65 o database prima di consenso.

**Decision: fixture 12/12 GREEN, Oracle NO-GO.**
