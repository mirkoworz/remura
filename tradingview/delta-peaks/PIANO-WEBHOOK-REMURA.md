# REMURA — Piano TradingView Premium → REMURA (solo progettazione)
**Aggiornamento: 11/11/2026, ore 13:55 CET**  
**Stato: NON ATTIVO, nessuna credenziale o URL webhook configurato.**  
**Riferimento:** [Radar ALL-IN-ONE v0.7](REMURA-ALL-IN-ONE-Premium-v0.7.pine) | [Manuale](MANUALE-V07-ORDER-FLOW.md)

## Obiettivo
Portare a REMURA **numeri e eventi** dal Pine (non screenshot della tabella) in formato strutturato. REMURA dovrà riconciliare con i propri dati, valutare qualità/freschezza della fonte, motivazioni e rischi e dare una valutazione motivata **ATTENDERE / SETUP DA STUDIARE / POSSIBILE LONG / POSSIBILE SHORT**. **Nessun ordine automatico in questa fase.**

## Fasi, sempre offline/prospettiche prima dell'attivazione live
1. **Inventario**: mappare campi Pine disponibili e feed REMURA già presenti; evitare duplicazioni di raccolta.
2. **v0.8-PINE-TELEMETRY (ramo separato o nuovo file)**: `alert()` con messaggio JSON dinamico e `alert.freq_once_per_bar_close`, inviato a eventi **ER+/ER-, nuovo livello DAY, sostituzione livello DAY, retest DAY/Previous DAY**, eventualmente heartbeat ogni 5m come impostazione opzionale (evitare spam). Mantenere i 4 alertcondition preesistenti per utente.
3. **Gateway webhook**: ricevitore HTTPS controllato (iniziare valutando risorse già attive; alternativa Cloudflare Workers Free) che accetta JSON, autentica richiesta con meccanismo appropriato senza includere password o token privilegiati nel repo/Pine, applica allowlist di IP se fattibile, schema validation, limiti dimensione/frequenza, controllo orologio e idempotenza `symbol+tf+barClose+eventType+version`. Risponde rapidamente; la consegna TradingView NON è garantita.
4. **Storage**: per primi test appoggiare su storage già disponibile in REMURA; valutare Firestore Spark o altra opzione gratuita evitando la pubblicazione sul sito pubblico dei dataset sensibili. Gestire quote e retention, nessun abbonamento aggiuntivo senza consenso.
5. **Motore**: analisi con regole spiegabili, baseline e validazione prospettica/out-of-sample. Non attribuire volume Forex FXCM a CME o banche. Non produrre percentuali di affidabilità senza campioni adeguati.
6. **UI**: pagina per eventi con dati originali, versione algoritmo, latency e stato di qualità (LIVE/CONFERMATO/MANCANTE), diagnosi e motivi del verdetto.
7. **Solo dopo**: notifiche push e possibili segnali operativi con controlli rischio (spread/slippage/ora/news/stop/limite perdite); ordini automatici **non autorizzati** da questo piano.

## Esempio di payload di progettazione (non attivo)
```json
{
  "schema": "remura.tv.flow.v1",
  "source": "TRADINGVIEW_FXCM_ESTIMATED",
  "indicator": "REMURA_ALL_IN_ONE_0.7",
  "event": "DAY1_RETEST",
  "symbol": "FXCM:EURUSD",
  "timeframe": "5",
  "bar_close_ms": 0,
  "confirmed": true,
  "close": 1.115,
  "delta_intrabar": 2400,
  "effort": 4.8,
  "efficiency": 0.042,
  "footprint": {
    "buy": 1900, "sell": 1650, "delta": 250,
    "poc": 1.1149, "vah": 1.1152, "val": 1.1146,
    "imb_buy_rows": 3, "imb_sell_rows": 1
  },
  "levels": {"day1": 1.115, "day2": null, "day3": null,
             "previous_day": null, "week": null, "current_month": null,
             "previous_month": null},
  "quality": "TEST_ONLY_EXAMPLE"
}
```
Tutti i numeri di questo esempio sono **fittizi**, e `bar_close_ms=0` è un segnaposto. In produzione usare `time_close` dell'evento e valori reali; campi mancanti devono essere JSON null, non NaN.

## Trasmissione dei dati
- Pine può formare JSON con serie runtime e spedirlo tramite `alert()` e webhook URL impostato nell'alert TradingView; `alertcondition()` usa testo statico/placeholder.
- I valori footprint complessivi (Buy/Sell/Delta/POC/VA/imbalance) e prezzi dei livelli del Pine sono calcolabili per un messaggio; anche **alcune righe `volume_row`** possono essere serializzate in una rappresentazione selezionata, ma non è l'esportazione magica dell'intero grafico footprint.
- Per test robusti preferire **eventi confermati** alla chiusura della candela e salvare ogni messaggio PRIMA di osservare la risposta futura. `LIVE` può ripitturare.
- Un alert TradingView contiene uno snapshot delle impostazioni/script usati alla creazione: quando cambi la versione, serve ricrearlo. TradingView webhook richiede 2FA, HTTPS pubblico 443 (o 80), server veloce (risposta entro 3s).
- Il ricevitore deve salvare anche il JSON originale, log di validazione ed errore delivery, e impedire doppie registrazioni.
- TradingView può non consegnare alcuni webhook, e la profondità/granularità dei Footprint cambia con lo storico.

## Architettura proposta
```
TradingView Premium + Pine v0.8 alert(JSON, bar close)
                 |
                 v HTTPS webhook
        Gateway isolato gratuito e sicuro
                 |
                 v
   Archivio eventi/quote REMURA (da verificare)
                 |
                 v
  Filone B: validazione/score + Filone C: visualizzazione
                 |
                 v
  Verdetto: ATTENDI / SETUP / VALUTA LONG / VALUTA SHORT
  + motivi + dati mancanti + livello invalidazione
  NESSUN TRADE AUTOMATICO
```

## Costi da verificare PRIMA di implementare
- TradingView Premium già presente. Attivazione webhook consentita dal piano ma richiede 2FA.
- Cloudflare Workers Free: 100.000 richieste/giorno, 10ms CPU/invocazione (limiti ufficiali al 29/10/2026). Limite gratuito NON equivale a zero limiti di storage; verificare scelta finale.
- Cloud Firestore standard free: 20.000 scritture/giorno, 50.000 letture/giorno, 1GiB archiviazione, **solo una database con quota gratuita**; non dare per scontato disponibilità nella configurazione attuale.
- Oracle VPS e raccolta già esistenti: NON dipendere da un upgrade a pagamento; verificare continuità dopo Free Trial senza modificarne le policy o intersecare i filoni.
- Volume teorico M5: 288 barre per 24h per mercato; l'invio solo per eventi riduce il volume. Le quotazioni e dati CME in tempo reale non sono incluse per il solo fatto di avere Premium.

## Fonti ufficiali
- [Alert dinamici Pine](https://www.tradingview.com/pine-script-docs/concepts/alerts/)
- [Webhook TradingView](https://it.tradingview.com/support/solutions/43000529348/)
- [Footprint Pine](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)
- [Workers Free](https://developers.cloudflare.com/workers/platform/limits/)
- [Firestore Free](https://firebase.google.com/docs/firestore/pricing)
