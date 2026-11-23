# REMURA Filone D — SHARK COCKPIT v1.70 LAB (COT TRENDS)
**Checkpoint:** 23/11/2026, dalle 15:01 CET (Europe/Rome). HTML timbrati v1.70 LAB / 23/11/2026 15:01 CET.
**Ramo indipendente:** `feature/shark-cockpit-v170-cot-trends-iphone-20261123`.
**Deriva da:** `feature/shark-cockpit-v169-evidence-iphone-20261123` (la v1.69 è stata dichiarata funzionante su Safari iPhone dall'utente).
**Rilascio:** nessun merge, nessun deploy, nessuna modifica alla produzione.

## Cosa è stato costruito
- `shark-trends-core.js`: prepara, senza fetch, 2 tracciati dalle sole osservazioni reali CFTC restituite da `core.historyFor()` (fino a 12 martedì ordinati). Metrica: netto long-short normalizzato su open interest (% OI); non è prezzo, volume eseguito, ordine o CVD.
- `shark-trends-ui.js`: SVG accessibile a colori diversi per le categorie TFF (Asset Manager / Leveraged Funds) e Disaggregated (Managed Money / Producer-Merchant). Puntini per report osservati, linee solo fra martedì consecutivi: nessuna interpolazione.
- Assi in percentuale OI, con zero visibile e tempo sull'asse orizzontale proporzionale ai giorni reali. Martedì mancanti lasciano un gap e spezzano le linee; le revisioni discordanti vengono escluse.
- `shark-cockpit.js`: il grafico appare nel pannello «Trend COT e storico reale» della singola scheda senza ulteriori chiamate alla CFTC; la tabella dei report rimane leggibile e utile per il confronto.
- `shark-cockpit.html`, `shark-cockpit.css`: versione e data in cima, guida di lettura, layout Safari iPhone, etichette di provenance.
- `sw.js`: shell statica v84 con due nuovi asset; **mai** scambiare cache per COT live.
- `preview/REMURA-Shark-COT-Trends-v170-iPhone-STANDALONE-LAB.html`: pagina singola HTML con 8 script inline, CSS inline, nessun JS esterno. Per la sola anteprima Myfxbook viene letto lo snapshot pubblico esistente su GitHub main; i collegamenti retail puntano a REMURA Pages.

## Verifiche
- Sette controlli mirati effettivamente eseguiti in runtime JS isolato, tutti PASS: assenza dati, martedì consecutivi, gap, zero negli assi, date non valide, valori non validi, collegamenti statici HTML/JS/SVG/PWA/preview.
- `tests/shark-trends.test.js`: sette nuovi test Node nel repository, non dichiarati come esecuzione CI autonoma finché il workflow non è verificato.
- Workflow `.github/workflows/remura-shark-cockpit-v170-trends.yml` predisposto per test di regressione UI interessati (target 69/69, partendo dal target v1.69 di 62/62). Job solo lettura e fixture offline, timeout 4 minuti, nessun secret e nessun deploy. **Non dichiarare 69/69 verdi senza log CI.**
- Safari v1.69: user conferma funzionalità. Safari **v1.70**: prova visuale grafici/scroll/CFTC non ancora attestata, resta un gate di rilascio.
- Nessun nuovo prezzo CVD acquisito e nessuna validazione Filone A eseguita.

## Free-first e confini
- I grafici leggono lo storico già caricato dall'app in memoria; zero nuove richieste API di mercato, zero nuovi database, D1, Firestore, Workers o hosting.
- GitHub Actions può consumare minuti del piano e gli utenti nel browser effettuano le chiamate CFTC/retail già previste. Costi e quota residua degli altri componenti non sono stati verificati qui.
- Nessuna modifica a Splash 3D Toro/Orso/SMF Mac/Codex, collector, Contributors backend, Oracle, Cloudflare o calcolo scientifico CVD / Filone A.
- Non dedurre direzione futura dei prezzi, timing degli ordini o alpha dal COT settimanale.

## Passi successivi
1. Verificare l'esito CI v1.70 senza ripetere suite storiche superate.
2. Aprire volontariamente su Safari iPhone la preview statica v1.70 e controllare grafici con almeno due martedì realmente leggibili, casi N/D e settimane mancanti.
3. Proseguire dashboard solo UI (eventuale focus preferiti/qualità per asset) sullo stesso ramo o nuova versione indipendente; release con gate coordinato e consenso esplicito, non ora.
