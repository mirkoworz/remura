# REMURA — ROADMAP CHECKPOINT V11 — 22 novembre 2026, Europe/Rome

**SOLO LAB. Incrementale, V01–V10 preservati.** Checkpoint V10 precedente: research/remura-roadmap-v10-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V10.md (commit 0176a38a13be6bce5148e32c63a39ff159bd6aed). Non riscrivere i checkpoint storici.

## Due filoni nuovi verificati

### 1. TradingView v0.8.192 — TEST CVD REAL-TIME GAP GATE
Branch: research/tv-cvd-live-gap-gate-v0192-lab-20261122.
HEAD codice/test/docs/CI: ccc1fb458ee7a90861d0a3e1fe651dd6d124d2ac.
- tradingview/delta-peaks/cvd_test_runtime_gap_v0192_lab.py
- tradingview/delta-peaks/test_cvd_test_runtime_gap_v0192_lab.py
- tradingview/delta-peaks/TV-V0192-CVD-REAL-STATE-GATE-20261122.md
- .github/workflows/remura-tv-runtime-gap-v0192-only.yml
- CI finale [run #45044822892](https://github.com/mirkoworz/remura/actions/runs/45044822892): SUCCESS, 15/15 PASS, log letto: Ran 15 tests, OK, REMURA_TV_CVD_RUNTIME_GAP_V0192=15_15_PASS. Prima CI 45044787370 aveva 14 test corretti e un errore di sola chiave della fixture (historical_test_deploy_verification_run contro historical_deploy_verification_run), corretto soltanto nel test. Non ripetuti i test storici.

**Scoperta operativa cruciale:** il run #43595646049 e il runbook PILOT-CVD-EURUSD-RUNBOOK.md documentano gateway CVD TEST attivato e impostazioni verificate il **14 novembre 2026**. Quattro ricevute TEST del 16 e 18 novembre nel branch indicano 40/40 barre delle specifiche finestre di prova; non costituiscono copertura generale del mercato, prova di first-seen indipendente o certezza che il gateway oggi sia ON.

Il sorgente candidato worker_cvd_candidate.mjs contiene gli ingressi CVD condizionati da INGEST_ENABLED/CVD_PREVIEW_ENABLED, token hash, binding TELEMETRY_DB a D1 TEST, rate limiter, insert append-by-event e rifiuto del retry CVD con contenuto discordante; il precedente worker.mjs e' il rollback legacy. Sono state controllate sorgenti Git SHA-pinned in checkout: questo **non** prova il codice realmente distribuito oggi, lo stato dell'alert TradingView, le nuove righe D1, la correttezza del proxy intrabar, quota Free o margine economico.

Il modulo offline produce schema statico con tutti gli UNKNOWN e checklist di preflight dell'operatore. Un insieme completo di dichiarazioni manuali non si trasforma mai in prova provider o via indipendente: **NO_GO_PROSPECTIVE_HOLDOUT_UNVERIFIED** e live_alpha_go=false. Nessun Cloudflare GET, query D1, creazione alert, workflow manuale, webhook, nuova spesa o attivazione. Nessun Secret esposto.

### 2. Shark Science COT v0.8 — SPOT / FUTURES MAPPING REVIEW
Branch: research/cot-spot-futures-mapping-v08-lab-20261122.
HEAD codice/test/docs/CI: 896f96c7b74f697ec35610bb8cc753b2ab57f670.
- research/cot/cot_spot_futures_mapping_v08_lab.py
- research/cot/test_cot_spot_futures_mapping_v08_lab.py
- research/cot/COT-FOREX-SPOT-MAPPING-V08-HANDOFF-20261122.md
- .github/workflows/remura-cot-fx-map-v08-only.yml
- CI [run #45044789829](https://github.com/mirkoworz/remura/actions/runs/45044789829): SUCCESS, 15/15 PASS, log letto: Ran 15 tests, OK, REMURA_COT_FX_MAPPING_V08=15_15_PASS.

Controllo descrittivo preventivo: l'output COT v0.7 di Asset Managers/Leveraged Funds e' sul future, non identifica da solo la coppia FX spot. Una proposta sintetica esplicita per una coppia con USD come una gamba e future NON-USD quotato in USD permette il calcolo orientativo del segno del cambiamento TFF, CON NOTA CHE E' SOLTANTO IPOTESI NON VERIFICATA; EURUSD stesso segno e USDJPY segno invertito nel modello sintetico. Non si associano automaticamente codici CFTC concreti alle valute; un file digest o documento dichiarato non prova la spec del contratto. I cross EURJPY, i contratti non esplicitamente compatibili e le settimane COT mancanti restano UNKNOWN. Mapping, scadenza, basis, CFTC publication e spot/FX feed non sono verificati. **Nessun segnale, no alpha, no Oracle reale**.

**Totale V11: 30/30 test nuovi GREEN su due branch LAB indipendenti; niente vecchie suite ripetute.**

## Vincoli principali, preservati
- Main prima delle modifiche visto bd19918f457809f0568aee5c674b1b36a254971e; checkpoint V11 su altro branch, nessun merge/deploy. Verificare main dopo salvataggio, distinguere eventuali automatici Myfxbook dai merge.
- PR #105 Contributors e #106 TradingView DRAFT NON MERGE.
- TradingView V2 FROZEN: development 16–22/11/2026 UTC; holdout1 [23/11 00:00 UTC, 30/11 00:00 UTC); holdout2 [30/11 00:00 UTC, 07/12 00:00 UTC). Primario prezzo-only vs CVD 60 minuti, secondari 4h/24h, FIFO M5, CVD entro chiusura+120s e prima della prossima barra, costi ipotetici 0/1/2 pip, nessun tuning, nessun matching inter-fold. L'holdout iniziera' il 23 novembre alle 01:00 CET: il calendario non crea dati!
- TradingView v0.8.188 firewall, v0.8.189 junction, v0.8.190 fold maturity, v0.8.191 audit di 4 JSON TEST e 16 workflow main erano gia' GREEN, non rieseguiti. V0.8.192 NON certifica la sorgente CVD reale.
- COT v0.1–v0.7: append-only simulazione, rollback, as-of e metriche TFF categorie istituzionali, gia' testate. Il collector scripts/cot_monitor.py con ON CONFLICT DO UPDATE puo' sovrascrivere storici, ma non e' dimostrato che abbia danneggiato Oracle. Non modificarlo senza coordinamento Mac, backup consistente e restore verificato.
- Retail Myfxbook v0.6 receipt ledger e v0.5 Git Actions brackets gia' verdi, prove originarie provider/clock NO-GO; retail non e' istituzionale.
- Contributors Access/D1 v0.92 e Free proof v0.93, scope v0.94 LAB: test verdi, ma Access Free seats e budget/account D1 non interamente attestati, login/logout/revoca Safari reale NO-GO, PR #105 aperta DRAFT; 1–2 amici pilot non attivati.
- Cloudflare: unico budget workflow .github/workflows/remura-cloudflare-budget-daily.yml esiste, non duplicarlo. Ultimo run disponibilita' D1 account UNKNOWN_NO_GRAPHQL_DATA e overall INCOMPLETE_OR_CRITICAL; precedente autorizzazione 2 GraphQL esaurita. Nessuna nuova richiesta Cloudflare, nessun uso Secret, D1, Workers, costi; per l'eventuale diagnostica reale serve AUTORIZZAZIONE nuova e controllo margine Free.
- Oracle/Mac: repo remura-collector branch codex/mac-custody-checkpoint-20261120, SHA storico 7a23f61b2cb1e520bff623348366231ee093bb3f, non controllato qui. v1.65 root-owned staged non installato, autoupdater inibito, collector preservato; backup/antirollback/Experience riservati a Mac.
- Experience v0.30 LAB: splash animato cinematografico scontro 3D toro/orso, caricamento/esplosione, REMURA con pinna, logo SMF/ringraziamento, rimozione foto utente; non pubblicato. Private Capture v0.15 LAB e Ampere Radar Oracle Milano Telegram preservati, nessuna duplicazione.
- Squalincome, Telegram livelli approvati, Shark Science scoring e comparatori come prossime roadmap, nessuna promessa di guadagno.
- Regola UI: ogni VERA pagina REMURA modificata in futuro deve mostrare in alto la versione PUBBLICA aggiornata e data/ora Europe/Rome. In V11 nessuna pagina app modificata.

## Priorita' V12
1. **CVD 23/11**: se l'owner autorizza una verifica reale, prima budget Free completo; poi controllo minimo dello stato esatto del Worker TEST e alert TradingView (senza token in chiaro), e solo con permesso successivo eventuale read D1 TEST aggregato di nuove barre temporizzate. Non avviare workflow manuali vecchi automaticamente. Nessun backfill per finestre non osservate.
2. First-seen indipendente per decisione, vendor feed e raw payload, denominatore M5/clock, price-only comparator; non utilizzare hash locali per promuovere in holdout.
3. COT: documentare prove ufficiali di codici/contratti, specifiche e calendario CFTC prima di applicare mapping EUR/USD o USD/JPY a dati veri; approvare migrazione forward-only Oracle solo dopo il Mac backup.
4. Contributors: quote Access/D1/GitHub e staging Safari 1–2 utenti reali, solo dopo consenso separato.
5. Conservare main e protocollo V2, niente nuove spese e no ripetizione di test storici.

**Verdetto:** 30 test nuovi verdi, fonte CVD storicamente funzionante in TEST ma operativita' attuale NON ATTESTATA; zero prove di vantaggio predittivo. Produzione preservata.
