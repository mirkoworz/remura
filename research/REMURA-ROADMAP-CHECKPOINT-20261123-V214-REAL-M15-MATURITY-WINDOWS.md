# REMURA — FILONE A V21.4 LAB — finestre temporali REALI già maturate e 24h pendente

**V21.4, aggiornamento 23/11/26, 21:37:15 Europe/Rome.** Ramo `research/remura-v211-source-derived-cvd-20261123`. PR #112 Draft. Solo checkpoint scientifico: nessun test vecchio ripetuto, nessun codice, HTTP, Cloudflare, prezzo o nuovo dato inventato.

## Derivato dai 12 timbri ricevuta realmente verificati, non da un simulatore di trading

Prova reale V20.3: [run 45121703188](https://github.com/mirkoworz/remura/actions/runs/45121703188), 12 CVD TEST M5 `FX:EURUSD` tra `2026-11-23 04:30` e `05:25 UTC`, lag massimo osservato 15.510 ms. La funzione `next_entry_after_max_receipt()` di `research/v204_private_cvd_price_coverage.py` seleziona come **ipotetica prima apertura M15 successiva alla ricevuta** quattro sole coorti uniche. Questa è una tabella di *possibile copertura prezzi*; NON abbiamo quattro decisioni con lato verificato.

| Coorte ipotetica M15 (UTC) | Fine 60m UTC | Fine 4h UTC | Fine 24h UTC |
|---|---|---|---|
| 23/11 04:45 | 23/11 05:45 | 23/11 08:45 | 24/11 04:45 |
| 23/11 05:00 | 23/11 06:00 | 23/11 09:00 | 24/11 05:00 |
| 23/11 05:15 | 23/11 06:15 | 23/11 09:15 | 24/11 05:15 |
| 23/11 05:30 | 23/11 06:30 | 23/11 09:30 | 24/11 05:30 |

**Lettura rigorosa alla sera italiana del 23/11/2026:**

- L'orizzonte 60m (tutte e 4) è già **temporalmente scaduto**, ma quanti prezzi cTrader M15 esistano e siano contigui è **N/D**. Nessun risultato direzionale.
- L'orizzonte 4h (tutte e 4) è già **temporalmente scaduto**, ma copertura dei prezzi autentici **N/D**. Nessun risultato direzionale.
- L'orizzonte 24h **non sarà temporalmente concluso fino al 24/11/2026 ore 05:30 UTC = 06:30 CET** per l'ultima coorte, anche se in seguito la disponibilità dei prezzi resta da dimostrare. Non anticipare risultato 24h il 23/11.
- Le coorti sono **sovrapposte sui futuri intervalli di uscita**, non 4 test indipendenti. Le 12 ricevute sono `OBSERVATION_ONLY`, non 12 transazioni o segnali. V20.7 richiede **30 confronti forward completi** e **10 finestre non sovrapposte** (per ogni orizzonte) più prezzi e costi; nessuna soglia è soddisfatta.

## Gate singolo già pronto senza riscrivere lettori

Con una copia **locale autorizzata** già esistente di `private/remura-prices.sqlite3`, eseguire in futuro, **senza collegamento broker o D1**:

~~~bash
python3 research/v204_private_cvd_price_coverage.py \
  --receipt-proof research/real-proofs/REMURA-V203-CVD-TEST-RECEIPTS-20261123.json \
  --private-sqlite /percorso/privato/offline/remura-prices.sqlite3
~~~

Il lettore esegue `sqlite3 mode=ro` + `PRAGMA query_only=ON`, confronta solo timestamp/contiguità dei prezzi e stampa conteggi aggregati, **non i valori OHLC**. L'esecuzione del comando non è avvenuta in questo checkpoint perché manca una copia privata accessibile tramite GitHub. **Non chiedere al collector Mac/Oracle di avviarsi automaticamente.**

Nessuna strategia, ricavo, verifica di spread/slippage o ritorno futuro è risultata da questo checkpoint.
