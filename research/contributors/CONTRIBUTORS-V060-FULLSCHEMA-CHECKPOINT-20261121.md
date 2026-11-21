# REMURA Contributors v0.60 LAB — checkpoint schema originale e concorrenza
**21 novembre 2026, 09:11 CET (Europe/Rome)**

## Catena di provenienza
- Repository: `mirkoworz/remura`.
- Branch v0.60 isolato `research/contributors-fullschema-concurrency-v060-20261121`, creato dall'HEAD v0.59 `ec53ce679d4d85cbb08bcd55a5d8c7ad93a3c5d3`, senza merge o deploy.
- Schema completo originale **verificato byte per byte** dal ramo Contributors v0.56 `research/contributors-offline-20261114`:
  `research/contributors/d1_access_candidate.sql`, Git blob **`9ed38b6ed83755186af05f1bf28b4608cdc5f901`**.
- La copia esatta è stata ricostruita localmente; `git hash-object d1_access_candidate.sql` coincide con quel blob GitHub. Le sue tabelle originali, indici, trigger di review, revoca, intenti e admin audit sono inclusi; nessun surrogato ridotto è stato caricato per le prove definitive.
- Overlay v0.59 immutato `d1_amendment_v059_lab.sql` blob `289cb54f0b3e33976b255ce976ca5e00bc43ab3c`; query immutate `d1_amendment_queries_v059_lab.mjs` blob `3d25cb33e38a4820bb19412606bb4908523f96ce`.
- Nuovo file `research/contributors/test_d1_amendment_concurrency_v060_lab.py` blob Git `5f15e5041f74a9638520823ab0add439d265c2b0`, commit `16fc8ae729557cfc296340d160cab317062ff9f7`.
- Il file test v0.60 pubblicato su GitHub corrisponde esattamente a `git hash-object` del file realmente eseguito. Nessuna riscrittura dei file v0.59 o del ramo Contributors originale.

## Risultati eseguiti, non presunti
- Ambiente: container Linux locale, Python 3.13.5, SQLite standard con `PRAGMA foreign_keys=ON`, WAL su file temporaneo, più connessioni e thread. Nessuna chiamata verso Cloudflare D1, Oracle o GitHub Actions per l'esecuzione della suite.
- Comando verificato:
  `cd research/contributors && python -W error::ResourceWarning -m unittest -q test_d1_amendment_v059_lab.py test_d1_amendment_queries_v059_lab.py test_d1_amendment_concurrency_v060_lab.py`
- Esito: **80/80 PASS, 0 errori**. Sono i 65 test nuovi della v0.59 eseguiti stavolta sullo schema completo originale, più **15 test realmente nuovi** v0.60.
- Stabilità nuova suite: `test_d1_amendment_concurrency_v060_lab.py` ripetuta 15 volte indipendenti → **225/225 esecuzioni di test PASS**, senza segnalazioni residue ResourceWarning.
- I 15 casi coprono: verifica dell'impronta dello schema completo, DB esclusivamente temporaneo, visibilità commit fra due connessioni, rollback non visibile, contesa con stessa idempotency key, due correzioni distinte parallele, doppia approvazione simultanea (una sola vince), revoca prima di una nuova correzione o approvazione, disabilitazione della scrittura, filtri delle ricevute aggiornati, proiezione senza fonte revocata, PENDING che non cambia il prezzo pubblicato, integrità FK e no retry implicito dopo errore.
- Si è usato multi-connessione con thread e database temporaneo: **non** è test di più processi/dispositivi reali o del motore D1 distribuito. Non attribuire tali garanzie al risultato.
- Non rieseguiti: storici 366 Experience, Safari Mac 40, Witness 001–005, APFS, Private Capture, vecchie CI o test scientifici TradingView. Il solo rerun della suite v0.59 era necessario per colmare il gate dichiarato aperto.

## Condizioni di sicurezza già mantenute
- Una modifica personale crea una nuova riga e non modifica mai `lab_entries`; record originali protetti da trigger immutabili.
- L'autore deve essere ancora autorizzato; origine personale e mapping attivo verificati sullo stesso DB. Un autore revocato non può presentare modifiche o ottenere approvazioni successive.
- Solo OWNER approva/rifiuta/revoca; non sono possibili due correzioni contemporaneamente approvate per la stessa origine.
- Le proiezioni di test mostrano solo livelli APPROVED, non inseriscono le modifiche PENDING/REJECTED nel prezzo pubblicato. Query delle ricevute filtrate su `subject+email_tag`.
- Errori di contesa o esito incerto non devono provocare una risottomissione automatica.

## Limiti verificati e NO-GO
1. Gli identificativi sintetici sono preparati in un trusted offline fixture; **non esiste ancora un endpoint collegato ad autenticazione reale Cloudflare Access**. Un body HTTP non deve decidere la propria identità.
2. Le query preparate non sono un servizio deployabile; dovranno essere collegate a Worker che ri-verifica Access, D1 primary, generazione, intent/CSRF, rate limiter e revoca immediatamente prima del commit. Necessaria validazione completa dei formati timestamp/prezzo (il guard SQL è difesa ulteriore, non validatore esaustivo).
3. La persistenza SQLite locale e le prove multi-thread non certificano D1 cloud, durabilità fra regioni o concorrenza multi-processo/HTTP. Mancano test D1 reali, test iPhone fisico e gestione di scritture con risposta sconosciuta.
4. Nessuna nuova migrazione D1 né binding/Worker né registrazione di amici. Il ramo v0.56 resta congelato al checkpoint `21338d4a405b0a3053e5a51322f8643c428ac757`.
5. Quote Cloudflare, GitHub Actions e Oracle non misurate di nuovo; nessun saldo Free attuale attestabile. Nessun requisito di pagamento è stato introdotto.

## Roadmap successiva
- **Contributors v0.61 LAB**: adapter Worker isolato per creare correzione/consultare solo le proprie ricevute; verificare in ogni fase identità trusted, freshness, owner review, rate limit, idempotenza e CSRF con fixture sintetiche. Non esporlo pubblicamente.
- **Contributors v0.62**: integrazione nel frontend esistente solo dopo prove negative su server, con chiara distinzione fra inserimento, correzione e approvazione. Qualunque pagina HTML nuova o aggiornata deve mostrare **versione e data/ora italiana in alto**.
- **Experience v0.30**: protocollo di custodia reale Mac/iPhone ancora **solo DESIGN** in `EXPERIENCE-V030-CUSTODY-REAL-GATES-20261121.md`; niente chiavi operative, niente dichiarazioni di monotonicità senza test fisico.
- **TradingView v0.8.181**: holdout1 23–29 novembre 2026 UTC e replica 30 novembre–6 dicembre; criteri congelati, non inferire risultati prima dei dati. Shark Science v0.4 ricerca senza edge attestato.
- Oracle collector invariato, autoupdater inibito, v1.65 NO-GO; Ampere Radar e Private Capture v0.15 senza nuove attivazioni.

**Stato: Contributors v0.60 LAB — schema integrale e concurrency locale verificati; autenticazione/deploy/custodia reale ancora NO-GO.**
