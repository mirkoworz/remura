# REMURA TradingView v0.8.185 LAB — HASH CHAIN CAPTURE REGISTER

**Checkpoint: 21 novembre 2026 · 18:19 CET (Europe/Rome)**

## Stato GitHub
- Repository pubblico `mirkoworz/remura`; branch isolato `research/tradingview-evidence-ledger-v0185-20261121`.
- Base v0.8.184: `8d914dbed0bf63794f8d7e63f4fa403b3e36f1ec`.
- Commit di CODICE testato `6280b158fd56100abbfe06a5f316b4bc44ef5b2f`.
- GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44929255418 — **SUCCESS** verificato con log `Ran 22 tests`, `OK`, `REMURA_TV_V0185_CHAIN=22_22_PASS`. Solo **22/22 test nuovi**, nessuna suite storica ritestata.
- Runner standard pubblico read-only, checkout senza credenziali, nessun Secret, deploy, dati live, Oracle, Cloudflare, merge in main o spesa.

## Cosa abbiamo realizzato
- `local_capture_ledger_v0185_lab.py`: catena locale SHA-256 deterministica sui soli record **sintetici** M5, abbinata esattamente a slot preregistrati, con stato `CAPTURED_TIMELY`, `CAPTURED_LATE` o `NOT_CAPTURED`. Chiama il guard calendario V2 pinned senza modificarne protocolli.
- `test_local_capture_ledger_v0185_lab.py`: 22 prove nuove su manomissione hash, ordine, timestamp, claims false, duplicati, missing data, fold errato e nessuna valutazione outcome. One-shot `.github/workflows/remura-tv-v0185-chain-one-shot-ci.yml`.
- La catena non attesta origine indipendente: un operatore potrebbe ricostruirla o retrodatare eventi. Serve futura attestazione esterna di timestamp e anchor **prima** di presentarla come prova scientifica; non pubblicare digest privati o dati utenti.
- Una riga `NOT_CAPTURED` NON prova assenza di attività del mercato. I fold rimangono holdout1 23/11 00:00–30/11 00:00 UTC e holdout2 30/11 00:00–07/12 00:00 UTC, estremi finali esclusivi.
- Soglie 120 s e prima del prossimo close M5, ordine temporale, nessuna imputazione di barre mancanti. `future_outcomes_used=false`, `institutional_edge_established=false`, `market_coverage_attested=false`, `decision=NO_GO_LIVE`.
- Nuovo runbook `TRADINGVIEW-V0185-EVIDENCE-CHAIN-RUNBOOK-20261121.md` sul perimetro e su cosa manca.

## Prossimi passi e altre linee
1. v0.8.186: preparare interfaccia per anchor esterno/clock indipendente senza usare Secret, senza attivare acquisizione e senza alterare V2; non simulare dati reali come verificati. L'esperimento rimane prospettico, e l'edge istituzionale non è dimostrato.
2. Shark Science v0.4 LAB, COT/sentiment/delta/CVD/assorbimento, deve restare metodologicamente separato finché le fonti non sono allineate a identità e timestamp.
3. Contributors v0.85 LAB per staging e rollback, monitor Cloudflare D1 daily incomplete/UNKNOWN e seats Access sconosciuti: no deploy. Pilot collaboratori solo su autorizzazione con OWNER audit.
4. Experience v0.30 toro/orso 3D, splash REMURA pinna e SMF, Safari fisico; Private Capture NON attivo, Oracle collector protetto, Ampere Radar operativo, backup/Squalincome/Telegram livelli approvati preservati.
5. Testare solo modifiche nuove; repo pubblico senza PII e Secret; nessun Mac o spesa necessari per l'attuale LAB.

**Risultato: 22/22 test sintetici PASS; ledger non ancorato, nessun dato di trading reale valutato.**
