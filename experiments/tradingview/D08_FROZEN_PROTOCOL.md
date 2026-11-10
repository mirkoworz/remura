# REMURA — Filone D: protocollo D0.8 congelato (SOLO RICERCA)

**Registrato:** 10 novembre 2026 (Europe/Rome). **Ambiente:** TradingView EURUSD 5m, etichetta FXCM, `FX:EURUSD` in Pine. **Stato:** D0.8 compilata e visualizzata nello screenshot utente; confronto quantitativo D0.8 ancora senza CSV. Nessun merge, deploy, alert o ordine.

## Versione e data da NON alterare durante il campione

- Identificatore analitico: `remura_fx_price_vs_cvd_d0.8`
- File Pine congelato: `experiments/tradingview/remura_shark_cvd_fx_v08.pine`
- Blob GitHub del sorgente sperimentato: `4160994d14240ab2af5eff0c67d00c95671d7567`
- Checkpoint di repository prima di questo documento: commit `18b3033d23c3d0e7f6a333046617cdcbce13f2c7`. Se il blob Pine cambia, aprire una nuova revisione/metodologia e non mescolare i dati.
- Evidenza di prima osservazione D0.8: screenshot utente del **10/11/2026 circa 12:23 CET**, tabella con `17 PREZZO` e `4 con CVD`; questi 21 conteggi non corrispondono a 21 eventi indipendenti: il sottoinsieme 4 è incluso nei 17.
- **Inizio prospettico conservativo:** **10/11/2026 ore 12:25:00 CET**, ISO 8601 `2026-11-10T12:25:00+01:00`. È l'inizio di una finestra di *osservazione*, NON garanzia di cattura automatica dei segnali. Confermare con un export di file salvato dopo tale ora; distinguere eventuali ricostruzioni storiche da snapshot contemporanei.

## Ipotesi fissata prima del nuovo campione

Gli eventi prezzo selezionati dalla divergenza CVD (`B`) avranno un movimento medio direzionale a 1h migliore degli altri eventi prezzo non selezionati (`A\\B`), a parità di criteri di qualità e sessione. La quantità primaria riportata è **media di pip 1h(B) − media di pip 1h(A\\B)**; riportare sempre anche numerosità, mediana, frazione favorevole e finestre censurate. Ipotesi attualmente **NON DIMOSTRATA**.

**Parametri immutabili per questo pilota:** pivot 2 sinistra + 2 destra, intervallo tra pivot 3–72 barre, almeno 5 tick di nuovo estremo prezzo, warmup 12 barre 5m, differenza minima CVD 10 volumi FX, 5/5 intrabar 1m e continuità 5m confermata, stesso segmento prezzo/CVD. L'evento è noto soltanto alla **chiusura** della barra di conferma; mai al pivot storico.

**Metriche predefinite:** variazioni direzionali da close di conferma a close di 12, 48 e 288 barre successive (1h primaria, 4h/24h secondarie), censurando gap, prezzi NA o barre non chiuse. I risultati sono **movimenti di prezzo lordi**, non P&L. Niente spread/slippage inclusi finché non saranno fissati ed esposti separatamente; non selezionare retroattivamente orizzonti vincenti.

**Requisiti minimi per analisi statistica preliminare:** 20 giornate distinte *successive* al cutoff e almeno 30 eventi osservabili per coorte a 1h, inclusi 10 ST+ del braccio CVD; questi requisiti non garantiscono significatività. Segmentazione per direzione, giornata e sessione, considerare autocorrelazione e sovrapposizione delle finestre. Se manca numerosità, risultato INCONCLUDENTE e proseguire senza cambiare regole.

## Acquisizione CSV (manuale, gratuito con Premium già in uso)

1. Tenere D0.8 + CVD nativo attivi sul grafico EURUSD 5m. Esportare dal menu TradingView `Esporta dati grafico...` con tutti i plot. Non serve modificare Pine.
2. Archiviare localmente l'**originale non modificato**, con data/ora effettiva di esportazione in Europe/Rome, nome file progressivo e, se possibile, hash SHA-256; conservare una serie di snapshot nel tempo per individuare eventuali ricostruzioni/backfill. La sola riesportazione di un intervallo passato non è prova di cattura prospettica in tempo reale.
3. L'analizzatore locale `experiments/tradingview/compare_d08_baseline.py` richiede le colonne `time`, `close`, `QUALITA_5M_COMPLETA`, `CONTINUITA_PRECEDENTE_5M`, `SEGMENTO_ELIGIBILE_STUDIO`, `EVENTO_STUDIO_RIALZISTA`, `EVENTO_STUDIO_RIBASSISTA`, `BASELINE_PREZZO_RIALZISTA`, `BASELINE_PREZZO_RIBASSISTA`. Se colonne mancano, **non inventarle**: segnalare il blocco.
4. Confronto esplorativo dell'intero file: `python experiments/tradingview/compare_d08_baseline.py "FX_EURUSD, 5.csv"`. Confronto del periodo dopo il checkpoint: `python experiments/tradingview/compare_d08_baseline.py "FX_EURUSD, 5.csv" --prospective-from 2026-11-10T12:25:00+01:00`. Controllare le barre di outcome realmente osservabili e non interpretare una singola esportazione retrospettiva come prova *live*.
5. Mai pubblicare CSV grezzi del provider in GitHub. Un file condiviso direttamente in questa chat può essere analizzato offline e i soli risultati aggregati registrati nella roadmap.

## Integrità degli snapshot CSV — registro offline (10/11/2026)

Per distinguere una nuova osservazione da una semplice riesportazione dello storico è disponibile `record_d08_snapshots.py` (Python standard library). **Non modifica Pine D0.8 né la definizione statistica congelata.** Memorizza solo SHA-256, fingerprint delle righe confermate, eventi prezzo/CVD e timestamp di prima comparsa, non OHLC o volume grezzi. Il file JSON del registro è **privato e deve restare fuori dal repository GitHub**.

Il CSV D0.8 già ricevuto il 10 novembre è stato registrato come **baseline storica**, 5.490 righe (5.489 confermate), 439 candidati prezzo di cui 87 con CVD: nessuno è quindi un nuovo evento comprovato in tempo reale. SHA-256 del CSV originale `e6a4306b9e5aa4eb7d0578d6cab361caedadce168af24a5f35280c8e4ec2758f`. Il timestamp della baseline è derivato dall'**orario approssimativo del file ricevuto in chat** (circa 13:10:55 CET), NON dall'orario di esportazione certificato da TradingView.

**Esempio in locale (su un computer con Python):**

```bash
python experiments/tradingview/record_d08_snapshots.py "FX_EURUSD, 5.csv" --ledger "../REMURA-private/d08_snapshots.json" --received-at "2026-11-10T13:10:55+01:00" --baseline
# In seguito, su ogni nuovo CSV, usare il medesimo ledger senza --baseline:
python experiments/tradingview/record_d08_snapshots.py "FX_EURUSD, 5.csv" --ledger "../REMURA-private/d08_snapshots.json" --received-at "2026-11-11T13:00:00+01:00"
```

Nella chat è stato prodotto anche un file JSON **baseline privato già pronto** per confronto successivo: non occorre rigenerare il primo import se si conserva quel file. Per le esportazioni successive `--received-at` deve essere l'ora reale di ricezione annotata, non scelta retroattivamente; la protezione temporale dipende dall'attendibilità di questa annotazione.

Classificazioni:
- `duplicate_unchanged`: file già ricevuto, nessuna importazione;
- `historical_at_baseline`: evento già presente nella prima fotografia, anche se successivo al cutoff;
- `new_on_new_bar`: evento che appare per la prima volta **dopo l'ultima candela chiusa del CSV precedente**, utile per audit fra snapshot ma **non prova automatica di rilevazione live**;
- `backfill_or_recalculation`: evento comparso per la prima volta su una candela già coperta da snapshot precedente; NON conteggiarlo come novità prospettica;
- `new_on_new_bar_timely_15m`: subset osservato entro 15 minuti dalla chiusura, **indicazione debole di tempestività**, non feed live certificato.

Ogni import registra il numero di righe modificate retroattivamente (possibili revisioni/backfill), il watermark confermato e i nuovi eventi. Blocca CSV più vecchi, orari impossibili, modelli non corrispondenti e l'archiviazione del registro all'interno di GitHub. **Non esiste polling automatico TradingView:** senza nuovi export o una futura integrazione lecita l'esperimento non raccoglie eventi 24 ore su 24. Nessuna modifica ai limiti di campione predefiniti.

## Vincoli di continuità

La PR #100 rimane **DRAFT**. L'app REMURA LIVE, la versione visibile e le nove pagine, Oracle, collector, Track A/B/C e le PR #89/#99 non vanno modificati da questo studio. Nessun webhook pubblico, notifica automatica, lettura del broker o ordini: il sistema attuale **non** registra autonomamente TradingView 24/24. Non dedurre un vantaggio istituzionale dalla replica dello stesso CVD.
