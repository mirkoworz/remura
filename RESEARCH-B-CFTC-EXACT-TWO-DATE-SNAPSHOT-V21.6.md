# REMURA Filone B V21.6 LAB — snapshot CFTC pubblico MIRATO, solo due date

**Aggiornamento B V21.6 LAB · 23/11/26, 23:57:28 Europe/Rome.**
**Ramo:** `research/filone-b-cot-intelligence-v206-20261123`. PR #108 Draft. Nessun deploy, merge, collector, Oracle, API broker, segreto, acquisto o trading.

## Sblocco reale richiesto: parità CFTC pubblico ↔ archivio privato

Il backup Oracle già verificato localmente (e non caricato sul repository) contiene, secondo Codex, **14/14 contratti per ciascuno dei report 2026-11-10 e 2026-11-17** e **14/14 timestamp first_seen per data**. I fattori 7/7 valute TFF e 28/28 cross sintetici sono stati calcolati sul Mac. **Manca la parità di valori con il dataset CFTC ufficiale.**

Il precedente audit pubblico CFTC della stessa giornata [run 45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974) aveva 980 righe sul runner ma NON ha conservato quelle righe come artifact; ne restano solo 12 risultati sintetici stampati e il digest dichiarato. Il recupero della parità richiede quindi uno snapshot pubblico completo **delle due sole date**.

Nuovo script `scripts/cot_public_two_date_archive_v216.py`: usa le definizioni CFTC TFF e Disaggregated originali di `scripts/cot_public_official_audit.py`. Se espressamente autorizzato, effettua massimo **2 richieste HTTPS GET pubbliche, sequenziali, senza retry**, con filtri esatti per 10 e 17 novembre 2026 e i 14 contratti whitelist. Valida **esattamente 28 righe**: TFF 11×2=22, Disagg 3×2=6. In caso di mancanze, duplicati, numeri invalidi, timeout o cambio schema: errore esplicito, non parità inventata.

### Default rigorosamente spento

~~~bash
python3 scripts/cot_public_two_date_archive_v216.py
~~~

Stampa solo `PUBLIC_CFTC_FETCH_NOT_AUTHORIZED`, `actualPublicGetRequests=0`, `expectedRows=28` e **nessun dato privato**. Non invoca la rete. Il codice è pronto ma **non sono state autorizzate o eseguite in questa chat le due richieste CFTC ufficiali**.

Solo con successiva autorizzazione esplicita una tantum, un operatore eseguirà in ambiente separato il comando `--confirmation ALLOW_2_PUBLIC_CFTC_GETS_NO_PRIVATE_DATA` e salverà l'output ufficiale in JSON pubblico, conservando il digest SHA-256. Non inserire nel repository alcun backup SQLite, ledger privato, first_seen o JSON privato.

Il JSON pubblico è compatibile con lo schema `remura-cot-intelligence-snapshot-v1`, con `source=official_public_cftc_socrata`, `captureClock=public_api_read_at_not_official_publication`, `readAtUtc`, `rows`, `dataSha256`. Si può così passare, offline, al validatore **già esistente** `scripts/cot_offline_parity_fx_bundle.py` con lo snapshot privato estratto da `scripts/cot_intelligence_snapshot.py`, senza ricreare altri calcoli o accedere al DB remoto.

La **parità eventuale** significherà soltanto che le cinque grandezze (OI, due long/short di Asset Manager/Leveraged Funds o Managed Money/Producer) coincidono **alla data di lettura del pubblico**: non attesta la versione originale al momento della prima acquisizione locale, il reale orario ufficiale di rilascio, la priorità informativa o un vantaggio sui prezzi futuri.

### Uso scientifico e confini

- Fonti ufficiali: [CFTC TFF Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if) (gpe5-46if) e [CFTC Disaggregated Futures Only](https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy) (72hh-3qpy).
- 7 fattori TFF = 7 future valutari distinti; 28 cross sintetici sono calcoli riutilizzando quelle sette gambe e **non** 28 osservazioni indipendenti. Per USD, 0 è baseline matematica, **non** un dato di posizione futures.
- La CFTC non fornisce ordini live, entry forecast, insider data o execution costi. `first_seen_at` resta un timestamp locale, non la prova della prima pubblicazione CFTC.
- Tests: `tests/test_cot_public_two_date_archive_v216.py` (6 casi con valori **interamente sintetici**, nessuna rete), più controllo del default no-network nella CI B. Conservare l'attuale suite e non ripetere audit reali passati.
- Costo della fase preparatoria: **0 richieste CFTC e €0 provider**. I minuti GitHub Actions consumati dai normali PR check sono diversi da chiamate CFTC e il saldo Free è N/D. La fase opt-in futura richiede 2 richieste pubbliche che non risultano avere costo API nel contesto presente, ma **non si presume una quota illimitata**.

**Dalla sola app iPhone:** il file è pronto su GitHub LAB, non serve accendere il Mac per questa fase. Il salvataggio reale dello snapshot CFTC richiederà una singola autorizzazione esplicita e una modalità d'esecuzione controllata. Nessun deploy/merge.
