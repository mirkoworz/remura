# REMURA v1.68 LAB — Shark Anatomy su iPhone
22 novembre 2026, ore 22:10 CET (Europe/Rome)

## Funzionalita' costruita
Dalle posizioni CFTC settimanali gia' caricate da Shark Cockpit, senza nuovi provider, il pulsante **"Radiografia del movimento · long e short reali"** nelle 14 schede futures mostra per ciascuno dei due gruppi di operatori:

- totale contratti long e short nel report CFTC recente, separati;
- variazione long/short in **numero di contratti** rispetto al martedi' precedente;
- netto (long minus short) in contratti e relativa variazione;
- differenza del netto normalizzato sull'open interest, in punti percentuali;
- open interest corrente e variazione settimanale.

Le categorie sono Asset Manager / Leveraged Funds per TFF; Managed Money / Producer-Merchant per Disaggregated. Il calcolo deriva dalle stesse righe CFTC che alimentano le card, non interroga CFTC altre volte. I report devono essere recenti e per due martedi' consecutivi; se manca uno, e' vecchio o ci sono revisioni discordanti, N/D. I valori **NON** provano ingressi, acquisti, ricoperture short, chiusure individuali, identita' dei fondi, ordini real-time o direzione futura dei prezzi.

## Dove si trova
Branch: feature/shark-cockpit-v168-flow-anatomy-20261122
- shark-cockpit-core.js: funzione pura anatomyFor, con gating stato del report e controllo settimana, oltre al modulo della v1.67.
- shark-cockpit.js: pannello espandibile per strumento su iPhone, senza nuovi fetch, apribile sotto la scheda.
- shark-cockpit.css e shark-cockpit.html: interfaccia mobile e nota esplicativa.
- nav.js e tutte le 10 pagine dell'anteprima: v1.68 LAB e timestamp 22/11/2026 22:10 CET nella barra alta, script nav.js?v=168.
- sw.js: cache shell statica v82-v1.68, senza memorizzare come live le GET CFTC.
- tests/shark-anatomy.test.js: 12 nuovi test di funzionalita' e integrita' di dati, piu' le 45 verifiche della pagina/menu gia' interessate.
- .github/workflows/remura-shark-cockpit-v168-anatomy.yml: 57 verifiche mirate, permission read-only, niente Secret/deploy.

## CI verificata
Run iniziale 45070861265: 56/57 per una vecchia stringa v1.67 in un test di wiring (non un errore sui calcoli).
Run finale [45070919371](https://github.com/mirkoworz/remura/actions/runs/45070919371): SUCCESS, log reali '# tests 57', '# pass 57', '# fail 0', REMURA_SHARK_COCKPIT_V168=57_57_PASS, commit 5774604d6b40eea60fb8589b9ffe78ad12ba703d.

## File unico realmente apribile su Safari in anteprima
preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html, primo commit 21f7871d153cdad8f894283afb147d3059f62cce.

Visualizzatore gratuito di terze parti (non hosting REMURA ufficiale):
https://raw.githack.com/mirkoworz/remura/21f7871d153cdad8f894283afb147d3059f62cce/preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html

GitHub file originale:
https://github.com/mirkoworz/remura/blob/feature/shark-cockpit-v168-flow-anatomy-20261122/preview/REMURA-Shark-Anatomy-v168-iPhone-STANDALONE-LAB.html

Assemblaggio statico inline di CSS e dei quattro moduli JS; 59.491 caratteri, senza script esterni, URL relativi, autenticazione o chiavi. GET pubblico CFTC e snapshot retail pubblico GitHub invariati. La versione precedente V15 risulta aperta e funzionale su Safari secondo conferma utente; la nuova V16 NON ha ancora conferma visiva o proof CFTC CORS/dati. Raw.githack puo' raccogliere IP/user-agent: non fornire password, dati privati o token su questo servizio. Se Safari segnala phishing non aggirare il blocco.

## Cosa rimane fuori
Nessun nuovo deploy o merge sul sito principale, Cloudflare/Oracle, database/ingest live, trading automatico o registrazione Contributor. CVD prospettico non validato, holdout V2 inizia 23 novembre alle 00:00 UTC e richiede primi timestamp indipendenti realmente raccolti. Contributori v0.94 esistono gia' in LAB: non duplicare i form e non attivare senza Access/D1, margini Free e autorizzazione. Mac Codex conserva Experience Toro-Orso e collector Oracle.

## Passo successivo
Verificare sul Safari iPhone la nuova apertura del pannello, i valori long e short e la corretta etichetta delle categorie. Se tutto funziona, portare il modulo in una preview su dominio REMURA autonomo soltanto dopo permesso esplicito e quota Free. Non eseguire nuovi test storici del CVD/COT per questa modifica di UI.
