# REMURA TradingView v0.8.192 LAB — prima del holdout: gate del ricevitore CVD TEST
22 novembre 2026, Europe/Rome — research only, nessuna chiamata Cloudflare, Secret o deploy.

## Risultato tecnico, distinguendo STORIA e STATO CORRENTE
- Il run [43595646049](https://github.com/mirkoworz/remura/actions/runs/43595646049) documenta il 14/11/2026 un gateway TEST CVD distribuito con SETTINGS_VERIFIED; NON prova la versione oggi attiva.
- Le quattro ricevute TEST del 16/18 novembre lette dal checkout danno 40/40 barre nelle sole finestre richieste; non provano nuovi dati del 23/11, mercato completo o first-seen indipendente.
- Il codice sorgente candidato worker_cvd_candidate.mjs controlla hash token, IP allowlist, flag INGEST_ENABLED e CVD_PREVIEW_ENABLED, binding D1, limiter, contenuto, clock e rifiuto di ritrasmissioni in conflitto. Sono **proprietà del sorgente pinned**, non garantiscono che l'edge attuale esegua tali byte.
- Il codice legacy worker.mjs non include il ramo CVD. Le due sorgenti sono bloccate per SHA Git, senza modificarle.
- Non ci sono 16 workflow TV schedulati su main, ma TradingView Alert e Worker Cloudflare possono funzionare indipendentemente dalla pianificazione GitHub.

## Consegna
- tradingview/delta-peaks/cvd_test_runtime_gap_v0192_lab.py
- tradingview/delta-peaks/test_cvd_test_runtime_gap_v0192_lab.py (15 nuovi casi).
- .github/workflows/remura-tv-runtime-gap-v0192-only.yml
- Gate separato in codice statico, con checklist di dichiarazioni manuali dell'operatore e UNKNOWN espliciti. Anche 100% manuale non sostituisce prove indipendenti; il codice restituisce NO_GO_PROSPECTIVE_HOLDOUT_UNVERIFIED in ogni caso.

## Verifica minima futura, nell'ordine, solamente dopo consenso separato e margine Free
1. Verificare nella dashboard Cloudflare soltanto il Worker TEST esistente, sua versione in uso, binding TELEMETRY_DB verso D1 TEST, limiter, stato di INGEST_ENABLED e CVD_PREVIEW_ENABLED. Non leggere o copiare il valore del token.
2. Verificare in TradingView l'alert EURUSD M5 già autorizzato: stato attivo, eventuali errori di webhook/recapito, sorgente corretta. Non creare un secondo alert concorrente e non condividere l'URL webhook segreto.
3. Con quota D1 account, Access/plan e condizioni Free chiarite, chiedere eventuale permesso specifico per una query aggregata READ-ONLY mirata alle nuove barre TEST e controllare clock ricezione, duplicati, intervallo M5 e provenienza. Non avviare i vecchi workflow di lettura senza consenso.
4. Richiedere una vera prova indipendente dei payload per singola decisione, del first-seen e del denominatore M5 prima di qualsiasi analisi statistica; il codice attuale non la fornisce.
5. Se gateway o alert non sono realmente attivi al 23/11 00:00 UTC, marcare i periodi scoperti NOT_OBSERVED/UNKNOWN. Non riempire da storico e non spostare il protocollo V2 per recuperare le osservazioni perdute.

NON eseguito: query Cloudflare, deploy, trigger dei workflow manuali, registrazioni, invio webhook, lettura di Secrets, acquisizione, spese. Il gate non genera segnali e non cambia V2.
