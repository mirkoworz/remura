# REMURA candidato v1.60 — Divergenze prezzo / CVD proxy, ricerca OFFLINE

Data: 3 novembre 2026. VPS LIVE: v1.59, SHA e924f4cf6f1a384fd84a3cef66c89a16e35de3fd verificato nella diagnostica privata #29. Nessun deploy da questo ramo.

## Origine
Porting pulito della vecchia PR #71 sul main v1.59, senza fondere i commit storici. Modulo JavaScript isolato cvd-divergence-core.js e 11 test sintetici in tests/cvd-divergence.test.js; CI corrente esegue controlli di sintassi e test.

## Limiti scientifici e tecnici
- Solo EURUSD e XAUUSD, M15, cTrader. CVD proxy = CLV × tick volume, non vero volume bid/ask eseguito o flusso istituzionale.
- Pivot stretti sinistra/destra 2/2 e conferma solo su barre chiuse, no look-ahead; errori/gap/stale/tick volume assente non generano eventi.
- confirmedAt è il momento teorico di conferma del pivot, non l'istante in cui il server ha raccolto e analizzato i dati.
- Nessuna richiesta broker/API, persistenza, notifica, nuovo segnale operativo, modifica UI, database o autoupdater. Il codice è solo in PR.

## Gate ancora aperti
1. CI offline verde contro main attuale; poi prova su storico di mercato non selezionato.
2. Benchmark contro pivot prezzo/ATR senza CVD e controlli permutando il tick volume.
3. Backend causale con parità numerica JS, deduplica, invalidazione, tempi collectedAt/detectedAt/deliveredAt.
4. Valutazione walk-forward con costi, spread, falsi positivi e rischio, senza promessa di guadagni.
5. Solo dopo: Radar e notifiche private iPhone opt-in, nuova versione e data/ora italiana su ciascuna pagina, backup e rollback.

Costi previsti da questo ramo: zero nuove API cTrader e zero nuovi servizi; quote Oracle/Firestore non certificate.

## Portabilità backend (solo offline)

- Aggiunto `scripts/cvd_divergence.py`: stessa logica causale di pivot, CLV × tick volume, ATR e soglie del motore JS, senza dipendenze esterne.
- Test parità automatici JavaScript ↔ Python su 30 scenari sintetici, con controlli di assenza look-ahead, timestamp di conferma, ID stabili, assenza volume, gap e mercati non supportati. Non sostituiscono la convalida su prezzi reali.
- Il modulo non è importato nel server live, non ha accesso rete/broker, e la PR resta in bozza.

## Benchmark comparativo causale (solo offline)

È stato aggiunto `scripts/cvd_benchmark.py`: per la stessa sessione UTC confronta **tutti i pivot prezzo+ATR causalmente confermati** con il loro **sottoinsieme filtrato dal CVD proxy**. Etichetta soltanto movimenti direzionali di chiusura dopo un orizzonte futuro prefissato (predefinito 4 M15), in ATR nota alla conferma; le osservazioni ancora immature restano pendenti. Tre rotazioni deterministiche dei tick-volume (offset 3, 7, 13) costituiscono controlli negativi *esplorativi*, non un test di significatività. Non espone segnali individuali né broker-ID.

**Forte limite:** nessun rendimento, PnL, spread, commissione, stop, slippage o valutazione out-of-sample; i candidati si sovrappongono e sono correlati. Non mostra percentuali di successo se ci sono meno di 30 osservazioni mature. I test sono sintetici; prima di procedere a Radar serve replay reale su campioni non selezionati, con calendario e fusi coerenti. Il benchmark non è distribuito alla VPS.

## Replay multi-sessione UTC su archivio esistente

- Modulo puro `scripts/cvd_session_replay.py`, **non importato dal server VPS**. Accetta solo il contratto `remura-price-v1` per EURUSD o XAUUSD cTrader, valida timestamp/volumi/OHLC e ripercorre fino a 45 sessioni UTC; massimo 4000 M15 per richiesta.
- Ogni sessione viene valutata con `now` fissato alla chiusura dell'ultima candela di quel giorno, non all'ora presente. Non combina pivot tra giornate, non fabbrica le barre mancanti e non anticipa i risultati delle quattro M15 future.
- Baseline prezzo/ATR vs sottoinsieme CVD proxy e 3 rotazioni volume. Output **solo contatori aggregati** e cause di esclusione predefinite; mai OHLC, simbolo broker, prezzi o segnali nominativi.
- Il replay offline è pronto per essere eseguito su dati cTrader storici del database privato (45 giorni max); il dataset reale e il numero di sessioni idonee **non sono ancora stati verificati**. Per raggiungerlo useremo un workflow privato separato che legge le due GET protette già disponibili, senza chiamate cTrader e senza esporre il payload nei log.
- Anche dopo questo replay, le statistiche descrittive di quattro M15 successive non sono PnL, walk-forward o evidenza del vantaggio istituzionale.
