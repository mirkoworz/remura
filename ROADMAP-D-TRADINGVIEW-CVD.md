# REMURA — FILONE D: TradingView FXCM / Shark CVD (sperimentale)

**Apertura:** 09/11/2026 (Europe/Rome). **Versione laboratorio:** D0.1. **Stato:** codice isolato, NON LIVE, NON VALIDATO SU TRADINGVIEW.

**Ramo:** `experiment/track-d-tv-fxcm-cvd-20261109`. Nessun merge, deploy, servizio, connettore VPS, endpoint pubblico o nuova API. Non cambiare versione applicativa LIVE: un esperimento Pine non è un aggiornamento delle nove pagine REMURA.

## Perché questo filone

L'utente dispone già di TradingView Premium e della watchlist **FXCM**. Screenshot del 09/11/2026: `FXCM:EURUSD`, grafico 5m, volume visibile. Non è stata misurata la latenza effettiva dei dati. Futures CME/COMEX su TradingView risultano ritardati senza pacchetto dati aggiuntivo, perciò la prima prova utilizza EURUSD FXCM senza acquistare niente.

**Ipotesi falsificabile:** il CVD *stimato* da OHLC + volume Forex dei minuti 1m, aggregato a 5m, migliora il potere predittivo delle sole divergenze di prezzo o di una semplice baseline prezzo+ATR. Il volume FXCM può essere tick volume/volume del singolo feed, NON contratti eseguiti sull'intero Forex né aggressor side istituzionale.

Diverso dal proxy cTrader `CLV × tick volume` già esistente in REMURA/PR #77: non mischiare i due indicatori, le sorgenti, le unità, le sessioni e gli orari. Il nuovo modello si chiama `remura_fxcm_1m_cvd_d0.1`.

## Architettura sperimentale

1. **TradingView Pine v6**, indicatore locale `experiments/tradingview/remura_shark_cvd_fxcm_v01.pine`: grafico limitato a `FXCM:EURUSD` 5m; `request.security_lower_tf(..., "1", [open,close,volume])`. Ogni minuto viene polarizzato per direzione open→close, con tie-break sull'ultimo close/direzione osservata; la somma produce un delta 5m. CVD si azzera con il nuovo giorno del feed `time("D")`.
2. **Qualità prima di segnali:** valutazione soltanto a candela 5m chiusa, obbligo di cinque barre 1m disponibili, niente volume NA/negativo, niente gap tra barre 5m nella stessa giornata. Un buco invalida la sessione per il resto della giornata (fail closed). Questo è deliberatamente severo: registrare la frequenza dei blocchi, non scambiarli per assenza di opportunità. Storico 1m limitato da piano e feed; non dedurre disponibilità di intere sessioni dal solo grafico corrente.
3. **Divergenza regolare e causale:** due minimi di prezzo (LL) con CVD più alto ai **medesimi** timestamp (HL), oppure due massimi prezzo (HH) con CVD minore (LH). Pivot 2+2 5m come impostazione iniziale; secondo pivot conoscibile solo dopo 2 barre destre: l'alert porta orario pivot e orario rilevamento distinti. Nessun confronto tra reset giornalieri.
4. **Alert solo sperimentali:** `sendResearchAlerts=false` di default, JSON dinamico con fonte, algoritmo, tipo, ID, prezzo, CVD, tempo pivot e riconoscimento. Non contiene entrate/SL/TP/ordini. Nessun webhook viene creato o attivato da GitHub: gli alert esistono soltanto quando l'utente incolla, salva e configura Pine su TradingView e abilita esplicitamente l'opzione.
5. **Futura integrazione:** soltanto dopo prova manuale dei payload, ricevitore HTTPS pubblico minimo e isolato; validazione schema, limite dimensione, timestamp, deduplica event_id, rate limit, niente segreti in URL o codice, inbox append-only e consenso esplicito. L'attuale VPS privata/Tailscale non è raggiungibile direttamente da webhook TradingView; valutare sicurezza, esposizione e quote **prima** di aprire endpoint. Un alert TradingView può perdersi; usare stato consegna/replay e mai assumere exactly-once.

## Roadmap Filone D

- [x] **D0 — inventario e branch:** schermate confermano `FXCM:EURUSD` e volumi; ramo separato da `main`; PR #77 e PR #89 già esistenti, evitare duplicazioni.
- [x] **D1 — prototipo sorgente Pine (non compilato):** calcolo 1m→5m, reset, qualità, pivot confermati, JSON opzionale e controllo rigoroso FXCM:EURUSD.
- [ ] **D1a — compilazione Pine su TradingView:** incollare il file in Pine Editor, salvare, verificare compilazione, grafico e valori; documentare eventuali correzioni; non certificare Pine compilato tramite soli test Python.
- [ ] **D1b — confronto CVD:** osservare 30+ candele confermate su sessioni distinte, confrontare il delta cumulato con l'indicatore CVD standard TradingView in modalità aggregata 1m, annotare differenze da tie-break, sessione, precisione, lacune e feed. Non paragonare un proxy al tick-based nativo come se fossero lo stesso dato.
- [ ] **D2 — test causali:** dati sintetici per due pivot, no look-ahead, barre mancanti, periodi giornalieri, tie e prezzo flat. Poi archiviare esempi prospettici *originali*, incluse occasioni senza segnale.
- [ ] **D3 — test alert senza VPS:** alert solo per ricerca (facoltativo), verificare JSON nel registro TradingView, un evento per pivot, deduplica, consegna potenzialmente fallita, no alert storici. Abilitare webhook esterni solo dopo autorizzazione e audit sicurezza.
- [ ] **D4 — protocollo statistico indipendente:** fissare parametri prima del periodo test, train/validation/test cronologico (coerente con B), baseline solo prezzo e prezzo+ATR, segni e risultati a 1h/4h/24h, spread/slippage, falsi positivi, intervalli di confidenza, data-snooping, walk-forward. Le caratteristiche calcolate dallo stesso prezzo non vanno trattate come fonti indipendenti.
- [ ] **D5 — decisione GO/NO-GO:** se non c'è miglioramento netto fuori campione, fermare la promozione; se c'è, valutare replicazione OANDA, futures veri e integrazione con Shark Science senza alterare i risultati del test originario.

## Costi e vincoli gratuità

- Il codice su GitHub non richiede feed futures, nuovi abbonamenti, endpoint né chiamate aggiuntive alla VPS.
- Premium TradingView è **già pagato**, non è un servizio gratuito in assoluto. Alert e richieste dati sono soggetti a quote TradingView, limiti disponibili sul piano e feed. Nessun dato futures real-time compreso nel prototipo.
- I webhook TradingView richiedono autenticazione a due fattori, destinazione pubblica HTTP(S) su porta 80/443 e timeout <=3s; possono fallire. Non esporre Tailscale/VPS o token e non creare tunnel/funnel in questo filone senza approvazione.
- Se una futura integrazione modifica REMURA app LIVE, si torna al gate unico A/B/C: aggiornare versione e data/ora effettiva italiana **in alto su tutte le nove pagine**, CI, backup/restore-test/rollback e deploy coordinato. D0.1 non modifica UI, cloud o produzione.

## Fonti tecniche
- CVD stimato: https://www.tradingview.com/support/solutions/43000725058-cumulative-volume-delta/
- Richieste lower timeframe: https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
- Alert dinamici: https://www.tradingview.com/pine-script-docs/concepts/alerts/
- Webhook, 2FA e limiti: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/

**Coordinamento:** non toccare `ROADMAP-B-SHARK-SCIENCE.md`, `ROADMAP-A-H1.md`, collector, Oracle, PR #89, PR #99, main o pagine applicative. Questo file è la roadmap del Filone D fino a integrazione governata nella roadmap principale.
