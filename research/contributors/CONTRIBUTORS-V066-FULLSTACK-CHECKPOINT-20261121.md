# REMURA Contributors v0.66 LAB — CHECKPOINT INTEGRAZIONE COMPLETA
**21 novembre 2026, 11:38 CET (Europe/Rome)**

## Provenienza e consegne
- Repository: \`mirkoworz/remura\`, branch isolato \`research/contributors-fullstack-v066-20261121\`.
- Base verificata: \`research/contributors-reconciled-http-v065-20261121\` @ \`a6cab848caf8d1c9914c7b733cbffa635b4bbd7d\`. Nessun merge, PR o modifica di \`main\` da questo filone.
- Nuovi file:
  1. \`research/contributors/fullstack_fixture_v066_lab.mjs\` — **blob Git SHA \`808262e4de786fd26a244fcaf8f3a7d91c949b51\`**. Fixture originale Node SQLite, identità HMAC sintetiche separate Alice/Bob/OWNER, rate-limiter simulato, D1 \`first-primary\` emulato con metadata esplicito, iniezione controllata di guasti. Ogni test crea un database \`:memory:\` e lo chiude. Non usa Cloudflare.
  2. \`research/contributors/test_reconciliation_fullstack_v066_lab.mjs\` — **blob Git SHA \`b02cafc3757eb431e6e597449383cd7172b4f335\`**. **45 nuovi test** eseguiti contro la composizione JavaScript **originale** dei moduli già versionati.
- SHA GitHub dei due nuovi file coincidono *esattamente* con \`git hash-object\` dei file usati per i test locali. Ogni fixture SQL ripresa da GitHub nel workspace locale è stata verificata byte per byte.

## Schema D1 completo, non surrogato
La suite carica nello stesso database SQLite \`node:sqlite\`:
- \`d1_access_candidate.sql\`, Git blob **\`9ed38b6ed83755186af05f1bf28b4608cdc5f901\`** — schema completo v0.24 originale con tutte le tabelle, trigger di autorizzazione/revoca/intenti/audit;
- \`d1_amendment_v059_lab.sql\`, Git blob **\`289cb54f0b3e33976b255ce976ca5e00bc43ab3c\`** — correzioni append-only e review OWNER;
- \`d1_reconciliation_v064_lab.sql\`, Git blob **\`2cc5f0ccdda660771bc56dc4ddb34bfc942f973a\`** — prenotazioni persistenti, owner clearance e trigger anti-ritardo.

Sono inoltre importati **senza modifica e con SHA controllato** i reali moduli del repository \`access_binding_candidate.mjs\` (HMAC di identità), \`amendment_intent_v062_lab.mjs\` (HMAC e burn dell'intento), \`operation_intent_candidate.mjs\`, \`d1_lab_adapter.mjs\`, \`amendment_adapter_v061_lab.mjs\`, \`d1_amendment_queries_v059_lab.mjs\`, \`amendment_http_v062_lab.mjs\`, \`reconciliation_reader_v064_lab.mjs\`, \`reconciliation_http_v065_lab.mjs\` e \`reconciliation_composition_v065_lab.mjs\`. Tutti i loro Git blob locali coincidono con GitHub, non sono stati alterati per far passare la suite.

## Nuovi test e risultati ESEGUITI
- Ambiente: Linux, **Node 22.16.0**, \`node:test\`, \`node:sqlite\` sperimentale, \`node:crypto WebCrypto\`. \`fetch\` HTTP interno alla fixture tramite \`Request\` e \`Response\`; nessuna rete reale.
- Comando per eseguire soltanto i test **nuovi**: 
  \`cd research/contributors && node --test --disable-warning=ExperimentalWarning test_reconciliation_fullstack_v066_lab.mjs\`
- **45/45 PASS, zero fail** sullo schema completo e con il codice originale v0.65. Non sono state ripetute le 79 prove v0.65, 76 v0.64, 56 v0.63, vecchie suite Experience, Mac, Oracle o TradingView.
- **10 ripetizioni indipendenti della NUOVA suite** dopo il confronto dei file: 450/450 esecuzioni di test PASS, zero fail. Queste ripetizioni non sono 450 test distinti.
- Casi testati: percorso completo submit → burn intent → reservation → amend append-only → recovery; stato COMMITTED_UNREVIEWED, OWNER APPROVED e proiezione livello aggiornato; rilascio manuale solo dopo review; NO_ATTEMPT e CLOSED mai abilitanti a riscrivere; chiave HMAC riutilizzata o body manipolato negati; due tab dello stesso collaboratore (una sola prenotazione); due **contesti Access indipendenti** di utenti diversi (entrambe le richieste legittime passano); logout/re-login e recupero stato; revoca durante burn o subito dopo la prenotazione; risposta persa dopo prenotazione o dopo write senza retry; scrittura ritardata dopo owner ABORTED_BY_OWNER negata; primo gen/journal pin sbagliato e metadata nonprimary negati; origine/CSRF e service token negati; altre identità non possono consultare le ricevute; read/write flag; original immutable; \`PRAGMA foreign_key_check\` vuoto.

## Gate ancora aperti — NO-GO utenti reali
1. Anche nella v0.66, **reservation e amendment sono due write primary separate**, NON una singola transazione D1. Dopo un commit incerto, l'esito può rimanere UNRESOLVED; l'OWNER deve verificare manualmente le evidenze prima della chiusura. Non implementare auto-abort o auto-retry.
2. **Non è un collaudo Cloudflare D1 reale o Cloudflare Access reale**: il SQL engine è SQLite locale, i metadati primary vengono emulati, \`ctx.access.getIdentity\` usa utenti sintetici, il limiter è una fixture e non c'è Worker deployato. I test di richieste concorrenti sono Promise JS sullo stesso SQLite; non certificano D1 distribuito, più processi remoti o più dispositivi reali.
3. La prova con due differenti contesti Access verifica separazione logica e origini dei soggetti, NON dimostra revoca istantanea del provider né autorizzazione da JWT reale.
4. \`lab_amend_releases_v064\` è ancora una procedura SQL con privilegi OWNER fuori da HTTP; manca una custodia realmente indipendente e audit di operatore capace di distinguere una write remota in volo. Il protocollo v0.30 Experience resta DESIGN.
5. Manca test Safari su **iPhone fisico** e un meccanismo persistente di blocco lato client su refresh: v0.65 offre lettura sicura ma la UI v0.63 resta offline e non è connessa. È vietato scambiare \`CLOSED\` con autorizzazione automatica di nuova submit.
6. Il portale amici richiesto deve limitare le scritture ai contributi propri e mostrare il resto di REMURA **soltanto in lettura**. Il permesso reale Access/contributors, la pagina read-only e la UI di recupero non sono attivati.
7. Quotes dei piani Free di Cloudflare D1/Workers, GitHub Actions, Oracle **non riesaminate** in questo ciclo: nessun deploy/migrazione/nuovo DB/runner hosted è stato intenzionalmente usato, ma non dichiarare disponibilità residua di quota.

## Roadmap operativa
- **v0.67 LAB — UX recupero iPhone e fail-closed:** integrare SOLTANTO visualizzazione stato nel client già offline, con nuova intestazione in alto \`REMURA Contributors v0.67 LAB · DATA/ORA ITALIANA\`; display distinzione NO_ATTEMPT/UNRESOLVED/COMMITTED_UNREVIEWED/COMMITTED_REVIEWED/CLOSED senza sbloccare invii; test DOM e isolamento network. Produrre un flusso pratico per l'OWNER che non richieda installare app.
- **v0.68 LAB — robustezza D1/Access cloud:** prima verificare quote Free, piano D1, bind separati e test autorizzati su fixture privata; implementare procedure di revoca e audit. Senza autorizzazione ESPlicita non migrare né creare identità/chiavi reali o deploy.
- **Experience v0.30:** anti-rollback con dominio di fiducia indipendente reale ancora non attestato; Mac/iPhone con stesso account non costituiscono prova di indipendenza.
- **TradingView v0.8.181 e Shark Science v0.4:** holdout 1 dal 23 al 29 novembre 2026 UTC e holdout 2 dal 30 novembre al 6 dicembre UTC, protocollo congelato; zero edge istituzionale certificato; Delta/CVD e COT non provano chi sta comprando.
- **Oracle collector, Ampere Radar v0.36, Private Capture v0.15:** nessuna modifica; autoupdater ancora inibito, v1.65 NO-GO, Private Capture hosted STOP; splash toro/orso 3D, logo REMURA/SMF invariati.

**Esito v0.66 LAB: 45 test reali sullo schema completo originale e composizione genuina passati; deploy Cloudflare, utenti reali e trading GO RESTANO BLOCCATI.**
