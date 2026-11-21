# REMURA Contributors v0.77 LAB — OWNER EVIDENCE AUDIT / NO-RELEASE

**Checkpoint: 21 novembre 2026, ore 16:52 CET (Europe/Rome)**

## Stato verificato / GitHub
- Repository: `mirkoworz/remura` (**pubblico**), branch isolato: `research/contributors-owner-audit-v077-20261121`.
- Base v0.76 preservata: `efe4f2236efd959f178250d7061931db58c1e306`.
- Codice v0.77 CI-verificato: `b60a4b999f7c9db57c31f7acb2ade190cdceb43b`.
- GitHub Actions run conclusivo GREEN: https://github.com/mirkoworz/remura/actions/runs/44921359254
- Runner pubblico GitHub-hosted Ubuntu/Node 22.16.0, D1 SQLite in memoria, **nessuna credenziale/Secret Cloudflare**, npm install, chiamata esterna, deploy o merge main.
- In tutte e quattro le pagine private v0.77 il banner in alto riporta `v0.77 LAB · 21/11/2026 16:44 CET`. Si tratta dell'ora d'inizio di aggiornamento; il checkpoint finale è alle 16:52 CET.
- **Nessuna modifica a Oracle, collector, autoupdater, produzione, D1/Access veri, Telegram, captazione reale, servizi a pagamento.**

## Cosa è stato costruito
1. `new_level_owner_audit_v077_lab.sql` è un **overlay additivo vuoto LAB** per audit OWNER dei tentativi di **nuovi livelli**, indipendente dall'audit delle correzioni/amendments. Le righe di `lab_new_level_owner_audit_v077` sono append-only (trigger NO UPDATE/DELETE), con unico evento per `(subject,request_id,classification)`, ruolo OWNER non revocato, `lab_state.read_enabled/recovery_enabled`, verifica ricevuta originale e riferimento a `lab_new_level_attempts` ancora RESERVED.
2. Classificazioni **`RECEIPT_FOUND`** se esiste la entry originale per lo stesso subject/request_id e receipt_id, oppure **`RECEIPT_NOT_OBSERVED`** per un'osservazione puntuale di assenza: non è prova permanente di inesistenza. Una ricevuta che appare tra consultazione e firma rende la seconda osservazione non valida; DB fail-closed.
3. `owner_level_audit_v077_lab.mjs`: coda OWNER paginata di tentativi RESERVED, confronto su D1 primary, storico append-only, motivo obbligatorio, intento HMAC legato a OWNER/tag/generazione/body/nonce/scadenza 90s e consumo monouso del nonce nell'immutabile `lab_intent_used`. Burn-before-audit: se si perde la risposta, **NON** si ritenta automaticamente.
4. `owner_level_audit_http_v077_lab.mjs`: quattro POST strettamente limitati: `/owner/new-level/pending` con `{after:0}`, `/owner/new-level/history` con `{after:0}`, `/owner/new-level/audit-intent` con `{body:{...}}`, e `/owner/new-level/attest` con body firmato e header `X-Remura-Intent`. Access ctx diretto, AUD, Origin + same-origin + CSRF + JSON 4KB, profilo D1 OWNER can_read/can_recover, rate limit, no-store.
5. `owner_level_audit_ui_v077_lab.mjs`: pagina iPhone OWNER ora mostra tentativi sospesi, ricevuta osservata, storico e pulsante esplicito «Registra osservazione OWNER (irreversibile)»; conferma dell'operatore, visualizzazione via textContent, nessun LocalStorage o auto-retry. La vista blocca ulteriori attestazioni durante esiti incerti; ricaricare la lista **NON** riabilita l'attestazione nella sessione.
6. `private_worker_router_v077_lab.mjs`: vecchia separazione Access/D1 e RECOVERY/LEVELS preservata; il modulo JS di verifica è reperibile **solo** dall'area `/owner/levels/` autenticata OWNER, non da `/contributors/levels/`. Nuove API owner protette da callback indipendente.
7. `private_levels_composition_v077_lab.mjs`: composizione ES Worker-friendly di Access binding+profilo D1+ v0.76 durable levels + v0.77 OWNER audit + vecchio protected amendment read, con 14 asset immutabili, **senza default fetch / deploy / Wrangler config**.
8. Pagine `contributors_recovery_v077_private_lab.html`, `contributors_owner_recovery_v077_private_lab.html`, `contributors_levels_v077_lab.html`, `owner_levels_v077_lab.html`: tutte riportano versione+data in cima. L'interfaccia di verifica appare **solo** nella pagina OWNER livelli, non nelle pagine degli amici.
9. `build_private_assets_v077_lab.mjs`, `private_assets_v077_lab.mjs`: bundle deterministico con 14 file esatti, verifica hash SHA-256 del manifest contro gli originali.

## Test realmente eseguiti (NON ripetere gli storici)
**Run GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44921359254 — SUCCESS**
- `test_owner_level_audit_v077_lab.mjs`: **38/38 PASS** — accesso OWNER vs Contributor, rivendicazione RESERVED senza prova di assenza definitiva, evidenza reale SQL, firma HMAC, nonce burn, idempotenza e UNIQUE, audit impossibile da UPDATE/DELETE, revoche, primary metadata, confusione with amendment, 409 su risposta persa, audit non approva e non sblocca.
- `test_owner_audit_assets_v077_lab.mjs`: **18/18 PASS** — corrispondenza byte per 14 asset, version/timestamp visibile, UI OWNER-only, assenza percorsi release/reset/retry, builder deterministico e senza `node:fs` nel runtime.
- Log verificato: `# tests 56`, `# pass 56`, `# fail 0`, `# cancelled 0`, `REMURA_V077_OWNER_AUDIT=56_56_PASS`.
- Asset build `REMURA_V077_ASSETS=14_MATCH`, SHA256 `3e2036692d07ebbee50483c2339a2e71593b3e7fb14b95d28e80de57fdb2fdef`.
- Non sono state rieseguite le suite preesistenti v0.76 64/64, v0.75 50/50, v0.74 55/55, v0.70 24/24 o v0.66/v0.67.

## Stati e confini di rischio
- Nella v0.76, un nuovo livello può stare in `NO_ATTEMPT`, `UNRESOLVED`, `COMMITTED_NEEDS_OWNER`, `COMMITTED`. L'OWNER in v0.77 osserva i primi due casi `RESERVED` e non autorizza un nuovo submit.
- Un audit v0.77 **NON cambia** `lab_new_level_attempts.state`, **NON** elimina RESERVED, **NON** approva `lab_entries`, **NON** modifica i contributi e **NON** fa transitare alcun dato sintetico verso REMURA principale.
- **Non è stata implementata una procedura di sblocco dell'invio**: per ora serve un protocollo separato, formalmente verificato, con evidence pin, backup, revisione e consenso prima di concedere una seconda proposta. Questo è il comportamento fail-closed desiderato.
- Il registro è append-only sul piano di applicazione/trigger; un amministratore DB privilegiato resta fuori da questo modello di minaccia. Non presentarlo come impossibilità crittografica assoluta di cambiare dati.
- Non è stato eseguito un test reale Cloudflare D1/Access/JWT, Safari fisico, quota Cloudflare Access Seats, verifica deploy, session/logout provider o recovery dopo disconnessione reale. **NO GO staging o collaboratori reali senza ulteriori verifiche e autorizzazione specifica**.
- Repo pubblico: non committare credenziali, HMAC segreti, PIN, nomi utenti/email reali, dati mercato privati o chiavi Cloudflare.

## Roadmap prossimi passi (senza Mac)
1. **Contributors v0.78 LAB**: audit di fault-injection aggiuntivo su interruzione fra burn HMAC e append evento, concorrenza OWNER, invalidazione per revoca durante la richiesta, paging e multi-attestation con evidenza cambiata. Piattaforma sempre offline.
2. Preparare **un piano staging Cloudflare Free reversibile**: account Access Free seats/policy allowlist, Worker diretto same-origin che non richiede Static Assets propagati, D1 fixture isolato, zero Secret nei file, un solo utente test e verifica quota attuale. Chiedere consenso esplicito prima di deploy, binding, migrazioni o enrollment.
3. Testare su Safari iPhone fisico dopo consenso: login/logout autentici, form submit perso, due schede, revoca OWNER, primary D1, rapporto rate limit, coda, restore e rollback.
4. Pilot privato 1–2 collaboratori **solo dopo** audit e controlli sicurezza: lettura generale REMURA consentita ma solo proposta livelli dello slot; OWNER revisiona e solo approvati possono diventare segnali pubblicabili o notifiche Telegram.
5. Monitor economico: ultimo report Cloudflare account read-only GitHub run `44772218921` del 20/11: 4 D1, 6,28 MB di storage e consumo Workers basso. Non equivale al budget attuale o agli utenti Access Free; nessuna spesa autorizzata.

## Filoni preservati, nessuna falsa promessa
- TradingView v0.8.181 LAB, holdout 1 **23–29 novembre UTC**, holdout 2 **30 novembre–6 dicembre UTC**. Prima di questi non affermare di avere un edge scientifico.
- Shark Science v0.4 LAB: COT, sentiment retail, delta/CVD, assorbimento ed effort/result sono proxy di comportamento, non accesso a ordini privati istituzionali.
- Experience v0.30 LAB, splash toro/orso 3D, esplosione, REMURA pinna + ringraziamento SMF, gestione custodia.
- Private Capture v0.15 LAB STOP; Ampere Radar v0.36 operativo; Oracle collector attivo, autoupdater bloccato, pacchetto v1.65 staged e non installato, backup, Squalincome e Telegram futuro invariati.

**Checkpoint completo, nessun Mac necessario per proseguire.**
