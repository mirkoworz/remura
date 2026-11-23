# REMURA — Filone A V21.3: verifica del contratto TradingView CVD v0.9.1 già esistente

**Checkpoint LAB:** 23/11/26, 21:11:39 Europe/Rome. **Branch** `research/remura-v211-source-derived-cvd-20261123`, PR #112 Draft. NESSUNA modifica al codice di ingest, al collector, alla CI o alla produzione.

## Fatto nuovo verificato sul codice storico, non dai dati di mercato

Nel commit immutabile [58dc84e0de93b48eb5a6c596664d4d338548754a](https://github.com/mirkoworz/remura/blob/58dc84e0de93b48eb5a6c596664d4d338548754a/tradingview/delta-peaks/gateway-lab/worker_cvd_candidate.mjs), il gateway di ricerca definisce effettivamente lo schema di **ricezione** `remura.tv.flow.cvd.preview.v1` / `0.9.1-cvd-lab` e la funzione `validateCvdEnvelope(payload,receivedMs)` (righe circa 160–217). Questo risolve il dubbio sull'esistenza del contratto: **non** dimostra tuttavia che nuovi byte originali fossero ricevuti, che il Worker identico sia attivo o che la sorgente sia autenticata.

La busta prevede `schema,snapshot,configuration,cvd` e `snapshot.bar_open_ms/bar_close_ms` UTC in millisecondi; `cvd` espone `raw_delta, trusted_delta, daily_cvd, segment_cvd, continuous, complete, eligible, day_valid, segment_id/segment_bars, pivot_close_ms`. La configurazione include modello `D08_SEGMENT_PORT_V091`, `lower_tf=1` e `timeframe=5`. La qualità è `VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS`: nessun volume di scambio CME/istituzionale certificato. Il receiver controlla anche la puntualità entro 120 secondi e conserva `raw_json` nella tabella TEST `tv_flow_events`, con `received_at_ms` del Worker.

### Blocco scientifico cruciale

Il validator **forza** `timely:false,transportTimely:true` nel valore restituito per il CVD preview (riga circa 215–216), e l'INSERT su D1 memorizza `is_timely` da `snap.timely` (riga circa 333–336). Quindi le ricevute CVD **TEST** rimangono non ammissibili come decisioni forward anche se il trasporto è puntuale. Non confondere `cvd_bull/cvd_bear` di divergenza (con latenza pivot) con un lato di ordine, né `trusted_delta` con flusso istituzionale eseguito. Le 12 ricevute V20.3 non vanno reinterpretate.

## Conseguenze operative: non aggiungere adattatori fittizi

1. L'input V21.1 `remura-v211-closed-m5-cvd-pair-v1` è un **contratto locale separato**, non il JSON nativo TradingView. Non attribuirgli autenticità del gateway né affermare che i valori `prior_cvd/event_cvd` siano campi presenti nel webhook. Nessuna retro-conversione.
2. Per una prossima coorte realmente prospettica occorrerà ottenere **nuovi** raw JSON nativi di due barre M5 contigue, con timestamp di ricezione attestato da infrastruttura indipendente, verificarli contro il validator originale del gateway e **soltanto in una modalità di ricerca esplicitamente autorizzata** progettare la derivazione CVD e il congelamento pre-outcome. Non invocare Worker, leggere D1 o cambiare flag TEST in questo passaggio.
3. La verifica prezzi reali cTrader M15 del 23/11 resta **N/D**: la sola prova CVD esistente è la ricevuta aggregata; DB SQLite privato non disponibile attraverso i file GitHub esaminati. La funzione `research/v204_private_cvd_price_coverage.py` esiste già: riutilizzarla per sola lettura di una copia locale autorizzata, non costruire un secondo lettore.
4. I moduli A V20.7–V21.2 e la custodia dei byte originali rimangono LAB. Decisioni nuove autentiche = **0**; outcome 60m/4h/24h = **N/D**; benchmark reale = **N/D**, costi osservati = **N/D**. La direzione nella V21.1 resta una **ipotesi di classificazione del proxy**, non un segnale validato.

**Nessuna CI eseguita per questo documento**: nessun codice A modificato rispetto alla CI verde V21.2 [45255523695](https://github.com/mirkoworz/remura/actions/runs/45255523695). Nessun costo o nuovo servizio.
