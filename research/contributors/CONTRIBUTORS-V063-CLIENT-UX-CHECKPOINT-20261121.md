# REMURA Contributors v0.63 LAB — client, UI e test integrati
**21 novembre 2026 — checkpoint operativo, ora italiana Europe/Rome.**

## Provenienza e integrità
- Repository privato GitHub: \`mirkoworz/remura\`.
- Nuovo ramo isolato: \`research/contributors-client-ux-v063-20261121\`, derivato dall'HEAD v0.62 \`7021b851abbfdf972a98f3e61b84d997ef60c622\`.
- File NUOVI, tutti con byte GitHub IDENTICI ai file eseguiti nel laboratorio locale (git hash-object):
  - \`research/contributors/amendment_client_v063_lab.mjs\`: \`da696aa1d7d7d7bcb7b701ab30a3e9ecfb057b56\`.
  - \`research/contributors/contributors_amendment_v063_lab.mjs\`: \`59e99f15fe2cf53bb8e62ca726adbf1f9a2e5e9d\`.
  - \`research/contributors/contributors_amendment_v063_lab.html\`: \`3243c579ece389114161fce1531721e83adcb564\`.
  - \`research/contributors/test_amendment_client_v063_lab.mjs\`: \`bc34adab8142902deca9dc4abd395a15fc384ae8\`.
  - \`research/contributors/test_contributors_amendment_ui_v063_lab.mjs\`: \`cd866d6dda244c63802d2514c49e04bde6d8d46b\`.
- Vengono riutilizzati, SENZA MODIFICARLI, il controller HTTP HMAC-CSRF v0.62, l'Access binding v0.31, l'adapter v0.61, schema D1 candidato integrale e overlay v0.59. Il CSS responsivo di v0.62 continua a essere referenziato dalla pagina v0.63.
- Niente edit di \`main\`, branch Contributors v0.56, Oracle collector, TradingView o Home REMURA; no merge, deploy o D1 migration.

## Codice client v0.63
\`AmendmentClientV063\` accetta ESCLUSIVAMENTE un \`fetcher\` esplicitamente iniettato. Niente \`globalThis.fetch\` di default e niente configurazione pubblica. Impone:
- Allowlist di soli percorsi HTTP del candidato v0.62. POST JSON, credenziali e modalità same-origin, redirect error, cache no-store, origin delle URL relativo (non network arbitrario).
- Input mutation esatto: propria correzione (id origine, UUID request_id, prezzo, UTC non futuro, nota) oppure azione OWNER (id, APPROVED/REJECTED/REVOKED, ragione). Nessun subject/role proveniente da form.
- Ogni mutazione chiede un intent HMAC breve e legato a body, identità, generazione, ruolo e percorso. Valida sintassi ed expiry del token prima dell'azione.
- Dopo l'invio della mutazione, su qualunque 409, errore rete, risposta non JSON, risposta 200 malformata, redirect o cambiamento di vista, lascia \`uncertain=true\`, NON ripete automaticamente la mutazione e NON mostra una conferma fittizia.
- Blocca mutazioni mentre ce n'è una attiva oppure dopo esito incerto; consente le sole letture autorizzate a fine richiesta, senza azzerare il blocco.
- Accetta solo risposta HTTP con \`application/json\`, \`Cache-Control: no-store\`, envelope \`{data}\`, dimensione di risposta <= 32768 byte e contenuti con forma esatta per ACK; evita dati privati nelle eccezioni.
- Importante: il blocco \`uncertain\` è **solo in RAM della singola istanza**. Un refresh o un'altra scheda non mantengono automaticamente il blocco; per l'accesso reale serve un registro server di idempotenza/riconciliazione con test multi-tab e recupero. Non abilitare live sulla base della sola memoria del browser.

## UI iPhone v0.63
- In alto, prima di ogni altra sezione: **REMURA Contributors v0.63 LAB · 21/11/2026 09:42 CET · OFFLINE**.
- HTML separato con la stessa estetica scura responsive e CSS v0.62; CSP \`connect-src 'none'\` e nessun handler di rete incorporato.
- Bottone invio e lettura ricevute **disabilitati per impostazione predefinita**: la pagina resta una vera anteprima browser offline, senza chiavi o sessioni. Per i soli test l'UI controller riceve un client passato da un fixture fidato; NON è stato cablato a un sito pubblico.
- \`mountAmendmentUIV063\` gestisce preview (non inviata), validazione prezzo/UTC/nota, UUID generato solo all'atto di invio del test, stato di richiesta in corso, conferma in base alla risposta del client, stato ESITO INCERTO bloccato e consultazione delle ricevute private (senza sblocco).
- Nessuna modifica automatica di \`#published\` dopo la preview o la conferma di invio: solo il backend OWNER APPROVED cambia la proiezione approvata.
- Nessun collaudo reale di Safari su dispositivo iPhone: i test sono DOM simulato con Node e backend SQLite sintetico.

## Test NUOVI effettivamente eseguiti
- Container Linux locale, Node.js v22.16.0, node:test, WebCrypto, node:sqlite sperimentale; HMAC, identità e D1 primary metadata sono mock o fixture. Nessun utente reale, nessun D1 cloud, nessun Telegram.
- Comando: \`cd research/contributors && node --test --disable-warning=ExperimentalWarning test_amendment_client_v063_lab.mjs test_contributors_amendment_ui_v063_lab.mjs\`.
- **56/56 PASS, 0 fail**: 35 test client (intent, roles, URL, no-store, anti-replay, lost-after-commit, 409, no network retry, forged response, 1 sola submit, letture incerte, busy lock) + 21 test UI (timestamp, CSP offline, pulsanti disabilitati, validazioni, stati e 3 end-to-end UI→client→HTTP→SQLite/OWNER).
- **Cinque ripetizioni separate dell'intera suite**: 5 × 56 = **280/280 PASS**, tutte dopo il salvataggio dei file. Sono ripetizioni di stabilità e NON 280 casi nuovi.
- Conservati gli 80 test full-schema v0.60, 40 v0.61 e 60 v0.62; NON sono stati rieseguiti in questa attività. Nessun test storico Experience, TradingView, Private Capture o Oracle ripetuto.

## NO-GO per utenti e mercato
1. Nessuna autenticazione Cloudflare Access reale né binding Worker/D1 o collaudo Safari iPhone fisico. Le credenziali HMAC e identità sono fittizie, il runtime Access è simulato.
2. La pagina offerta agli utenti non invia richieste, anche perché \`connect-src 'none'\` e non esiste un fetcher configurato; le prove end-to-end avvengono solo nei test.
3. Stato incerto non persistente a refresh/schede multiple: NO-GO live fino a server-side reconciliation, ripristino sicuro, logout/lock e verifica firme/idempotenza.
4. Gli oggetti mock D1 primary e SQLite locale non dimostrano proprietà di Cloudflare D1 distribuito, consistenza regionale o quote residue.
5. Livelli approvati sintetici NON sono ordini, broker reali, né evidenza diretta di acquisti istituzionali o vantaggio di trading. Mantenere Data Science e TradingView separati.
6. Nessun deploy, nuovi database, chiavi private reali, CI-hosted manuale, spesa o attività Oracle è stato avviato.

## Roadmap successiva
- **Contributors v0.64 LAB**: server ledger di richieste per riconciliazione SICURA tramite request_id, separazione dei casi “non avviato / consumato ma incerto / committato / revocato”; verifica della concorrenza di due schede, reload Safari, logout, nuovo browser, token bruciati e revoca dopo commit. Vietare reset automatici di uncertain.
- **Contributors v0.65/UI**: schermata di accesso e flusso end-to-end Safari Mac/iPhone con fake server; solo in seguito al collaudo di sicurezza/quote ed esplicita autorizzazione, valutare D1 fixture privato e Cloudflare Access reali.
- **Experience v0.30**: custodia anti-rollback realmente indipendente ancora solo progettata; prove fisiche Mac/iPhone e root of trust NON eseguite; riprendere dal relativo checkpoint, non reinterpretare due firme come indipendenza.
- **TradingView v0.8.181**: primo holdout 23–29/11/2026 UTC, secondo holdout 30/11–06/12; evitare nuovi parametri o falsi risultati prima dei dati.
- **Shark Science v0.4**: distinguere Delta/CVD proxy, sentimento retail e COT ritardato dall'informazione istituzionale diretta; richiedere baseline price-only, timestamp ex-ante, validazione holdout e costo ipotetico.
- **Mac/Oracle**: collector operativo all'ultimo checkpoint, autoupdater inibito, v1.65 NO-GO installazione; Ampere Radar v0.36, Private Capture v0.15 senza nuove attivazioni. Splash toro/orso, pinna REMURA e ringraziamento SMF invariati.

## Gratis e consumi
Per questo ciclo sono stati utilizzati solo Node/SQLite locali e commit GitHub \`[skip ci]\`: nessuna CI hosted avviata volontariamente, nessuna chiamata Cloudflare D1 o nuova risorsa. Contatori reali GitHub/Cloudflare/Oracle **non letti**: NON dichiarare margine gratuito misurato finché non viene verificato.

**Checkpoint v0.63 LAB: UI/Client/HTTP/SQL sintetici end-to-end PASS; utenti reali, deploy e market GO restano vietati.**
