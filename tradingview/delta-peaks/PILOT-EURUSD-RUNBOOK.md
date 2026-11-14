# REMURA — Piano operativo pilota EURUSD v0.8.54
**Aggiornamento: 14/11/2026 CET. Solo TEST, nessun segnale operativo.**

## Sabato: preparazione completata
Gateway TEST esistente accetta FXCM:EURUSD M5 e BINANCE:BTCUSDT M5 solo durante finestra weekend. Non cambiare token, URL, Worker, DB o Pine con formato v1 durante la raccolta. Formato configurato v0.8.53 è candidato offline, non accettato dal gateway distribuito.

## Domenica sera / riapertura effettiva Forex
1. Disattivare alert BTC domenica 15/11 sera, prima del 16/11 01:00 CET. Non cancellare storico TEST.
2. Aprire TradingView su FXCM:EURUSD M5, usare Pine v0.8.1-lab, salvare la schermata input effettivi e verificare riferimento: 1m intrabar, lookback30, multiplier3.5, maxEfficiency0.07, minPeakGap6, fpTicks10, VA70% fisso, imbalance300%, dailyMinEffort1.5, HL2, daily/previous-day ON, telemetryEnabled e heartbeat ON. Non confondere i default sorgente con valori attivi.
3. Una volta confermate impostazioni, creare l'alert “Any alert() function call” su quel grafico. Usare esattamente il webhook TEST già funzionante, senza trascriverlo in chat, repo o log. Non usare endpoint produzione. Non modificare gli input dopo creazione alert: TradingView conserva snapshot separato.
4. Alla prima chiusura reale M5 osservata, verificare ricezione con [workflow metadata già esistente](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-first-receipt-readonly.yml). Non assumere che mercato apra a un orario fisso; usare timestamp effettivo. Distinguere record eventualmente precedenti al nuovo alert.
5. [Workflow EURUSD analitico](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-fx-analytic-readonly-manual.yml): inserire start_utc/end_utc nel formato UTC YYYY-MM-DDTHH:MMZ, massimo 72 slot, end maturato 120s. In novembre Roma=UTC+1; il reader v0.8.52 non accetta finestre precedenti 16/11 00:00 UTC. Se primi dati prima di tale limite, non usare per questa verifica e fissare start effettivo ammesso. Non avviare durante chiusura.
6. Dopo un campione completo, controllare schema, latenza, footprint disponibile, retest, effort condizionale default30. Esiti 15/30/60 minuti su barre successive tempestive; confronti heartbeat per sessione UTC. Mai chiamare un esito pendente “mancante”, né dichiarare profitto o causalità. Parametri non integralmente attestati nel payload v1: dati descrittivi, non campione scientifico finale.
7. Proseguire con configurazione telemetrizzata, prova indipendente di prima ricezione, join as-of B/C, benchmark, costi, OOS. Nessun cambio produzione senza autorizzazione e gate esistenti.

## Limiti
Non sono state misurate le quote effettive dell'intero account. Nessun abbonamento aggiunto. Il controllo BTC già concluso con 42/42 barre, 298 verifiche applicabili coerenti, non è prova di edge Forex. Non serve ripetere subito la stessa lettura.
