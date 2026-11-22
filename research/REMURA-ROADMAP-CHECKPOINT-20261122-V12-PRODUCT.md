# REMURA — ROADMAP V12 / PRODUCT CHECKPOINT — 22 novembre 2026, Europe/Rome

**Dal controllo scientifico alla costruzione effettiva della web app.** V01–V11 preservati, V11 in research/remura-roadmap-v11-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V11.md (commit 55f9f0139290b85e4ba6096f8a62862ba57ffb9b).

## PRODUCT: SHARK COCKPIT v1.65 LAB REALMENTE CODIFICATO
Branch esclusivo senza merge: feature/shark-cockpit-v165-preview-20261122
HEAD al salvataggio: fe710ae6a93bbcfb281bc61350953d1657f5aac4.
File di handoff: SHARK-COCKPIT-V165-PREVIEW-20261122.md.
Pagina: shark-cockpit.html; CSS shark-cockpit.css; JS browser shark-cockpit.js; modulo analitico puro shark-cockpit-core.js.
Navigazione: nav.js nuova voce "Shark Cockpit · Fondi CFTC", nuova selezione attiva, nuova etichetta di release **v1.65 LAB · 22/11/2026 17:32 CET** in cima a ogni pagina, cache bust nav.js?v=165 presente su tutte le 9 pagine precedenti e la nuova; nessun altro contenuto delle 9 vecchie pagine alterato.
PWA: sw.js nuova cache shell v79 con i 4 asset della nuova pagina; CFTC esterno mai archivio live.
Test nuovi tests/shark-cockpit.test.js e release aggiornato tests/release-consistency.test.js.
Workflow mirato .github/workflows/remura-shark-cockpit-v165-preview.yml.

**CI verificato:**
- Primo run [45047433354](https://github.com/mirkoworz/remura/actions/runs/45047433354) SUCCESS 24/24.
- Ultimo run [45047547629](https://github.com/mirkoworz/remura/actions/runs/45047547629) SUCCESS 24/24 sul commit a4540969bfa6dfb2f0f9d9a13f4e0cb068fbfd0f. Lettura reale log: '# tests 24', '# pass 24', '# fail 0' e REMURA_SHARK_COCKPIT_V165=PRODUCT_SMOKE_GREEN.
- Il successivo commit fe710ae crea solo il documento di handoff, non file eseguibili. Non ritestare storico per questo documento.

**Funzionalita' effettive in browser dopo preview/release:**
- 14 contratti CFTC pubblici gia' censiti nella app, 7 futures valutari, 4 indici/USD Index, 3 disagg (oro, argento, WTI).
- Fetch dall'endpoint ufficiale CFTC TFF gpe5-46if e Disaggregated 72hh-3qpy via browser, usando campi/whitelist gia' presenti nello scanner mercati.html, senza server/cloud/chiavi nuovi.
- Rendicontazione per Asset Manager / Leveraged Funds su TFF e Managed Money / Producer Merchant su disagg; LONG, SHORT, nettto/OI, differenza WoW solo se due martedi' consecutivi, quattro settimane se 5 report consecutivi. Dati futuri/invalidi ignorati; report obsoleti >14 giorni marcati, duplicati discordanti stesso contratto/data in quarantena.
- Filtro famiglie, ricerca, ordinamento per massimi movimenti, divergenze o data, cards adattive iPhone.
- Sezione Myfxbook RETAIL distinta da dati istituzionali, GET del file gia' pubblicato data/myfxbook/latest.json, 7 coppie piu' rilevanti, percentuali sui lotti realmente contenuti, dati oltre 3 ore marcati come archiviati; non usa API Myfxbook direttamente.
- Nessun segnale trading, price inference, insider, first-seen attestato, conferma di esecuzioni, previsione o conversione automatica futures/spot.

**COSA NON E' ANCORA COMPLETATO:** anteprima non pubblicata su GitHub Pages/produzione, nessuna vera navigazione Safari iPhone o verifica Live fetch CFTC dei 14 contratti, nessun codice di autenticazione Contributor attivo, nessuna verifica live CVD. I test sono su dati sintetici in memoria e wiring della nuova UI, non su una raccolta live o screenshot. NON parlare di 14 dati reali visibili finche' non collaudati nel browser.

## Integrazione e cautela
Prima di rilasciare v1.65 verificare release Mac/Codex Experience splash toro/orso 3D e branch Oracle v1.65: quel lavoro e' separato. Non sostituire splash.js, CSS splash o collector. La modifica a index.html sul nuovo branch e' soltanto il riferimento query nav.js?v=165.
Repository main verificato a checkpoint: 9758bdcbf1c55b1c63ad66bcf6716872cdc906e4, avanzato autonomamente rispetto a bd199...; nessun merge Shark Cockpit. PR #105 Contributors e #106 TV sono ancora OPEN/DRAFT, non merged. Non ritoccare main senza approvazione deployment.

## Roadmap prioritaria V13 — lavoro vero, non incremento di test
1. **Preview iPhone della pagina vera.** Con consenso distinto per deploy/preview, pubblicare SOLO in un ambiente autorizzato o aprire ramo in ambiente di anteprima, senza toccare Pages principale. Safari: verificare layout, menu, CFTC TFF/disagg, ricerca, divergenze, dati mancanti e Myfxbook archiviato. Limitare provider calls ai GET dell'apertura + un refresh volontario; non automatizzare polling.
2. **Integrare lo Shark Cockpit nei percorsi principali** se visivamente approvato. Evitare creare altri radar duplicati: la novita' e' dettaglio per singola categoria/contratto future.
3. **Contributors utilizzabile:** progettare UI reale di inserimento livelli, lettura REMURA senza scrittura altrove, ruoli a minimo privilegio. Cloudflare Access, D1 budget Free, login/revoca Safari, 1–2 amici piloto solo dopo gate, evidenza quota e autorizzazione. No utenti reali ora.
4. **Prospettico CVD:** v0.8.192 checkpoint storico dimostra TEST 14/11 passato, non il receiver attuale. Per il holdout che si apre 23 novembre 00:00 UTC (01:00 CET) servono conferma stato Worker/Alert, provider first-seen e copertura reali. Prima chiedere specifico consenso READ-ONLY e margine Cloudflare Free; precedente limite di 2 GraphQL gia' consumato. Nessun controllo fittizio o backfill.
5. **COT v0.7–v0.8 LAB** rimangono algoritmi sintetici per coorti/mapping, NON alimentati al nuovo cockpit senza origine/verifica, schema reale append-only, prova CFTC e coerenza con collector Mac.
6. A ogni nuova VERA release web aggiornare etichetta in cima a tutte le pagine con versione/data/ora Europe/Rome. Rispettare FREE-first, no costi Cloudflare nuovi, niente Oracle e no schemi D1 reali senza autorizzazione. Tracciare successiva roadmap.

**Risultato V12: un prodotto web concreto creato e integrato nel menu, 24 test di funzione/release verdi. Pronto per preview guidata, non pubblicato in produzione.**
