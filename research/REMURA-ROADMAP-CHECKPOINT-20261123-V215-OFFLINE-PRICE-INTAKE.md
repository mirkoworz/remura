# REMURA — Filone A V21.5 LAB — ingresso dati privati in una sola operazione

**Aggiornamento V21.5 · 23/11/26, 22:18:05 Europe/Rome.** PR #112 Draft, ramo `research/remura-v211-source-derived-cvd-20261123`. Solo codice di ricerca offline: no merge, deploy, letture Cloudflare/D1, broker, Mac, Oracle, operazioni o spese.

## Cosa è stato collegato

`research/v215_offline_price_readiness.py` richiama **senza riscriverli** il validatore della prova autentica V20.3 da 12 ricevute TEST e il lettore cTrader M15 V20.4 già esistente. Con una **copia SQLite locale e coerente**, il comando risponde solo con conteggi delle quattro coorti M15 ipotetiche coperte realmente per 60m/4h/24h, finestre non ancora mature e candele mancanti. I prezzi numerici, i ticker broker, i percorsi privati e i dati sensibili non sono mai visualizzati. Non calcola P&L, operazioni, segnali, profitti o alpha.

**Utilizzo senza DB:** `python3 research/v215_offline_price_readiness.py` restituisce solo `AWAITING_LOCAL_PRIVATE_SQLITE_COPY` e non scrive nulla.

**Utilizzo futuro con la copia privata già disponibile:**

~~~bash
python3 research/v215_offline_price_readiness.py \
  --offline-sqlite ~/REMURA-private-offline/remura-prices-snapshot.sqlite3 \
  --confirm-offline-copy
~~~

Il flag `--confirm-offline-copy` è una dichiarazione dell'operatore: non è una prova automatica che il DB sia una copia. Non usare come argomento il database live del collector/Oracle. Il lettore è `sqlite3 mode=ro + PRAGMA query_only=ON`. La registrazione originale `research/real-proofs/REMURA-V203-CVD-TEST-RECEIPTS-20261123.json` rimane immutata.

### Passaggio manuale minimo, quando il proprietario ha il Mac e un DB già accessibile

Occorre soltanto disporre di un **file SQLite privato e coerente** di `remura-prices.sqlite3`. Se il database live usa SQLite WAL, **non** è sicuro copiare soltanto il file `.sqlite3` mentre il processo scrive: le transazioni possono essere ancora in `-wal`. Una copia coerente si ottiene dall'API `sqlite3.Connection.backup()` o da un backup offline già creato. L'operazione di generazione del backup sul Mac/Oracle **non è stata eseguita, autorizzata o attivata in questo sviluppo**. Se il DB è soltanto su Oracle, serve un'autorizzazione separata per una sua esportazione privata sicura. Non pubblicare il DB su GitHub/ChatGPT o inviarlo via messaggio.

### Condizioni di ammissione scientifica ancora assenti

- 12 ricevute TradingView CVD TEST reali = `OBSERVATION_ONLY`, non dodici operazioni.
- Quattro coorti M15 ipotetiche e sovrapposte, non quattro segnali directional.
- La copertura prezzo dimostra **presenza temporale delle barre**, non origine autenticata del feed.
- Le metriche net 60m/4h/24h del valutatore V20.7 richiedono ancora **30 confronti ex ante** con **10 intervalli non sovrapposti**, un freezer temporale indipendente e costi osservati o ipotesi dichiarate.
- Stato prima della copia: 0 decisioni prospettiche autentiche, copertura cTrader effettiva N/D, P&L e alpha N/D.

## Verifica automatica

`research/test_v215_offline_price_readiness.py`: sei nuovi controlli con un DB sintetico locale e il solo proof V20.3 reale già salvato. Nessuna nuova acquisizione o interrogazione del broker. Il test prova solo i limiti del codice. Il percorso COT/posizionamento istituzionale resta nel **Filone B**, non viene copiato qui.

**Nota:** test/CI sono GitHub Actions già esistenti, ma il margine residuo gratuito effettivo dell'account non è verificabile dalle sole prove di codice; non presumere minuti illimitati.
