# REMURA Filone A v21.2 — Custodia privata dei byte RAW CVD

**Versione:** A V21.2 LAB. **Aggiornamento Europe/Rome:** 23/11/26, 21:00:53.
**Ramo:** `research/remura-v211-source-derived-cvd-20261123`; **PR:** #112 Draft. Nessun merge/deploy.

## Collegamento costruttivo, non un segnale inventato

In V21.1 il freezer genera un ledger privato e un manifesto di solo hash ma il file RAW originale resta nella posizione iniziale: se viene modificato/cancellato, il successivo audit del segno LONG/SHORT/FLAT non può più ricostruire in modo verificabile i medesimi byte. V21.2 modifica il percorso `--write-private` del freezer esistente: conserva **tre file** in directory privata fuori dal checkout, modalità directory 0700 e file 0600, con esclusione di sovrascrittura e controllo SHA-256 dei byte prima della custodia:

1. `<decision_id>.original-cvd.raw.json` — byte originali esatti, senza riserializzazione;
2. `<decision_id>.private.json` — decisione congelata, prezzi baseline e nonce;
3. `<decision_id>.hash-only.json` — manifesto opaco, nessun prezzo/direzione/nonce.

I percorsi e i dati privati non vengono restituiti su stdout. Il salvataggio è **solo locale ed esplicito**, quando vi sono input reali ammessi, DB cTrader preesistente in sola lettura e `--write-private`. La custodia fa controlli preventivi su digest/schema/direzione, vieta directory pubblica o permessi aperti e non sostituisce file preesistenti. Il meccanismo di congelamento rimane fisicamente **non attivo** senza input.

## Verifica, limiti e blocchi

- Nuovi test: `research/test_v212_private_raw_custody.py` (cinque casi: conservazione byte esatti, SHA, permessi, no overwrite, rifiuto modifiche, path pubblico/symlink). Test esclusivamente sintetici, da eseguire nella CI dedicata; i 21 test V21.1 restano regressione mirata del modulo modificato.
- Questa versione **non autentica TradingView**, non dimostra il timestamp del primo arrivo del sorgente e non introduce un adattatore per un formato mai ispezionato. L'hash conserva l'integrità della copia, non certifica l'identità del mittente.
- Prezzi cTrader M15 reali del 23/11 nel DB privato: **N/D** (nessuna copia SQLite fornita al contesto GitHub). La prova di 12 ricevute TEST rimane OBSERVATION_ONLY, NON convertibile in segnali, 4 coorti M15 al massimo.
- Decisioni reali direzionali ammesse V21.2: **0**. Outcome reali calcolati: **0**. Osservazioni future 60m/4h/24h: **N/D**. Benchmark price-only con prezzi privati: **N/D**. Costi e quote broker realmente osservati: **N/D**.
- Nessuna richiesta GitHub/Cloudflare/broker attivata da questo codice. Nessun dato sensibile o file originale incluso nel repository.

**Priorità assoluta:** verificare offline i prezzi privati già presenti via `research/v204_private_cvd_price_coverage.py`, senza interrogare il broker; subito dopo confermare il payload originale autentico di un **nuovo** evento CVD (non le vecchie 12 ricevute) e predisporre la custodia temporale esterna prima degli outcome. Solo allora valutare rendimenti forward e baseline identica.
