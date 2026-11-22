# REMURA v1.69 LAB / Contributors v0.95 — Bozza locale iPhone
22 novembre 2026, 22:20 CET — Europe/Rome.

## Prodotto creato, non un secondo simulatore di ruoli
Questa e' una versione autonoma **dell'interfaccia di compilazione** dei livelli, adattata dai campi gia' realizzati in research/contributors/contributors_candidate.html e .css, senza duplicare il vecchio portale server/revisione. Non crea nuove identita', non attiva accesso, non simula una conferma server e non sostituisce la candidate UI originaria. L'utente ha gia' confermato che l'anteprima Shark Anatomy v1.68 si apre e funziona sul proprio iPhone; il nuovo file Contributors v0.95 richiede ancora prova Safari.

File:
- preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html — un solo HTML, CSS dall'interfaccia candidate incorporato e UX per iPhone.
- preview/contributors-draft-v095-core.js — validatore di contratto dati locale, riutilizzabile nella futura UI privata per anteprima prima di invio (ma **non** come validazione/autorizzazione server).
- tests/contributors-draft-v095.test.js — 15 test mirati al nuovo prodotto.
- .github/workflows/remura-contributors-v095-iphone-draft.yml — CI dedicata, permessi contents read, timeout 4 minuti, nessun Secret o deploy.

Link anteprima HTML di terze parti da Safari (NON il sito REMURA ufficiale):
https://raw.githack.com/mirkoworz/remura/b832c3079299acb1df2aca4b91fc0e979931a67d/preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html

File originale GitHub:
https://github.com/mirkoworz/remura/blob/feature/contributors-iphone-draft-v095-20261122/preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html

## Cosa permette
- Compilare uno strumento, broker/provider, ticker specifico, tipo prodotto (Spot/CFD, Future, Altro), contratto future se previsto; periodo DAY/WEEK/CURRENT_MONTH/PREVIOUS_MONTH; metodologia DELTA_PEAK/EFFORT_RESULT/OTHER_VOLUME_LEVEL; livello prezzo, anchor UTC, ora osservata UTC e note fino a 280.
- Popolare l'ora UTC corrente con un tocco. Verificare localmente valore numerico positivo (massimo 8 decimali, virgola accettata), campi, data ISO Z, ordine temporale e limite di 180 giorni.
- Visualizzare una bozza JSON con schema remura.contributors.local_draft.v095 e stato LOCAL_ONLY_UNVERIFIED. Flags esplicite identity_verified=false, mapping_verified=false, sent_to_server=false, received_by_owner=false, approved=false. Nessun ID fittizio.
- Copiare volontariamente negli appunti dell'iPhone oppure selezionare testo se la copia automatica fallisce. Cancellazione manuale.
- Uscire verso la REMURA pubblica (read-only) su un link esterno; non e' prova di accesso autenticato.

## Confini di sicurezza e privacy
La pagina contiene CSP connect-src 'none', form-action 'none', script/styles inline senza JS esterno, non usa fetch, XMLHttpRequest, WebSocket, API /api/submit, cookie, Account, localStorage o sessionStorage. Non spedisce, salva, sincronizza o protocolla nessun livello; i contenuti sono mantenuti soltanto in memoria finche' la pagina e' aperta. L'utente puo' copiarli negli appunti, che sono esterni al controllo della pagina. **Usare dati di prova, non livelli riservati** nel visualizzatore raw.githack di terzi. Il sito di terzi puo' vedere IP/user-agent. Se Safari segnala rischio, non aggirare.
Il catalogo broker/ticker non e' verificato lato server: i campi sono manuali e il risultato si chiama UNVERIFIED. Non suggerire che un codice ticker validato regex sia automaticamente un contratto autorizzato.
La candidate UI originale richiede profile server JWT/Cloudflare Access e catalogo con mapping approvati: non e' stata aggirata e resta sul branch v0.94 LAB.

## Collaudo e conti
Run GitHub Actions [45071688327](https://github.com/mirkoworz/remura/actions/runs/45071688327), SUCCESS, stdout # tests 15, # pass 15, # fail 0, REMURA_CONTRIBUTORS_V095_LOCAL_DRAFT=15_15_PASS.
Nessuna modifica main/Pages/Oracle/D1/Cloudflare, nessun account, Worker, Secret, invio reale o servizio a pagamento. Sono stati utilizzati pochi minuti GitHub Actions; margine quota gratuita non attestato direttamente.
L'apertura da Safari della nuova anteprima non e' ancora attestata dall'utente. CI verifica validazione e isolamento dal network, non video/test Safari reali.

## Prima del vero pilot 1–2 collaboratori
Restano in vigore gli access/D1 NO-GO v0.93 e scope v0.94. Per fare POST reali occorrono: quota Free verificata e consenso specifico, ruolo firmato dal server, catalogo mappings, ownership persistente, ricevuta server append-only, meccanismo indempotente/no retry sul fallimento incerto, revoca reale e prova Safari con due identita' separate; owner approva, contributor modifica solo livelli propri. PR #105 v0.92 resta DRAFT. Non pubblicare questa UI con un endpoint o nominare come 'attivo' alcun utente.
