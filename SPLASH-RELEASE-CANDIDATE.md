# REMURA — Splash squalo/remura (candidato, 05/11/2026 Italia)

**Stato:** sviluppo isolato, NON LIVE, nessun deploy né merge su main. Il sistema operativo attestato rimane v1.62 finché una release unica coordinata non lo sostituisce.

## Comportamento implementato
- La sola `index.html` (start_url della PWA iPhone) monta lo splash prima del contenuto. I rientri alla Home con referrer stessa origine non lo riproducono.
- Mascotte approvata dall'utente, alleggerita in `splash-mascot.webp`, tenuta in locale e precaricabile dal service worker; palette blu navy/turchese.
- Squalo SVG a sinistra, remura SVG a destra: posizione della remura e barra legate alla stessa percentuale; aggancio al 100%, dissolvenza e apertura della Home.
- Tempo minimo in condizioni normali ~1,85 s + ~0,42 s animazione finale. Riduzione animazioni per le impostazioni di accessibilità iOS.
- **Un solo** fetch GET same-origin all'endpoint `./private-api/health` già presente, cache no-store, credentials same-origin, timeout 1,1 s. Questo è soltanto un **health tecnico**, NON dimostra stato aggiornato del COT, sentiment o prezzi, salute SQLite né segnale di trading. Nessuna nuova chiamata cTrader/Myfxbook/CFTC/Firestore.
- Se health fallisce o va in timeout, lo splash conclude e apre l'app con avviso di disponibilità non verificata. Fail-safe massimo 4,5 s.
- Banner reale con versione e data/ora viene letto dal banner condiviso di `nav.js` (non contiene timestamp fittizi). `nav.js` e gli altri otto HTML non cambiano.
- `sw.js` include i tre asset in STATIC mantenendo **per ora** il nome cache v1.62: il bump SW/ver/versione si effettua solo nella release coordinata.

## Passaggio successivo: gate v1.63 (NON eseguito)
1. Eseguire CI `splash-checks` e le CI Price/Insights, fare verifica manuale su PWA Safari iPhone: cold start, warm start, ritorno alla Home, connessione assente e modalità riduzione movimento.
2. Coordinare con Track A/B prima di qualsiasi merge/deploy: al momento vi sono rami scientifici parallelizzati. Rileggere SHA attuali main/LIVE e data bot Myfxbook, senza sovrascrivere modifiche.
3. Preparare **v1.63** con banner `nav.js` e asset URL `nav.js?v=163` in **tutte le nove pagine**, SW cache v1.63, timestamp Italiano **effettivo al deploy** (non adesso), piano di restore/rollback e reconciliation autoupdater secondo il gate precedente.
4. Installare solo con release protetta, backup SQLite + restore-test offline, rollback operativo, verifica SHA app/autoupdater, 9/9 pagine e contatori API/costi.
5. Testare velocità e qualità grafica sul dispositivo reale; se la piccola mascotte WebP risultasse poco nitida, sostituirla con copia ottimizzata a risoluzione maggiore senza cambiare la logica.

## Costi
Zero provider nuovi, nessuna API finanziaria aggiunta. L'unica GET health va **aumentare di uno** il contatore locale delle richieste a Oracle per ogni avvio dall'Home. Carico e traffico molto ridotti ma non è lecito dichiarare spesa cloud effettiva zero senza verificare il billing dei portali. La CI GitHub è on-demand con attivazione su PR e timeout di cinque minuti; nessun cron aggiunto.
