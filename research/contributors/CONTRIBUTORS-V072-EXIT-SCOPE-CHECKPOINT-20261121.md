# REMURA Contributors v0.72 LAB — PRIVATE ASSET SCOPE + ACCESS EXIT

**21 novembre 2026 · 12:55 CET (Europe/Rome) — CHECKPOINT OPERATIVO**

## Provenienza GitHub
- Repository: mirkoworz/remura.
- Branch dedicato: research/contributors-exit-scope-v072-20261121.
- Base immutata: v0.71 commit 18a0a330a5da9cf4835002e8fecdb78925f1006f.
- Nessun merge su main, nessun deploy, nessun database Cloudflare reale scritto, nessuna identità/Secret reali, nessuna modifica Oracle e nessun costo introdotto.
- Test originali v0.66/v0.67 NON ripetuti.

## Nuovi componenti e stato
1. secure_exit_v072_lab.mjs — coordinatore uscita di sola vista; se lo staging HTTPS autorizzato ha un trasporto attivo, dopo blocco immediato della vista richiede la navigazione same-origin a /cdn-cgi/access/logout. Non afferma mai che il logout provider sia completato. Disabilitato in modalità offline.
2. test_secure_exit_v072_lab.mjs — **20/20 nuovi test PASS localmente** Node.js v22.16; blocco immediato, nessuna seconda navigazione, origin TLS esatto, fail-closed, eccezioni e nessuna conferma falsa.
3. private_worker_router_v072_lab.mjs — clone isolato del router v0.71; gli asset /owner/* sono serviti SOLTANTO a OWNER e /contributors/* SOLTANTO ai CONTRIBUTOR dopo il profilo D1 autenticato. Il nuovo kill switch è PRIVATE_WORKER_V072=OFFLINE_FIXTURE_ONLY, NON il precedente V071. Nessun default export fetch, nessuna attivazione.
4. test_private_scope_v072_lab.mjs — **20/20 nuovi test PASS** Node.js v22.16; separazione statica delle due aree, risposta 403, security headers, CSS/import closure, banner v0.72.
5. recovery_portal_v072_lab.mjs — copia isolata del portale v0.70 con il coordinatore di logout; dopo click invalida epoch della vista impedendo di ridistribuire dati di richieste tardive. L'identità e il ruolo restano verificati solo server-side.
6. contributors_recovery_v072_private_lab.html e contributors_owner_recovery_v072_private_lab.html — due pagine separate per iPhone. Primo elemento visibile: REMURA Contributors v0.72 LAB · 21/11/2026 12:55 CET · STAGING PRIVATO NON ATTIVO; pagina con pulsante Esci dall’area privata. Le pagine **non sono pubblicate**.
7. V072 checkpoint: presente documento.

### Evidenza locale
- Nuove suite v0.72: **40/40 PASS**, zero errori, controllate su esatti byte GitHub SHA blob per ogni file (sha1 Git).
- Nuova prova rendering Chromium statico: **4/4 PASS** a 320, 390, 375 e 768 px, senza overflow orizzontale; solo HTML+CSS, nessun collaudo Safari fisico, nessuna prova CSP su HTTP reale.
- Le immediate 42 prove v0.71 (30 router +12 asset reali) sono state confermate su sorgente locale identica, **42/42 PASS**, per verificare la base; non è stato ripetuto l'insieme storico v0.66/v0.67.
- Suite v0.70 completa di 24 nuovi test integrati contro originali SQL+Access, già salvata su GitHub, **rimane da eseguire**; NON segnarla come PASS. Richiede sorgente completo del repository, non file minimi del bundle locale. Il Mac NON è richiesto per sviluppare le nuove funzioni, e nessun test GitHub Actions è stato attivato.
- Zero autenticazioni Access reali, dati veri, user enrollment, Cloudflare Worker reale o D1 reale impiegati.

## Sicurezza e Provider — limitazioni
- La pagina NON concede il ruolo OWNER. Il router autentica ctx.access da invocazione Worker diretta, calcola i tag via originale accessBinding e verifica il profilo D1 con sessione first-primary; in v0.72 test locale le dipendenze sono mock, non provider.
- I nuovi percorsi statici sono sotto whitelist per la corretta area. L'app Worker non ha una route pubblica autorizzata.
- Cloudflare Access rende disponibile ctx.access solo alla richiesta direttamente autenticata; non si propaga automaticamente via Service Bindings o Worker Static Assets: https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- Cloudflare Access documenta logout <application-domain>/cdn-cgi/access/logout; cancella immediatamente il cookie del browser, ma la revoca di token già emessi può impiegare ~20–30 secondi e il logout vale per più app Access. Non trattare la richiesta di navigazione come attestazione di logout: https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/
- Nessun nuovo collegamento a produzione o modifica della policy Access.

## Verifica reale dei limiti gratuiti (non billing)
Il monitor read-only Cloudflare GitHub run 44772218921 del 20 novembre 2026 (conclusione success) ha riportato:
- REMURA_CF_ACCOUNT_QUOTA=OK, stima D1 letture 196 e scritture 784 nel giorno monitorato; limiti Free 5M righe lette e 100K scritte/giorno.
- REMURA_CF_WORKERS_USAGE=OK, circa 417 richieste/giorno, 0 errori, limite 100K/giorno. Stima GraphQL, NON fatturazione esatta.
- REMURA_D1_TEST_STORAGE=OK, 5.984.256 byte nel DB fixture; singolo DB Free massimo 500.000.000 byte.
- REMURA_D1_ACCOUNT_STORAGE=OK: 4 database, 6.275.072 byte complessivi, limiti Free 10 database e 5.000.000.000 byte.
- GitHub report: https://github.com/mirkoworz/remura/actions/runs/44772218921
- I report delle quote non provano il margine attuale Access, GitHub Actions o Oracle, né garantiscono costo futuro zero. Nessuna spesa autorizzata.

## Prossimi step senza Mac
1. Verificare se possibile ottenere una vera esecuzione del SOLO test v0.70 integrato senza nuovi costi o credenziali; se non verificabile, mantenere NO-GO e non ripetere suite precedenti.
2. Preparare in modo statico (senza deploy) la lista esatta delle configurazioni Cloudflare Access + Worker senza assets router + D1 binding; verificare contatori attuali e app/utenti.
3. Verificare UX logout reale con un solo utente sintetico e revoca per owner, **solo dopo autorizzazione esplicita** per staging reale.
4. Completare il percorso per l'inserimento dei livelli degli amici soltanto dopo audit delle mutazioni idempotenti, revoca, audit OWNER e firma/backup; non presentare l'attuale Recovery Desk come portale di contribuzione completo.

## Roadmap generale preservata
TradingView v0.8.181 LAB (baseline + holdout 23-29/11 e 30/11-06/12 UTC); Shark Science v0.4 LAB; Experience v0.30 LAB splash toro/orso 3D + SMF, controllo custodia; Private Capture v0.15 STOP; Ampere Radar v0.36 operativo; Oracle collector attivo e autoupdater bloccato, pacchetto v1.65 NO-GO; Backup, Squalincome, Telegram contributor futuro dopo approvazione, monitoring dei costi invariati.
