# REMURA — FILONE D: TradingView FXCM / Shark CVD (sperimentale)

**Apertura:** 09/11/2026 (Europe/Rome). **Versione laboratorio:** D0.2 (10/11/2026 ore 07:14 Italia). **Stato:** D0.1 compilato su TradingView ma fermato dal controllo iniziale; D0.2 eseguito su TradingView con diagnostica funzionante: grafico attivo `FX:EURUSD`, timeframe 5m, mentre la sperimentazione richiede `FXCM:EURUSD`. Prova CVD su FXCM ancora DA VERIFICARE. NON LIVE.

**Ramo:** `experiment/track-d-tv-fxcm-cvd-20261109`. Nessun merge, deploy, servizio, connettore VPS, endpoint pubblico o nuova API. Non cambiare versione applicativa LIVE: un esperimento Pine non è un aggiornamento delle nove pagine REMURA.

## 10/11/2026 — Riscontro runtime D0.2 (screenshot PC)

- [x] L'indicatore D0.2 si avvia e mostra la tabella diagnostica senza il vecchio errore `RE10142`.
- [x] Screenshot sul PC: `REMURA D0.2 | SORGENTE/TIMEFRAME ERRATO`; riga `Letto: FX:EURUSD | TF=5` e indirizzo grafico con `symbol=FX%3AEURUSD`. **Il timeframe è corretto, il provider/simbolo NON è FXCM**. Arancione e CVD assente sono quindi il comportamento previsto dal blocco di qualità, non un difetto numerico dimostrato.
- [ ] **Prossimo unico controllo:** cambiare simbolo nel selettore TradingView in **`FXCM:EURUSD`**, mantenere 5m e D0.2 già installato, verificare `Letto: FXCM:EURUSD | TF=5` con riga verde e CVD presente. Solo allora studiare eventuali mancanze delle barre 1m. Nessun nuovo codice, nessun allentamento dei gate, nessuna nuova spesa.
- [ ] L'avvio su un grafico errato NON dimostra correttezza del CVD, supporto della serie volume in tutti i minuti, validità statistica o possibilità di inviare alert al cloud.

## Perché questo filone

L'utente dispone già di TradingView Premium e della watchlist **FXCM**. Screenshot del 09/11/2026: `FXCM:EURUSD`, grafico 5m, volume visibile. Non è stata misurata la latenza effettiva dei dati. Futures CME/COMEX su TradingView risultano ritardati senza pacchetto dati aggiuntivo, perciò la prima prova utilizza EURUSD FXCM senza acquistare niente.

**Ipotesi falsificabile:** il CVD *stimato* da OHLC + volume Forex dei minuti 1m, aggregato a 5m, migliora il potere predittivo delle sole divergenze di prezzo o di una semplice baseline prezzo+ATR. Il volume FXCM può essere tick volume/volume del singolo feed, NON contratti eseguiti sull'intero Forex né aggressor side istituzionale.

Diverso dal proxy cTrader `CLV × tick volume` già esistente in REMURA/PR #77: non mischiare i due indicatori, le sorgenti, le unità, le sessioni e gli orari. Il nuovo modello si chiama `remura_fxcm_1m_cvd_d0.2` (D0.1 storico non interoperabile per aggregazione scientifica).

## Architettura sperimentale

1. **TradingView Pine v6**, indicatore locale `experiments/tradingview/remura_shark_cvd_fxcm_v01.pine`: grafico limitato a `FXCM:EURUSD` 5m; `request.security_lower_tf(..., "1", [open,close,volume])`. Ogni minuto viene polarizzato per direzione open→close, con tie-break sull'ultimo close/direzione osservata; la somma produce un delta 5m. CVD si azzera con il nuovo giorno del feed `time("D")`.
2. **Qualità prima di segnali:** valutazione soltanto a candela 5m chiusa, obbligo di cinque barre 1m disponibili, niente volume NA/negativo, niente gap tra barre 5m nella stessa giornata. Un buco invalida la sessione per il resto della giornata (fail closed). Questo è deliberatamente severo: registrare la frequenza dei blocchi, non scambiarli per assenza di opportunità. Storico 1m limitato da piano e feed; non dedurre disponibilità di intere sessioni dal solo grafico corrente.
3. **Divergenza regolare e causale:** due minimi di prezzo (LL) con CVD più alto ai **medesimi** timestamp (HL), oppure due massimi prezzo (HH) con CVD minore (LH). Pivot 2+2 5m come impostazione iniziale; secondo pivot conoscibile solo dopo 2 barre destre: l'alert porta orario pivot e orario rilevamento distinti. Nessun confronto tra reset giornalieri.
4. **Alert solo sperimentali:** `sendResearchAlerts=false` di default, JSON dinamico con fonte, algoritmo, tipo, ID, prezzo, CVD, tempo pivot e riconoscimento. Non contiene entrate/SL/TP/ordini. Nessun webhook viene creato o attivato da GitHub: gli alert esistono soltanto quando l'utente incolla, salva e configura Pine su TradingView e abilita esplicitamente l'opzione.
5. **Futura integrazione:** soltanto dopo prova manuale dei payload, ricevitore HTTPS pubblico minimo e isolato; validazione schema, limite dimensione, timestamp, deduplica event_id, rate limit, niente segreti in URL o codice, inbox append-only e consenso esplicito. L'attuale VPS privata/Tailscale non è raggiungibile direttamente da webhook TradingView; valutare sicurezza, esposizione e quote **prima** di aprire endpoint. Un alert TradingView può perdersi; usare stato consegna/replay e mai assumere exactly-once.

## Roadmap Filone D

- [x] **D0 — inventario e branch:** schermate confermano `FXCM:EURUSD` e volumi; ramo separato da `main`; PR #77 e PR #89 già esistenti, evitare duplicazioni.
- [x] **D1 — prototipo sorgente Pine (non compilato):** calcolo 1m→5m, reset, qualità, pivot confermati, JSON opzionale e controllo rigoroso FXCM:EURUSD.
- [ ] **D1a — prova TradingView aggiornata:** schermata utente 10/11/2026 ore 07:11 Italia: `REMURA CVD D0.1` è stato accettato dal runtime, ma errore `RE10142` / `Error on bar 0` / `#main():19`, causato dall'`if` iniziale che controllava `syminfo.prefix`, `syminfo.ticker` e `timeframe.period` senza mostrare quale dato fosse diverso. Lo screenshot mostra 5m ed EURUSD; il provider FXCM era stato confermato in screenshot precedente, ma non abbiamo osservato **direttamente** il valore delle variabili Pine. Patch D0.2: usa `ticker.standard(syminfo.main_tickerid)` e `timeframe.isminutes && timeframe.multiplier == 5`, stampa `Letto: <ID> | TF=<period>` nel pannello, elimina `runtime.error` e sopprime CVD/eventi/alert su grafici non corrispondenti. **Non affermare che D0.2 funzioni** finché l'utente non lo ricarica e invia uno screenshot del pannello.
- [ ] **D1a-bis — gate runtime:** se D0.2 indica `FXCM:EURUSD | TF=5` ma il CVD resta vuoto/arancione, controllare copertura 1m, buchi 5m e reset sessione: non disattivare il fail-closed per ottenere una linea fittizia.
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
