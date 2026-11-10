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

## Vincoli di continuità

La PR #100 rimane **DRAFT**. L'app REMURA LIVE, la versione visibile e le nove pagine, Oracle, collector, Track A/B/C e le PR #89/#99 non vanno modificati da questo studio. Nessun webhook pubblico, notifica automatica, lettura del broker o ordini: il sistema attuale **non** registra autonomamente TradingView 24/24. Non dedurre un vantaggio istituzionale dalla replica dello stesso CVD.
