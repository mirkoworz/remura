# REMURA v1.0 · Motore prezzi personale (in sviluppo)

REMURA v0.9 resta pubblicata separatamente. La v1.0 introduce un componente **locale e manuale** per collegare prezzi OHLC verificabili all'analisi COT e al sentiment già presenti. Nessuna API key, file OHLC o dato del tuo broker viene aggiunto a GitHub.

**Attenzione privacy:** il repository e il sito GitHub Pages esistenti sono pubblici. "Solo uso personale" non rende automaticamente privati sito o repository. Questa nuova funzione viene preparata su un ramo separato: non pubblicarla finché non avremo deciso come utilizzare un ambiente realmente privato. Non caricare mai file OHLC o token come commit GitHub o secret nella pagina. Il file selezionato nel browser viene elaborato in memoria e non inviato dal nostro modulo a un server.

## Come funziona

1. Il raccoglitore `scripts/price_feed.py` recupera M15 chiuse da **Twelve Data**, **OANDA v20** oppure un **CSV M15 UTC** esportato da un terminale MT5/cTrader o da un fornitore consentito.
2. Con controlli espliciti su allineamento UTC, ordinamento e dati mancanti, vengono ricostruite solo barre H1 e H4 che contengono rispettivamente 4 e 16 M15 **contigue** e complete. Nessuna candela sintetica per colmare i buchi.
3. Il raccoglitore salva `local/price-snapshot.json` sul TUO computer, ignorato da Git. Una volta attivata l'interfaccia, dalla scheda REMURA si seleziona il file con il controllo **Importa il tuo file prezzi locale** (anche tramite app File di iPhone).
4. L'analisi calcola EMA20/EMA50, ATR14, supporti/resistenze precedenti e conferma della rottura mediante due chiusure oltre 20 candele precedenti (+/- 0,1 ATR). Poi confronta H4, H1, M15, bias COT recente e Myfxbook quando disponibile.
5. Se prezzi, timeframe, COT o retail mancano, sono datati o discordanti, il risultato resta **N/D / Monitorare**. Non vengono inventati ordini, target, stop o percentuali di successo.

**NOTA**: queste condizioni sono euristiche da testare; non risultano ancora backtestate su storico di esecuzioni e COT con timestamp di pubblicazione.

## Requisiti

- Python 3.11+ su computer locale, nessuna libreria da installare.
- Uno tra: una chiave API Twelve Data, un token OANDA v20 idoneo, oppure un tuo CSV di candele.
- Internet soltanto per gli adapter API; modalità CSV completamente offline.
- Non serve MetaApi.

## Opzione 1 — Twelve Data (Forex, verifica copertura metalli)

Crea un account e ottieni una chiave personale: https://twelvedata.com/pricing

Imposta la variabile d'ambiente **solo sul tuo computer**: `TWELVE_DATA_API_KEY`. Non scriverla nei comandi condivisi, in GitHub, negli screenshot o nel JavaScript della pagina.

Poi esegui nella cartella REMURA:

```bash
python scripts/price_feed.py --provider twelve --symbols EURUSD GBPUSD XAUUSD --output local/price-snapshot.json
```

Il piano Basic dichiarato dal fornitore ha 8 crediti API/minuto e 800/giorno; lo script attende 9 secondi fra i simboli per prudenza. La disponibilità di ogni mercato e di ogni granularità dipende dal piano: in caso di risposta negativa non crea prezzi di esempio.

Per tutte le coppie puoi passare i 28 simboli come argomenti. Per indici e CFD la mappatura **NON è automaticamente inventata**: consulta i simboli esatti del provider, quindi aggiungili ad un tuo file JSON locale (esempio `private/symbols.json`) e passa `--symbol-map private/symbols.json`.

## Opzione 2 — OANDA v20

OANDA pubblica il servizio practice e live: https://developer.oanda.com/rest-live-v20/development-guide/

È necessario un token abilitato per il tuo account e il mercato di riferimento. Imposta **sul tuo computer** `OANDA_API_TOKEN`.

```bash
python scripts/price_feed.py --provider oanda --oanda-environment practice --symbols EURUSD GBPJPY XAUUSD --output local/price-snapshot.json
```

Lo script interroga `/v3/instruments/<INSTRUMENT>/candles`, con `granularity=M15`, `price=M` (midpoint) e `count=2400` per default. Esclude le candele segnate `complete=false`.

Per indici o strumenti non standard non assumiamo che tutti i broker abbiano lo stesso ticker. Esempio di struttura di un *file privato*, da adattare SOLO dopo avere verificato il simbolo reale sul proprio account:

```json
{
  "US500": "TICKER_ESATTO_DEL_TUO_PROVIDER",
  "NAS100": "ALTRO_TICKER_ESATTO"
}
```

Se OANDA non espone un certo indice/metallo, REMURA lo segnala come non disponibile.

## Opzione 3 — CSV M15 UTC (anche da MT5, cTrader, broker o storico consentito)

Salva su computer un file con intestazione e timestamps UTC:

```csv
datetime,open,high,low,close
2026-01-05T08:00:00Z,1.1020,1.1030,1.1010,1.1025
2026-01-05T08:15:00Z,1.1025,1.1035,1.1020,1.1030
```

Le righe mostrate sono SOLO un esempio di formato, **non sono dati di mercato** e non devono essere usate per analizzare un prezzo reale.

```bash
python scripts/price_feed.py --provider csv --symbols EURUSD --csv private/EURUSD-M15.csv --output local/price-snapshot.json
```

Accetta colonne `datetime` oppure `date` + `time` e `open,high,low,close`. I timestamps senza fuso orario sono considerati UTC: converti prima i file esportati in orario broker. Il CSV deve già essere M15.

## Copertura degli strumenti

- **28 Forex:** codici EURUSD ecc. mappati in EUR/USD per Twelve Data o EUR_USD per OANDA. La disponibilità resta da verificare sul fornitore.
- **XAUUSD, XAGUSD:** mappatura nominale dei metalli spot; verificare abilitazione e origine dati.
- **US500, NAS100, US30, US2000, DXY:** ticker e accessibilità sono legati a provider/contratto (future, CFD, indice); **non viene sostituito un asset con un altro** per completare artificialmente la copertura. Aggiungere alias verificati o importare CSV.
- Il report COT rimane quello di futures ufficiali (TFF o Disaggregated); un grafico spot/CFD NON contiene le stesse transazioni del future e gli orari H4 UTC potrebbero differire dal tuo broker.


## Opzione 4 — MetaTrader 5 (senza MetaApi, lettura automatica da PC Windows)

Se hai MT5 installato su Windows, questa è la via più rapida per testare i prezzi del tuo broker. **Non occorre condividere le credenziali REMURA con ChatGPT:** apri MT5, connettiti al tuo account, quindi installa il modulo Python ufficiale localmente.

```powershell
py -m pip install MetaTrader5
py scripts/price_feed.py --provider mt5 --symbols EURUSD GBPJPY XAUUSD XAGUSD --output local/price-snapshot.json
```

Il modulo chiama soltanto `mt5.initialize`, `mt5.symbol_info`, `mt5.symbol_select`, `mt5.copy_rates_from_pos` e `mt5.shutdown` — **nessun ordine, trading automatico, password o storico di operazioni**. L'indice zero corrisponde alla candela potenzialmente non chiusa e le candele vengono filtrate usando l'orario UTC della chiusura.

Le coppie sono cercate con il loro nome esatto (es. `EURUSD`). Se il tuo broker usa suffissi come `EURUSD.r`, devi mappare i simboli reali in `private/symbols.json`. Per gli indici è obbligatoria una corrispondenza esplicita verificata dal tuo broker: non sostituire US500 con DXY o un future non corrispondente.

Per avviare la lettura ripetuta mentre **il computer Windows e il terminale MT5 sono operativi**, usa l'Utilità di pianificazione di Windows e configura ogni 15 minuti il comando `py` con questi argomenti:

```text
scripts/price_feed.py --provider mt5 --symbols EURUSD GBPJPY XAUUSD XAGUSD --output local/price-snapshot.json
```

Imposta **Avvia in** sulla cartella REMURA del tuo computer e limita l'attività a **una sola istanza contemporanea**. Al primo avvio esegui il comando manualmente e controlla i simboli effettivamente disponibili. Lo script non deve essere copiato su GitHub Actions: la piattaforma GitHub non dispone del tuo terminale MT5.

Questa automazione crea soltanto il file **locale**, non lo trasferisce automaticamente su iPhone. Per la visualizzazione privata completamente automatica in remoto serve un backend autenticato; cTrader Open API è la candidata principale.

## Opzione 5 — cTrader Open API (fonte primaria per il cloud)

La Open API ufficiale di cTrader consente la lettura storica e in tempo reale dei trendbar e funziona indipendentemente dal terminale desktop. Richiede però la **registrazione di una tua applicazione**, approvazione Spotware, client ID e OAuth. La voce `scope=accounts` concede sola lettura, mentre `scope=trading` abilita gli ordini: **scegliere sempre accounts** per REMURA. È possibile accedere a demo e live; ambiente e broker vanno verificati.

Per iniziare, consulta https://help.ctrader.com/open-api/api-application/ e accedi al portale https://openapi.ctrader.com/ . Non comunicare `client_secret`, refresh token o credenziali nella chat. I token vanno conservati come segreti di un backend privato.

**Stato della connessione:** adapter cTrader remoto NON ancora autenticato né configurato; sarà completato dopo la registrazione dell'app e la scelta dell'hosting protetto. Non presentare questa guida come connessione cTrader già operativa. La versione attuale supporta in modo verificabile l'importazione di dati CSV, Twelve Data, OANDA e, quando disponibile il terminale Windows, MT5.

## Sicurezza operativa e sviluppi

- Nessun backend pubblico, richiesta prezzi dal browser o caricamento automatico di token. Il file JSON è letto localmente in RAM dall'interfaccia.
- Il selettore file **non carica dati esterni**. Alla chiusura della scheda, l'importazione deve essere ripetuta.
- `local/`, `private/`, `.env` e `data/prices/` sono ignorati da Git.
- Non è ancora inclusa l'acquisizione continua 24/7 né il feed centralizzato di prezzi. Per automatizzare in futuro useremo un ambiente privato autenticato, separato da GitHub Pages pubblico.
- Uso responsabile: prima di automatizzare avvisi va eseguito un backtest con COT disponibile **dal venerdì di pubblicazione**, non dalla data del martedì delle posizioni, e controllo di spread, slippage, sessione e lookahead bias.

Test locali (nessuna API key):

```bash
node --test tests/insights.test.js tests/price.test.js
python -m unittest discover -s tests -p 'test_price_feed.py'
```
