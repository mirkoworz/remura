# REMURA — FILONE D: TradingView FXCM / Shark CVD (sperimentale)

**Apertura:** 09/11/2026 (Europe/Rome). **Versione laboratorio:** D0.5 (10/11/2026, Italia). **Stato:** D0.4 non compilava per parentesi mancante su `table.cell` (CE10015), corretta e confermata compilabile dall'utente. Il grafico CVD rimane vuoto; non abbiamo ancora visto il conteggio 1m né l'esatto stato dati. D0.5 diagnostica separata NON ANCORA COMPILATA/VALIDATA su TradingView. NON LIVE.

**Ramo:** `experiment/track-d-tv-fxcm-cvd-20261109`. Nessun merge, deploy, servizio, connettore VPS, endpoint pubblico o nuova API. Non cambiare versione applicativa LIVE: un esperimento Pine non è un aggiornamento delle nove pagine REMURA.

## 10/11/2026 — D0.5: compilazione confermata D0.4, CVD vuoto e diagnosi della copertura

- [x] Nuova prova utente: Pine D0.4 segnala `CE10015 Missing closing parenthesis` alla riga 140, chiamata `table.cell`. Corretta aggiungendo `)`, confermata la compilazione dall'utente; il grafico CVD continua a rimanere **vuoto**. Il successo della compilazione NON verifica disponibilità dei volumi 1m o correttezza del CVD.
- [x] Difetto logico nel prototipo: `validSession := false` al primo 5m non perfettamente completo, mantenuto fino al prossimo reset giornaliero; quando TradingView limita gli intrabar storici o una 5m è incompleta, può non esserci alcuna linea pur con dati successivi validi. Gli array da `request.security_lower_tf` possono contenere meno di cinque minuti o essere vuoti; vedere https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/.
- [x] Creato `experiments/tradingview/remura_shark_cvd_fx_v05.pine`, modello `remura_fx_1m_cvd_d0.5`. Presenta **due curve distinte**: verde CVD giornaliero solo se la sessione parte dall'ancora giornaliera ed è integra; arancione **CVD PARZIALE (NO SIGNAL)** ricostruito da almeno due barre 5m consecutive con cinque minuti completi. Dopo ogni gap la curva arancione riparte da zero e non collega segmenti separati. Non si chiama mai CVD di giornata e non entra nei pivot/alert.
- [x] Diagnostica del grafico: fonte `FX:EURUSD`, TF, `1m x/5` dell'ultima 5m chiusa, ragione osservata `FX_5M_ASSENTE` / `1M_PRESENTI_x_SU_5` / `ORARI_1M_NON_CONTIGUI` / `VOLUME_O_PREZZO_1M_ND` / `OK`, conteggio barre segmento e lacune. I dati sono validati solo alla chiusura della 5m; non trattare la candela aperta come definitiva.
- [x] Aggiunti test statici con verifica delle parentesi per non ripetere CE10015 e di separazione dei due tracciati; NON sostituiscono il Pine Editor.
- [ ] **Gate manuale D0.5:** provare il nuovo file su `FX:EURUSD` 5m e leggere una delle due curve oppure il motivo in tabella. Se c'è soltanto `0/5`, indagare disponibilità reali 1m del piano/feed; se c'è `5/5` e curva arancione, confermare segmento parziale ma **nessun segnale**. Non acquistare altri feed e non inviare webhook.
- [ ] Confronto futuro con CVD nativo aggregato TradingView solo su stessa fonte e timestamp; validazione scientifica B prima di qualsiasi notifica o livello operativo. Nessuna asserzione di vantaggio.

## 10/11/2026 — D0.4: errore `Invalid symbol` e ticker canonico FXCM su TradingView

- [x] Screenshot utente dopo aver inserito D0.3: `Errore di runtime — Invalid symbol: FXCM:EURUSD`. Non era un errore del calcolo CVD: il simbolo chiamato nello script non risulta valido in questa sessione di TradingView.
- [x] Verifica pubblica: la pagina TradingView `https://it.tradingview.com/symbols/EURUSD/?exchange=FX` presenta l'ID `FX:EURUSD` con etichetta provider **FXCM**; questo coincide con l'ID effettivamente letto da Pine D0.2: `FX:EURUSD`. Non equiparare automaticamente etichetta UI ad API accessibile con prefisso `FXCM:`.
- [x] Nuovo file **D0.4** `experiments/tradingview/remura_shark_cvd_fx_v04.pine`, `FEED = "FX:EURUSD"` identico per `request.security(..., "5", ...)` e `request.security_lower_tf(..., "1", ...)`, qualità dati fail closed e `ignore_invalid_symbol=true` per evitare blocco runtime su simboli non disponibili; diagnostica mostra ID, provider dichiarato da UI e numero di barre 1m per 5m.
- [x] Modello distinto `remura_fx_1m_cvd_d0.4` e provenienza eventi `TV_FX_EURUSD_TICK_VOLUME_PROXY_1M`. D0.3 e D0.2 restano storici, non mischiare dati/risultati.
- [ ] **Prossimo test:** sostituire Pine D0.3 con D0.4 sul grafico già aperto, verificare compilazione e comparsa di `DATI: FX:EURUSD (TV: FXCM) 5m+1m`; leggere numero barre 1m per ultima 5m. Solo dopo 1m completi verificare curva e divergenze; se dati parziali, non disattivare regole anti-falso-segnale.
- [ ] Nessun alert, webhook, operazione, raccolta prospettica, segnale o redditività certificati. Questa prova non usa dati futures eseguiti.

## 10/11/2026 — D0.3: ricerca FXCM esplicita, anziché fidarsi della testata del grafico

- [x] Prova utente: nella stessa schermata la testata grafico riporta `Euro / Dollaro · 5 · FXCM`, ma la diagnostica Pine D0.2 legge `FX:EURUSD | TF=5`. La discrepanza è confermata e **non è una prova di dato FXCM nel codice**.
- [x] Creato un **nuovo file** `experiments/tradingview/remura_shark_cvd_fxcm_v03.pine` (non modifica D0.2 storico): `FEED = "FXCM:EURUSD"` passato esplicitamente alle chiamate `request.security(FEED,"5",...)` e `request.security_lower_tf(FEED,"1",...)`; i pivot e il prezzo corrente provengono da FXCM, non dal grafico alias. `FX:EURUSD` è ammesso solo come **alias di visualizzazione**, non come provider di calcolo.
- [x] Valida tempo barra a 5m e copertura di **tutti e cinque** i minuti da FXCM con timestamp coerenti; in caso di NA, gap, volume mancante o chart non EURUSD 5m, **NO SIGNAL**. Tabella contiene `Grafico: ...` e `DATI CALCOLATI: FXCM:EURUSD 5m+1m`. Alert manuali disabilitati, nessun ordine.
- [ ] **D0.3 runtime gate:** sostituire D0.2 con il codice del nuovo file D0.3 nel Pine Editor, verificare compilazione, riga `DATI CALCOLATI`, pannello CVD e eventuale messaggio `DATI 1m INCOMPLETI`. Se la linea manca dopo aver bloccato correttamente la fonte, investigare gap/backfill con campioni temporizzati e senza aggirare i controlli.
- [ ] **Parità e disciplina statistica:** provare con dati 5m realmente FXCM, confrontare CVD e pivot con lo stesso broker; annotare che un chart `FX:EURUSD` può avere candele visivamente differenti, quindi non usare i massimi/minimi visualizzati come conferma dei pivot FXCM senza riscontro numerico.
- [ ] Nessun runtime Pine D0.3, dato di mercato, alert, webhook, profitto o costo reale è stato ancora validato. Test GitHub sono soltanto offline.

## 10/11/2026 — Riscontro runtime D0.2 (screenshot PC)

- [x] L'indicatore D0.2 si avvia e mostra la tabella diagnostica senza il vecchio errore `RE10142`.
- [x] Screenshot sul PC: `REMURA D0.2 | SORGENTE/TIMEFRAME ERRATO`; riga `Letto: FX:EURUSD | TF=5` e indirizzo grafico con `symbol=FX%3AEURUSD`. **Il timeframe è corretto, il provider/simbolo NON è FXCM**. Arancione e CVD assente sono quindi il comportamento previsto dal blocco di qualità, non un difetto numerico dimostrato.
- [ ] **Prossimo unico controllo:** cambiare simbolo nel selettore TradingView in **`FXCM:EURUSD`**, mantenere 5m e D0.2 già installato, verificare `Letto: FXCM:EURUSD | TF=5` con riga verde e CVD presente. Solo allora studiare eventuali mancanze delle barre 1m. Nessun nuovo codice, nessun allentamento dei gate, nessuna nuova spesa.
- [ ] L'avvio su un grafico errato NON dimostra correttezza del CVD, supporto della serie volume in tutti i minuti, validità statistica o possibilità di inviare alert al cloud.

## Perché questo filone

L'utente dispone già di TradingView Premium e della watchlist **FXCM**. Screenshot del 09/11/2026: `FXCM:EURUSD`, grafico 5m, volume visibile. Non è stata misurata la latenza effettiva dei dati. Futures CME/COMEX su TradingView risultano ritardati senza pacchetto dati aggiuntivo, perciò la prima prova utilizza EURUSD FXCM senza acquistare niente.

**Ipotesi falsificabile:** il CVD *stimato* da OHLC + volume Forex dei minuti 1m, aggregato a 5m, migliora il potere predittivo delle sole divergenze di prezzo o di una semplice baseline prezzo+ATR. Il volume FXCM può essere tick volume/volume del singolo feed, NON contratti eseguiti sull'intero Forex né aggressor side istituzionale.

Diverso dal proxy cTrader `CLV × tick volume` già esistente in REMURA/PR #77: non mischiare i due indicatori, le sorgenti, le unità, le sessioni e gli orari. Il modello attivo per il prossimo test è `remura_fx_1m_cvd_d0.4`, distinto dai modelli storici D0.1/D0.2/D0.3; non mescolare eventi fra revisioni.

## Architettura sperimentale

1. **TradingView Pine v6**, indicatore D0.3 `experiments/tradingview/remura_shark_cvd_fxcm_v03.pine`: grafico EURUSD 5m con alias grafico `FXCM:EURUSD` o `FX:EURUSD`, fonte dati **vincolata esplicitamente a `FXCM:EURUSD`** in entrambe le richieste 5m e 1m. Ogni minuto viene polarizzato per direzione open→close, con tie-break sull'ultimo close/direzione osservata; la somma produce un delta 5m. CVD si azzera con il nuovo giorno del feed `time("D")`.
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
