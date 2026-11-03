# REMURA v1.61 — Piano di rilascio PROTETTO: telemetria batch privata

**Preparazione: 03/11/2026 13:06 Italia.** Il banner include un'ora **di preparazione**, NON l'ora di installazione. Non fornire comandi live finché tutti i gate non sono verdi.

## Stato di partenza certificato
- REMURA sulla VPS Oracle Always Free = **v1.60** SHA `47d48e1b742358c45e04e980a7c81935d496644a`, installazione con SQLite backup/restore-test, rollback e autoupdater riconciliato; ultima diagnostica privata [#33](https://github.com/mirkoworz/remura-collector/actions/runs/41628436734): 38/38 prezzi recenti, COT TFF 11/11 + Disagg 3/3, Squalincome 19/34 prezzi idonei, 15 H1 oltre 120 minuti, 0 M15/H4 stale.
- [PR #81](https://github.com/mirkoworz/remura/pull/81) = modulo batch timing e hook backend **opt-in / default OFF**, CI Price + Insights verdi. Non è stata integrata o installata.
- Questo ramo di release parte dall'HEAD della PR #81 e deve essere integrato **solo dopo** la PR #81 e dopo nuova valutazione del diff. [PR privata collector #19](https://github.com/mirkoworz/remura-collector/pull/19) resta una simulazione offline, non fa parte del rilascio.

## Pacchetto di codice da installare (13 file esatti)
1. `scripts/private_server.py` (nuova telemetria flag OFF, stesso scheduler e stesso endpoint privato).
2. **Nuovo** `scripts/batch_timing.py` (SQLite privata, max 256 batch, aggregati; nessun simbolo o token).
3. `nav.js` + `sw.js` (banner **v1.61**; service worker `remura-shell-v75-v1.61-batch-timing`, API private escluse dalla cache).
4. Nove HTML: `index, asset, mercati, forex, catalogo, statistica-squali, stato-prezzi, fonti, impostazioni`; tutti richiamano `nav.js?v=161`.

Il codice non aggiunge alcuna API broker, thread, nuovo endpoint o servizio e non autorizza ordini/notifiche. L'installazione NON deve modificare `remura.env` e NON deve attivare la flag `REMURA_BATCH_TIMING_ENABLED`: questa è un'operazione successiva e separata, con backup privato e controllo del carico. Non è ancora disponibile una misura reale di latenza batch. Il vecchio `squalincome-freshness-core.js?v=160` rimane intenzionalmente nell'HTML Mercati perché il suo contenuto non cambia; la shell PWA viene comunque invalidata.

## Script preparati, non eseguiti
- `deploy/oracle/release_v161.py`: base v1.60 pinned, 12 blob live prima del rilascio (il banner live originale porta un timestamp diverso da Git), controlli SHA/CI, preflight **`--check`** read-only, verifica SQLite e spazio, backup `backup_v156.py` con restore test isolato, rollback manifest SHA256, installazione dei soli 13 file e health; autoupdater STATE non modificato. Modulo di backup pinnato al Git blob `dc01f2b4767a5427b1d65b96f7a883870b82f608`.
- `deploy/oracle/reconcile_v161.py`: recupera l'installer verificandolo con **commit immutabile `615df979f92756207a9f0134aa7c7c5626857979` + Git blob `62ca1b7ea319e9745297998db72fc1d44ad62712`**; controlla i 13 file sul disco, ora italiana realmente timbrata, backup SQLite e rollback, CI `push/main` verdi. `--check` non muta lo stato, `--apply` salva una copia e cambia **solo** `private/autoupdate-state.json` nel lock.
- Versione+data/ora italiana effettiva timbrata nell'installer SOLO al momento dell'installazione, condivisa sulle nove pagine. Le due CI **PR** verdi non sostituiscono le due CI **push/main** da verificare al momento del deploy.

## Sequenza obbligatoria e condizioni di STOP
1. Entrambe le CI del candidato verdi (script di test protetto v1.61 e regressioni v1.60 incluse), review completa del diff; nessun file estraneo, CVD sperimentale o modifica API.
2. Integrare prima PR #81 in `main` con commit esatto, poi **retarget/review** della PR di rilascio v1.61 senza trascinare vecchi commit. Sul `main` finale richiedere le due CI **push/main** verdi. Se `main` cambia dopo la verifica, fermarsi e ricontrollare tutto.
3. **Solo preflight VPS:** scaricare il file d'installazione da un ref immutabile con Git blob verificato (NON eseguire script dalla branch mobile), `--check --commit <SHA_MAIN_FINALE>`; se non è `PREFLIGHT_V161=OK`, STOP. Nessun backup/installazione nel check.
4. **Apply separato, previo esito OK:** snapshot SQLite e restore-test obbligatori; rollback directory verificata prima della sostituzione; installazione protetta e health. Se fallisce, recuperare il rollback e non continuare.
5. Controllare su iPhone nove banner e cache PWA, diagnostica privata e compatibilità 38/38 prezzi, COT e Squalincome, assenza di segnali inventati; `collectorTiming` deve restare `disabled` prima dell'attivazione esplicita.
6. `reconcile_v161.py --check` poi **`--apply`** separati, dopo aver verificato l'installer pinned e lo SHA finale; nuovo audit privato. Non intervenire con forzature su autoupdater.
7. Preparare un'attivazione indipendente della flag con backup di `remura.env` e controllo servizi, senza nuove API, poi misurare per più giri i tempi: inizio batch → ritorno dall'ingest (limite superiore al commit per simbolo) → fine analisi post-ingest. Se gli intervalli sono inutili o creano carico, disattivare e fare rollback flag.

## Costi
Nessuna spesa autorizzata; minimo spazio SQLite max 256 righe e stesse chiamate cTrader. RAM/disco letti da VPS **non certificano** costi: Oracle Always Free, quote cTrader, GitHub Actions e Firestore restano da verificare sui provider.

**ATTUALE:** CANDIDATO GITHUB, NON LIVE. Finché mancano review, CI su SHA finale, backup/restore-test reale e collaudo, la sola versione dichiarabile LIVE è v1.60.
