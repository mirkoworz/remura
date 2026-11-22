# REMURA Shark Cockpit v1.67 LAB — Pulse movimenti istituzionali
22 novembre 2026, 21:41 CET (Europe/Rome).

## Nuova funzionalita' prodotto reale
Aggiunta a shark-cockpit.html una sezione visibile **Le mosse piu' grandi dei fondi**. Presenta fino a 6 contratti CFTC selezionati dai dati settimanali gia' caricati nel browser. Ciascuna card mostra il contratto, la specifica categoria Asset Manager/Leveraged Funds o Managed Money/Producer Merchant, la variazione in punti percentuali del netto futures/OI, la direzione della variazione e un pulsante per aprire la scheda approfondita.

I nuovi moduli shark-movers-core.js e shark-movers-ui.js non fanno richieste di rete. Il modulo di calcolo applica regole fail-closed: deve esserci un report recente e una settimana immediatamente precedente con delta valido; non aggrega martedi' diversi. Se ci sono report differenti seleziona solo l'ultima data comune nel set corrente e scrive chiaramente quante osservazioni sono state escluse. Se mancano prove o sono discordanti, visualizza N/D e zero movimenti inventati. Non interpreta il delta come trade, quote Forex spot, posizione nominativa, prezzo o segnale.

La vista rispetta i filtri di famiglia, ricerca e ★ preferiti gia' presenti; il click sulla card scorre alla scheda del future, senza navigazioni esterne o comunicazioni aggiuntive. Nessun backend nuovo e nessun effetto su Oracle, Cloudflare, CVD, Mac Experience, Contributors o TradingView.

## Files di prodotto
- shark-movers-core.js: funzione pura scan() e discriminazione dei report per data martedi' uguale.
- shark-movers-ui.js: DOM con textContent, pulsanti accessibili per iPhone, zero fetch.
- shark-cockpit.html + shark-cockpit.js + shark-cockpit.css: montaggio reale nella schermata esistente; target delle schede per navigazione.
- sw.js: shell cache remura-shell-v81-v1.67-shark-cockpit-movers-preview con i nuovi asset; i dati CFTC non diventano cache 'live'.
- nav.js e 10 pagine HTML: versione/testo in alto v1.67 LAB · 22/11/2026 21:41 CET, cache bust nav.js?v=167.
- tests/shark-movers.test.js: 12 test mirati nuovi; i 33 test del cockpit e delle pagine versionate devono essere rieseguiti solo per la reale modifica ai loro file; suite storiche trading/Oracle/COT non ripetute.
- .github/workflows/remura-shark-cockpit-v167-movers.yml: workflow sul solo branch/path modificato, read-only, senza Secrets, provider, deploy.

## NO DEPLOY
Questa e' una pagina web completa nel branch LAB, ma non e' ancora pubblicata su GitHub Pages e non e' ancora stata visitata direttamente su Safari iPhone. La pubblicazione/preview vera richiede autorizzazione distinta e verifica del margine Free. L'URL GitHub blob e' soltanto codice, non anteprima web navigabile.

Non rimuovere la separazione: COT futures per settimana, Myfxbook retail distinto, CVD prospettico ancora da verificare. Holdout V2 dal 23/11 00:00 UTC non retrodata nessun dato. Aucun alpha dichiarato.
