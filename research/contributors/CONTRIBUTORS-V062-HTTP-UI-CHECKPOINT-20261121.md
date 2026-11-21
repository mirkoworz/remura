# REMURA Contributors v0.62 LAB — checkpoint integrato
**21/11/2026, 09:35 CET (Europe/Rome)**

## Provenienza / branch
- Repository \`mirkoworz/remura\`; branch nuovo \`research/contributors-http-ui-v062-20261121\` da v0.61 \`a0c4db9454cb813652847c4dc3bd5ceef5f664ad\`.
- NON modificati i precedenti rami v0.56, v0.59, v0.60, v0.61 né \`main\`. Nessuna PR/merge, deploy, cloud identity, binding, migrazione D1, raccolta di mercato, secret reale o modifica Oracle.
- Nuovi file nella cartella \`research/contributors/\` con impronta GitHub **MATCH** di \`git hash-object\` degli stessi file eseguiti localmente:
  - \`amendment_intent_v062_lab.mjs\` → \`bc464f200663394d538d5503f775fb99c5d0f895\`
  - \`amendment_http_v062_lab.mjs\` → \`4d305c1169a7b1d07e63c10b26fb261fc8fd76fb\`
  - \`amendment_http_fixture_v062_lab.mjs\` → \`92d4c5a42d083299c007e9ca6242b97b6b24a5b6\`
  - \`test_amendment_http_v062_lab.mjs\` → \`4ba0de46a97c28e439e2ec83856ea4178111c111\`
  - \`contributors_amendment_v062_lab.html\` → \`2913a9bc9528db95c9af99be2089475cdbf236e3\`
  - \`contributors_amendment_v062_lab.css\` → \`d1acd5cad6a98a28dcbdde06f82ee8c20c5433f8\`
  - \`contributors_amendment_v062_lab.mjs\` → \`85116219eeb8b203bc95170d4ae5293fa168859a\`
  - \`test_contributors_amendment_ui_v062_lab.mjs\` → \`a765fc36e2ff929e61965db37f92c87c44f5dc7a\`
- Derivata da modulo Access e adapter v0.61 già collaudati; fixture di test derivata dalla porzione iniziale del test v0.61 senza eseguirne nuovamente i 40 vecchi casi.
- Durante la pubblicazione è stato corretto un singolo errore di trascrizione nel modulo HTTP prima di fissare l'impronta finale, senza modificarne la logica collaudata.

## Controller HTTP LAB, NON montato
\`amendment_http_v062_lab.mjs\` esporta solo una funzione chiamabile in-process, **non** un Worker fetch pubblico e **non** una route configurata. Rifiuta in assenza di entrambi i flag \`OFFLINE_FIXTURE_ONLY\`; accetta soltanto POST all'origine HTTPS esatta, URL senza query/hash, contenuto JSON, header Origin/Sec-Fetch-Site same-origin, X-Remura-CSRF e limite corpo streaming di 4096 byte. Risposte \`no-store\`, no CORS/redirect, status generici 400/403/409 senza dettagli SQL o identity.

Route sintetiche distinte:
- \`/api/amendment/intent\`: chiede un intento monouso per una delle due mutazioni.
- \`/api/amendment/submit\`: correzione del proprio livello con binding del body/nonce/identità/ruolo/generazione; originale immutabile, nuovo record pending.
- \`/api/amendment/mine\`: solo ricevute del proprio soggetto.
- \`/api/amendment/approved\`: solo livelli originali o correzioni realmente APPROVED, mai pending/rejected/revoked.
- \`/owner/amendment/queue\` e \`/owner/amendment/review\`: decisioni OWNER riservate.
Le funzioni di business sono importate senza cambiamenti dall'adapter v0.61. Nessun dato di mercato reale.

## Intenti monouso e verifica
\`amendment_intent_v062_lab.mjs\` crea/controlla un token HMAC-SHA256 di 90 secondi associato a generazione, journal pin, soggetto+email_tag Access, path, ruolo, modalità WRITE/RECOVERY, corpo ordinato, nonce ed expiry. Impiega \`SQL.permission\` e \`SQL.burn\` già presenti nel file storico \`operation_intent_candidate.mjs\`, registrando l'uso in \`lab_intent_used\` **prima** di qualunque effetto. Il test locale aveva una copia minima dei soli due letterali SQL importati da tale modulo: lunghezze e checksum semplici confrontati con il file GitHub originale, uguali; **non** è stata rieseguita l'intera suite originale di intent. Nel repository il modulo nuovo importa direttamente il file originale esistente. Nessun token può essere fornito per identity o dati diversi; write incerto → 409 no retry, l'intento già consumato non può essere riusato.
- Le intestazioni Origin/Sec-Fetch sono difese aggiuntive, NON autenticazione. La provenienza trusted di \`ctx.access\` non è attualmente attestata da un servizio cloud reale.
- Non si dichiara protezione anti-rollback o indipendenza crittografica da questi token; non pubblicare finché le vere chiavi e il dominio di fiducia non siano approvati.

## UI iPhone LAB (solo anteprima offline)
Tre file HTML/CSS/JS separati, senza rete, fetch, salvataggio, invio, token o dati live. In cima alla pagina: **REMURA Contributors v0.62 LAB · 21/11/2026 09:29 CET · OFFLINE**. Tema scuro, responsive, accessibilità aria-live, input prezzo + timestamp UTC + nota, stato PENDING solo simulato, percorso Contributor → OWNER → REMURA. Originale fittizio EURUSD 1,12300; stato di pubblicazione non cambia con l'anteprima. Nessuna API o endpoint chiamati; pagina non distribuita. HTML CSP vieta \`connect-src\`. Test eseguiti in simulazione DOM Node, non in Safari fisico.

## Test NUOVI, realmente eseguiti
- Container Linux locale, Node.js v22.16.0, \`node:test\`, \`node:sqlite\`, WebCrypto HMAC; fixture D1 SQL originale verificato nelle versioni precedenti. Nessun servizio Cloudflare o Actions.
- Comando: \`node --test --disable-warning=ExperimentalWarning test_amendment_http_v062_lab.mjs test_contributors_amendment_ui_v062_lab.mjs\`
- Risultato **60/60 PASS**: 42 test protocollo, route, CSRF, HMAC, replay, origin, payload/corpo, OWNER vs contributor, revoca post-token, generazione, rate limit, badge HTTP no-store; 18 test HTML/JS responsive e simulazione preview locale.
- Sono state effettuate inoltre **cinque ripetizioni complete** della nuova suite: 5 × 60 = **300/300 PASS**. Queste sono ripetizioni di stabilità, non 300 distinti nuovi casi.
- Impronte degli otto file pubblicati coincidono con la copia locale testata.
- Non rieseguiti: 40 adapter v0.61, 80 v0.60, 65 v0.59, e le suite Experience/TradingView/Oracle precedenti.

## Gate aperti (NO-GO reale)
1. **Cloudflare Access**: ctx.access in test è simulato. L'integrazione reale JWT/Account/AUD/revoca istantanea, rate limit reali e Secrets non è attestata. Nessun utente reale invitato.
2. **D1 Cloud**: SQL originale provato in SQLite Node; semantiche reali first-primary, commit ambiguity, latenza/consistenza e costi non collaudati su Cloudflare.
3. **UI**: offline demo non è collegata al controller, non è iPhone Safari fisico. Il passo successivo è costruire un client con intent token, stato incerto e test negativi in fixture; NON commistionare con una pagina che fingerebbe un invio reale.
4. **Budget**: non abbiamo rimisurato quota attuale GitHub, D1, Cloudflare Workers o Oracle; questo lavoro è stato svolto localmente senza runner hosted o database D1. Evitare chiamate o migrazioni senza verifica limiti Free.
5. **Custodia Experience v0.30**: rimane solo design della radice monotona indipendente, senza prova fisica Mac/iPhone. Witness 001–005, APFS e Safari Mac checkpoint precedenti conservati.
6. **TradingView v0.8.181**: holdout 1 dal 23 al 29 novembre 2026 UTC; holdout 2 dal 30 novembre al 6 dicembre UTC; protocollo e soglie congelati. Nessun vantaggio statistico dimostrato, nessuna identificazione diretta degli istituzionali.

## Prossimi lavori v0.63
- Client browser di **staging LAB** isolato, capace di chiedere intent, inviare richiesta una sola volta, mostrare conferma solo se attestata dall'HTTP e bloccare qualunque retry automatico dopo 409/timeout.
- Integrazione UI e controllo form su Safari Mac e successivamente iPhone fisico; assicurare badge versione/data/ora in cima a ogni pagina toccata.
- Collaudo del controller con *reale* Worker/D1 solo se autorizzato dopo verifica quote gratuite, identità/revoca e modifica limitata a fixture non contaminate; non avviare nulla automaticamente.
- Continuare separatamente Shark Science e TradingView holdout, senza contaminare campioni.
- Oracle collector/autoupdater/v1.65, Private Capture hosted STOP e Ampere Radar invariati.

**Stato finale: v0.62 LAB — controller + intent + UI offline implementati, 60 test nuovi PASS, nessun deploy.**
