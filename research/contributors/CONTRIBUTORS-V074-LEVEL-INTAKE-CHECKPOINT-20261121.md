# REMURA Contributors v0.74 LAB — INSERIMENTO LIVELLI + DESK OWNER

**Checkpoint: 21 novembre 2026, 15:43 CET (Europe/Rome)**

## Provenienza GitHub e stato reale
- Repository: `mirkoworz/remura` (**pubblico**); branch isolato: `research/contributors-level-intake-v074-20261121`.
- Base preservata: Contributors v0.73 `776a58c7a50bfdcd05952be0dc7f280d2f040d5a`.
- La v0.74 implementa un **nuovo livello originale proposto da collaboratore**, NON una `amendment`/correzione. I due flussi non sono equivalenti e non vanno mescolati.
- Nessun merge su `main`, deploy, risorsa Cloudflare, migrazione, login reale, Secret reale, spesa, modifica Oracle o Telegram reale.
- UI di recupero e coda amendment ancora v0.72; le due **nuove** pagine livelli sono v0.74 e hanno banner versione/timestamp in alto.

## Nuovi componenti riusando il codice storico
- `contributors_levels_v074_lab.html` — pagina iPhone «Proponi un livello», con catalogo strumento/provider/ticker/prodotto, periodo, metodologia, prezzo, anchor UTC, osservazione UTC, nota, ricevute personali. Dati di esempio soltanto e backend disattivato.
- `owner_levels_v074_lab.html` — desk OWNER separato con registro, decisioni esplicite APPROVED/REJECTED/REVOKED, cronologia privata. Il ruolo UI non concede privilegi backend.
- `contributors_levels_v074_lab.css` — CSS responsive da asset esistente; `contributors_levels_ui_v074_lab.mjs` — riuso UI originale v0.31, con ulteriore conferma esplicita prima di invio e spiegazione che «ricevuta» NON è approvazione.
- `level_api_gate_v074_lab.mjs` — perimetro di ruolo API, same-origin, POST, CSRF, audience Access runtime, profilo server D1, whitelist di 8 path e blocco headers di impersonazione. L'intent HMAC viene limitato a 4096 byte e il target viene verificato secondo il ruolo autorizzato; body grande non può bloccare il runtime su stream tee. Server originale ricontrolla identità, generazione, permesso, rate limiting e consumo token HMAC.
- `private_worker_router_v074_lab.mjs` — percorsi UI separati `/contributors/levels/` e `/owner/levels/`, stessi asset serviti sotto prefisso di ruolo; GET/POST controllati lato server in stile v0.72.
- `private_levels_composition_v074_lab.mjs` — solo orchestrazione LAB: riusa `accessBinding`, `d1_access_candidate.profile`, `http_access_candidate.candidateRequest`, `protectedReadCandidateV069`. Usa `node:fs` per caricare asset locali: **NON è un Worker pronto al deploy**, serve un futuro bundle statico verificato.
- Test nuovi: `test_level_api_gate_v074_lab.mjs` (35 casi) e `test_level_fullstack_v074_lab.mjs` (20 casi). Non sono stati rieseguiti i test storici v0.66/v0.67 né il collaudo v0.70 24/24.
- Workflow GitHub una tantum: `.github/workflows/remura-contributors-v074-one-shot-ci.yml`; solo push su branch isolato, solo modifica workflow con messaggio pinned, `permissions: contents:read`, `persist-credentials:false`, runner Ubuntu pubblico gratuito, Node 22.16, nessun secret o cloud.

## Prova verificata sul runner reale GitHub con dati sintetici
**SUCCESS: https://github.com/mirkoworz/remura/actions/runs/44915244674**

- SHA testato: `b2c5bcf9c785ac1890e9a51d0f290c8017c2b1b8`.
- Log attestato: `# tests 55`, `# pass 55`, `# fail 0`, `# cancelled 0`, marker `REMURA_V074_LEVEL_ENTRY=55_55_PASS`.
- **35/35 nuovi test di gate**: contributore vs OWNER, preflight CSRF+Origin, validazione intent, dimensione JSON, client actor/role injection, switch disabilitato, profilo e risposta no-store.
- **20/20 nuovi test di integrazione reale con fixture in memoria**: rendering delle pagine private dal router, asset scope, profilo Access + HMAC, catalogo D1, ricevute partizionate Alice/Bob, nuovo livello EURUSD sintetico → intent → insert → ricevuta personale → queue OWNER → APPROVED → ricevuta aggiornata, replay nonce, revoche, D1 first-primary, limiter, kill switches.
- Primo run 44915161198: **48 PASS / 1 FAIL / 6 cancellati**; causa tecnica identificata in `await reader.cancel()` su request clone tee con body >4KB, più aspettativa errata `403` anziché risposta rate limit `429`. Corrette solo gestione bounded stream e aspettativa test, senza cambiare le regole di autorizzazione. Secondo run SUCCESS sopra: **55/55**.
- Questo test non prova un utente Access reale, una vera D1 Cloudflare, transazioni distribuite, né compatibilità su Safari iPhone fisico.

## Sicurezza, rischi bloccanti e spese
1. `LEVEL_HTTP_V074=OFFLINE_FIXTURE_ONLY` e `PRIVATE_WORKER_V074=OFFLINE_FIXTURE_ONLY` sono richiesti; l'intera composizione **NON è esposta** da Worker `default fetch` né configurata in Wrangler. Non attivare in real stage; queste etichette sono consapevolmente impossibili da interpretare come GO produzione.
2. Il vecchio `CandidateClient` tiene il blocco di esito incerto soltanto in RAM: refresh o seconda scheda possono perdere il contesto, benché il nonce server sia bruciato e il `request_id` sia idempotente quando riutilizzato. **NO-GO per invio reale** finché non esiste una riconciliazione durevole server-side per l'ingresso originale e test di due schede/reload iPhone.
3. Le due fasi `intent` + `submit` non sono un'unica transazione. Non avviare retry automatici su 409 o risposta persa.
4. Il ruolo proviene dall'identità Access del Worker diretto e dal profilo D1, non dalla pagina; i file sono segregati per percorso e i dati personali non vengono inseriti in GitHub.
5. Il modulo Node-only `private_levels_composition_v074_lab.mjs` dovrà essere sostituito da un bundle Worker compatibile, con asset immutabili e CSP verificata su hosting reale. Il link a `/cdn-cgi/access/logout` nella UI v0.72 è solo navigazione richiesta e NON prova revoca.
6. Repository **pubblico**: no email, UUID, token, HMAC key, prezzi riservati, identità e log di clienti reali nei commit. Isolare qualunque provisioning.
7. Ultima quota Cloudflare monitorata con run https://github.com/mirkoworz/remura/actions/runs/44772218921 del 20/11: 4 D1, 6,275MB storage, stima 417 richieste Workers, letture ~196 e scritture ~784 nel giorno. Access Free seats, uso corrente e fatturazione non verificati. Nessuna spesa autorizzata.
8. Non è presente alcun collegamento a Telegram: futuro invio formattato solo dopo approvazione OWNER e attivazione autorizzata.

## Roadmap senza Mac — il percorso più corto al pilot privato
1. In v0.75, rendere navigabile l'area `/contributors/` e `/owner/` alle nuove pagine livello, con versioni/timestamp coerenti e home sicura dopo login.
2. Produrre manifest di asset immutabili + bundle Worker compilabile in LAB senza `node:fs`, senza deploy.
3. Rinforzare il flusso «nuovo livello» con registro tentativi persistente, recupero dopo refresh/dual tab/lost response e verifica dell'assenza di invii doppi. Non riutilizzare impropriamente il ledger delle `amendment`.
4. Rilevare budget Cloudflare Free e Access seats, completare piano allowlist / identità Google, logout, revoca; poi chiedere autorizzazione specifica per staging Access + D1 con fixture separato e test su iPhone.
5. Primo pilot 1–2 collaboratori reali **solo dopo** i gate; abilitarli a leggere REMURA e proporre solo i livelli del proprio slot, senza scrivere altrove; OWNER revisiona, mantiene audit e controllo pubblicazione.
6. Filoni TradingView, Shark Science, Experience, Private Capture, Ampere/Oracle, backup, Squalincome e Telegram mantenuti in roadmap: COT/sentiment/delta sono proxy e non provano informazioni istituzionali o edge predittivo.

## Filoni e checkpoint preservati
- TradingView v0.8.181 LAB: protocollo congelato e holdout 1 23–29/11 UTC, holdout 2 30/11–6/12 UTC; no nuovi parametri senza ex-ante validation.
- Shark Science v0.4 LAB: ricerca COT, sentimento retail, Delta/CVD, Effort/Result, absorption e divergenze, senza promesse di riconoscere le intenzioni degli istituzionali.
- Experience v0.30 LAB: splash toro/orso 3D, collisione, esplosione, REMURA pinna e ringraziamento SMF, custodia da certificare.
- Private Capture v0.15 LAB fermo; Ampere Radar v0.36 attivo; Oracle collector operativo con autoupdater bloccato e pacchetto v1.65 non installato; backup, Squalincome e Telegram futuro invariati.
