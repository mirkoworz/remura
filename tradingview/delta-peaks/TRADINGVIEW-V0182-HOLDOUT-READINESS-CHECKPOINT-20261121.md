# REMURA TradingView v0.8.182 LAB — HOLDOUT CALENDAR FREEZE

**Checkpoint: 21 novembre 2026 · dopo run GitHub delle ore 18:02 CET (Europe/Rome)**

- Repo pubblico: `mirkoworz/remura`, branch isolato `research/tradingview-holdout-readiness-v0182-20261121`.
- Base immutata: `research/tradingview-delta-peaks-20261111` SHA `bf24eab0e9f833b6a8b7b3b6d04d28a2927829c5` (TradingView v0.8.181 LAB).
- Commit testato: `28adfcf4232c0249985809382416ac0e53af36b5`.
- Nuova run ONE-SHOT https://github.com/mirkoworz/remura/actions/runs/44927820591 — **18/18 nuovi test PASS**; log verificati: `Ran 18 tests`, `OK`, `REMURA_TV_V0182_HOLDOUT=18_18_PASS`.
- Nessun test storico rieseguito, nessun dato di mercato acquisito, nessun deploy, nessuna modifica Oracle/Cloudflare, nessun merge `main`, nessuna spesa nuova introdotta.

## Nuovo lavoro
- `holdout_freeze_v0182_lab.py`: preflight a sola lettura della data di `CVD-PROSPECTIVE-PROTOCOL-V2.md`, confronta il **Git blob SHA-1 esatto** `4b0f5d5defacfdbf8e902af5a8eea32947cabeca`. Non è firma del deploy né firma temporale esterna.
- `test_holdout_freeze_v0182_lab.py`: 18 verifiche NUOVE su immutabilità byte, presenza del preregistro, finestre UTC esclusive, confini esatti, timezone, file mancante/symlink/alterato e output senza risultati PnL.
- Workflow dedicato `.github/workflows/remura-tv-holdout-v0182-one-shot-ci.yml`, runner standard pubblico read-only e zero Secret. Non legge dati di trading né modifica protocolli.

## Calendario congelato (inizio incluso, fine esclusa, UTC)
| Intervallo | Da | A |
|---|---|---|
| Sviluppo | 2026-11-16 00:00 | 2026-11-23 00:00 |
| Holdout 1 | 2026-11-23 00:00 | 2026-11-30 00:00 |
| Holdout 2 | 2026-11-30 00:00 | 2026-12-07 00:00 |

Rispetta V2 preregistrato: primario CVD vs price-only a 60 minuti, secondari previsti nel documento; costi ipotetici e pairing FIFO non vengono modificati. Non selezionare soglie, finestre o vincitori a posteriori. Il weekend iniziale resta diagnostico; non imputare barre mancanti. Un reader batch 48h non basta per due fold completi. Nessun matching tra fold, nessuna sostituzione di coppie assegnate, nessuna analisi anticipata di holdout.

## Rischi ancora aperti
- `outcomes_measured=false`, `institutional_edge_established=false`, `captures_active=false`, `release_deploy_allowed=false`.
- Servono dati con timestamp di disponibilità e controllo indipendente dei conflitti prima di qualsiasi pretesa predittiva, più verifica prospettica fuori campione.
- Shark Science v0.4 LAB resta separato; non combinare aggregati senza identificativi decisione verificati.
- Private Capture v0.15 LAB non attivato; collector Oracle non modificato; blocchi staging Contributors immutati.
- Prossimo passo: checklist input OOS privato senza spostare date, migliorare qualità/provenienza dei dati in LAB. Non eseguire acquisizioni reali senza autorizzazione.

**Questo è soltanto un controllo di calendario e immutabilità del protocollo, non un risultato di trading.**
