# REMURA Contributors v0.88 LAB — CHECKPOINT LOCAL FREE PANEL

**Checkpoint registrato il 21 novembre 2026, Europe/Rome — dopo il test GREEN**

## Versione, codice e prove GitHub
- Repo pubblico `mirkoworz/remura`, branch isolato `research/contributors-free-local-panel-v088-20261121`, base esatta Contributors v0.87 LAB `68ee7d13d149e6841ff9cb95646f9ddf45f88892`.
- Commit CODICE HTML/JS nuovo: `e139036ed0a6703a92339a206a20bea2f6fa454b`.
- Commit CODICE+CI effettivamente validato: `ba8a34f048e6164547d0d4179b79813e7e065618`.
- Run finale GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44933120866: **SUCCESS**, log verificato `tests 22`, `pass 22`, `fail 0`, `REMURA_V088_FREE_OFFLINE=22_22_PASS`. Solo nuovi test su nuova pagina; non rieseguite suite storiche.
- Prima esecuzione 44933070406 era **FAILED nel parser delle righe log**, benché i 22 test Node fossero tutti PASS. Node v24 stampa `ℹ tests` invece di `# tests`; corretto soltanto il workflow, senza modificare la logica JS.

## Cosa è nuovo e realmente fruibile
- Pagina unica HTML: `research/contributors/contributors_free_local_v088_lab.html`, autosufficiente iPhone/Safari e desktop, con banner v0.88 e ora Europe/Rome in cima, grafica dark REMURA e **calcolo locale sui numeri digitati manualmente**.
- Dati: D1 rows read/write, Workers requests, numero D1 DB, storage totale e DB maggiore (byte), posti Access usati e previsti dal piano, istante UTC dell'osservazione.
- Stati separati: `SCONOSCIUTO`, `NON VALIDO`, sotto 70%, vicino alla soglia, al limite/sopra. Controlla coerenza DB maggiore <= totale, seats used <= total, UTC dello stesso giorno e max quattro ore, senza assumere che l'orologio locale del browser o i dati digitati siano certificati.
- Soglie nominali validate su fonti Cloudflare 21 novembre 2026: D1 Free 5M reads/day, 100k writes/day, 10 DB, storage 5 GB/account, 500 MB/database (https://developers.cloudflare.com/d1/platform/pricing/ e https://developers.cloudflare.com/d1/platform/limits/). Workers Free 100k requests/day (https://developers.cloudflare.com/workers/platform/limits/).
- Non inserire ID account, credenziali, indirizzi email, JWT o PII. File non fa chiamate o richieste di rete, ha CSP `connect-src 'none'`, zero storage/cookie/clipboard/CDN/fetch; bottone per cancellare input. Nessun auto-polling né attivazione di servizi. I numeri restano volatili e appartengono solo alla pagina aperta.
- `test_free_local_v088_lab.mjs`: 22 **nuovi** test di logica applicativa Node-vm e vincoli HTML/CSP, valori al limite, missing vs zero, numeri invalidi, seats e reset. `.github/workflows/remura-contributors-v088-one-shot-ci.yml`: CI one-shot isolata, `contents:read`, niente Secret.

## Limiti e decisione
- **STAGING NO-GO sempre**, anche in presenza di tutti i valori digitati sotto le soglie. Il browser non può attestare che gli input provengano da Cloudflare, che l'account sia Free, che le seats Access siano effettivamente acquistate/disponibili o che politiche di login/revoca siano corrette.
- L'ultima run D1 reale nota del 21 novembre `44919682812` era `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`. Non riempire i campi D1 read/write con zero. Ultimi metadati mostrati dal vecchio monitor: Workers ~199 richieste stimate, D1 4 DB e 6.557.696 byte complessivi; informazioni storiche non attestate oggi dal nuovo pannello.
- Access: verificare la dashboard Zero Trust per seat usati/totali; la revoca sessione e la rimozione della seat sono operazioni diverse, e da sole non necessariamente impediscono un nuovo login consentito dalla policy (https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/).
- Nessun deploy GitHub Pages/Cloudflare, merge su main, query reali, modifica Oracle, Mac, utente reale o nuova spesa introdotti. Le quattro pagine private pinned v0.78 LAB e la nuova anteprima statica iPhone v0.87 sono immutate.

## Roadmap coordinata, non perdere le priorità
1. **Priorità vera**: acquisire una prova attuale in sola lettura di D1 daily e posti Access reali, con autorizzazione specifica e verifica del margine gratuito. Il piano v0.86 per max due GraphQL POST su oggi/ieri resta preparato e **NON eseguito**. Se metrica vuota, NO-GO.
2. **Pilot collaboratori**: dopo le verifiche, staging privato isolato, deny-default Access, ruoli JWT+D1 verificati lato server, fixture separata, collaudo Safari login/logout/revoca e rollback. Invito di 1–2 amici soltanto con autorizzazione. Vedono REMURA, ma propongono solo propri livelli, OWNER approva/audita; original-level e amendment distinti, RESERVED senza retry/auto-release. Telegram livelli solo dopo approvazione e consenso.
3. **TradingView**: v0.8.186 LAB `research/tradingview-anchor-request-v0186-20261121`, HEAD `c1a35edfeb914fc5f24564b5ca2f11994bc9ee0d`, CI 16/16 PASS. Holdout1 23–29 novembre UTC e holdout2 30 novembre–6 dicembre UTC. Non inventare catture o timestamp e non anticipare outcome. Anchor non attestato, alpha non dimostrato.
4. **Shark Science**: v0.4 LAB `research/track-b-shark-science-20261104` HEAD `05e731b26bccb167ba7e0859797de01136a5c933`. Il dossier TV/Shark `research/tv-shark-source-bridge-20261121` HEAD `9bd7004246d5bb74c66c61f9ce8de044f1ae1c2f` identifica mapping/first-seen/identità decisione come blocchi veri; non duplicare moduli COT, retail, CVD già presenti.
5. **Experience** v0.30 LAB splash toro/orso 3D collisione/esplosione, REMURA pinna e SMF, rimuovere foto; Safari fisico in futuro.
6. **Oracle** collector attivo, autoupdater bloccato, v1.65 signed root-owned staged **NON installare**, Ampere Radar v0.36 Milano/Telegram operativo; Private Capture v0.15 LAB solo sintetico, backup reale, Squalincome e notifiche Telegram approvate sulla roadmap.
7. Controllare Free periodicamente, mai confondere mancanti con zero o un verde offline con prova provider. Nessun test storico ripetuto. Quando chat pesante, passaggio completo con SHAs e run ID.

**v0.88 LAB 22/22 PASS, utility locale disponibile nel repository; conto reale e staging rimangono NON attestati / NO-GO.**
