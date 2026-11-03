# REMURA — v1.62, confronto H1 prima/dopo ingest (SOLO RICERCA)

**3 novembre 2026** · modulo di ricerca non installato, senza effetti sulla VPS.

## Problema reale e limite della v1.61

- La diagnostica privata #37 ha mostrato **12 H1 oltre 120 minuti su 34 mercati**, pur con M15 recenti, 9 batch e 45/45 acquisizioni salvate. La lettura SQLite ha certificato **otto slot distinti** da cinque acquisizioni. Durata batch mediana 17,530 s, massima 28,930 s; post-ingest 254 ms mediana.
- La **full-scan** conserva in `squalincome_last_scan` un oggetto con 34 mercati, `lastScanAt` e `timeframes.H1.lastClosedAt`. Il **post-ingest** esegue `scan_once(targets=...)` fino a cinque mercati alla volta, senza sovrascrivere la full-scan. Sono due fotografie, NON due contatori già comparabili.
- La GET `/private-api/signals/status` non espone una fotografia H1 post-ingest per tutti gli strumenti aggiornati. La diagnostica privata esistente può solo attestare tempi, contatori di esito e ordine cronologico, non il numero reale di H1 recuperate.

## Nuovo modulo, attualmente scollegato dal runtime

`scripts/h1_batch_comparison.py` espone `compare_paired_h1(full_scan, updated_frames, post_scan_utc, ingest_returned_utc)`. Riceve strutture già prodotte da `signals_monitor.safe_frame_diagnostics` e `scan_once`, **senza accedere a SQLite, rete, broker, file, token o pagine**. Compara soltanto 1–5 strumenti già raccolti, usando lo **stesso istante UTC** per vecchia e nuova ultima chiusura H1; mantiene la soglia 120m e richiede almeno 55 barre complete per H1. Non abbassa mai le soglie né produce indicatori BUY/SELL.

Risultato esclusivamente aggregato: `compared`, `fullScanH1ReadyAtSameUtc`, `postIngestH1ReadyAtSameUtc`, `staleToReady`, `freshestH1Advanced`, `unchangedH1`, età della scansione e stato. **Nessun simbolo o timestamp per mercato** nell'output. Non riporta valori OHLC, profitto o probabilità di segnale.

Il confronto è **N/D se** manca la full-scan completa di 34 mercati, anche un solo H1 è ambiguo, i batch sono fuori ordine temporale, la scansione è vecchia di oltre 30 minuti, il post-scan è più di due minuti dopo il ritorno ingest, il numero di obiettivi supera cinque, uno dei frame è incompleto o il tempo torna indietro. Un N/D non viene trasformato in uno zero.

**Importante:** una variazione `staleToReady` è un confronto tra fotografie archiviali e non dimostra automaticamente che l'ultimo batch abbia causato il recupero H1; nessun vantaggio operativo può essere dedotto dalla differenza.

## Gate e percorso per v1.62

1. Test offline e CI verdi per cambi ora UTC, soglia 120m, completezza dei dati, assenza di segreti e limite del gruppo; **nessun servizio o stato di autoupdate cambia in questo ramo**.
2. In una PR di rilascio separata, integrare il confronto **solo durante i controlli post-ingest già esistenti**, passando i frame H1 già letti da `scan_once` (evitando nuove query per singolo mercato). Salvare in SQLite un registro privato limitato di soli aggregati, con backup/rollback. **Nessuna nuova chiamata cTrader**.
3. Solo dopo nuovi test e PR revisione, aggiornare a **v1.62 la stringa in alto su tutte le pagine con data/ora italiana** e preparare installer pin SHA, preflight, backup SQLite, restore-test e riconciliazione autoupdater. Non cambiare pagine/live/servizi in questa PR di ricerca.
4. Esporre gli aggregati mediante la **stessa GET** privata e verificare che il numero di campioni confrontabili sia adeguato; mantenere `N/D` per campioni non validi. Non dare per dimostrato un aumento della copertura da un solo campione.
5. Solo se i dati LIVE confermano una differenza utile e persistente, decidere se ottimizzare il momento della full-scan o l'ordine dei gruppi a budget cTrader invariato.

**Costi:** il modulo puro non consuma risorse VPS, broker, API o Firestore. I test GitHub consumano eventuale quota Actions secondo il piano; la gratuità effettiva va verificata. RAM/disco da soli non dimostrano fatturazione zero.

**Ambiente LIVE durante questa PR:** REMURA v1.61, SHA `106e14a0b58c9e668b421a5982a9ffde22dc9243`, con telemetria batch attiva; nessun deploy automatico da questa ricerca.
