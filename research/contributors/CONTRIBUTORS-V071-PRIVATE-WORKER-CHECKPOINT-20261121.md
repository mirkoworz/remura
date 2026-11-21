# REMURA Contributors v0.71 LAB — DIRECT PRIVATE WORKER ROUTER
**21 novembre 2026 · 12:42 CET (Europe/Rome) — CHECKPOINT ISOLATO**

## GitHub e custodia
- Repo privato: mirkoworz/remura; branch: research/contributors-private-worker-v071-20261121.
- Base intatta: v0.70 commit e5d14ee33e78f66af756347c7dcf33e8729c2028.
- Nessun merge main, deploy, Worker reale, Access reale, D1 reale, configurazione Wrangler attivata, migrazione, utente reale, Secret, acquisto, modifica Oracle o download dati finanziari.
- Pagine v0.71 con banner in cima: REMURA Contributors v0.71 LAB · 21/11/2026 12:42 CET · STAGING PRIVATO NON ATTIVO.

## Cosa è stato implementato
1. private_worker_router_v071_lab.mjs — router candidato INERTE senza default export: solo GET /contributors/ per CONTRIBUTOR, GET /owner/ per OWNER, cinque asset JS/CSS per i percorsi autorizzati, e tre POST di lettura delegati al bridge v0.69. Tutti gli altri percorsi negati. Ogni GET richiede ctx.access con AUD corretto, identità actor HMAC da funzione trusted e profilo D1 autorizzato, con fail-closed. Non riceve il ruolo dal browser. Invia CSP, no-store, X-Frame-Options, nosniff e nessuna intestazione CORS. Ammesso esclusivamente con PRIVATE_WORKER_V071=OFFLINE_FIXTURE_ONLY e STAGING_ENABLED=D1_CANDIDATE.
2. contributors_recovery_v071_private_lab.html — vista amico read-only, timestamp aggiornato, NON pubblicata.
3. contributors_owner_recovery_v071_private_lab.html — vista OWNER read-only, timestamp aggiornato, NON pubblicata.
4. test_private_worker_router_v071_lab.mjs — **30/30 PASS** Node v22.16 locale, usando solo identità e ruoli sintetici; byte blob locale identico a GitHub.
5. test_private_asset_integration_v071_lab.mjs — **12/12 PASS** Node locale, usando byte ORIGINALI dei file UI v0.70 e HTML v0.71 verificati tramite SHA GitHub. Controlla contenuti esatti, import JavaScript, percorsi CSS, CSP, versione, accesso OWNER, assenza CORS/no-store.
6. run_v070_unfinished_integration_v071_lab.sh — solo runner offline per i **24 test v0.70 ancora non eseguiti**. Niente vecchie suite, npm install, deploy, network o spese. Bash sintatticamente verificato in locale; blob sorgente identico a GitHub.

### Distinzione delle prove
- v0.71 NEW: **42/42 TEST PASS** locali (30 router mock + 12 asset integrati con byte reali). Eseguiti con:
  node --test research/contributors/test_private_worker_router_v071_lab.mjs research/contributors/test_private_asset_integration_v071_lab.mjs
- v0.70: test_recovery_transport_v070_lab.mjs **20/20 PASS**, browser synthetic 6/6 PASS precedenti, non ripetuti ora.
- v0.69/v0.68: **63/63 PASS** nei checkpoint precedenti; non ripetuti ora.
- **24 prove v0.70 contro il fixture SQLite originale: PENDING/NOT RUN**. Non spacciarle per superate.
- Nessun test reale Apple Safari, GitHub Actions appena eseguito, Cloudflare Access o D1 reale.

## Vincolo Cloudflare ufficiale (verificato 21 novembre 2026)
- Direct Worker con Cloudflare Access: ctx.access è disponibile dopo autenticazione.
- Worker Static Assets/router e Service Bindings NON propagano il medesimo ctx.access; perciò il candidato v0.71 propone un Worker diretto per pagine, JS/CSS e API, senza router Static Assets.
- Docs: https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- Logout Cloudflare: /cdn-cgi/access/logout revoca la sessione, ma l'invalidazione token può impiegare 20–30 s; bloccare subito la UI, fermare richieste pendenti e verificare revoca server. Logout reale NON implementato.
- Docs: https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/

## Come chiudere i 24 test v0.70 dal Mac Codex, una volta sola
Usare worktree isolato, NON modificare il working tree attivo, NON rifare i test v0.66/v0.67:
```bash
git fetch origin research/contributors-private-worker-v071-20261121
git worktree add --detach /tmp/remura-v071-integration-check origin/research/contributors-private-worker-v071-20261121
cd /tmp/remura-v071-integration-check
bash research/contributors/run_v070_unfinished_integration_v071_lab.sh
```
Raccogliere log e SHA HEAD, correggere soltanto eventuali errori attuali. Poi rimuovere il worktree TEMP solo quando non serve più; nessuna modifica main.

## Gratis e autorizzazioni
- Cloudflare Access Free fino a 50 utenti, Workers Free 100.000 richieste/giorno, D1 Free 5M righe lette e 100k scritte/giorno, 5GB complessivi e 10 DB nel piano gratuito (verificare pagina prezzi aggiornata prima di usare).
- **Non sappiamo il consumo effettivo del suo account e il numero di DB residui.** Nessuna telemetria cloud reale interrogata. Non asserire 'sotto soglia gratis' sulla base del solo pricing.
- Prima del deployment servono verifiche quota e autorizzazione separata per Access application, Worker, rotte, D1, chiavi, dati veri e amici; sempre primo approccio gratis.
- Per il futuro login Access e backend devono essere realmente verificati; non usare la sola etichetta data-role=OWNER nella HTML come permesso.
- Possibile costo lato Worker (richieste/CPU) e D1 (letture per asset) da misurare; nessun carico reale generato da v0.71.

## Roadmap futura
A. Eseguire una volta i 24 test v0.70, non retrocedere.
B. Preparare build-time embedding degli asset e un SOLO Worker diretto senza static assets e senza entrypoint attivo (per ora candidati).
C. Verificare Cloudflare Zero Trust allowlist, IdP, D1 LAB, budget reale, sessioni/logout/revoca.
D. Ottenere consenso esplicito per staging privato e test veri; poi pilot di collaboratori reali.
E. Abilitare il contributo di livelli con autorizzazioni server-side e revisione OWNER distinta dal recupero, senza invio automatico; Telegram soltanto dopo approvazione.
F. Mantenere inalterati gli altri filoni: TradingView v0.8.181 LAB, Shark Science v0.4 LAB, Experience v0.30 LAB (splash toro/orso 3D e SMF), Private Capture v0.15 LAB STOP, Ampere Radar v0.36 operativo, Oracle collector attivo e autoupdater bloccato v1.65 NO-GO, backup e Squalincome.
