# REMURA — ROADMAP V13 PRODUCT CHECKPOINT — 22 novembre 2026, Europe/Rome

PRODOTTO, non nuova ricerca astratta. V01–V12 preservate, V12 in research/remura-roadmap-v12-product-20261122, commit e997c14529419d8f206f5d0697afeccc55d98eb4.

## Shark Cockpit v1.66 LAB — funzionalita' reale
Branch separato: feature/shark-cockpit-v166-watchlist-lab-20261122. Commit funzionale con CI GREEN: 6e85d9642e35fa0d6e9307cc02267bffdf21aab2.
- shark-cockpit.html: filtro ★ Solo seguiti, messaggio sul salvataggio locale, pagina CFTC/retail della V12 e dati cronologici espandibili.
- shark-cockpit.js: bottone ★ per contratto CFTC, watchlist salvata solo nel localStorage dell'iPhone, fallback temporaneo segnalato in caso di memoria negata; nessun account, raccolta privata, polling o notifiche. Storico per contratto con massimo 12 report CFTC e differenze non inventate se manca una settimana.
- shark-cockpit-core.js: codici preferiti whitelist dei 14 contratti, deduplica, selezione contratti e historyFor da CFTC pubblico; ciascun report e' un martedi' e i delta si calcolano solo se la settimana precedente e' davvero presente; correzioni discordanti in quarantena. Nessuna inferenza spot/FX, alpha o clock first-seen originario.
- shark-cockpit.css: UI mobile per controlli 44px e tabella storico a scroll interno.
- nav.js, dieci pagine HTML e cache shell sw.js: intestazione v1.66 LAB 22/11/2026 18:13 CET in cima a tutte le pagine, riferimenti nav.js?v=166 aggiornati senza alterare le funzionalita' dei vecchi moduli; cache sw v80, nessuna cache live del provider CFTC. Splash Toro/Orso Mac rimasto intatto.
- Test nuovo prodotto e versione: tests/shark-cockpit.test.js e tests/release-consistency.test.js. Workflow mirato remura-shark-cockpit-v166-watchlist.yml.

### CI effettiva
Il primo run v166 45048352166 ha riportato 31/33 per due test non aggiornati alla nuova versione (regex v1.65 e blocco localStorage ormai intenzionalmente usato per la watchlist). Allineati i test in un unico commit, non alterato il modello CFTC.
Run definitivo [45048411520](https://github.com/mirkoworz/remura/actions/runs/45048411520) SUCCESS: log letto # tests 33 / # pass 33 / # fail 0 / REMURA_SHARK_COCKPIT_V166=33_33_PRODUCT_PASS.
I test verificano funzionamento del codice e del wiring, NON rappresentano una visita reale a Safari iPhone o CFTC live disponibile.

## Contributors — evitare duplicati e rispettare autorizzazione
Il branch research/contributors-pilot-scope-v094-lab-20261122 contiene gia' un form candidato completo research/contributors/contributors_candidate.html, un simulatore interattivo mobile v0.89, una preview v0.87 e modello dei permessi v0.94 per 1 owner + 1–2 contributors. NON costruire un altro frontend da zero.
Il candidato puo' scegliere mercato, broker, ticker, periodo, metodologia, prezzo, anchor UTC e osservato UTC, note, ed esporre una coda proprietario nel LAB. Non e' ancora una sessione reale autorizzata; non aggiungere link al pubblico o scritture D1 fino a prova di Access, quota Free, reale ownership, login/logout/revoca Safari e autorizzazione specifica. Test v0.92–v0.94 gia' effettuati: non ripetere.

## Stato generale mantenuto
- Main verificato 9758bdcbf1c55b1c63ad66bcf6716872cdc906e4; nessun merge, deploy Pages o modifica Oracle realizzata in V13. Branch v1.65 precedente conservato.
- PR #105 Contributors e #106 TradingView ancora OPEN/DRAFT e NON MERGED; non aprire PR nuova automaticamente se quota Actions non attestata.
- Cloudflare D1 e Access Free headroom tuttora UNKNOWN_NO_GRAPHQL_DATA; autorizzazione precedente di due GraphQL esaurita. Nessuna nuova API o Secret interrogata o nuova spesa.
- Mac Codex continua custodia, backup, collector Oracle v1.65 staged non installato, Experience 3D toro/orso e anti-rollback separati.
- TradingView CVD TEST storicamente verificato nel run 43595646049, stato attuale UNKNOWN. Holdout V2 dal 23/11/2026 00:00 UTC (01:00 CET): l'apertura del calendario non crea prove prospettiche; NO GO alpha senza ricevute/clock/mapping/denominatore verificati.
- COT v0.7 e v0.8 coorti/mapping in LAB non sono real data migrations. Myfxbook retail separato da CFTC istituzionale. Ampere Radar Oracle Milano Telegram gia' attivo senza duplicazioni.
- UI release future: numero aggiornato e ora Europe/Rome sempre all'inizio di ogni pagina realmente modificata.

## Priorita' dalla V14: lavorare sul prodotto
1. Ottenere un ambiente di preview iPhone sicuro **con consenso specifico prima di qualunque deploy**, verificare layout, scelta dei preferiti persistente, tabella 12 report, risposta CFTC browser e versione del menu. Non presentare file GitHub come URL di app navigabile.
2. Riutilizzare il form Contributors candidato gia' costruito, senza aggiungere un secondo design, ma attivare pilot 1–2 amici solo dopo gate Cloudflare Free, JWT Access reale e test Safari di least privilege e revoca. No account reale adesso.
3. Verificare eventuale ricevitore CVD TEST reale solo dopo margine gratuito e nuovo consenso in sola lettura; mai riempire retroattivamente holdout.
4. Evitare scanner duplicati: mercati.html resta il radar di asset/proxy; Shark Cockpit mostra contratti futures individuali.

VERDETTO: vera UI migliorata, 33 test funzionali passati, nessuna modifica produzione, nessun costo nuovo, no deploy.
