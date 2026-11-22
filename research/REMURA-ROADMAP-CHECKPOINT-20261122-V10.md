# REMURA — ROADMAP CHECKPOINT V10 — 22 novembre 2026, Europe/Rome

**SOLO LAB — incremento dalla V09, nessun merge/deploy.** Conservare V01–V09. Checkpoint precedente: research/remura-roadmap-v09-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V09.md, commit 70ace3590b09ab9e15cb03f4c9c02b8e4c418f1c. I precedenti V08–V01 rimangono raggiungibili dai rispettivi checkpoint.

## Verifiche concrete della catena TradingView
Al checkpoint, MAIN e' bd19918f457809f0568aee5c674b1b36a254971e. I 16 workflow originali di main con prefisso remura-tv- sono stati ispezionati con GitHub in sola lettura: 16 workflow_dispatch, **zero schedule**, 1 include push. Una snapshot con nome, Git blob SHA, trigger e commit base si trova in tradingview/delta-peaks/evidence/main_tv_workflow_snapshot_20261122_v0191.json, branch research/tv-receipt-reality-audit-v0191-lab-20261122. Non copiare o attivare questi 16 workflow nel branch LAB. Questo inventario NON verifica se TradingView abbia alert attivi o se Cloudflare Worker stia ricevendo dati esternamente; servizio reale UNKNOWN.

Sul branch di ricerca sono presenti quattro JSON **TEST** storici, sanitizzati e immutati, con PIN SHA:
- fx_first_receipt_20261116.json: run 43839770016, 4/4 barre richieste;
- fx_second_receipt_20261116.json: run 43851249699, 12/12;
- fx_third_receipt_20261118.json: run 44294693651, 12/12;
- fx_fourth_receipt_20261118.json: run 44362438343, 12/12.

**40/40 barre delle sole finestre TEST scelte**, non del mercato o del prossimo holdout. Source target EU_D1_TEST_ONLY; conflict_ledger_available=false; independent_provenance=false; scientific_admission=false; account_quota_utilization=null. La presenza dei file non dimostra copertura M5 del mercato, primo orario esterno, originari payload autenticati, il funzionamento attuale di un Worker o un vantaggio predittivo.

## TRACK 1 — TradingView v0.8.191 REALITY AUDIT (nuovo, LAB)
Branch research/tv-receipt-reality-audit-v0191-lab-20261122
HEAD verificato fc1518b952b8712a09a30a46e4fa34213899658d (documentazione aggiornata dopo CI).
File:
- tradingview/delta-peaks/checked_in_receipt_reality_v0191_lab.py
- tradingview/delta-peaks/test_checked_in_receipt_reality_v0191_lab.py
- tradingview/delta-peaks/evidence/main_tv_workflow_snapshot_20261122_v0191.json
- tradingview/delta-peaks/TV-V0191-ACTUAL-TEST-RECEIPTS-CHECKPOINT-20261122.md
- .github/workflows/remura-tv-reality-v0191-only.yml

CI finale [run 45043222255](https://github.com/mirkoworz/remura/actions/runs/45043222255) sul commit ca5bb60f2383b88e559a071fbdfb411571f1da9d: **SUCCESS, 14/14**, log letto Ran 14 tests / OK / REMURA_TV_REALITY_V0191=14_14_PASS. La modifica successiva fc1518 e' SOLO al documento non compreso nel path trigger.

La prima CI fallita per refuso PINN/PINNED nel nuovo modulo. La seconda ha mostrato che il branch research non contiene tutti i workflow main: correttamente NON sono stati copiati. Un manifest inerte della vera ispezione main ha risolto il problema. Il penultimo run aveva un caso test con aspettativa errata (manifest mancante rende tutti e 16 gli stati UNKNOWN, non uno); corretto. Tutte le prove attuali 14/14 PASS; non nascondere i log iniziali ma non ripetere i test precedenti.

Il modulo legge solo byte della propria checkout, quattro file con SHA Git pinned, una snapshot main pinned, rispettivi metadati TEST, date e trigger. Risultato strutturale VERIFIED_PINNED_HISTORICAL_TEST_METADATA_ONLY con sempre live_alpha_go=false; non contatta provider, D1, API GitHub o Secret quando eseguito in CI. Non verifica dati futuri non presenti nel repository.

## TRACK 2 — COT Shark Science v0.7 TFF COHORT FLOW (nuovo, LAB)
Branch research/cot-institutional-flow-v07-lab-20261122
HEAD verificato 7346159d4ffc6efbba41d5d1626cc785c69d2558
File:
- research/cot/cot_institutional_cohort_flow_v07_lab.py
- research/cot/test_cot_institutional_cohort_flow_v07_lab.py
- research/cot/COT-INSTITUTIONAL-COHORT-FLOW-V07-HANDOFF-20261122.md
- .github/workflows/remura-cot-cohort-v07-only.yml

CI [run 45042994455](https://github.com/mirkoworz/remura/actions/runs/45042994455): **SUCCESS 17/17**, log letto Ran 17 tests / OK / REMURA_COT_FLOW_V07=17_17_PASS.

Nuova utilita' reale a livello di codice scientifico: per uno stesso codice CFTC TFF, confronta due o tre martedi' consecutivi in memoria. Per Asset Managers e Leveraged Funds calcola il saldo netto long-short / open interest in percentuale, variazioni WoW in punti percentuali, accelerazione con tre settimane, open-interest change e co-moving/divergent/flat descrittivo. Le due categorie non vengono confuse. Se qualunque settimana NON esiste nel sidecar v0.6 alla data decisione, il confronto e' UNKNOWN senza fabbricare valori dal legacy. Le revisioni ricevute dopo la decisione non contaminano l'as-of. I test sono sintetici, non CFTC live. Le percentuali non sono probabilita' di successo; i gruppi sono categorie aggregate e non singoli istituti, insider o nomi di balene. Non provano direzione futura, spot/futures mapping o esecuzione.

**TOTALE NUOVI TEST V10 = 31/31 GREEN**, solo nuove suite. Main inalterato, PR #105 Contributors e #106 TV ancora OPEN/DRAFT NON MERGED.

## Situazione scientifica e holdout imminente
Protocollo V2 bloccato byte-pinned:
- Development: dal 16/11/26 00:00 UTC al 23/11/26 00:00 UTC escluso;
- Holdout 1: 23/11/26 00:00 UTC -> 30/11/26 00:00 UTC escluso (**23/11 ore 01:00 CET**);
- Holdout 2: 30/11/26 00:00 UTC -> 07/12/26 00:00 UTC escluso.

Confronto preregistrato CVD vs price-only a 60 minuti, secondari 4h/24h, FIFO M5, ricevuta M5 entro close +120 secondi e prima del successivo close, costi teorici 0/1/2 pip, nessun tuning, no backfill, non attraversare i fold. Le analisi v0.8.188 firewall, v0.8.189 junction e v0.8.190 maturity restano validi LAB e non alterati. L'apertura del calendario domani non equivale alla prova di un flusso attivo o indipendente. **NO-GO SCIENTIFIC ALPHA**.

## Altri TRACK da mantenere senza sovrapporre i lavori
- Retail Myfxbook: history Git 34 file, 3984 osservazioni al checkpoint precedente; v0.5 Actions time bracket 16/16 GREEN e v0.6 provenance receipts 14/14 GREEN. Myfxbook e' retail, NON istituzionale; clock originale provider/first-seen indipendente ancora da dimostrare.
- COT precedenti: v0.1 revision, v0.2 capture atomic, v0.3 WAL reopen, v0.4 global integrity, v0.5 additive sidecar e v0.6 forward-only, tutti collaudati LAB con numeri esatti nel V09. Il collector corrente scripts/cot_monitor.py conserva ON CONFLICT DO UPDATE; rischio teorico di storicizzazione, NON danno Oracle diagnosticato.
- Contributors v0.94 role/scope matrice 16/16 GREEN, v0.93 budget free proof 16/16 GREEN e integrazione D1/Access v0.92; PR #105 DRAFT. Solo 1–2 amici dopo verifica di Free/seat/account, staging, Safari iPhone reale, revoca e consenso distinto. **Pilot NO-GO**.
- Cloudflare: workflow remura-cloudflare-budget-daily.yml gia' esistente, non rilanciare/duplicare. Ultima diagnosi disponibile D1 account quota UNKNOWN_NO_GRAPHQL_DATA (run 44919682812 INCOMPLETE_OR_CRITICAL); budget Workers/Access seat e costi complessivi non certificati. Due GraphQL del consenso precedente gia' esaurite. Nessuna nuova chiamata, Secret o spesa.
- Mac/Oracle: filone esclusivo Mac Codex, repo remura-collector branch codex/mac-custody-checkpoint-20261120 (SHA noto 7a23f61b2cb1e520bff623348366231ee093bb3f, non rivalidato in questo turno); collector preservato, autoupdater inibito, v1.65 archiviata root-owned ma non installata; backup/custodia/antirollback solo Mac.
- Experience v0.30 LAB (toro/orso 3D collisione e loading, splash esplosivo, REMURA pinna, SMF ringraziamento, togliere foto) rimane non pubblicata; Private Capture v0.15 LAB non attivata. Ampere Radar Oracle Milano con Telegram gia' operativo al checkpoint, senza duplicazione. Squalincome e contributi formattati Telegram successivi.

## Priorita' da V11
1. **Non perdere il primo holdout**: identificare in maniera AUTORIZZATA la vera rotta TradingView alert -> Worker Cloudflare -> D1 TEST -> ricevuta originale con clock e identita' decisione, senza assumere che i 16 workflow manuali la sostituiscano. Nessuna attivazione automatica, quota o deploy senza nuovo consenso e stato Free verificato.
2. Ottenere autentici witness esterni e ricevute non retroattive per singola barra; verificare denominatore M5, first-seen, prezzo-only e spot/futures mapping prima di classificare l'alpha.
3. Preparare integrazione COT v0.7 in letture future as-of quando il sidecar verra' autorizzato e affidabile sul Mac; NON recuperare versioni storiche da cot_reports sovrascritte.
4. Contributors pilot e release UI solo con gate ancora aperti; controllare Access seats/Cloudflare quota, Safari login/revoca; non superare il Free per automatismi.
5. Ogni pagina pubblica REMURA eventualmente modificata dovra' mostrare in cima versione pubblica aggiornata e timestamp Europe/Rome. Nessuna pagina pubblica aggiornata in V10.

**VERDETTO V10: due moduli nuovi +31 test GREEN, scoperta operativa importante della mancanza di attestazione di un feed prospettico automatico. LAB GREEN; dati esterni, alpha, pilot reale e migrazione Oracle NO-GO. Produzione e main non modificati.**
