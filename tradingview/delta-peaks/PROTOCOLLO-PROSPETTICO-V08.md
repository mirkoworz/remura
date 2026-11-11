# REMURA — Protocollo prospettico v0.8.1 TELEMETRY (LAB)
**Versione aggiornamento: 0.8.1 — 11/11/2026, ore 16:18 CET**
**STATO: SOLO OFFLINE — nessun alert, gateway, cron o ordine attivato.**

## Obiettivo e preregistrazione (congelare prima degli esiti)
Pilota: `FXCM:EURUSD` M5, TradingView Premium, timeframe intrabar 1m,
footprint 10 tick/riga, value area 70%, imbalance 300%, DAY threshold 1.5,
ER effort >= 3.5, efficiency <= 0.07, minPeakGap = 6 (barre **intermedie**),
livelli con anchor HL2 (POC in un esperimento distinto).
Nessuna ottimizzazione delle soglie durante il pilota. Il primo test resta esplorativo.
Trattare i segnali come osservazioni, non ordini né prova di ordini istituzionali.

## Contratto evento `remura.tv.flow.v1`
La v0.8.1 emette **un JSON per barra chiusa** quando almeno un flag è vero;
heartbeat opzionale DISATTIVATO. Gli eventi simultanei sono flag separati in
`events`; non forzare un solo tipo. `bar_close_ms` è l'istante di **chiusura UTC
in millisecondi**, `sent_clock_ms` è l'orologio Pine (diagnostico), mentre
`received_at_ms` verrà timbrato DAL GATEWAY, mai fidarsi dell'ora del client.
`event_type` = BAR_EVENT oppure HEARTBEAT. `version` = 0.8.1-lab.
`symbol` include il prefisso feed, `timeframe` è il codice TradingView "5".
`confirmed` e `realtime` devono essere true.

- `ohlc`: open/high/low/close, `prev_close`, ATR14 all'evento; questi valori sono
  il prezzo e il denominatore dell'esito congelato.
- `delta_intrabar`, `effort`, `signed_result_atr`, `efficiency` = stime
  intrabar; `footprint` fornisce buy/sell/delta/POC/VAH/VAL/imbalance e
  `available`. Nessuna equivalenza con tape CME.
- `levels` e `level_origin_ms` fotografano DAY1–3, previous day, WEEK e i
  due MONTH. `level_scores` include i valori dei primi tre DAY.
- `events` distingue peak, ER+/ER-, action `ADDED|REPLACED|NONE`,
  rank aggiunto, livello espulso, e 4 flag di retest DAY1/DAY2/DAY3/
  previous day.
- `quality` dichiara disponibilità dei dati, tipo di volume, lower TF,
  anchor e età relativa `freshness_ms`. Un numero sconosciuto è JSON `null`,
  mai "N/D", NaN, Infinity, né inventato come 0.
- Identità snapshot: `symbol|timeframe|bar_close_ms|version|event_type`.
  La fonte vera di deduplica usa questa chiave; ogni nuovo livello ha
  identità `symbol|timeframe|level_origin_ms|anchor`. I RANK cambiano,
  l'identità del livello resta. Conservare sia livello espulso sia stato
  aggiornato. Se cambia parametro/versione, trattare come nuovo esperimento.

## Protocollo misurazione: ER, RT e picchi DAY
1. Accettare SOLO eventi osservati **in tempo reale**, arrivati al gateway prima
   dell'inizio della finestra di esito. Gli esempi offline e le simulazioni
   restano fuori dalla statistica prospettica.
2. Per ciascuna barra evento `t0`, fissare timestamp, close_t0,
   ATR14_t0, high/low, livello e origine. Distinguere sottotipi:
   ER_POS, ER_NEG, RETEST_DAY1/2/3, RETEST_PREVIOUS_DAY, DAY_ADDED,
   DAY_REPLACED; una barra può popolare più coorti senza essere contata
   due volte nella coorte aggregata.
3. Dopo 3, 6, 12 **barre M5 effettivamente successive** misurare:
   `return_atr_h = (close[t0+h]-close_t0)/ATR14_t0`;
   `mfe_up_atr_h = (max(high[t0+1:t0+h])-close_t0)/ATR14_t0`;
   `mae_down_atr_h = (min(low[t0+1:t0+h])-close_t0)/ATR14_t0`.
   Sono orientamenti grezzi senza supposizione di LONG o SHORT.
   ATR14_t0 <= 0, barre mancanti o orari irregolari => esito MISSING,
   **mai** interpolare o eliminare silenziosamente fallimenti.
4. Classificare per il retest `RIFIUTO` se close a t+h resta dal lato
   precedente al tocco per almeno 0.1 ATR14_t0, `ROTTURA` se dal lato
   opposto per almeno 0.1 ATR; altrimenti `INDEFINITO`.
   Lato precedente = segno(prev_close - prezzo_del_livello). Se
   prev_close coincide col livello => INDEFINITO. Etichette a ogni h.
5. ER_POS ed ER_NEG NON implicano SHORT/LONG: registrare entrambi i
   segni del ritorno; l'ipotesi esplorativa di contrarian è una coorte
   dichiarata, non un filtro nascosto. Riportare sempre continuazione,
   inversione e movimenti nulli.
6. Anche se un livello DAY è sostituito durante la finestra, la sua
   osservazione rimane nel dataset. Registrare `evicted`, nuovo rank,
   scomparsa e tempo di vita: non usare la classifica finale del giorno
   per correggere i segnali precedenti.
7. Benchmark prefissati: **tutte le barre M5 confrontabili** della stessa
   finestra/simbolo/sessione senza evento, e un benchmark di segno
   permutato per ER. Non selezionare controlli dopo aver visto i profitti.
   Se i dati delle barre senza evento mancano, benchmark NON VALUTABILE.
8. Preservare contatori di **tutti** gli eventi, falsi positivi e missing:
   tasso copertura, duplicati, latenza gateway, disponibile footprint,
   per-sessione, per-livello e percentuale di sostituzione. Per eventuali
   modelli usare split temporale train/test out-of-sample, non random
   mescolando eventi sovrapposti; includere costi ipotetici spread/slippage
   separati, senza scambiarli per dati reali.
9. Nessuna conclusione di efficacia con pochi casi: prima confronto
   descrittivo, intervalli di confidenza, dipendenze temporali e verifica
   rispetto ai benchmark. NON trasformare una coorte favorevole in un
   comando di ingresso. Verdetti di REMURA B/C solo su futura integrazione
   autorizzata.

## Sequenza e isolamento
- Check statici Pine offline; test manuale **di compilazione** TradingView è
  ancora PENDING, senza creare alert.
- Validatore Python `validate_telemetry_v1.py` rifiuta input errati e duplicati.
  Dati di unit test sono SINTETICI, non risultati reali.
- Gateway HTTPS isolato: solo dopo revisione di autenticazione (non inserire
  password o segreti nel messaggio alert), allowlist IP da documentazione
  TradingView e ulteriori difese, rate limit/body limit, validazione,
  idempotenza, log dei rifiuti, retention e storage.
- Workers Free (documentazione 29/10/2026): 100.000 richieste/giorno,
  10ms CPU per chiamata. 1 heartbeat/M5 = **288 richieste/giorno per
  simbolo a mercato continuo** prima degli altri eventi/riconsegne.
  Richiede conteggio con gli altri servizi Cloudflare nello stesso account.
  Workers D1 Free ha limiti separati, applicati con blocco oltre quota.
- TradingView: webhook HTTP POST JSON con 2FA, porte 80/443 e timeout
  del server dopo 3s. La consegna può fallire; non significa che il
  segnale non si sia verificato. Monitorare registri e buchi.
- **Nessun** deploy Cloudflare/Oracle/Firestore, nessun webhook TV,
  nessuna modifica a filoni A/B/C o all'applicazione in produzione.

## Da verificare prima della prima osservazione reale
Compilazione Pine v0.8.1; cambio giornata; campo `prev_close`; `null`;
nuovo DAY e sostituzioni; POC N/D; eventi simultanei; assenza di alert con
telemetria OFF; frequenza e ritardi; quote e disponibilità storage.
