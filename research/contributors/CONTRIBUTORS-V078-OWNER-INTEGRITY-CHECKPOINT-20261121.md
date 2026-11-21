# REMURA Contributors v0.78 LAB — OWNER INTEGRITY + FREE STAGING NO-GO

**Checkpoint: 21 novembre 2026, ore 17:02 CET (Europe/Rome)**

## Identificatori immutabili e risultato realmente eseguito
- Repository **pubblico**: `mirkoworz/remura`.
- Branch LAB nuovo: `research/contributors-owner-integrity-v078-20261121`.
- Base v0.77: `ecab6f33d22e2c48fdb071db86c8cc0e3c125ffa`. `main` non modificato.
- GitHub Actions con dati sintetici: https://github.com/mirkoworz/remura/actions/runs/44922091303
- Commit esatto sottoposto a test: `7a073c80f0bc1f99952fbf8776bba5cd48a27fa5`.
- **50/50 nuovi test PASS, 0 FAIL, 0 CANCELLED**; log `REMURA_V078_OWNER_INTEGRITY=50_50_PASS`.
- 30 test nuovi su OWNER integrity, stale evidence, due attestazioni indipendenti, response lost AFTER append, due nonce concorrenti, revoca OWNER durante query, Access, generazione, CSRF, primary, read-only e divieto release.
- 20 test nuovi su sorgenti byte-identici, quattro banner, dependency closure, owner-only UI, nessun endpoint release/reset. Nessuna ripetizione delle suite precedenti v0.77 (56/56), v0.76 (64/64), v0.75 (50/50), v0.74 (55/55), v0.70 (24/24).
- Hash SHA256 asset manifest `6052f5711a29c16a3a2f92a346bfdd663e0e9fd7ccaf483c07b5362e144d2916`, 15/15 byte source match.
- Run diagnostico iniziale `44922014665`: fallito PRIMA di avviare la suite di integrazione completa, per import rimasti con suffisso v0.77 e un errore di sintassi nel test di revoca a metà lettura. Correzioni applicate ai **soli nuovi** file; successivo run sopra 50/50 GREEN.
- Nessun Secrets Cloudflare, deploy, Wrangler live, D1 cloud, Access real identity, modifica Oracle, merge, spese.

## Nuovo codice v0.78
- `owner_level_integrity_v078_lab.mjs`: sola lettura OWNER su tentativi ORIGINALI ancora RESERVED, non sulle correzioni. Accede a D1 `withSession('first-primary')`, filtra per stato e prova in SQL la permission OWNER attuale; controlla i permessi **prima e dopo** il SELECT per ridurre rischio revoca durante query. Max 20 righe; `after` cursor monotono; no `UPDATE`, `INSERT` o `DELETE`.
- Condizioni esplicite: `NOT_OBSERVED_UNATTESTED`, `ABSENCE_SNAPSHOT_ONLY`, `RECEIPT_FOUND_UNATTESTED`, `RECEIPT_ATTESTED_LOCKED`, `EVIDENCE_CHANGED_NEEDS_OWNER`, `INCONSISTENT_EVIDENCE`. Anche `RECEIPT_ATTESTED_LOCKED` non autorizza un nuovo submit. L'assenza osservata in passato **NON** è una prova definitiva di inesistenza.
- `owner_level_audit_http_v078_lab.mjs`: mantiene i quattro endpoint OWNER firmati v0.77 e aggiunge solo `POST /owner/new-level/integrity` con body `{after:0}`; stesso TLS/origin, Access AUD, HMAC subject, CSRF, rate limit, D1 OWNER e no-store. V0.78 richiede anche l'esplicito `OWNER_INTEGRITY_V078=OFFLINE_FIXTURE_ONLY`.
- `owner_level_integrity_ui_v078_lab.mjs`: nuova diagnostica OWNER iPhone, contenuto mostrato con `textContent`, nessun ritentativo o modifica, segnala soprattutto ricevuta comparsa dopo una vecchia attestazione di assenza; nessun codice release, reset, delete o approvazione automatica.
- `private_worker_router_v078_lab.mjs`: aggiunge il percorso API e rende lo script diagnostico disponibile SOLO a ruolo OWNER in `/owner/levels/`; blocca Contributor, recovery e risorse fuori lista.
- `private_levels_composition_v078_lab.mjs`: composizione con v0.76 durable submission + v0.77 audit owner + v0.78 integrity reader; nessun default `fetch`/Worker pubblicato; ES module senza Node runtime.
- Quattro pagine LAB nuove in cima con versione **v0.78 LAB · 21/11/2026 16:56 CET**: `contributors_recovery_v078_private_lab.html`, `contributors_owner_recovery_v078_private_lab.html`, `contributors_levels_v078_lab.html`, `owner_levels_v078_lab.html`.
- `build_private_assets_v078_lab.mjs` + `private_assets_v078_lab.mjs`: embedding offline deterministico 15 file; no import Node nel Worker.

## Verifiche fault-injection indipendenti
- OWNER può riportare `RECEIPT_NOT_OBSERVED`; poi un livello compare nel fixture DB: il lettore ora espone `EVIDENCE_CHANGED_NEEDS_OWNER` invece di persistere una rappresentazione di assenza definitiva.
- Due attestazioni successive con evidenza distinta conservano **due righe append-only** (e la cronologia), senza cambiare `RESERVED`.
- Due attestazioni concorrenti con nonce validi non possono duplicare la stessa `(subject,request_id,classification)`.
- Il DB ha scritto l'audit ma la risposta HTTP si perde: status 409/unknown; il token consumato non viene riutilizzato, l'audit esiste e il nuovo lettore mostra lo stato corretto.
- Revoca OWNER immediatamente **dopo il SELECT**: seconda verifica primaria nega l'output.
- Reader non modifica numero tentativi, audit, righe `lab_entries` o nonce.

## Audit delle quote Free (NOVITÀ IMPORTANTE)
- GitHub budget quotidiano **21/11/2026**: https://github.com/mirkoworz/remura/actions/runs/44919682812 — **FAIL / INCOMPLETE** dovuto a `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`; righe D1 read/write giornaliere **NON MISURATE**. NON dichiarare Free account completamente attestato.
- Stesso report: Workers `OK`, **stima 199 richieste** al 21/11 UTC, 0 errori; D1 fixture storage **6.266.880 byte**, 1,2534% singolo limite; account **4 database e 6.557.696 byte totali** su 5.000.000.000 nominali.
- Ultimo run Cloudflare D1 analytics GREEN `44772218921` del 20/11; i valori del giorno precedente NON sostituiscono quelli mancanti oggi.
- Cloudflare ha **reso obbligatorio il rispetto del limite D1 Free giornaliero dal 01/09/2026**; query falliscono se superato: https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/
- Workers Free nominale 100.000 richieste/giorno; D1 Free storage totale 5 GB, max 10 DB e quota righe lettura/scrittura. Fonti ufficiali: https://developers.cloudflare.com/workers/platform/pricing/ e https://developers.cloudflare.com/d1/platform/pricing/ e https://developers.cloudflare.com/d1/platform/limits/
- Access Free fino a 50 utenti nominali: **seats effettivi non verificati**. https://www.cloudflare.com/plans/zero-trust-services/
- La recente anomalia GraphQL NON dimostra uno sforamento né una spesa; il problema è **mancanza evidenza**, quindi applicare NO-GO per staging reale e monitorare.

## Piano staging reversibile (solo testo, nessuna esecuzione)
File: `CONTRIBUTORS-V078-FREE-STAGING-GATES-20261121.md` su questo branch.
- Prima di ogni attivazione: quote D1 giornaliere verificate, Free seats Access realmente disponibili, policy allowlist, DB staging isolato e backup, HMAC Secrets fuori GitHub, Worker diretto same-origin con `ctx.access`, audit di logout e revoca, Safari iPhone e rollback.
- Restrizione Cloudflare: `ctx.access` non passa automaticamente via Service Bindings o Static Assets router. Fonte: https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- Nessuna produzione/deploy/merge/D1 nuova/spesa autorizzata in questo turno.

## Stato roadmap globale
1. **Prossimo Contributors v0.79 LAB**: diagnosi in sola lettura del workflow Cloudflare monitor `UNKNOWN_NO_GRAPHQL_DATA`, fallback sicuro per quote Free e verifica indipendente dei byte della configurazione staging; non riavviare suite già GREEN.
2. Staging privato Cloudflare solo con consenso specifico dopo recupero metriche; Access Free, D1 isolato e cancelli fail-closed.
3. Pilot massimo 1–2 collaboratori dopo login e D1 reali verificati, ruolo read-only per REMURA generale e POST dei soli propri livelli; OWNER controlla/approva e mantiene audit; Telegram solo contenuti approvati.
4. TradingView v0.8.181 LAB: holdout1 23–29/11 UTC; holdout2 30/11–06/12 UTC. Nessuna pretesa di edge scientifico prima di test out-of-sample.
5. Shark Science v0.4 LAB, Experience v0.30 LAB splash toro/orso + REMURA SMF, Private Capture v0.15 STOP, Ampere Radar v0.36 operativo, Oracle collector attivo/autoupdater bloccato, v1.65 staging root-owned **NO-GO install**, backup e Squalincome invariati.

## Ambito di sicurezza
- Repository pubblico, quindi vietato caricare qualsiasi identificativo reale, token, chiave, telefono, e-mail o dato di mercato proprietario.
- L'audit DB è append-only contro i permessi di applicazione e i trigger SQL. Non rende impossibile la manomissione da parte di un amministratore DB privilegiato.
- Versione v0.78 è **LAB**; zero accesso pubblico reale o elaborazioni dati istituzionali attivate. Nessun Mac necessario.
