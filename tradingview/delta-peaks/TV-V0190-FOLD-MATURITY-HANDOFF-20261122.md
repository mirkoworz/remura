# REMURA TradingView v0.8.190 LAB — fold-exclusivity and horizon maturity
22 novembre 2026 · Europe/Rome · offline no trades.

## Delta rispetto a v0.8.189
La v0.8.189 collega quattro fonti tramite lo stesso ID decisione; v0.8.190 **rifiuta anche i dati CVD/price M5 di un fold precedente**, sebbene fossero già ricevuti, e impedisce che un outcome teorico oltre il termine holdout sia analizzato come in-fold.

- Modulo: tradingview/delta-peaks/frozen_fold_maturity_v0190_lab.py
- Test nuovi: tradingview/delta-peaks/test_frozen_fold_maturity_v0190_lab.py (16 casi).
- Reimpiega inspect_join() della v0.8.189 e guard() con blob V2 immutato della v0.8.182; non ripete suite precedenti.
- CVD_M5 e PRICE_ONLY_M5 richiedono barra closed UTC in [fold_start, fold_end), oltre alle condizioni temporali e identità del join. Retail/COT possono essere as-of storici: non li si obbliga al fold della barra.
- Orizzonti immutati: primaria 60 minuti e secondari 240/1440 minuti. target <= fold_end non attraversa il limite; target > fold_end è bloccato per quel fold. Termine esclusivo.
- evaluation_utc è soltanto una dichiarazione del chiamante e distingue PENDING da WINDOW_ELAPSED_CLAIM_ONLY: NON dimostra maturità, pubblicazione, copertura delle barre o outcome.
- Non crea outcome, confronto, scambio o segnale; mancanze restano UNKNOWN e l'entry della decisione non implica CVD realmente acquisito.
- Holdout 1 inizia 23/11/2026 00:00 UTC = 01:00 CET, NON prova la presenza di dati ammissibili.

**Stato:** NO_GO_PROSPECTIVE_ALPHA; niente modifiche V2, tuning, real feed, deploy, Cloudflare, Oracle o servizi.
