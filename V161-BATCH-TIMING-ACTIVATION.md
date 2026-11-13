# REMURA v1.61 — Attivazione controllata telemetria batch H1 (NON LIVE)

**03/11/2026 — ramo ricerca, nessuna modifica sulla VPS.**

## Situazione osservata
- Ultimo rilascio Oracle v1.61 installato, SHA app e autoupdater `106e14a0b58c9e668b421a5982a9ffde22dc9243`. Diagnostica privata [#34](https://github.com/mirkoworz/remura-collector/actions/runs/41649580706) del 03/11/2026 15:01 Italia: ACTIVE; 38/38 prezzi recenti; COT 11+3; Myfxbook running; 33/33 post-ingest e 33/33 periodiche riuscite, nessun nuovo evento. RAM 29,1%, disco 8%.
- Freschezza H1: **0 fuori soglia nella full-scan delle 14:48 Italia**, 15 entro 30 min dal limite 120; **19 READY / 15 STALE** nel controllo atomico svolto alle ~15:01. I due conteggi fanno riferimento a **orari diversi**. Non interpretare come bug OHLC né come guadagno di copertura garantito.

## Attivazione in due tempi, senza nuovi broker endpoint

`deploy/oracle/batch_timing_v161.py` è un **helper manuale** nel ramo ricerca: `--check` *sola lettura*, `--enable` e `--disable` (reversibili). Non è incluso nei 13 file del deploy e **non è stato eseguito sulla VPS**.

**Protezione attesa:**
- Pin rigido degli SHA/blobs già installati: `private_server.py` = `4bae49bbe6297a6970c521d0dc9d3bc1d72bbfde`, `batch_timing.py` = `68ef3244b3b4c055121b11be506b436f0551e6ac`, `installedSha`=`targetSha`=`106e14a0b58c9e668b421a5982a9ffde22dc9243`; stato autoupdater `enabled=true`, `up_to_date` e nessun failedSha.
- Verifica del collector esplicitamente abilitato, stato servizio `remura-private.service` attivo/health, `remura-autoupdate.service` non in esecuzione; flag di processo uguale al file, `remura.env` non symlink e permessi privati, lock condiviso con aggiornamenti.
- `--enable`: backup privato 0600 di `remura.env`, cambia **solo** `REMURA_BATCH_TIMING_ENABLED=1`, restart controllato del servizio, verifica variabile del nuovo processo/health; se fallisce ripristino env e riavvio, senza toccare SHA/database/segnali.
- `--disable`: può tornare a 0 con recupero verificato anche in presenza dello stato `manual_required` futuro, purché il codice LIVE sia ancora quello con blob pinnato.
- Il restart è un evento operativo con **possibile giro extra di raccolta nell'immediato**, se cade in mezzo al normale ciclo. Non sostiene che il numero di chiamate API sia matematicamente identico al minuto del riavvio; il ciclo standard rimane invariato dopo.
- I record SQLite vengono scritti in privato quando la flag è attiva: massimo 256 batch, con soli timestamp/slot/contatori aggregati. Non esporre mai `remura.env`, IP, token o simboli nei log.

**Gate:** CI della PR deve essere verde e review completa. Solo successivamente proporre **prima `--check`** con download da commit immutabile e blob SHA; esaminare output senza stampare segreti. L'abilitazione effettiva `--enable` deve essere un comando **separato**, dopo il controllo OK e consenso operativo. Non fondere questa PR su main durante il periodo di misure se ciò rischia di spostare l'autoupdater dallo SHA installato.

Dopo attivazione, far crescere il campione per più batch aperti; rilevare mediamente tempo inizio→ritorno ingest e tempo ingest→fine post-ingest, errori e andamento H1 senza alterare soglie M15/H1/H4 o notifiche. Verificare anche quote Oracle, cTrader, GitHub Actions e Firebase sui rispettivi provider; RAM e disco non certificano billing.
