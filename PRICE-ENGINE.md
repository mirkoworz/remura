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

## Opzione 6 — cTrader Open API ufficiale, adapter pronto in attesa dell'approvazione

Il file `scripts/ctrader_feed.py` ora esiste nel ramo di sviluppo. Si appoggia all'SDK ufficiale Spotware `ctrader-open-api` e legge esclusivamente:

- autenticazione applicazione e **soltanto il conto esplicitamente autorizzato** dal token OAuth;
- elenco simboli abilitati del broker, `symbolId` e `digits` del loro server;
- `ProtoOAGetTrendbarsReq` per candele M15 storiche, tramite finestre UTC di 24 ore e richieste seriali (circa 3/secondo);
- decodifica dei prezzi relativi `low + deltaOpen/High/Close`, convertiti da unità /100000 e arrotondati alla precisione ufficiale del simbolo;
- esclusione automatica delle candele ancora in formazione tramite `price_feed.market_document`.

Non sono presenti messaggi di apertura/chiusura ordini e non vengono richiesti saldo, posizioni aperte o informazioni della prop firm non necessarie all'analisi.

**STATO: soltanto codice preparato e testato con simulazioni.** Fino a quando Spotware non approva l'app, non si può effettuare l'autorizzazione reale del conto né verificare i ticker del broker. Nessun token API è presente nel repository.

Documentazione ufficiale: https://help.ctrader.com/open-api/api-application/ e https://help.ctrader.com/open-api/account-authentication/.

### Dopo l'approvazione: autorizzazione locale, senza trasmettere segreti a ChatGPT

1. Imposta sul portale la Redirect URI reale della futura applicazione protetta (non GitHub Pages pubblico).
2. Apri tu il flusso OAuth ufficiale cTrader con `scope=accounts`, non `scope=trading`.
3. Recupera i token e il tuo account ID **esclusivamente nel tuo ambiente protetto**; non pubblicarli in screenshot, messaggi, GitHub né JavaScript.
4. Su computer con Python 3.11+ e connessione Internet installa l'SDK `pip install ctrader-open-api`.
5. Imposta sul computer/server privato le variabili d'ambiente `CTRADER_CLIENT_ID`, `CTRADER_CLIENT_SECRET`, `CTRADER_ACCESS_TOKEN`, `CTRADER_ACCOUNT_ID`, `CTRADER_ENV` (`demo` o `live`).
6. Avvia:

```bash
python scripts/ctrader_feed.py --days 14 --symbols EURUSD GBPJPY XAUUSD US500 --output local/price-snapshot.json
```

Se un indice ha un ticker diverso dal simbolo REMURA, usa `--symbol-map private/symbols.json` con il **nome esatto e verificato del broker**. Lo script rifiuta corrispondenze mancanti o ambigue e scrive `N/D` al posto di prezzi fittizi. Il file locale rimane ignorato da Git.

### Automatizzazione cloud futura

L'adapter è stato progettato per poter essere eseguito periodicamente da un **processo Python privato** senza terminale cTrader aperto. Serve un servizio con connessione TCP in uscita, archivio persistente, gestione sicura del rinnovo OAuth e accesso all'app protetto; GitHub Pages statico non basta. Al momento non sono ancora implementati la rotazione automatica dei token, la persistenza del feed cloud o l'aggiornamento senza importazione sul telefono. Saranno realizzati dopo aver deciso l'ambiente di hosting e autorizzato un conto demo o idoneo.

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


---
## REMURA v1.13 · DAX e petrolio (38 strumenti)

Screenshot cTrader: GER30 (DAX), USOil (WTI), UKOil (Brent), US100 (Nasdaq100), SPX500 (S&P500). REMURA ora supporta GER30, USOIL e UKOIL; le mappature broker *verificate* NAS100→US100 e US500→SPX500 vanno in un file privato `/opt/remura/private/ctrader-symbols.json`, mai nel codice pubblico. DXY e US2000 richiedono ancora verifica sui simboli del broker.

Con `REMURA_SYMBOLS=all`, dopo installazione VPS la rotazione comprende 38 mercati in 8 gruppi da 5, nominalmente ~120 minuti per giro. COT WTI: NYMEX Disaggregated futures-only codice `067651`, distinto dal CFD. Per DAX GER30 (Eurex) e Brent UKOIL (ICE) REMURA mostra COT N/D finché non viene integrata una fonte pertinente e verificata. Non inventiamo posizionamenti istituzionali.

La modifica a `scripts/` richiede installazione manuale approvata sulla VPS, preservando file privati e token.


---
## REMURA v1.14 · Diagnostica visiva di tutti i 38 strumenti

Il nuovo pannello `stato-prezzi.html` è accessibile dal menu iPhone via VPS Tailscale. L'endpoint privato `/private-api/prices/status` produce un unico riepilogo leggero: nome dei 38 strumenti, ultimo timestamp M15, conteggi M15/H1/H4, fonte principale/riserva, data ed esito dell'ultima richiesta cTrader registrata per simbolo. Non serializza liste OHLC, token, password o ID dei conti. Non è accessibile pubblicamente tramite GitHub Pages, a meno di errata configurazione esterna del proxy.

Le categorie risultato per simbolo sono codificate su una whitelist (`ok`, `ticker_unavailable`, `no_historical_bars`, `incomplete_history`, `invalid_bars`, `request_failed`, `unknown_error`). Le risposte cTrader, nomi di errore arbitrari e credenziali non sono esposti. I motivi del mancato salvataggio saranno popolati progressivamente durante i prossimi cicli della VPS v1.14; prima di allora si legge “non ancora registrato”.

Soglia UI: M15 recente entro 180 minuti (rotazione prevista ~120 minuti + buffer), datato oltre la soglia. Un mercato chiuso può apparire datato correttamente, senza implicare che la connessione sia guasta. La dashboard si aggiorna manualmente o ogni 3 minuti se la pagina è visibile.

**Installazione manuale sulla VPS necessaria**: vengono modificati `scripts/price_store.py` e `scripts/private_server.py`, file protetti dal verificatore degli aggiornamenti automatici. I dati privati non vengono cancellati o ricostruiti.


---
## REMURA v1.16 · gruppi di raccolta e tentativi diagnostici corretti

**Correzione verificabile**: in v1.15 il contatore `collector_batch` mostrava il gruppo *successivo* mentre il collector lavorava su quello corrente (errore di indice: incremento anticipato). Ora etichetta il gruppo realmente selezionato, da `1/8` a `8/8`.

Quando la richiesta cTrader restituisce solo un errore globale (per esempio `errors.connection`) o il processo figlio fallisce interamente, registriamo `request_failed` per ciascun simbolo effettivamente tentato, invece di nascondere la situazione dietro un esito generico o `mai`. I codici sono allowlist: nessun messaggio grezzo, secret, token o ID del conto passa nella dashboard privata. Gli storici esistenti, l'elenco degli asset, le API dei prezzi e la pianificazione delle richieste restano immutati.

Test aggiunti: il primo di due gruppi mostra `1/2`; un processo fallito produce uno stato diagnostico per ogni simbolo e non espone il testo dell'errore. **Modifica a `scripts/private_server.py`: installazione manuale sulla VPS richiesta**, con le protezioni dell'autoaggiornamento già esistenti.


---

## REMURA v1.17 · DAX 40, indice dollaro e VIX, senza Russell

La watchlist privata rimane a **38 strumenti** (28 FX + 2 metalli + 6 indici + 2 energie): rimosso **US2000 / Russell 2000**, aggiunto **VIX** come strumento cTrader. Il DAX è prioritario per l'utente. L'identificativo interno **GER30** resta invariato per mantenere lo storico già salvato; sull'attuale screenshot del broker il DAX è indicato **GER40**, quindi eventuali passaggi GER30→GER40 devono avvenire solo mediante **alias privato verificato** dopo aver visto il ticker effettivo dello storico; i due flussi non devono essere mescolati.

Il simbolo logico **DXY** richiede l'alias privato **DXY → USDX** visto nell'elenco strumenti del conto. L'elenco mostra per USDX il riferimento a un contratto **DXZ6** con scadenza: il prezzo del CFD/contratto non va presentato come copia perpetua dell'indice spot ICE DXY né confuso con il COT futures (rilevazione settimanale). Il nuovo **VIX** è mostrato dal broker come contratto sulla volatilità con sigla e scadenza: verificare M15 effettivamente fresche prima di usarlo come indicatore di risk-off; non è per definizione l'indice CBOE spot VIX.

**COT**: DXY mantiene il riferimento futures CFTC già integrato; il VIX non riceve per ora un COT, né riceve impropriamente posizioni istituzionali da altri strumenti. DAX 40 e VIX hanno COT N/D fino a integrazione di fonti appropriate. I dati del prezzo si ottengono esclusivamente da cTrader privato, nessuna candela sintetica.

**Deploy VPS**: modificati i registri backend Python, quindi necessita una installazione manuale del codice verificato dalla branch main. La mappatura si scrive nel file protetto `/opt/remura/private/ctrader-symbols.json` preservando tutte le chiavi esistenti e modalità 0600; includere DXY:USDX. VIX:VIX si risolve per corrispondenza esatta senza alias. Nessuna chiave OAuth, ordine o dato sensibile va inviato a GitHub.


---
## REMURA v1.18 · Radar Macro e audit M15/H1/H4 (solo frontend)

Nuova sezione `stato-prezzi.html#macro` accessibile da menu, con **DAX GER30, DXY/USDX, VIX** e possibilità di controllare un mercato diverso dall'elenco di 38, un simbolo alla volta. Usa esclusivamente `GET /private-api/prices/<SYMBOL>` per richiedere candele cTrader alla **VPS privata**; non richiede nuove dipendenze, credenziali, né modifica `scripts/`.

Qualità: presenza M15/H1/H4, age dalla **chiusura M15** (non apertura), con soglia 180 minuti indicativa; ultimi 97 M15 per contare discontinuità (pause di mercato comprese). Le ultime 30 H1 e 30 H4 vengono ricostruite dalle M15 disponibili e confrontate a OHLC già salvati: contatore di bucket verificati, mancanti o discrepanti. Le discontinuità non sono classificate automaticamente come malfunzionamenti. Per conferme tecniche servono almeno 55 H4.

Correlazione: Pearson sui **rendimenti logaritmici H1** di coppie DAX-DXY, DAX-VIX, DXY-VIX, soltanto quando gli orari UTC degli intervalli **contigui** coincidono; finestra 336h (14 giorni), almeno 30 coppie. Non viene pubblicata una correlazione utilizzabile su mercati datati/anomali; manca il dato → N/D. Questi risultati **non sono previsioni**, e gli strumenti USDX/VIX possono essere contratti a scadenza non equivalenti agli indici spot. Senza dati comparabili o senza gestione rollover non si generano segnali di trading.

L'aggiornamento è solo frontend (asset allowlist e endpoint già presenti). Il deploy automatico della VPS può aggiornare il codice quando i test sono superati, senza reinstallazione manuale backend. Non viene conservato né pubblicato alcun OHLC sul GitHub.


Il server privato pubblica esclusivamente asset statici allowlist. La nuova analisi è quindi integrata nei file già consentiti `stato-prezzi.html`, `stato-prezzi.js`, `price-status-core.js`, e carica i tre storici soltanto all'apertura dell'ancora `#macro`. Nessun intervento sul backend Python o sui token è necessario.


---
## REMURA v1.19 · Macro globale autonomo, non centrato sul DAX

**Separazione chiara**: nel menu, catalogo, homepage e diagnostica di prezzo ci sono 4 indici azionari (GER30/DAX, US500, NAS100, US30) e 2 indicatori macro (DXY, VIX); gli altri 32 strumenti sono invariati. La raccolta Python resta a 38 simboli identici e nessuno storico cTrader viene cancellato. DXY conserva il suo COT futures ICE di riferimento nella scheda dedicata, ma DXY e VIX vengono esclusi dalla classifica Radar Squali sui movimenti istituzionali, che non deve mescolare indicatori di contesto e opportunità operative.

Radar Macro in `stato-prezzi.html#macro` analizza innanzitutto **solo DXY e VIX**, non DAX. Mostra prezzi validati, ultime quattro ore H1 consecutive e un confronto con la mediana delle variazioni assolute a quattro ore (fino a 80 finestre recenti); nessuna direzione viene indicata se gli storici non sono freschi, coerenti o sufficienti. Le combinazioni dollaro/volatilità sono presentate come *contesti possibili*, non verdetti long/short. L'utente può scegliere **qualunque altro mercato REMURA** (DAX incluso) per leggerne la qualità e due correlazioni H1 contro DXY e contro VIX. La correlazione usa solo rendimenti logaritmici con timestamp UTC comuni e min 30 osservazioni.

Le quotazioni cTrader USDX e VIX possono derivare da contratti a scadenza e non essere uguali agli indici spot. Le correlazioni non significano causalità né individuano direttamente il flusso degli istituzionali. Nessun endpoint, token, data privata o script backend modificato: aggiornamento frontend auto-distribuibile dopo test GitHub.
