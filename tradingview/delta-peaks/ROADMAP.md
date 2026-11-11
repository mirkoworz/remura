# REMURA TradingView — ROADMAP Radar + Footprint Premium LAB v0.5
**Aggiornamento documentazione v0.5: 11/11/2026, ore 12:48 CET**

## Nuovo checkpoint visuale v0.5 — 11/11/2026 12:48 CET

- [x] **FOOTPRINT v0.5 visibile e dati nativi presenti** su `FXCM:EURUSD` M5 (screenshot utente). Indicatore `REMURA Order Flow Radar Premium LAB v0.5` compilato e pannello presente.
- [x] Verifica qualitativa di Buy 92, Sell 109, Delta -17, Delta/Volume circa -8,5%, 0 righe BUY imbalance e 0 righe SELL imbalance su candela LIVE. POC/VAH/VAL visibili: dati provvisori, nessuna interpretazione istituzionale.
- [ ] Verificare **vista RADAR** del medesimo script v0.5 e confronto dei marker ER con v0.4.
- [ ] Verificare variazioni durante la candela e dati della candela chiusa; differenze footprint vs delta stimato.
- [ ] Avviare protocollo di misurazione a 3/6/12 barre (M5), prima ipotesi e benchmark fissati *prima* di interpretare gli esiti.

Nota: nel grafico l'utente ha attivato anche il tipo **Footprint volume nativo**. Le celle colorate appartengono al tipo di grafico TradingView, NON alla tabella disegnata dallo script Pine.

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

## Test Premium riuscito e integrazione v0.5 (11/11/2026, ore 12:40 CET)

- [x] `REMURA-Footprint-Premium-Probe.pine` si compila e produce dati in TradingView su **FXCM:EURUSD M5** (screenshot utente). POC/VAH/VAL e imbalance valorizzati; sulla candela LIVE osservati buy 16, sell 23, delta -7, POC 1.11335, VAH 1.11340, VAL 1.11330, BUY IMB=0, SELL IMB=1.
- [x] Creata **[REMURA-Order-Flow-Radar-Premium-v0.5.pine](REMURA-Order-Flow-Radar-Premium-v0.5.pine)** come nuovo file separato. Condivide in un unico script il radar v0.4 e i campi Footprint Premium, con viste RADAR/FOOTPRINT selezionabili; una sola `request.footprint()`.
- [x] Preservati ER, marcatori, ultimi tre picchi, livelli Week/Monthly e alert solo su barre confermate.
- [ ] **Test compilazione** v0.5 in Pine Editor + screenshot delle viste FOOTPRINT e RADAR; controllare feed N/D e aggiornamento LIVE.
- [ ] Confronto su alcuni eventi della differenza tra delta intrabar stimato e footprint (non forzarne uguaglianza).
- [ ] Valutare se POC/imbalance migliorano la capacità di leggere Sforzo/Risultato in modo prospettico, senza introdurli ancora nei segnali.
- [ ] Definire le metriche di efficacia a 15/30/60 minuti su dati prospettici e procedere alla loro misurazione. Includere falsi positivi e benchmark.

**Limite:** footprint FXCM non identifica esecuzioni CME o banche. v0.5 ancora senza test sul grafico; resta una ricerca separata in PR #102 DRAFT.

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
