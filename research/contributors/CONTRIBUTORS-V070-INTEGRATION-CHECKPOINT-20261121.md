# REMURA Contributors v0.70 LAB — CONTINUITÀ SICURA + IPHONE CANDIDATE
**21 novembre 2026, 13:10 CET (Europe/Rome) — CHECKPOINT**

## GitHub e isolamento
- Repo: mirkoworz/remura, branch `research/contributors-integration-v070-20261121`.
- Base invariata: v0.69 commit `8c0f0bd94ba4a35da19d51b29569ff00db31a4cd`.
- Nessun merge, deploy, Cloudflare D1 o Access reale, utente reale, Secret, acquisto, modifica Oracle o intervento al collector.
- Le pagine originali v0.67, il backend v0.69 e tutti gli altri filoni rimangono immutati. v0.70 è un candidato separato.

## Nuovi file e stato reale
1. `test_protected_read_integrated_v070_lab.mjs`: **24 prove di integrazione NUOVE SCRITTE** contro il fixture originale `fullstack_fixture_v066_lab.mjs` e l'effettiva composizione v0.69 Access→HMAC→D1 profile→HTTP v0.65. **ESECUZIONE NON ANCORA EFFETTUATA**; non dichiarare 24 PASS. Non ripetere la precedente suite v0.66.
2. `recovery_transport_v070_lab.mjs`: whitelist di tre letture POST same-origin, JSON e CSRF, nessun endpoint di scrittura, ruolo o identità nel browser.
3. `test_recovery_transport_v070_lab.mjs`: **20/20 PASS** su Node.js v22.16 locale; blob SHA verificato identico a GitHub.
4. `recovery_portal_v070_lab.mjs`: copia indipendente del portale v0.67 con bootstrap opzionale di trasporto read-only; accetta SOLO pagina marcata `data-read-bridge=STAGING_CANDIDATE` su HTTPS, non verifica l'identità da sé. Il runtime deve imporre Access lato server.
5. `contributors_recovery_v070_private_lab.html`: pagina iPhone amico (sola lettura / recovery e ricevute), banner primo elemento `REMURA Contributors v0.70 LAB · 21/11/2026 13:10 CET · STAGING PRIVATO NON ATTIVO`.
6. `contributors_owner_recovery_v070_private_lab.html`: pagina OWNER, stessa intestazione versione; ruolo nell'HTML è solo UI, backend verifica ruolo realmente con D1.
7. `CONTRIBUTORS-V070-INTEGRATION-CHECKPOINT-20261121.md`: presente documento.

## Prove realmente eseguite (solo nuovi componenti)
- **20/20 PASS** test unitari di trasporto, senza HTTP reale.
- **6/6 PASS** smoke Chromium con HTML/CSS/JS reale della v0.70, due ruoli e viewport **320, 390, 768 px**. Per ogni scenario: pulsante di lettura attivo, POST solo route prevista, per contributor lettura ricevute, per OWNER coda personale, chiusura della vista disabilita refresh, nessun overflow orizzontale, zero errori JS.
- Harness browser completamente sintetico: perché le navigazioni HTTPS sono bloccate dal runtime, è stato impiegato `page.set_content` e iniezione di bundle JS IIFE delle stesse sorgenti: **solo nel test** sono state sostituite la verifica `location.protocol==='https:'` e `location.origin` con valori fixture; CSP meta rimossa solo per consentire injection e verificare comportamento UI. Pertanto **NON attesta** la vera navigazione HTTPS, verifica CSP, integrazione Cloudflare, token, logout provider né Safari iPhone.
- File generati in ambiente locale a partire dagli originali verificati v0.67, SHA blob Git corrispondenti ai file effettivamente salvati su GitHub.
- **63/63 PASS** confermati localmente per sole nuove suite precedenti v0.68+v0.69. Non ripetuti test storici v0.66/v0.67.
- **24 prove integrate v0.70 non eseguite** perché l'intero substrato SQL e JS originale non è montato nell'ambiente locale corrente. Eseguire solo `node --test research/contributors/test_protected_read_integrated_v070_lab.mjs` da checkout GitHub completo (Mac Codex o runner sintetico autorizzato).

## Security model e NO-GO
- Browser non concede alcuna autorizzazione; `data-role=OWNER` è soltanto una vista, non un privilegio.
- v0.69 strict read bridge usa l'identità da `ctx.access` diretto verificato, il tag HMAC e il profilo D1 in sessione `first-primary`. Il fixture v0.66 era già completato e NON è stato ritestato nella sua suite storica.
- Le tre uniche route sono `/api/amendment/reconcile`, `/api/amendment/mine`, `/owner/amendment/reconcile-queue`. Nessuna mutazione via la nuova UI.
- Il pulsante 'Cancella i dati dalla schermata' **NON è logout reale Cloudflare Access**. Implementare e verificare logout autentico prima del primo collaboratore.
- Le due pagine candidate **NON SONO PUBBLICATE**. No live identities, Cloudflare Workers e D1 non collegati, test con utenti reali non eseguiti, nessun Access/JWT certificato.
- Cloudflare Free plausibile secondo limiti ufficiali; **margine effettivo NON MISURATO**. Verificare dashboard Access, Workers, D1, GitHub Actions, eventuale quota Oracle prima di staging.
- PR, deployment, binding/secret reali, migrazione, attivazione dati, nuova spesa, pubblicazione Telegram, installazione Oracle v1.65 o merge main richiedono nuove autorizzazioni esplicite.

## Roadmap immediata
1. Eseguire **soltanto** le nuove 24 prove v0.70 con fixture originale dal repository completo; correggere eventuali errori, non anticipare un PASS.
2. Implementare gate Access diretto Worker con audience, account, identità attiva, consent list e session invalidation; non assumere `ctx.access` su asset statici o service bindings.
3. Misurare quota gratuita residua e numero database; confermare quali D1 sono LAB/fixture.
4. In ambiente staging privato autorizzato, testare reale identità sintetica, blocco OWNER, logout, CSP HTTP, rate limiter, revoca, primary D1.
5. Solo dopo, pilot ristretto amici, inserimento di livelli autorizzati separato da vista di recupero e revisione OWNER, poi Telegram post approvazione.

## Filoni preservati
- TradingView v0.8.181 LAB — baseline e holdout 23–29/11 e 30/11–06/12 UTC.
- Shark Science v0.4 LAB — COT/sentiment/delta senza promesse su edge predittivo non dimostrato.
- Experience v0.30 LAB — splash toro/orso 3D, esplosione, pinna, ringraziamento SMF, custodia.
- Private Capture v0.15 LAB — STOP ingestione reale.
- Ampere Radar v0.36 operativo — Oracle Milano in attesa disponibilità gratis.
- Oracle collector attivo, autoupdater bloccato, v1.65 staging NO-GO.
- Backup, Squalincome, Telegram contributors futuro, sicurezza e roadmap generale invariati.
