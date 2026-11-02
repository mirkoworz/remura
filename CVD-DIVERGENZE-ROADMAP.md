# REMURA — Specifica roadmap: Divergenze prezzo–CVD e avvisi privati

**Data pianificazione:** 02/11/2026 (Europe/Rome). **Stato:** roadmap e progettazione; NON implementato, NON attivo su VPS, nessuna notifica inviata. Versione applicativa live: v1.57, con priorità EURUSD/XAUUSD attivata alle 17:08 ma cadenza effettiva ancora da misurare.

## Obiettivo

Far rilevare automaticamente a REMURA le divergenze tra massimi/minimi del **prezzo** e il **CVD stimato**, associando solo le evidenze disponibili (tick volume del broker, OHLC chiuse, struttura tecnica, COT e sentiment), indicando dove *potrebbe* formarsi un movimento senza presentare l'evento come trade certo o come prova di attività istituzionale.

**Distinzione fondamentale:** il CVD oggi presente in `price-core.js` è `delta_proxy = tick_volume * CLV` con `CLV=(2*close-high-low)/(high-low)`, e somma cumulata della sola giornata UTC, su M15; i prezzi sono parte della stessa formula. È quindi una stima **non indipendente dal prezzo**, non delta aggressivo di ordini eseguiti. CFTC/COT è settimanale; non è un trigger intraday. cTrader documenta `ProtoOATrendbar.volume` come *volume in tick*, non contratti/lot acquistati o venduti.

## Fase DIV-0 — Qualità, cadenza e contesto (prima di qualunque alert)

- [ ] Dimostrare dai log VPS su almeno due cicli completi dopo l'attivazione v1.57 che EURUSD/XAUUSD ricevono tentativi `lastAttempt` con intervalli coerenti col piano di ~60 min, esito valido, e che tutti gli altri 36 mercati conservano i dati.
- [ ] Verificare giorno/sessione, contiguità M15, tick volume non nullo/negativo/assente, broker/provenienza, UTC e freschezza. Nessuna divergenza valida se il `flow.status` è `partial`, `missing`, `stale` o se ultimo M15 ha età oltre la guardia corrente di 90 minuti.
- [ ] Riprodurre **esattamente** sul server l'algoritmo CVD mostrato in `price-core.js`, con test numerici incrociati JS/Python, evitando che l'UI e gli alert producano numeri differenti. Non mischiare periodi UTC o dati di broker diversi.
- [ ] Valutare lo storico utile per due swing confermati *entro la stessa sessione UTC*. Il CVD corrente si resetta ogni giornata; non confrontare automaticamente massimi del giorno precedente. Se mancano due swing significativi, stato `DATI_INSUFFICIENTI` (non forzare una segnalazione).

## Fase DIV-1 — Rilevatore deterministico di divergenze

- [ ] Su **candele M15 chiuse**, identificare swing high/low del prezzo con pivot sinistri/destri confermati (es. 2+2 M15 come candidato iniziale, poi confronto tra parametri). Un pivot viene conosciuto **solo dopo** le barre di conferma, non alla sua candela centrale; salvare timestamp del pivot e timestamp reale di riconoscimento.
- [ ] Confrontare il CVD **agli stessi timestamp dei pivot di prezzo** (niente scelta opportunistica di due picchi CVD diversi); imporre distanze temporali e numero di barre minimi/massimi tra gli swing. Tolleranze basate su ATR/volatilità e tick volume, per evitare micro-divergenze e flat.
- [ ] **Divergenza rialzista regolare:** prezzo minimo 2 più basso del minimo 1 (LL), CVD allo stesso pivot 2 più alto del precedente (HL). **Ribassista regolare:** prezzo massimo 2 più alto (HH), CVD al secondo pivot più basso (LH).
- [ ] Versioni *nascoste* (continuazione) solo in una seconda iterazione, classificate separatamente: rialzista prezzo HL/CVD LL; ribassista prezzo LH/CVD HH. Nessun mescolamento dei risultati tra regolari e nascoste.
- [ ] Se l'ultima candela chiusa modifica il contesto prima del pivot confermato, classificare `POTENZIALE_NON_CONFERMATA` (eventuale anteprima solo in app, **mai** alert di divergenza confermata). Una volta emesso, un evento non viene riscritto con dati futuri.
- [ ] Aggiungere segnali di **fallimento della divergenza** (es. rottura in direzione opposta, sweep non confermato) e un timestamp di scadenza, non solo stati positivi.

## Fase DIV-2 — Qualificazione e pagina Radar Squali

- [ ] Introdurre nel Radar/Squalincome una scheda autonoma `DIVERGENZE PREZZO–CVD (proxy)`: simbolo, rialzista/ribassista, tipo regolare/nascosta, due coppie di pivot con orari UTC/Italia, prezzo, CVD, ampiezza in ATR/tick-volume, freshness, motivo, stato `OSSERVAZIONE | CONFERMATA | INVALIDATA | N/D`. NON confondere con l'attuale etichetta `divergent` di Squalincome, che indica **COT contro direzione del prezzo**.
- [ ] Evidenziare graficamente **i due swing su prezzo e CVD** con linee coerenti e date di disponibilità; nessun grafico “repainting”. I valori CVD sono **unità di tick-volume stimato**, non lotti o pressione reale di compratori/venditori.
- [ ] Confluenze separabili e verificabili: struttura M15/H1/H4, livelli/sweep (quando realmente calcolati), volatilità, COT pubblicato alla data corretta, evoluzione Myfxbook/Capital solo se freschi. Non sommare punteggi duplicati derivati dallo stesso OHLC.
- [ ] Stato `OSSERVAZIONE` non significa “compra/vendi”; `CONFERMATA` significa solo regola tecnica verificata, non inversione garantita. Nessun auto-trading.

## Fase DIV-3 — Storico eventi, backtest e falsi positivi

- [ ] Persistenza **privata** in SQLite: identificativo deterministico `(broker,symbol,tf,session_utc,tipo,pivot_1,pivot_2,versione_algoritmo)`, input-fingerprint, `observed_at`, `confirmed_at`, `invalidated_at`, qualità, due valori pivot prezzo/CVD e contesto. Idempotenza su ricalcolo e riavvii, retention configurabile.
- [ ] Test offline: pivot su plateau/equal highs, doji, volume zero, gaps, fine giornata UTC, cambio DST Italia, feed stale, due mercati, broker diversi, storico insufficiente, ritardi, aggiornamento di una stessa candela, riavvio e mancata duplicazione. Prevenire **look-ahead** e uso del `confirmed_at` prima del reale tempo di disponibilità dati.
- [ ] Backtest “walk-forward” e campioni **in avanti**. Misure a 1h/4h/24h: movimento favorevole/sfavorevole, MFE/MAE, percentuale di falsi allarmi, precisione, expectancy simulata **al netto di spread/slippage**, drawdown e intervalli di confidenza; distinguere sessioni e strumenti.
- [ ] **Benchmark obbligatorio:** confrontare prezzo-solo/pivot+ATR con prezzo+proxy CVD sullo stesso campione. Poiché `CLV` dipende dal prezzo, l'eventuale “vantaggio CVD” non può essere presunto. Se il proxy non aggiunge valore fuori campione, lasciare il radar come osservazione e NON promuovere notifiche operative.
- [ ] Eventuale fase indipendente: valutare tick Bid/Ask live/storici cTrader e un proxy distinto, tenendo presente che quote Bid/Ask **non** rivelano eseguiti né aggressor effettivo; il vero CVD eseguiti richiederebbe feed futures e verifica licenza/costo.

## Fase DIV-4 — Notifiche iPhone solo dopo validazione

- [ ] Prima: **eventi nell'app + archivio** senza notifiche esterne, con filtro `solo confermate / tutte le osservazioni`, uno stato “nuovo evento” e possibilità di disattivare gli alert.
- [ ] Poi canale privato opt-in: **Web Push** per REMURA aggiunta alla Home iPhone (supporto Apple da iOS 16.4, richiede HTTPS, Service Worker, permesso utente con gesto esplicito, subscription sicura e server con connettività push); nessun abbonamento Apple Developer necessario. Verificare compatibilità con REMURA su Tailscale, dominio/certificato e raggiungibilità outbound.
- [ ] Alternativa se Web Push con Tailscale è problematico: **bot Telegram privato** (Bot API), token e chat ID conservati solo in `private/`, verifica destinatario, HTTPS uscente e nessuna informazione sensibile nel repository/log. Richiede scelta esplicita dell'utente: i messaggi transitano da infrastruttura di terze parti.
- [ ] Regole anti-spam: deduplica su ID evento, un alert per divergenza confermata + facoltativa invalidazione, cooldown per simbolo/tipo, tetto giornaliero, finestra oraria configurabile, retry idempotente, nessuna notifica per dati stale o scomparsi. Non inviare segnalazioni per varianti “potenziali” finché non dimostrano utilità.
- [ ] Esempio testo: `REMURA · XAUUSD M15 · divergenza rialzista regolare CONFERMATA · pivot (orari) · prezzo LL / CVD proxy HL · qualità dati OK · nessun ordine automatico · apri dettaglio privato`. Senza linguaggio “squalo sta comprando” o “trade sicuro”.
- [ ] Verificare spedizione, ritardi, revoca permesso, offline iPhone, gestione ripristino, privacy e costi dati/quote prima di abilitare le notifiche vere.

## Ordine di consegna / criteri di uscita

1. **Ora:** chiudere la prova della frequenza prioritaria v1.57; 38/38, qualità, costi. Nessuna variazione del collector mentre si misura.
2. **Prossimo sviluppo, candidato v1.58:** rilevazione e test **offline** delle divergenze M15 su EURUSD/XAUUSD con JSON locale e dati sintetici, senza modificare subito la VPS e senza notifiche.
3. **Solo dopo test:** rilascio protetto/backup e dashboard in-app, con versione/data/ora italiana in tutte le pagine; confrontare output e latenza live.
4. **Solo dopo valore incrementale verificato:** notifiche private opt-in, graduali e revocabili; nessun costo/servizio a pagamento senza approvazione.
5. Espansione ad altri mercati/timeframe soltanto dopo misure e regolazione del carico, evitando parametri “ottimizzati” retroattivamente sui successi.

**Nota sul "gratis":** la fase di calcolo su SQLite e dati OHLCV già raccolti non richiede nuove API broker. L'eventuale ricampionamento tick, i sistemi push e i controlli cloud vanno invece misurati; OCI RAM/disco bassi da soli non certificano il costo della rete o la permanenza in Always Free.

Fonti di riferimento: cTrader `https://help.ctrader.com/open-api/model-messages/` (volume trendbar in tick); Apple Web Push `https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers`; Telegram `https://core.telegram.org/bots/api`.
