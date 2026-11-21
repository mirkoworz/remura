# REMURA Contributors v0.75 LAB — NAVIGAZIONE PRIVATA + ASSET WORKER IMMUTABILI

**21 novembre 2026, ore 15:48 CET (Europe/Rome)**

## Provenienza e stato su GitHub
- Repository pubblico: `mirkoworz/remura`.
- Branch isolato: `research/contributors-private-navigation-v075-20261121`.
- Base di partenza: v0.74 HEAD `89701c87850af0523ab371ba23a790bd05167ac3`.
- Non toccati `main`, Cloudflare Access/Workers/D1 reali, Secret, identità reali, Oracle, collector, Telegram, acquisizione dati e risorse a pagamento.
- La UI aggiornata porta **v0.75 LAB · 21/11/2026 15:48 CET** in posizione visibile in cima a **tutte e quattro le pagine private modificate**; i file originali v0.72/v0.74 restano intatti nei loro branch.

## Funzionalità raggiunte: due percorsi non confusi
- `/contributors/` => recupero personale e ricevute amendment, con link `./levels/` alla propria pagina per **nuove proposte**.
- `/contributors/levels/` => nuovo livello con strumento/provider/ticker/prodotto esatti, periodo, kind, prezzo, anchor UTC, observed UTC, note, ricevute personali; link `../` all'area personale.
- `/owner/` => coda reconciliation amendment dell'OWNER con link `./levels/` alla revisione dei livelli originali.
- `/owner/levels/` => decisioni OWNER sui nuovi livelli, con link `../` alla coda delle correzioni.
- Le correzioni/amendment v0.65–v0.72 rimangono distinte dall'originale `/api/submit` v0.74. Nessuno stato di recovery autorizza una nuova mutazione.
- Le voci di navigazione sono semplici collegamenti **non autenticanti**; ogni GET e POST verifica nuovamente Access diretto e profilo D1 server-side.
- La nuova UI di livelli `contributors_levels_ui_v075_lab.mjs` usa `createExitCoordinatorV072`: quando si sceglie Esci, blocca subito i comandi (anche durante richieste pendenti) e aggiorna la vista; sul futuro HTTPS autorizzato richiederà la navigazione di logout Access senza dichiarare la revoca del token completata.

## Asset e composizione
- Nuove HTML: `contributors_recovery_v075_private_lab.html`, `contributors_owner_recovery_v075_private_lab.html`, `contributors_levels_v075_lab.html`, `owner_levels_v075_lab.html`.
- Nuove CSS responsive: `contributors_private_recovery_v075_lab.css`, `contributors_private_levels_v075_lab.css`.
- Router `private_worker_router_v075_lab.mjs`: oltre alla separazione CONTRIBUTOR/OWNER, ogni asset statico viene servito soltanto nell'**area funzionale** corretta (RECOVERY oppure LEVELS); nega il recupero di file dismessi, SQL, manifest, script da sezione sbagliata e percorsi esterni.
- `private_assets_v075_lab.mjs`: 13 asset statici ES module, generati con i byte delle sorgenti; non importa `node:fs` né altri Node builtin. Il generatore locale `build_private_assets_v075_lab.mjs` è indipendente dal runtime Worker, e dispone di `--check` per rilevare asset drift.
- `private_levels_composition_v075_lab.mjs`: solo import ES con embed di asset, `accessBinding`, D1 profile, gate livelli v0.74, bridge read v0.69. **Senza default export fetch e senza Wrangler config**, quindi NON distribuibile per errore. Non sono stati usati Service Bindings né Worker Static Assets per propagare un'identità Access.
- Manifest `REMURA_V075_ASSETS=13_MATCH` SHA-256: `e5c930ffca752c4a6fb418d327a1e15a87e30ff6325211dc445d3178684c9164`.

## Nuovi test realmente attestati su GitHub (nessuna suite storica ripetuta)
**Run GREEN: https://github.com/mirkoworz/remura/actions/runs/44915848764**

- SHA di codice sottoposto a test: `89e1c2d99dcfdfa504af83808b2a3575659b3f72`.
- Ubuntu GitHub public runner + Node.js 22.16.0; nessun Secret, npm install, deploy, API privata o D1 cloud. Workflow one-shot `.github/workflows/remura-contributors-v075-one-shot-ci.yml` con `contents:read`, checkout senza credenziali e filtro sul messaggio esatto.
- `test_private_navigation_v075_lab.mjs`: **30/30 PASS** — attraversamento tra home e livelli, ritorno, permessi server OWNER/collaboratore per le quattro pagine e asset, Access mancante, revoche D1, first-primary, versione, query/path injection, kill switch e protezione della route logout.
- `test_private_assets_v075_lab.mjs`: **20/20 PASS** — byte esatti per 13 sorgenti, generatore deterministico, import closure HTML/ESM per area, header data/ora, collegamento logout, denylist di file estranei.
- Output CI verificato dai log: `# tests 50`, `# pass 50`, `# fail 0`, `# cancelled 0`, `REMURA_V075_PRIVATE_NAVIGATION=50_50_PASS`.
- Prova diretta di `node build_private_assets_v075_lab.mjs --check` passata, e `node --check` del router e composizione passati.
- Non ripetuti 55 casi v0.74, 24 casi v0.70, né le suite storiche v0.66/v0.67.

## GO/NO-GO prima del pilot vero
1. **NO GO** utenti reali, Cloudflare staging o modifiche produzione finché il nuovo flusso `/api/submit` non ha **riconciliazione server-side persistente** dopo risposta persa, reset Safari e doppia scheda. Il vecchio client blocca la risposta incerta soltanto in RAM; il `request_id` viene generato al momento dell'invio.
2. **NO GO** senza Access application/policy e allowlist identità reali, controllo user seats Free, AUD, direct `ctx.access`, logout/revoca effettiva, e prova da browser iPhone reale.
3. La composizione v0.75 è **sintatticamente Worker-friendly ma non dimostrata con build Wrangler né con una richiesta Cloudflare reale**. Prima di staging richiede bundle esplicito, feature switches sicuri e deployment autorizzato.
4. Le pagine dei nuovi livelli sono ancora candidate; non c'è una home privata realmente raggiungibile dai collaboratori sul Web.
5. Verificare quote cloud attuali prima di deploy. Ultimo monitor account read-only verificato: 20/11/2026 https://github.com/mirkoworz/remura/actions/runs/44772218921 (4 D1, circa 6.28 MB, ~417 richieste Workers/giorno); sono metriche parzialmente stimate, non fatturazione. Nessuna spesa nuova.
6. Nessun contributo reale influenza REMURA, Telegram o suggerimenti operativi senza provenance, audit e approvazione OWNER. I dati COT/sentiment/delta rimangono proxy, non evidenza di ordini istituzionali.

## Roadmap complessiva non persa
- **Contributors v0.76:** registro durevole tentativi nuovi livelli, UI di recovery dedicata, esiti certi/incerti, no auto-retry, test multi-tab/reload, revoche e idempotenza; mantenere separato dal journal amendment.
- **Access staging:** Free seats e quote, policy privata, Worker diretto, HMAC Secret, D1 dedicato e test con soli account sintetici dopo autorizzazione specifica.
- **Contributors pilot:** 1–2 amici, consultazione REMURA e proposta dei soli livelli autorizzati; OWNER gestisce approvazione/reiezione, senza accessi di scrittura generali.
- **Experience:** v0.30 LAB, splash toro/orso 3D, esplosione, pinna REMURA, ringraziamento SMF, custodia anti-rollback indipendente non certificata.
- **TradingView:** v0.8.181 LAB, holdout 1 23–29 novembre UTC, holdout 2 30 novembre–6 dicembre UTC; baseline price-only e no leak ex-ante.
- **Shark Science:** v0.4 LAB; COT, sentiment, Delta/CVD, absorption, Effort/Result, con valutazione scientifica senza promesse predittive non dimostrate.
- **Private Capture:** v0.15 LAB solo sintetico. **Ampere Radar:** v0.36 operativo (Oracle Milano). **Oracle collector:** attivo, autoupdater bloccato, package v1.65 staged non installato (NO-GO). Backup, Squalincome, Telegram futuro e security invariati.

**Non serve il Mac per la prossima fase di sviluppo LAB.**
