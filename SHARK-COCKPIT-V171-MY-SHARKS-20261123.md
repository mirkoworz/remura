# REMURA — Filone D · Shark Cockpit v1.71 LAB · MY SHARKS
**Checkpoint:** 23 novembre 2026, ore 20:20 CET (Europe/Rome).
**Branch UI:** `feature/shark-cockpit-v171-my-sharks-iphone-20261123`, derivato da `feature/shark-cockpit-v170-cot-trends-iphone-20261123`.
**Contesto:** Shark Cockpit v1.69 funzionava su iPhone/Safari per conferma utente; v1.70 era stata preparata con grafici COT e 7 verifiche mirate. Nessun merge o deploy delle versioni LAB.

## Incremento costruttivo
- Nuova sezione **★ I miei squali** subito dopo l'hero, con link da navigazione rapida iPhone.
- `shark-focus-core.js`: lettura *in memoria* delle card CFTC già fornite da `shark-cockpit-core.js` e dei codici preferiti salvati con la chiave esistente `remura:shark:favorite-cftc:v166`.
- La whitelist è riutilizzata dal core storico, quindi nessun futuro sconosciuto, duplicato o arbitrario entra nella vista.
- Stati per contratto: CONFRONTABILE (report recente, due martedì consecutivi), SOLO_REPORT (WoW non verificabile), DATATO, CONFLITTO e NON_DISPONIBILE.
- Ordinamento di consultazione: **qualità → data del report → ampiezza della variazione in punti percentuali** solo per elementi di pari data. Se le variazioni recenti appartengono a martedì diversi, l'interfaccia avverte che non descrivono lo stesso periodo.
- Ogni preferito mostra data del report, stato, variazioni delle categorie solo quando ammesse; nessuna direzione del prezzo, score di trading o previsione.
- `shark-focus-ui.js`: schede touch-friendly con rimozione stella e pulsante **Apri radiografia e storico**. Il pulsante azzera solo i filtri visuali che nascondono il contratto, lo apre e posiziona lo scroll sulla scheda. I dati e la watchlist rimangono invariati.
- `shark-cockpit.html`, `shark-cockpit.css`, `shark-cockpit.js`, `sw.js` aggiornati; timestamp **v1.71 LAB · 23/11/2026 20:20 CET (Europe/Rome)** in cima all'HTML modificato e nella preview.
- Cache PWA shell v85 con due moduli aggiunti; nessuna cache di nuove API live, nessun backend.
- Preview iPhone singolo file: `preview/REMURA-Shark-Focus-v171-iPhone-STANDALONE-LAB.html`. Include CSS e 10 script inline, con i consueti URL pubblici per CFTC e snapshot Myfxbook. Nessuna credenziale, API privata o file del Mac.
- I test UI storici interessati hanno soltanto le stringhe di wiring/versione allineate (v171 e cache v85); non è stata modificata la matematica COT, il CVD o il funzionamento backend.

## Verifiche svolte
- **8/8 verifiche puntuali eseguite** in JS isolato sul codice GitHub realmente recuperato: lista vuota, codici ammessi, due report confrontabili, settimane mancanti, stale/conflitti, ordinamento per data, divieto di segnale, script/markup standalone.
- Verifica sintattica JS del core e dei file UI coinvolti mediante parsing JS senza esecuzione di rete.
- `tests/shark-focus.test.js`: 8 test Node nuovi scritti nel repository.
- **Non dichiarare CI completa verde:** non è stata lanciata una nuova Actions run e non sono disponibili log finali sul workflow precedente; l'esito di un collaudo integrato resta un gate.
- **Safari v1.71** non ancora provato dall'utente. La preview non è una distribuzione di produzione.

## Costi, sicurezza e confini
- Zero nuovi GET di mercato: le schede focus derivano da `cards` già in memoria e dalla watchlist locale Safari. Nessun D1, Workers, Firestore, Oracle, acquisizione extra, Secret, API key o servizio paid.
- Nessuna esecuzione Actions aggiuntiva in questa lavorazione (8 verifiche nel runtime JS isolato). Non abbiamo verificato Billing/quote residue di tutti i prodotti, quindi non dichiarare l'intero sistema gratis in assoluto.
- Nessun lavoro a Splash 3D Toro/Orso/SMF Mac/Codex, Contributors backend, valutazione prezzi/CVD Filone A, Filone B, collector privato o produzione.
- Nessun deploy, merge o attivazione utenti, notifiche o automazioni trading.

## Release gate / prossimi passi
1. Collaudo volontario dell'anteprima v1.71 in Safari iPhone: selezione/rimozione stelle, visita diretta alla radiografia, gestione filtri, schermata vuota e CFTC se disponibile.
2. Verifica CI integrata prima del rilascio e controllo reale delle quote Free per i servizi coinvolti.
3. Coordinare in release futura versioni di tutte le pagine e Splash Mac senza sovrapporre i filoni; non farlo su questo ramo.
4. Possibile successivo miglioramento UI: comparatore storico fra report settimanali solo per contratti selezionati, mai come previsione prezzo o correlazione CVD senza Filone A.

**Nota scientifica:** il COT descrive posizioni aggregate di futures e non dimostra movimenti individuali né anticipazione assicurata degli istituzionali.
