# REMURA — Contratto di passaggio D → B v0.8.50
**Aggiornamento: 14/11/2026 10:46 CET — candidato offline, PR #102 DRAFT.**

## Separazione delle fonti
Il filone D espone osservazioni descrittive di FXCM:EURUSD M5. BTC weekend non è ammesso a ricerca FX. COT, CVD, sentiment e prezzi cTrader rimangono fonti distinte e governate dal filone B. Non uguagliare prezzo FXCM e cTrader, delta intrabar e aggressioni CME. Non importare questo modulo nel motore live.

## Causalità
Il chiamante specifica bar_close_ms e decision_ms. La finestra è [bar_close_ms, bar_close_ms+5min). Un record disponibile solo dopo decision_ms non esiste per quella decisione. Nessun fallback a barre vecchie. Timestamp del gateway necessario; trasporto oltre 120s escluso. Il modulo non attesta l'autenticità di un export fornito dal chiamante. I costi e gli esiti futuri NON entrano nelle feature as-of.
L'integrazione futura richiede witness immutabili di prima ricezione e del momento di decisione, mapping esplicito strumenti/feed, versioni as-of COT/CVD/sentiment/prezzo e un outcome separato a 3/6/12 barre, costi e OOS. Vedi protocollo v0.8.3 e shark_sample_admission.py (filone B, sola lettura).

## Parametri Pine: evidenza mancante
Il payload v1 non contiene tutti gli input congelati all'attivazione dell'alert. lower_tf e daily_anchor sono presenti; lookback, multiplier, maxEfficiency, minPeakGap, dailyMinEffort, ticks per row, value-area %, imbalance %, flag daily/previous-day/heartbeat e versione effettiva della configurazione devono essere attestati prima della validazione scientifica. I default del sorgente non costituiscono prova degli input attivi.
Futura telemetria versionata: oggetto parametri con valori effettivi, identificatore configurazione calcolato su rappresentazione canonica dal ricevitore, validazione stretta, nuova coorte all'eventuale cambio. Migrazione separata: mantenere v1 in TEST senza modifiche, sviluppare schema e gateway candidato, test offline, solo dopo coordinare eventuale nuova compilazione e alert su FX. Nessun parametro reale inventato e nessuna modifica Pine in questo checkpoint.

## Stati del candidato
NO_CURRENT_ASOF_OBSERVATION, BLOCKED_INVALID_OR_CONFLICT, BLOCKED_NOT_PROSPECTIVELY_TIMELY, BLOCKED_DIAGNOSTIC_REVIEW, PARTIAL_DESCRIPTIVE_ONLY, DESCRIPTIVE_CANDIDATE_ONLY.
Un footprint assente rimane null; nessuna imputazione. La coerenza numerica usa tolleranze diagnostiche provvisorie. Entrambi gli stati descrittivi sono SEMPRE non ammessi a previsione, ordini o notifiche. Non pubblicare output per-barra, prezzi o raw JSON.
