# REMURA — CHECKPOINT V17 / CONTRIBUTORS iPHONE — 22 novembre 2026 Europe/Rome

**Punto di partenza confermato dall'utente:** anteprima Shark Anatomy **v1.68 FUNZIONA su iPhone**. Questo conferma la UX dell'anteprima, non attesta che CFTC abbia tutti i report, CVD live, alpha o permessi Contributors. V01–V16 preservati; V16 in research/remura-roadmap-v16-shark-anatomy-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V16-SHARK-ANATOMY.md, SHA 620ff5f0ee69d530258017c603e2d55bac826cc6.

## Nuova costruzione: Contributors v0.95 / REMURA v1.69 LAB
Branch: feature/contributors-iphone-draft-v095-20261122, HEAD edfd88865ea23daed2f99b0ada94855daeb992d1.
NON una nuova simulazione di ruolo, NON un secondo backend o portale duplicato: e' **l'interfaccia di compilazione dei livelli** pronta a essere provata su Safari, adattata dai campi di research/contributors/contributors_candidate.html e dal relativo CSS nel branch research/contributors-pilot-scope-v094-lab-20261122 (SHA c59ed284fa3a650ea28ec4456de3f8cf81e89f0a). Il portale protetto esistente resta authority per autenticazione/permessi reali; non e' attivo ne' modificato.

Prodotto concreto:
- preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html: pagina HTML autonoma iPhone con titolo e banner **REMURA v1.69 LAB · 22/11/2026 22:20 CET · CONTRIBUTORS v0.95**, forma adattata da candidate per strumento, broker, ticker originale, prodotto, contratto futures, periodo, metodologia, prezzo, UTC anchor e observed, note. Funzione inserisci UTC e pulsante controlla bozza.
- preview/contributors-draft-v095-core.js: validatore riutilizzabile, parsing numerico con virgola, max 8 decimali, UTC Z date canoniche, anchor <= observed, controllo data futura/180gg, prezzi non-positivi, mapping manuali non attestati. Esporta SOLO oggetto JSON con schema remura.contributors.local_draft.v095, stato LOCAL_ONLY_UNVERIFIED, tutti i booleani identity_verified, mapping_verified, sent_to_server, received_by_owner, approved = false. Nessuna falsa ricevuta server.
- La UI mostra il JSON pronto per copia esplicita con clipboard da iPhone e fallback alla selezione, senza inviare, persistere o promuovere dati. Cancellazione e pulizia memoria. Link esterno alla sola REMURA pubblica read-only.
- CSP connect-src 'none', form-action 'none'; NO fetch, no Worker, no D1, no Session, no Secret, no webhook, no utenti reali e no nuovi servizi/hosting. Provare con VALORI DI FANTASIA, non livelli riservati, specialmente su raw.githack di terzi.
- tests/contributors-draft-v095.test.js: 15 nuove verifiche mirate di validazione, privacy/isolamento rete e riuso dei campi candidate; .github/workflows/remura-contributors-v095-iphone-draft.yml: runner 4min max, only branch/path, permission contents read, NO deploy o secret.

## CI verificata
Run SUCCESS [45071688327](https://github.com/mirkoworz/remura/actions/runs/45071688327), log reale '# tests 15', '# pass 15', '# fail 0', REMURA_CONTRIBUTORS_V095_LOCAL_DRAFT=15_15_PASS. Non ripetute prove vecchie V01–V16, PR #105 o CVD/Mac.

## Anteprima iPhone da aprire
Link sperimentale statico non ufficiale:
https://raw.githack.com/mirkoworz/remura/b832c3079299acb1df2aca4b91fc0e979931a67d/preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html

Sorgente GitHub:
https://github.com/mirkoworz/remura/blob/feature/contributors-iphone-draft-v095-20261122/preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html

README dettagliato:
https://github.com/mirkoworz/remura/blob/feature/contributors-iphone-draft-v095-20261122/preview/README-REMURA-CONTRIBUTORS-V095-IPHONE.md

Il link raw.githack, gia' usato con successo per le preview precedenti, e' gestito da terzi, potrebbe mostrare conferma, e vede l'IP/user agent. Nessuna password, chiave, livello reale o altro dato privato deve essere inserito. Se Safari segnala rischio, non aggirare il blocco. **Il nuovo link Contributors NON e' stato ancora verificato visivamente su Safari dall'utente**; GH CI dimostra solo comportamento del validatore/integrazione statica, non la prova Safari.

## Stato generale invariato
- Main verificato 9758bdcbf1c55b1c63ad66bcf6716872cdc906e4, NON modificato. Nessun merge, deploy, GitHub Pages, Cloudflare Worker/Access/D1, Oracle, Firestore, Telegram, nuova spesa.
- PR #105 Contributors v0.92 e PR #106 TradingView ancora OPEN / DRAFT / NOT_MERGED. Rimangono presenti candidate UI, composition, protected read e scope v0.94, senza duplicazioni.
- Cloudflare Free margin D1 UNKNOWN_NO_GRAPHQL_DATA; precedente autorizzazione 2 GraphQL esaurita, Access seats/quote non attestati. Non chiamare live Cloudflare o registrare 1–2 amici prima di consenso preciso, verifica costo e sicurezza.
- Mac Codex: custodia Oracle collector v1.65 root-owned staged, antirollback/backup, Experience toro/orso 3D, separati. Ampere Radar H24 Oracle Milano e Myfxbook retail restano invariati.
- CVD TV TEST storico deploy non prova ricevitore attivo o receipts prospettici. Holdout V2 apre 23/11/2026 00:00 UTC / 01:00 CET; nessun backfill o alpha senza first-seen/time provenance e benchmark.

## Priorita' V18 concreta
1. Una prova Safari iPhone **Contributors v0.95 bozza**: aprire link, inserire solo dati di prova, verificare controllo prezzo/UTC, pulsante copia e cancellazione. Una conferma sufficiente; non rieseguire test verdi.
2. **Collegamento sicuro al vero portal Contributors** (nuova autorizzazione necessaria prima di API reali): riusare candidate UI e Cloudflare Worker/D1 v0.92/0.94, con autenticazione Cloudflare Access JWT validata server, catalogo dati server, ownership e ricevuta server, controllo degli esiti incerti e revoca dei collaboratori. Verificare quota Free D1, Access seats e budget; 1–2 piloti con esclusione totale da modifiche di COT/Oracle/Secrets e owner queue.
3. Continuare prodotto Cockpit sui dati CFTC di martedi' evitando ricerche solo su fixture, preview v1.68 gia' confermata dall'utente; eventuale release/hosting ufficiale richiede autorizzazione separata e sincronizzazione con Mac.
4. Prospettico TV CVD: prima confermare receiver/alert/test actual read-only con nuovo consenso e Free, e non affermare un edge.
5. Versionare ogni pagina toccata con numero aggiornato e data/ora Europe/Rome. La nuova pagina v1.69 ha gia' la propria intestazione; le altre 10 pagine v1.68 non sono state modificate, non mentire sulla loro versione.

**Risultato V17: un'interfaccia Contributors concreta che genera bozze valide senza backend (15/15 verdi), sicurezza intatta, 0 nuove spese/attivazioni e main invariato. Il pilot reale NON e' ancora autorizzato.**
