# REMURA v1.60 — Piano di rilascio protetto Squalincome

**Preparazione: 03/11/2026, 11:20 Italia.** NON è la data dell'installazione.
**LIVE certificata dall'ultima diagnostica privata #31:** **v1.59** su Oracle Always Free, SHA `e924f4cf6f1a384fd84a3cef66c89a16e35de3fd`, autoupdater `up_to_date`. Dopo la diagnosi GitHub `main` ha ricevuto un commit con soli dati Myfxbook; questo non è un aggiornamento di codice VPS.

## Separazione delle modifiche

- **PR #78** `feature/squalincome-freshness-states-offline-20261103`: lettura atomica del prezzo in Squalincome e vista iPhone con stato prezzo distinto da COT/eventi, senza modificare soglie.
- **PR #79** `release/v160-squalincome-freshness-guarded-20261103`, costruita sopra PR #78 (base di PR #79 = ramo #78): file/versione/cache + installer di codice con backup SQLite, restore-test e rollback, più riconciliazione SHA. **Non fondere #79 direttamente in main senza #78**.
- **PR #77** `feature/cvd-divergence-v160-offline-20261103`: ricerca **CVD proxy** indipendente, ancora in bozza. **Esclusa dal rilascio 1.60 di freschezza** e da qualsiasi pretesa di vantaggio economico.

## Pacchetto previsto

**16 file da installare**: nove pagine HTML (`index`, `asset`, `mercati`, `forex`, `catalogo`, `statistica-squali`, `stato-prezzi`, `fonti`, `impostazioni`), `nav.js`, `sw.js`, `squalincome-diagnostics.js`, **nuovo** `squalincome-freshness-core.js`, `scripts/private_server.py`, `scripts/signals_monitor.py`, `scripts/squalincome_timing.py` già esistente.

Nove pagine condividono `nav.js?v=160`; il banner in cima è predisposto in `nav.js` come `REMURA · Aggiornamento v1.60 · 03/11/2026 11:20 (Italia, preparazione)`. **Solo nell'effettiva installazione** `release_v160.py` rimpiazza esattamente quel timestamp con l'ora italiana effettiva (prima salva l'hash/manifest di rollback). `sw.js` aggiorna la cache a `remura-shell-v74-v1.60-squalincome-freshness` e precache del nuovo JS; endpoint privati NON devono mai essere messi in cache.

Non ci sono nuove chiamate cTrader, Firebase, retail o altre API; nessuna nuova porta/servizio o provider. Non c'è modifica dello schema del database SQLite; il record JSON dell'ultima scansione include pochi metadata in più. Lo stato `waiting_verified_batch` rimane non usato dalla UI finché il collector non avrà un orario di prossimo batch veramente attestato.

## Gate prima di qualsiasi installazione

1. In GitHub lasciare #78 e #79 in bozza fino a **entrambe** le CI verdi con test vecchi e nuovi, inclusi `test_release_v160.py`, `test_reconcile_v160.py`, sicurezza PWA e verifiche degli ultimi 34 mercati. In particolare verificare che il candidate ZIP sia pinnato a Git blob/SHA, venga arrestato se si modifica `main` o trova file live diversi dal SHA v1.59.
2. Scegliere il merge sequenziale e controllato (**prima #78 in main, poi RETARGET della #79 da ramo #78 a `main`, infine merge #79 su `main`, senza includere #77**). Ricontrollare il diff dopo il retarget: nessun file CVD e nessuna modifica imprevista. Qualsiasi variazione del ramo base o dei file dopo test invalida il gate e richiede nuove CI. L'autoupdater deve trattare le modifiche script/server come **manual_required**, mai distribuirle implicitamente.
3. Dopo merge, sullo SHA esatto del `main` controllare il verde delle **due CI di evento push** (non solo PR), autoupdater non occupato, VPS `remura-private` attiva, SQLite `PRAGMA integrity_check=ok`, spazio per almeno tre copie del DB+codice e versione installata esattamente v1.59.
4. **Preflight solo lettura**: prima procurarsi sulla VPS l'installer `release_v160.py` dal **commit GitHub immutabile e verificato**, senza sincronizzare tutto il repository né lanciare script non autenticati; la v1.59 live non contiene ancora quel file. Eseguire in modo isolato `python3 <PERCORSO_INSTALLER_VERIFICATO> --check --commit <SHA_MAIN_VERIFICATO>`. Il comando **non esegue backup**, **non installa** e non cambia lo stato. Il percorso e il contenuto devono essere verificati (SHA Git blob), mantenendo la VPS sempre privata.
5. **Applicazione solo in un passaggio esplicito separato**, dopo `PREFLIGHT_V160=OK`: `python3 deploy/oracle/release_v160.py --apply --commit <STESSO_SHA>`. L'installer blocca gli aggiornamenti concorrenti, usa il modulo di backup verificato `backup_v156`, richiede `RESTORE_TEST=OK`, salva `rollback-v160-...` con SHA256 per ogni file, sostituisce solo gli approvati, crea il JS nuovo e verifica health dopo riavvio. Su failure tenta il rollback automatico; se `ROLLBACK=ATTENZIONE_CONTROLLO_MANUALE` interrompere immediatamente senza nuovi deploy.
6. Dopo controllo web/iPhone e verifiche dati, scaricare allo stesso modo **l'eseguibile di riconciliazione verificato e pin-nato** (non è uno dei 16 file applicativi), poi **preflight separato di riconciliazione**: `python3 <PERCORSO_RECONCILER_VERIFICATO> --check --target <STESSO_SHA>`. Esige che **tutti 16 i file live** coincidano col Git tree (tranne il banner con l'ora reale), sia presente il rollback verificabile, backup SQLite integro, API sana e due CI green. `--check` NON altera lo stato.
7. Solo con `RICONCILIAZIONE_V160=VERIFICATA`, eseguire `python3 <PERCORSO_RECONCILER_VERIFICATO> --apply --target <STESSO_SHA>` per aggiornare **solo** `private/autoupdate-state.json`, creando prima un backup privato; app, SQLite, credenziali, servizio e codice restano invariati.
8. Confermare tramite diagnostica privata (workflow su `remura-collector`), intestazione v1.60 con orario italiano **su tutte le nove pagine**, cache iPhone aggiornata, Squalincome scan atomic quality, 34 mercati, assenza di eventi falsi, 38 fonti prezzo, COT, timing, backup e spazio VPS.

**Rollback manuale dopo installazione**, solo se indispensabile e utilizzando il percorso realmente stampato dall'installer (non inventarlo): `python3 deploy/oracle/release_v160.py --rollback-dir <PERCORSO_ROLLBACK_DIR>`. Ripristina solo i file verificati, elimina il JS introdotto dalla v1.60 e riavvia la VPS; SQLite non viene ripristinato automaticamente. Se la riconciliazione SHA è già stata applicata, va verificata e corretta separatamente in un piano di recupero.

## Gratuità e limiti

Nessun provider acquistato, nessuna nuova richiesta al broker prevista, due workflow CI già usati in progetto. Tuttavia **gratuitezze e quote vere** di Oracle, GitHub Actions, Firestore, cTrader e traffico dati richiedono controlli provider specifici: CPU/RAM/disco della VPS da soli non certificano assenza di costi. Autorizzazione ad acquistare: **nessuna**.

**Stato:** solo preparazione del codice su PR #79, non è un rilascio live. Non eseguire comandi di installazione prima del gate completo.
