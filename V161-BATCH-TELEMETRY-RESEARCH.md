# REMURA v1.61 — Telemetria reale dei batch (candidato NON LIVE)

**3 novembre 2026 — sola ricerca GitHub.** Il server Oracle resta **v1.60**, applicazione e autoupdater puntano al commit `47d48e1b742358c45e04e980a7c81935d496644a`. Nessun merge/deploy da questo ramo.

## Decisione tecnica

La diagnostica privata [#33](https://github.com/mirkoworz/remura-collector/actions/runs/41628436734) mostra **19/34 prezzi tecnicamente idonei**, **15/34 H1 oltre 120 minuti**, **0 M15/H4 fuori soglia**, con 38/38 prezzi generalmente recenti. L'esperimento [collector PR #19](https://github.com/mirkoworz/remura-collector/pull/19) mostra che spostare l'ora di lettura *può* alterare i contatori anche senza migliorare i dati. Prima di cambiare la frequenza o la fase serve una misura empirica dei tempi dei batch.

## Nuova strumentazione in questo ramo

- `scripts/batch_timing.py`: SQLite privata `remura_batch_timing`, **massimo 256 record**, uno per ciclo; contiene **solo orari aggregati, numero dei mercati pianificati/salvati, slot 1–8 e stato della scansione**. Nessun simbolo, broker ID, candela, prezzo, credenziale, ordine o URL.
- `scripts/private_server.py`: integra il record solo quando `REMURA_BATCH_TIMING_ENABLED=1`. **Default = 0**. Quando disabilitato: zero scritture, nessun nuovo thread, nessuna nuova chiamata broker.
- Il timestamp **`ingest_returned`** è misurato subito dopo che `collect_once` ha restituito il controllo successivamente all'archiviazione SQLite; **NON** è la data esatta di commit di ogni simbolo, né un attestato del futuro batch. Fattori come cTrader, subprocess, parsing, SQLite e fonti backup sono inclusi nel tempo osservato.
- Il timestamp finale dell'eventuale `post_ingest` permette di distinguere risposta del collector e fine analisi; i campioni già registrati da `squalincome_timing.py` restano invariati. Se la scansione non parte, si registra `not_run`, non un falso successo.
- `/private-api/signals/status` espone sotto `collectorTiming` **solo aggregati** (N batch, mediane, massimi, conteggio `ok/failed/not_run` e ultimo timestamp), sfruttando la stessa GET già esistente. Quando la flag è OFF mostra soltanto `state: disabled`.
- Il collector usa gli **stessi 8 batch, gli stessi 38 strumenti/2h nella configurazione standard** e le stesse politiche broker/backup. `scheduledMarkets` NON è un conteggio di HTTP/API request: fallback o ritentativi richiedono audit provider separato. Nessun costo aggiuntivo autorizzato.

## Test e vincoli

- `tests/test_batch_timing.py`: flag OFF, dati mancanti, validazioni tempo/contatori, retention 256, redazione segreti, aggregati e assenza di rete. CI `price-checks.yml` esegue i test nuovi e quelli preesistenti.
- La telemetria è **best effort**: se SQLite metrica fallisce non deve arrestare il collector né generare segnali.
- **Non attivare** la flag in VPS prima di un rilascio protetto, con SHA-pin, preflight in sola lettura, backup SQLite e restore-test, rollback, CI `push/main` verdi, banner **v1.61 con data+ora italiane su tutte le 9 pagine** e riconciliazione separata. Nessun semplice toggle Termius come surrogato dell'installer.
- La flag può essere attivata solo dopo confronto del carico e test del ciclo reale. In nessun caso pubblicare dati privati su GitHub Pages, aggiungere endpoint pubblici o aprire porte.

## Criterio di uscita

Attestare su più cicli aperti la distribuzione dei tempi tra **inizio raccolta, conclusione ingest (limite superiore), analisi post-ingest e scansioni periodiche**, abbinando i conteggi H1 alla **fase UTC**. Non attribuire ai modelli sintetici 6 minuti una durata osservata. Un risultato di maggiore copertura deve rappresentare un'**informazione realmente disponibile più presto**, non soltanto una dashboard letta più tardi.

**NOTA:** questo pacchetto è un prototipo di telemetria e non una release pronta. Le misure reali non sono ancora disponibili; nessuna promessa di redditività, latenza garantita o anticipo istituzionale.
