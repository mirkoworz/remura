# REMURA Contributors v0.76 LAB — REGISTRO DUREVOLE NUOVI LIVELLI

**Checkpoint verificato: 21 novembre 2026, ore 16:03 CET (Europe/Rome)**

## Stato GitHub, branch e isolamento
- Repository: `mirkoworz/remura` (PUBBLICO, quindi mai depositare credenziali o dati privati).
- Branch isolato: `research/contributors-durable-level-v076-20261121`.
- Base invariata v0.75: `d12a99a491a0f6a26d7e62ffb51f491cdaf80bdd`.
- SHA di codice completo effettivamente sottoposto a CI: `284628393a190f4b9f9ea0418c536cafc1798a27`.
- Nessun merge in `main`, deploy, D1 Cloudflare reale, nuove migrazioni reali, Cloudflare Access users, Google identity, Secret, acquisto, Oracle, collector, ingestione di mercato, Telegram.
- Le 4 nuove pagine private `contributors_recovery_v076_private_lab.html`, `contributors_owner_recovery_v076_private_lab.html`, `contributors_levels_v076_lab.html`, `owner_levels_v076_lab.html` contengono **in alto** la versione v0.76 LAB e timestamp **21/11/2026 15:57 CET**. Le vecchie pagine LAB rimangono nel repository intatte e non pubblicate.

## Nuova funzione: registro distinto dei tentativi di livello ORIGINALE
Il journal per **nuovi livelli** non è il journal di correzioni/amendment. Non riciclare stati né ricevute dei due flussi.

- `new_level_attempts_v076_lab.sql` introduce esclusivamente uno **schema additivo vuoto candidato**:
  - `lab_new_level_attempts` con `(subject,request_id)` unico, fingerprint SHA-256 del contenuto normalizzato, stato `RESERVED` oppure `COMMITTED`, timestamp, eventuale receipt_id reale della tabella lab_entries;
  - unique partial index `new_level_single_inflight` su subject per `state='RESERVED'`, barriera server a due schede, più browser o processo riavviato;
  - trigger che vietano DELETE e rebind del tentativo; unico aggiornamento ammesso `RESERVED -> COMMITTED` solo se esiste la corrispondente ricevuta originale;
  - **nessuna procedura SQL che sblocchi automaticamente RESERVED**, nessun retry, nessuna modifica alle tabelle reali o allo schema storico.
- `level_attempt_journal_v076_lab.mjs` usa sessioni `D1.withSession('first-primary')`, verifica generazione/journal pin e consenso live D1, hash del payload, prenotazione SQL atomica, conferma della ricevuta originale e verifica di stato. La lettura controlla **in modo separato il diritto attivo di lettura**, per non confondere l'accesso negato con un reale `NO_ATTEMPT`.
- Stato restituito esclusivamente per l'identità Access+HMAC server-side:
  - `NO_ATTEMPT`: nessun tentativo nel **nuovo registro**;
  - `UNRESOLVED`: RESERVED senza entry confermata; invii bloccati;
  - `COMMITTED_NEEDS_OWNER`: la entry originale esiste, ma la fase di conferma del registro è rimasta RESERVED; invii bloccati e controllo OWNER;
  - `COMMITTED`: entry e conferma nel journal concordano; solo un nuovo intento volontario può proseguire.
- `level_intent_precheck_v076_lab.mjs` convalida la **vera firma HMAC dell'intent originale** PRIMA di inserire la prenotazione; l'intent firmato è comunque consumato una sola volta dalla logica storica originale al momento dell'effetto. Una firma mancante/falsificata NON deve creare il blocco di prenotazione.
- `durable_level_api_v076_lab.mjs` implementa il flusso `/api/submit` (con original handler HMAC e D1) e il nuovo POST `/api/level-attempt/status` con body `{}`; applica limite richieste, verifica ruolo CONTRIBUTOR, CSRF/same-origin, schema esatto, attesta il receipt_id prima di dichiarare COMMITTED.
- **I tre stadi RESERVE -> SUBMIT originale -> CONFIRM NON sono un'unica transazione D1**. Per qualsiasi risposta persa, permesso revocato o errore ambiguo si accetta il blocco `RESERVED` e futura verifica umana, non una nuova submission.
- Una seconda scheda che prova a scrivere mentre c'è RESERVED riceve rifiuto (UNIQUE lato DB). Lo schema storico `lab_entries` continua ad avere UNIQUE per payload semantici, ma **NON significa che ogni nuovo payload diverso sia automaticamente un duplicato**.

## iPhone v0.76 e build Worker compatibile
- `contributors_candidate_client_v076_lab.mjs`: il vecchio client può leggere anche lo stato server, non possiede API di retry o reset del journal.
- `contributors_levels_ui_v076_lab.mjs`: all'apertura verifica il profilo e **poi** il journal; se UNRESOLVED/COMMITTED_NEEDS_OWNER/stato non verificabile, nasconde e disabilita invio. Durante l'invio blocca immediatamente il comando; uscita disabilita la vista. OWNER non riceve l'autorizzazione di contribuzione.
- `private_worker_router_v076_lab.mjs`: routing GET delle 4 pagine e degli asset in aree separate RECOVERY/LEVELS e ruoli separati CONTRIBUTOR/OWNER, più endpoint di stato. Ogni invocazione ha i controlli Access e D1 con denial di default.
- `private_levels_composition_v076_lab.mjs`: integra runtime Access originario, profilo D1, HMAC originale, nuovo controller e router usando **solo moduli ES Worker-friendly**; intenzionalmente SENZA `default fetch`, route live, secret, URL di deployment o Wrangler config.
- `private_assets_v076_lab.mjs`: 13 asset byte-embedded; `build_private_assets_v076_lab.mjs --check` verifica la corrispondenza con i sorgenti e non usa la rete. SHA256 del manifest confermato da CI: `5a0b56ad3bcec27ada8d3c72c512e04a82a2cb7a55737d26f012d74f2fa9bf97`.
- Il build script usa Node **solo nel laboratorio di build**, non nel modulo runtime Worker.

## Test nuovi REALMENTE eseguiti su GitHub e percorso di debug
**Run GitHub Actions GREEN: https://github.com/mirkoworz/remura/actions/runs/44917023813**

- SHA del run: `284628393a190f4b9f9ea0418c536cafc1798a27`.
- **64 test / 64 PASS / 0 FAIL / 0 CANCELLED**, marker del log `REMURA_V076_DURABLE_ORIGINAL_LEVELS=64_64_PASS`.
- 24 test **solo nuovi** sul journal SQL, UNIQUE per subject, revoca, state read, generazione, blocco delle modifiche, no side-effects sulle amendment.
- 26 test **solo nuovi** end-to-end contro il fixture SQLite/D1 originale: HTTP Access/HMAC, intent valido/non valido, 2 schede in concorrenza, receipt ID, perdita risposta dopo write, status COMMITTED_NEEDS_OWNER, isolamento Alice/Bob, OWNER review, D1 first-primary e kill-switches.
- 14 test **solo nuovi** di byte asset, UI di recupero, versione/date e import closure per Worker.
- Ancora eseguita: `node build_private_assets_v076_lab.mjs --check` + `node --check` sui 3 nuovi moduli; tutti PASS.
- Primo run `44916896926`: 53 PASS / 11 FAIL. Due difetti reali individuati e corretti senza ripetere altri test:
  1. `p[mode]!=='boolean'` confrontava erroneamente il valore col tipo stringa; aggiornato a `typeof p[mode]!=='boolean'`.
  2. Un elenco di tentativi vuoto con `read_enabled=0` veniva interpretato come `NO_ATTEMPT`; aggiunta verifica primaria e autonoma del permesso prima di classificare lo stato.
- Successivo run `44917023813`: **64/64 SUCCESS**. Non sono stati rieseguiti test storici 55/55 v0.74 o 50/50 v0.75 o 24/24 v0.70.

## Limiti tassativi / NO GO
1. **Nessuna durabilità Cloudflare reale ancora certificata**: il collaudo usa SQLite locale in memoria su runner GitHub. La logica e lo schema sono progettati per il comportamento persistente server ma non è stata eseguita migrazione D1/cloud reale, login Access reale o Safari fisico.
2. `LEVEL_JOURNAL_V076` e `PRIVATE_WORKER_V076` sono solo `OFFLINE_FIXTURE_ONLY`. Nessun deploy possibile senza futura compilazione, binding e autorizzazione specifica. I due UI flow (nuovi livelli/amendment) restano separati.
3. Una prenotazione `RESERVED` può rimanere aperta dopo errore; manca ancora il **protocollo OWNER di risoluzione con audit append-only e attestazione di assenza/presenza della entry**. Non permettere la riapertura automatica a seguito di un 409 o dopo refresh.
4. D1 reale, eventuale sincronizzazione multi-regione, sessioni Access, revoca Cloudflare, write rollback, payload fraud, limiti quantità, seat Free, logout iPhone Safari e strumenti di pubblicazione devono essere collaudati prima del primo collaboratore reale.
5. Il repo `remura` è **pubblico**: no credentials, personal email, utenti reali, JSON di prezzi riservati, token, HMAC o IP nei commit/fixture.
6. Nessuna pubblicazione Telegram o contributo REMURA operativo automatico: approvazione OWNER, provenance e qualità scientifica richieste.
7. Ultimo monitor Cloudflare Free verificato: GitHub run `44772218921` del 20/11/2026, 4 D1 (~6,28 MB) e consumo Workers basso; dati account-specific **non aggiornati in questo ciclo**, Access seat/quota non verificati. GitHub hosted Actions su repository pubblico standard gratuito per il workflow usato.

## Prossima roadmap v0.77 senza Mac
- Disegnare e collaudare un **protocollo OWNER di riconciliazione del journal dei nuovi livelli**, indipendente da amendment: coda riservata, evidenza SQL `lab_entries`, motivazione e audit append-only, nessun reset automatico da OWNER per nuove submission.
- Verificare le due fasi SQL con fault injection: crash dopo RESERVE, dopo INSERT e dopo confirm; evitare promesse di atomicità non provata.
- Produrre un piano di deploy staging privato esplicito e reversibile con Cloudflare Access, D1 fixture dedicato, policy allowlist, quote Free e prova logout; qualsiasi uso reale richiede nuova autorizzazione.
- In seguito pilot con 1–2 collaboratori: lettura REMURA (senza modifica), proposta di soli livelli propri, OWNER approva e può pubblicare solo dopo audit.
- Filoni invariati: TradingView v0.8.181 LAB holdout 1 23–29 novembre e holdout 2 30 novembre–6 dicembre UTC; Shark Science v0.4 LAB; Experience v0.30 LAB toro/orso 3D, pinna REMURA, ringraziamento SMF; Private Capture v0.15 LAB STOP; Ampere Radar v0.36 operativo; Oracle collector in funzione con autoupdater bloccato, v1.65 staged NO-GO; backup, Squalincome e Telegram futuro.

**La v0.76 è una release LAB tecnicamente verificata su GitHub, non una release pubblicata. Nessun Mac necessario per continuare.**
