# REMURA TradingView — ROADMAP Order Flow Radar LAB v0.4
**Aggiornamento documentazione v0.4.1: 11/11/2026, ore 11:58 CET**

## Checkpoint
- [x] Laboratorio indipendente `tradingview/delta-peaks/`, PR #102 DRAFT.
- [x] **v0.1**: primo indicatore con delta stimato, segnalazioni ER e livelli, verificato in screenshot TradingView.
- [x] **v0.2**: soglia delta su 30 barre precedenti, distanza minima 6 barre, riduzione rumore.
- [x] **v0.3**: formule numeriche Sforzo/Risultato/Efficienza e test visivo su EURUSD FXCM M5.
- [x] **v0.4**: radar con colorazione dinamica delta, intensita' 1–5, picchi arancioni, anomalie viola, stato LIVE/CONFERMATO, storico di 3 picchi confermati, barre colorate solo su richiesta.
- [ ] **Compilazione v0.4** e screenshot del radar durante una barra aperta e alla chiusura.
- [ ] Verificare l'assenza di segnali aggiunti o rimossi rispetto a v0.3 a parametri identici.
- [ ] Verificare gestione di dati NA/zero, ATR non disponibile, storico intrabar limitato, cambio timeframe e ricarica.
- [ ] Confrontare livelli WEEK/CURRENT MONTH/PREVIOUS MONTH con i video del metodo di riferimento.

## Codice v0.4
- **Sforzo**: `abs(deltaBar) / SMA(abs(deltaBar[1]), 30)`.
- **Risultato**: `sign(deltaBar) * (close - open) / ATR(14)`.
- **Efficienza**: `Risultato / Sforzo`.
- **ER**: Sforzo >=3.5, Efficienza <=0.07, gap minimo 6 barre e barra confermata.
- **LIVE**: anteprima aggiornata mentre la candela e' aperta, mai salvata come segnale definitivo.
- **CONFERMATO**: marcatori, allarmi e ultime 3 anomalie/picchi solo a barra chiusa.
- **Livelli**: per ora massimo |delta| della candela in periodo, prezzo hl2, non un livello istituzionale identificato.

## Nuovo filone Premium — test footprint (11/11/2026 11:58 CET)
- [x] Confermata da documentazione TradingView disponibilita' di `request.footprint()` per piano **Premium**.
- [x] Creato **[REMURA-Footprint-Premium-Probe.pine](REMURA-Footprint-Premium-Probe.pine)** su questo ramo: prova isolata di BUY/SELL classificati, delta footprint, POC, VAH/VAL, conteggio imbalance per riga.
- [ ] **Compilare il test** in TradingView su `FXCM:EURUSD` M5 e verificare che non sia tutto N/D; acquisire screenshot.
- [ ] Ripetere, se possibile, su un future CME con dati autorizzati e distinguere volume reale da tick volume forex. **Non acquistare feed senza preventivo e autorizzazione.**
- [ ] Confrontare i delta della v0.4 (requestVolumeDelta con 1m) con il delta footprint nativo (granularita' interna differente), senza sommarli o considerarli uguali.
- [ ] Solo dopo prova positiva: pianificare integrazione POC/imbalance in una **v0.5 del RADAR**, mantenendo toggle e fallback N/D, e successiva misurazione prospettica ER a 15/30/60 minuti.

Il piano Premium e' gia' attivo secondo l'utente; **nessun ulteriore abbonamento** necessario per la funzione Pine Premium. L'accesso a particolari dati futures CME in tempo reale potrebbe richiedere un abbonamento dati distinto. Nessun deploy di REMURA live.

## Registro nuovo
- **11/11/2026 11:58 CET — Footprint Premium PROBE v0.1**: aggiunta una prova nativa autonoma alla PR #102 DRAFT; Radar v0.4 lasciato invariato. Attesa compilazione in TradingView.

## Fase successiva — MISURA
1. Definire ora, prima di osservare i risultati, una metrica per ogni evento ER confermato: prezzo, delta, effort, efficiency, ATR, simbolo, timeframe, istante e origine del feed.
2. Misurare reazioni a **3, 6 e 12 barre M5** (15/30/60 minuti), MFE/MAE e spostamento in ATR, senza classificare ER+ come SELL o ER- come BUY senza test.
3. Confrontare con le normali candele e con picchi non-ER; includere i falsi positivi e la dipendenza da sessioni e notizie.
4. Documentare versione e parametri per evitare ottimizzazioni retrospettive.
5. Dopo: valutare la fedelta' alla metodologia Week e Monthly con esempi verificabili, eventuali modifiche ai livelli e solo poi integrazione REMURA.

## Regole del laboratorio
- Priorita' al gratuito, monitorare quote e limiti TradingView prima di usare alert o webhook.
- Nessuna dichiarazione di ordine istituzionale da tick volume/volume FXCM.
- No merge, deploy, credenziali, webhook o modifiche ai filoni A/B/C.
- Sempre versione e data/ora CET/CEST in testa a script e documenti.
- Compilazione in Pine Editor e comportamento LIVE vanno osservati separatamente dai test di statistica e predittivita'.

## Registro
- v0.1 — 11/11/2026 08:41 CET: prototipo.
- v0.2 — 11/11/2026 08:54 CET: selezione picchi e pulizia.
- v0.3 — 11/11/2026 09:03 CET: metriche ER.
- 11/11/2026 09:39 CET: screenshot di v0.3, compilazione e grafico apparentemente corretti.
- **v0.4 — 11/11/2026 11:26 CET**: Order Flow Radar colorato, LIVE/CHIUSA, intensita' e registro ultimi tre picchi. **In attesa di compilazione sul grafico**.
