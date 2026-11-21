# REMURA Contributors v0.61 LAB — checkpoint di integrazione offline
**Versione v0.61 LAB · 21 novembre 2026, 09:24 CET (Europe/Rome)**

## Provenienza, branch e integrità
- Repository: mirkoworz/remura; branch isolato **research/contributors-adapter-v061-20261121** creato dalla v0.60 @ **c33bbaa5fd766f3e4a75991dab0bc59eb1010666**.
- **Nuovo** research/contributors/amendment_adapter_v061_lab.mjs — blob SHA Git **b5f6b6b45ee618c1f0bcd1a6304bddbc3776637c**, commit **8fd909f667dbec10a50def08fbca9a209472164f**.
- **Nuovo** research/contributors/test_amendment_adapter_v061_lab.mjs — blob SHA Git **795a0c2c574d089d68ccf88e68a3a3ea05742478**, commit finale di allineamento esatto **945294938e8ecd62f85f7069433d3bca840677cd** (commit di creazione precedente 837c2224fb1b3b177acf5cba63136ea6ea979ee6). Una parentesi in eccesso nella prima pubblicazione della suite è stata corretta nel branch LAB prima del checkpoint finale.
- Dipendenze precedenti riutilizzate IDENTICHE (tutte corrispondenti a git hash-object dei file locali):
  - access_binding_candidate.mjs — **3bb233eba371728b2d5ef146826efe0a4045dee9**
  - d1_access_candidate.sql, schema D1 candidato **integrale** — **9ed38b6ed83755186af05f1bf28b4608cdc5f901**
  - d1_amendment_v059_lab.sql — **289cb54f0b3e33976b255ce976ca5e00bc43ab3c**
  - d1_amendment_queries_v059_lab.mjs — **3d25cb33e38a4820bb19412606bb4908523f96ce**
- Nessun file HTML/UI, browser entrypoint, Wrangler config, D1 migration, workflow, Oracle o collector modificato. Versione/data/ora sulle pagine esistenti non cambiano, perché nessuna pagina viene pubblicata.

## Nuove funzioni (solo candidato in-process, NON HTTP)
Modulo Node/Worker-compatible che IMPORTA l'accessBinding esistente (la verifica identity HMAC/pseudonym dipende dal trusted runtime). Per ogni operazione applica:
1. Attivazione **solo** con env.AMENDMENT_V061_ENABLED='OFFLINE_FIXTURE_ONLY' e STAGING_ENABLED='D1_CANDIDATE'. Non è deployato e non presenta un handler fetch o route.
2. Identità ottenuta soltanto da ctx.access.getIdentity() verificato nel contesto fidato e Access AUD/account/HMAC; service-token negati. Nessun campo role/subject accettato nel payload.
3. Rate limiter per soggetto (obbligatorio e deny se assente/ambiguo), generazione+journal pin D1 esatti, ruolo/permessi attuali su primary session, stesso subject ed email_tag per ogni query.
4. sessione D1 **first-primary** creata per ogni richiesta SQL e risultato accettato solo se success=true e meta.served_by_primary=true. Prima della mutazione è ricalcolata l'identità attuale; il guard SQL della v0.59 ricontrolla revoca/sorgente/modo al commit.
5. submitAmendmentLab: valida input esatto source_entry_id, request_id UUID, price positivo, observed_utc canonico non futuro e note <=280 senza controlli. received_utc generato dal server; record originale preservato. Chiave idempotente richiesta: confronta i campi di un precedente invio; se divergono rifiuta.
6. In caso di scrittura incerta, risposta NON CONFERMATA e **nessun retry automatico**. Una scrittura riuscita viene verificata con una nuova query di riconciliazione.
7. ownAmendmentsLab: filtro soltanto sul soggetto autorizzato e relativo email_tag, mai esposti subject/secret nella vista delle ricevute.
8. ownerAmendmentQueueLab e ownerAmendmentDecisionLab: solo OWNER, con flag WRITE o RECOVERY distinto; reason obbligatoria; transizioni vincolate dallo schema SQL.
9. approvedLevelsLab: per CONTRIBUTOR con lettura abilitata, solo livello originale APPROVED e rettifica APPROVED; non pubblica PENDING, REJECTED o fonte REVOKED; non mostra note private.
10. Non crea API, account, inviti, chiavi reali o flussi di mercato.

## Collaudo locale EFFETTIVO
- Ambiente Linux, Node.js v22.16.0, **node:sqlite** integrato/experimental, node:crypto WebCrypto HMAC e node:test, tutto offline.
- Fixture con schema D1 completo originale + overlay v0.59 completo, owner/alice/bob fittizi con due livelli, originali e review di prova. Connessione D1 simulata in modo da verificare prepared SQL e metadata primary; non è Cloudflare D1 reale.
- Comando: cd research/contributors && node --test --disable-warning=ExperimentalWarning test_amendment_adapter_v061_lab.mjs
- **40/40 test PASS**, 0 fallimenti. 10 esecuzioni consecutive indipendenti della nuova suite → **400/400 esiti PASS**.
- Verifiche: invio valido, idempotenza e replay divergente, protezione dal livello di altri, impersonificazione OWNER, autore revocato, gate write, generazione errata, switch/limiter assenti, primary non attestato, risposta scrittura incerta senza retry, identità cambiata prima/dopo commit, iniezione subject/role dal client, formato UUID/prezzo/UTC/nota, ricevute personali, visibilità owner-only, review e vista approvata, divieto di revoca senza recovery, denial Access service token/AUD/identity.
- Tutte le impronte di dipendenze e codice/test pubblicati nel repo corrispondono ai file realmente eseguiti. Non ripetute le 80 prove v0.60 o suite storiche.

## Limiti e gate aperti
**NO-GO produzione:**
- Il modulo si appoggia a un trusted ctx.access SOLO SIMULATO nei test. Nessun provider autenticato, nessuna verifica JWT/network eseguita, nessun Access binding reale attivato.
- Non ha un endpoint HTTP: per Web servono CSRF, intent one-time già candidati, body cap, cookie/origin, anti-replay, idempotenza transazionale, nessun retry, verifica di revoca nelle corse e gestione esito incerto. NON collegare queste funzioni direttamente a browser input.
- La test fixture espone metadata primary simulate; il servizio Cloudflare D1 e le semantiche di consistenza regionali NON sono collaudati. Le query sono preparate ed eseguite su SQLite Node sperimentale, non contro D1 remoto.
- La validazione di prezzo/UTC avviene lato adapter per payload del cliente; il guard SQL non è un equivalente completo e un amministratore del database non è soggetto agli stessi gate. Prima del deploy verificare i casi Unicode/UTF8, byte limit e procedure di privacy.
- Accesso OWNER alla proiezione livelli e pagina completa REMURA sono separati e non abilitati da questo adapter: l'interfaccia richiederà integrazione dedicata.
- Nessuna quota attuale Cloudflare/GitHub/Oracle letta: costi Free reali da verificare prima di attivare utenti o Worker.

## Roadmap senza ripetere prove concluse
1. **Contributors v0.62 LAB**: controller HTTP fittizio non distribuito con origin/CSRF e intent monouso, binding server-side dell'attore; unire adapter v0.61 senza bypass dei gate. Continuare test negativi e simulated race, senza deploy o migrazioni.
2. **Contributors UI iPhone**: aggiungere schermata “Correggi il mio livello”, conferma PENDING, ricevute personali e coda OWNER. Versione e timestamp italiano visibili IN ALTO su ogni pagina modificata; collaudo reale Safari fisico ancora aperto.
3. **Contributors live**: richiede autorizzazione distinta per Access/login reali, migrazione/Worker, autenticazione, collaudo D1 Cloudflare, budget gratuito, audit e revoca. Nessuna identità reale ora.
4. **Experience v0.30**: resta *solo design* per custodia monotona realmente indipendente; Mac+iPhone e due firme non provano da soli la freschezza anti-rollback.
5. **TradingView v0.8.181 e Shark Science v0.4**: holdout CVD/price-only 23–29 novembre 2026 UTC e 30 nov–6 dic UTC immutati; nessuna efficacia predittiva verificata. Non confondere proxy Delta/CVD con identificazione degli istituzionali.
6. **Oracle**: collector e autoupdater non toccati, installazione v1.65 NO-GO; Private Capture hosted STOP; Ampere Radar invariato. Telegram amici ancora solo progetto.

## Costi e autorizzazioni
Solo file GitHub su branch LAB e processi locali; nessun merge, deploy, migrazione D1, utilizzo di Secrets reali, GitHub-hosted test avviato intenzionalmente, dati di mercato reali o spese nuove. Le quote Free effettive non sono state misurate nuovamente.

**Esito: Contributors v0.61 LAB — adapter multi-ruolo verificato localmente, accesso reale e pubblicazione ancora NO-GO.**
