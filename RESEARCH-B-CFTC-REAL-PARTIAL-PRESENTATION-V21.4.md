# REMURA — Filone B V21.4 LAB — 12 valori CFTC reali pronti per il cockpit, senza falsa freschezza

**Aggiornamento V21.4 · 23/11/26, 22:18:05 Europe/Rome.** PR #108 Draft, ramo `research/filone-b-cot-intelligence-v206-20261123`. Integrazione frontend Filone D non toccata. Nessun merge, deploy, Cloudflare, Oracle, API o spesa.

## Modulo realizzato

`scripts/cot_real_partial_presentation.js` produce un JSON **READ ONLY** a partire dal file pubblico `research/real-proofs/REMURA-B-CFTC-20261123-STDOUT-PARTIAL-EXCERPT.json` esistente. È un **contratto di presentazione**, non un collector e non un sostituto della parità pubblica/privata completa.

Comando locale, nessuna richiesta esterna:

~~~bash
node scripts/cot_real_partial_presentation.js
~~~

La risposta include tre gruppi effettivamente stampati dall'audit precedente: **5 cross FX sintetici TFF**, **4 futures finanziari TFF**, **3 futures materie prime Disaggregated**. Per ogni voce: simbolo, `weeklyNetDeltaPp`, `categoryGapPp` e data CFTC 17/11/2026; inoltre provenienza del [run 45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974), orario lettura pubblica, spiegazione delle categorie e status `HISTORIC_PARTIAL`.

Il modulo controlla il contratto esatto e non permette un output se manca una voce, ci sono duplicati, numeri non finiti, timestamp falsi o l'audit non corrisponde. Al superamento di **14 giorni dalla data del report** segnala `STALE_HISTORIC_PARTIAL`. Il dato rimane storico anche prima di questa soglia e **non** significa che REMURA riceva eventi istituzionali live.

Nell'output i seguenti campi sono permanentemente `false`: `raw980SourceRowsRecovered`, `firstSeenAuthenticated`, `privatePublicParityVerified`, `institutionalLiveOrders`, `forecastOrTradeSignals`, `alphaProven`. I cinque cross rappresentano due componenti futures ciascuno, **non flussi spot indipendenti**. Sono mostrati con categoria TFF Asset Manager/Institutional vs Leveraged Funds; materie prime Disagg Managed Money vs Producer/Merchant.

### Collegamento futuro senza invadere Filone D

Il responsabile Filone D può importare o copiare **solo il JSON di presentazione** nel proprio LAB per dare alla UI i primi dati settimanali autentici, con etichette ben visibili **CFTC / SETTIMANALE / PARZIALE / STORICO**, provenienza e stato N/D per gli altri 23 cross. Nessuna modifica a D viene fatta da questo ramo; integrazione, deploy e merge richiedono i gate coordinati C+D.

### Perché non è ancora il finale scientifico

La prova audit originaria includeva 980 righe CFTC sul runner, **non recuperabili** da questo estratto. Il digest dichiarato non è ricalcolabile dai soli 12 valori stampati. Le cache CFTC private e timestamp `first_seen_at` non sono verificati; quindi il percorso B V21.2 di parità offline continua a richiedere i veri file completi. Non usare l'estratto per ricostruire 28 cross o dichiarare una predizione.

**Nuovi test:** `tests/cot-real-partial-presentation.test.js` (5 prove synthetic mutation + preservation of real log excerpt). Non vengono interrogate API né consultati Secrets. Quote GitHub Actions reali ancora da verificare.
