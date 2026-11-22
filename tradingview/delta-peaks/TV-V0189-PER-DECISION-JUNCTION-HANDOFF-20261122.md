# REMURA TradingView v0.8.189 LAB — per-decision junction
22 novembre 2026, Europe/Rome. Contratto offline, nessuna produzione.

## Consegna
- Codice: tradingview/delta-peaks/decision_evidence_junction_v0189_lab.py
- Test nuovi: tradingview/delta-peaks/test_decision_evidence_junction_v0189_lab.py (18 casi dedicati).
- Ogni decisione porta quattro slot espliciti con ID CVD_M5, PRICE_ONLY_M5, RETAIL, COT_TFF; le osservazioni devono riferirsi esattamente alla decisione. Nessun join per posizione e nessun rimpiazzo retrospettivo FIFO.
- Vietati ID duplicati, evidenze incrociate, strumento incoerente e campioni futuri. CVD M5: close allineato, ricezione entro close +120 secondi e non oltre la decisione. Comparatore prezzo con identica barra M5. RETAIL con ricezione e campione distinti.
- COT con as-of, pubblicazione e ricezione temporalmente coerenti come DICHIARAZIONI, ma mapping futures/spot mai verificato automaticamente.
- Evidenze non referenziate esplicite e nessun segnale o backfill; campioni mancanti mai convertiti a zero; niente esiti prezzo.
- La presenza strutturale di tutti e quattro i record non promuove l'ammissione: ID, clock e hash dichiarati NON sono prove indipendenti del first-seen.

Protocollo V2 immutato: holdout 1 il 23/11/2026 00:00 UTC, non certifica acquisizioni autentiche. NO-GO scientifico. Nessun deploy, API, Secret, Oracle, Cloudflare, merge o intervento Mac. Prossimo gate: first-seen autenticato per decisione, mapping verificato e valutazione fuori campione.
