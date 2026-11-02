# REMURA v1.58 — Prototipo offline divergenze prezzo–CVD

**02/11/2026 — progettazione, non installato.** La v1.57 continua sulla VPS con flag di raccolta prioritaria attivo. Questo ramo è **impilato** su `feature/intraday-priority-v157`; PR e commit non devono essere uniti direttamente su `main` prima del collaudo della v1.57.

## File

- `cvd-divergence-core.js`: libreria deterministica che richiama la **stessa** `price-core.flow(market,{now})` della pagina prezzi. Nessuna seconda formula CVD, nessuna rete, nessun archivio, nessuna notifica, nessun invio ordini e nessuna modifica ai sorgenti già installati.
- `tests/cvd-divergence.test.js`: dati sintetici (non prezzi di mercato); verifica divergenze rialzista LL/HL, ribassista HH/LH, tempo di riconoscimento successivo a pivot 2+2, ID stabili, price–CVD agli stessi timestamp, nessun evento su dati assenti/stale/gap/plateau, reset UTC, no look-ahead.
- Workflow: test in GitHub Actions, nessun segreto.

## Caratteristiche e limiti

1. **Primi due soli simboli:** EURUSD e XAUUSD, timeframe M15, broker `ctrader`.
2. **CVD proxy** = tick volume × close location value, cumulato dalla mezzanotte UTC. Come già previsto dalla v1.56, flusso `partial`, `stale` o `missing` genera **zero eventi**. Una giornata incompleta non genera finti segnali.
3. Pivot high/low **stretti**, confermati solo dopo due barre M15 a destra. Quindi in condizioni ideali un segnale richiede almeno 30 minuti *dopo* la candela del pivot; più l'attesa di raccolta, che attualmente punta a circa 60 minuti per i due simboli (ancora da verificare).
4. Divergenza rialzista regolare: prezzo seconda valle più bassa e CVD ai medesimi due pivot più alto; ribassista regolare: prezzo seconda cima più alta e CVD inferiore. Escluse provvisoriamente le varianti nascoste e i pivot piatti.
5. Filtri iniziali **NON ottimizzati**: pivot sinistra/destra 2/2; separazione fra pivot 3–36 M15; differenza minima prezzo 0,1 ATR, CVD 4% dei tick fra i pivot e la conferma. I parametri non sono prova di predittività.
6. Eventi contengono `confirmedAt` come **primo istante matematicamente disponibile** (chiusura M15 a destra), ma non pretendono che il server lo abbia effettivamente visto a quell'ora. Il futuro backend dovrà registrare anche `collectedAt`, `detectedAt`, `deliveredAt`. Se una scansione legge dati vecchi, non deve inviare un avviso attuale come se l'evento fosse appena nato.
7. Per ora nessun collegamento a Squalincome né notifiche; questo evita di reinterpretare come “nuova divergenza CVD” l'etichetta già esistente di divergenza **COT contro prezzo**.
8. **Benchmark obbligatorio prima di promuovere a trigger:** CVD proxy incorpora OHLC e volume di quotazioni: paragonare eventi del rilevatore a pivot prezzo/ATR soli, con walk-forward, costi e misure di falsi positivi. Nessun vantaggio su ordini istituzionali è dimostrato.

## Prossimi gate

- [x] Nuovo algoritmo isolato, senza API e senza modifiche live.
- [ ] Test CI verde sul commit finale e correzioni eventuali.
- [ ] Sviluppare analogo calcolo server-side con vettori numerici confrontabili al JS, preservando la causalità senza look-ahead.
- [ ] Persistenza SQLite privata + deduplicazione, orario di prima osservazione reale; **nessuna notifica ancora**.
- [ ] Validazione prospettica, campione non selezionato e benchmark prezzo-solo.
- [ ] Solo dopo: Radar e notifiche iPhone opt-in con parametri misurati, versioning e rilascio protetto.

**Costi previsti per questo prototipo: zero API aggiuntive cTrader e nessun nuovo servizio cloud.** Restano da controllare le quote e fatture Oracle; non dedurre gratuità solo da RAM/disco.
