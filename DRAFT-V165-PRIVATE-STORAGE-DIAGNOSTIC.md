# REMURA — candidato v1.65: diagnostica privata dello spazio SQLite (DRAFT, NON LIVE)

Preparazione del 8 novembre 2026 (Italia). **Nessuna versione LIVE modificata**.
Branch isolato da Track B #89 e C #97. La versione LIVE resta v1.64 finché
non viene autorizzato un rilascio completo, compreso l'aggiornamento del numero
di versione e della data/ora visibili in cima a ogni pagina.

## Cambiamenti preparati

- Nuovo `scripts/storage_inventory_v165.py`: rilevazione **sola lettura dei
  metadati** di `/opt/remura/private/remura-prices.sqlite3`, possibili WAL/SHM,
  spazio/inode disponibili e copie locali sotto `predeploy-backups`. Limiti a
  directory e file; rifiuto di link, contenuti non previsti e inventari parziali.
  **Scansione LIVE con directory descriptor ancorati da `/` con `O_DIRECTORY|O_NOFOLLOW`,**
  `stat(..., dir_fd=..., follow_symlinks=False)` e `fstatvfs`: il codice apre
  solo directory, non apre SQLite/WAL/SHM o backup e non legge contenuti.
  Protezione contro redirect tramite symlink e sostituzioni di directory;
  non costituisce snapshot atomico né prova di inode LIVE attuale.
- Nuovo `scripts/storage_cache_v165.py`: cache in memoria; campionamento solo
  in **thread separato**, una volta ogni 15 minuti se e SOLO se la variabile
  `REMURA_STORAGE_DIAG_ENABLED=1` viene impostata esplicitamente.
  Le GET leggono soltanto la cache, non eseguono `stat` o `scandir`; cache
  scaduta oltre 20 minuti diventa `UNKNOWN` senza riutilizzare le misure.
- `scripts/private_server.py`: stessa rotta `GET /private-api/resources`
  senza cambiamenti quando il flag è OFF (default). Con flag ON compare
  esclusivamente `storageInventory` con metadati precomputati.
  Nessun endpoint nuovo, nessuna chiamata al broker, provider, SSH o OCI.
- Test offline con SQLite *non necessario*: file sintetici temporanei e HTTP
  loopback; incluse incompatibilità backup e rollback, symlink, cache stantia,
  default-off, dati privati nascosti e assenza di sampler nel GET.

## Audit offline C4b(k) — 08/11/2026

**Evidenza verificata dal codice su GitHub, non dalla VPS:**
- Applicazione in `private_server.py`: bind di default e costante a `127.0.0.1`, nessuna nuova rotta; la GET `/private-api/resources` aggiunge `storageInventory` soltanto con flag esattamente `1`, e usa `no-store`. Nessun controllo di identità applicativo autonomo sull'endpoint: **non basta** il bind locale a certificare protezione end-to-end.
- Diagnostica nel repository privato `remura-collector`, workflow `remura-vps-diagnostic.yml` letto senza cambiarlo: job remoto condizionato da repo privato, branch `main`, gate di configurazione; Tailscale GitHub Action con identità effimera `tag:remura-ci-read`; client accetta HTTPS su MagicDNS `.ts.net`, senza redirect e con timeout. L'ACL tailnet, l'accesso effettivo dell'origine, la configurazione del reverse proxy e le policy di autorizzazione **non sono verificati operativamente**.
- Scanner FD-pinned contro la sostituzione dei percorsi, con test anche su directory rinominata durante la lettura; file SQLite e sidecar mai aperti dalla diagnostica. Una directory ormai scollegata dal percorso corrente può ancora restituire metadati storici: misure non atomiche e possibile `UNKNOWN` per errori o permessi.
- La scansione è fuori dal thread HTTP; se una syscall del filesystem resta bloccata, il worker può tardare, ma la cache scade a 1200 s e passa a `UNKNOWN`. Nessun hard timeout sicuro applicabile a una syscall bloccata dentro il thread: escludere ogni promessa di latenza LIVE massima.
- `scripts/storage_cache_v165.py` valida a campi strettamente permessi risposta/inventario ed elimina qualsiasi field aggiuntivo potenzialmente sensibile. Nessun valore `true` per proof off-host, billing o abilitazione C5.

**Prove automatiche:** `tests/test_storage_v165_draft.py` **42/42 PASS** (30 preesistenti + 5 protezione cache + 7 directory fd); [Price Engine #42492857462](https://github.com/mirkoworz/remura/actions/runs/42492857462) e [Insights #42492857472](https://github.com/mirkoworz/remura/actions/runs/42492857472) **SUCCESS** sul commit `8c4901cd76e09ddef5b1f24e6092fa50da176fa6`. Test eseguiti solo su GitHub runner con file fittizi.

**Gate non soddisfatti / NO-GO prima di qualunque installazione:**
1. Approvazione dedicata e separata del rilascio v1.65; la PR #98 resta DRAFT, non mergiare da questa conversazione.
2. Dimostrare da ambiente autorizzato origin/ingress `127.0.0.1`, configurazione reverse proxy, Tailscale ACL e tag `tag:remura-ci-read`, nessuna raggiungibilità anonima/pubblica della diagnostica. Conservare l'evidenza nel repository **privato** senza URL/token sensibili.
3. Accertare nel processo effettivo percorso del DB, permessi directory e disponibilità delle syscall FD su Linux; prova di carico non intrusiva e timeout/fail-closed. Nessun `chmod`, restart o toggling flag durante la revisione.
4. Backup coerente SQLite via API di backup, verifica `integrity_check` in copia isolata, restore-test e rollback dello stack v1.64, con inventario versione/autoupdater pinned. **Non eseguire qui**: tocca la VPS e richiede consenso.
5. Verifica concreta in console Oracle di fatturazione/Always Free post-trial, quote GitHub/Firestore e storage effettivamente gratis. Budget e alert NON bloccano la fatturazione.
6. Preparazione separata della release atomica v1.65: banner **versione + data/ora Italia in alto su tutte le nove pagine**, service worker/cache coerenti, preflight SHA/manifest, file allowlist, piano di rollback, monitoraggio post-deploy. Non anticipare il timestamp LIVE.
7. Solo dopo i gate e autorizzazione, attivare la diagnostica e osservare le dimensioni REALI tramite l'endpoint privato esistente. `C4b(l)` e raccolta prospettica `C5` restano NO-GO finché non esistono evidenze indipendenti.

## C4b(k) — anteprima pacchetto release v1.65 offline (08/11/2026)

L'anteprima è **eseguibile solo come controllo su checkout GitHub**, non installa nulla e NON include opzioni `--apply`, `--deploy`, backup, restore, rollback o reconcile. Una nuova release completa deve ancora essere progettata e verificata separatamente.

- `deploy/oracle/v165_release_offline_preview.py` blocca la vista alla baseline `main` `5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74` e agli esatti SHA Git blob di **14 file allowlisted**: 9 pagine HTML, `nav.js`, `sw.js` e 3 moduli backend. Qualsiasi file inatteso o contenuto cambiato causa STOP. Questo SHA di `main` NON attesta lo SHA installato sulla VPS.
- Simulazione **interamente in memoria**: in ogni pagina `nav.js?v=164` viene previsto come `nav.js?v=165`; il banner comune nella barra alta passa a `v1.65` con un **segnaposto esplicitamente non LIVE**. I test generano timestamp simulati Europe/Rome in inverno ed estate. La data/ora vera va timbrata **solo al momento dell'installazione autorizzata**; i file attualmente pubblicati e la LIVE v1.64 sono invariati.
- Il service worker è simulato con cache distinta `remura-shell-v79-v1.65-storage-diagnostic`; resta esclusa dalla cache la rotta privata. I file SQLite e di configurazione non vengono letti, scritti o caricati.
- Ispezione `ast` della **struttura**, senza esecuzione, di `release_v164.py`, `reconcile_v164.py` e `backup_v156.py`. Questo NON dimostra che il backup e rollback v1.64 funzionino oggi, né crea un installer v1.65. Lo script restituisce sempre `NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION`, con dieci gate LIVE esplicitamente pendenti.
- `tests/test_v165_release_offline_preview.py`: **18/18 PASS** sui pin SHA, tutte le pagine, segnaposto, fuso orario, payload modificati, protezione SW, sorgenti non autorizzate, assenza di scritture/rete/SQLite e necessità dei gate. CI [Price Engine #42494182930](https://github.com/mirkoworz/remura/actions/runs/42494182930) e [Insights #42494182866](https://github.com/mirkoworz/remura/actions/runs/42494182866) **SUCCESS**, commit verificato `78b566cb6f4e718ac200f04329600dbd989ddf8f`. Il primo run della nuova suite aveva un errore di sintassi nel test Unicode e il secondo una condizione troppo restrittiva sull'import di `NO_GO`: entrambi corretti e rieseguiti, risultato finale verde.
- **Resta obbligatorio** prima del rilascio reale: installer v1.65 con allowlist atomica e SHA LIVE attestato indipendentemente, backup coerente SQLite, restore-test indipendente, rollback verificato, compatibilità autoupdater, effettivi permessi e policy Tailscale, verifica costi e quote, aggiornamento reale del banner su tutte le 9 pagine, esplicita autorizzazione. Non ricavare alcun GO da questa anteprima.

**Controllo offline in CI:** `python -m unittest discover -s tests -p 'test_v165_release_offline_preview.py' -v`. Nessun input di autenticazione o chiave richiesto.

## C4b(k) — laboratorio transazione release, SQLite WAL e rollback sintetico (08/11/2026)

**Cosa è stato realmente eseguito:** nuovo `deploy/oracle/v165_release_transaction_lab.py`, con CLI **soltanto** `--simulate-offline`. Genera in directory temporanee su **uno stesso runner** un DB inventato EURUSD/XAUUSD e righe di stato, abilita WAL e lascia la connessione sorgente aperta durante il backup coerente `sqlite3.Connection.backup()`. Ricostruisce una copia con un secondo `backup()`, controlla `PRAGMA integrity_check` e i record attesi. Verifica il digest SHA256 della copia prima del restore, rifiuta alterazioni/symlink/assenza/corruzione. Non usa `shutil.copy` per copiare a caldo il DB WAL.

**Rollback codice simulato:** manifest di **14 nomi fissi** (9 HTML, nav.js, sw.js, 3 backend) con contenuti inventati; modifica solo queste copie fittizie in memoria e ne verifica il ripristino completo dopo il tentativo. Sono provati guasti in sei punti: dopo backup, snapshot corrotto, dopo staging, sostituzione parziale, sostituzione completa e finta riconciliazione. Lo stato autoupdater è un marcatore **fittizio in memoria** e non viene mai modificato. La directory temporanea e le prove sono eliminate automaticamente.

**Evidenza CI:** `tests/test_v165_release_transaction_lab.py` **18/18 PASS** su [Price Engine #42495151783](https://github.com/mirkoworz/remura/actions/runs/42495151783), [Insights #42495151777](https://github.com/mirkoworz/remura/actions/runs/42495151777) **SUCCESS**, codice finale commit `a5290300d2d61b36ab0f5f0bbee10c9c49d496c0`. Un primo run ha rilevato un tipo invalido trattato con eccezione prima dell'allowlist; ora gli input sono validati prima di costruire i file di prova. Le suite già esistenti sul medesimo workflow, inclusi i 42 test scanner e i 18 test della preview, sono verdi.

**Cosa NON significa:** NON esiste ancora un installer v1.65 di produzione; nessuna misura, backup, restore, file, servizio, impostazione, autoupdater o configurazione LIVE è stata toccata; nessuna prova di copia fuori macchina, cifratura, continuità dei provider o quote OCI. Il test del rollback è **solo su file fittizi**, non un recupero della VPS. Lo script restituisce sempre `NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION` e non offre `--apply` o argomenti di percorso LIVE.

**Prossimo gate:** progettare separatamente l'installer/reconciler LIVE di v1.65 con preflight pinned e verifiche operative reali (percorso e SHA VPS, servizi, backup coerente con restore-test, permessi, rollback, quote e banner), ma SENZA invocarlo prima di una specifica autorizzazione.

## C4b(k) — protocollo progettuale per installer v1.65, fail-closed (08/11/2026)

Nuovo modulo `deploy/oracle/v165_release_protocol_draft.py`, **solo `--plan-offline`**, commit `3575d4d0aa8db9dff928f3002279d44658abb44a`. Aggiunto `tests/test_v165_release_protocol_draft.py` con **17/17 PASS** e nuova verifica nella CI `price-checks.yml` (commit `d03341b7cb038731fba0bb2e0d6f7687b865a491`): [Price Engine #42495793193](https://github.com/mirkoworz/remura/actions/runs/42495793193) e [Insights #42495793214](https://github.com/mirkoworz/remura/actions/runs/42495793214), entrambe SUCCESS. Tutti i controlli v1.65 precedenti sono ancora verdi in Price Engine.

**Contratto vincolante proposto per il futuro installer (NON ancora realizzato):**
1. File manifest esatto 12 preesistenti (nove HTML, `nav.js`, `sw.js`, `scripts/private_server.py`) e due nuovi (`scripts/storage_inventory_v165.py`, `scripts/storage_cache_v165.py`). Non servire file di configurazione, SQLite, chiavi, cartelle private o branch di ricerca.
2. Non assumere che `main` GitHub `5ec7d73` sia lo SHA realmente installato su Oracle: l'identità LIVE va attestata separatamente con manifest e timestamp banner.
3. Rispettare sequenza: consenso separato, billing e ACL; pin del target con CI push/main; preflight disco+SQLite; snapshot coerente e restore-test; backup rollback codice sigillato; lock autoupdater e stop servizio; installazione dei 12 esistenti + 2 moduli nuovi; verifica hashes, health e banner su nove pagine; riconciliazione updater **solo in un passaggio separato**; conferma continuità della raccolta e costi.
4. Se uno step fallisce: non avanzare; il modello consente esclusivamente rollback **sintetico**, non attesta recovery della VPS. Il modello `advance_synthetic` rifiuta tutte le prove non marcate `synthetic`, i passaggi fuori ordine e gli stati terminali.
5. Dimensionamento disco: con misure sconosciute restituisce `UNKNOWN`; con input interi sintetici fornisce soltanto un **reserve estimate** prudenziale (4× DB+WAL+SHM, 3× codice e margine 512 MiB). Non misura capacità, inode o quota reali e non autorizza un deploy.

**Limitazione tecnica fondamentale:** `v165_release_protocol_draft.py` non contiene `--apply`, funzione di installazione o di rollback reale, non apre file SQLite, non usa rete, `systemctl`, Oracle o autoupdater, e restituisce sempre `NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION`. È un **contratto di progettazione testato**, non l'installer pronto da lanciare. L'attestazione attuale dello SHA installato e i gate operativi/Always Free non sono disponibili da questi test.

## Limitazioni e barriere NON superate

- Questo ramo **NON è la release 1.65** e NON è un'autorizzazione a installare o
  attivare la funzione. Nessuna misura reale della VPS è stata raccolta.
- La presenza di backup locale e il numero di byte NON dimostrano che il backup
  si possa ripristinare da un altro host o che esista fuori Oracle.
- Lo scanner presuppone un percorso preciso: se il database LIVE è diverso,
  restituisce `UNKNOWN` e non scandisce altrove.
- Operazione futura subordinata ad autorizzazione esplicita, revisione security
  (compresi permessi, symlink race, timeout in filesystem), test di carico,
  quota/costi Oracle post-trial, backup coerente realmente verificato e
  **ripristino off-host** controllato, version banner completo, release SHA,
  autoupdater/rollback e verifica isolata. Non mergiare questa PR prima di tutto.
- I test GitHub Action consumano normali minuti CI, non attivano nuove
  risorse OCI/Firestore/Myfxbook/cTrader. Nessun dato reale o segreto in commit,
  file diff o artifact.
- `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION` rimane: la ricerca prospettica
  Track C/C5 non parte per effetto della diagnostica, neppure se verde.

## Percorso operativo dopo approvazione

1. Verificare percorsi/permessi e metriche reali in un contesto di controllo
   con limiti; autenticazione e accesso solo dal privato già esistente.
2. Confermare che lo scanner non impatti la raccolta e che `storageInventory`
   contenga solo contatori sanitizzati e abbia stato `UNKNOWN` se cache scaduta.
3. Verificare costi/quota, backup/restore test, rollback; **niente bypass**.
4. Preparare un separato rilascio atomico con banner v1.65 e data/ora in alto
   su **tutte** le pagine coinvolte; non aggiornare solo il numero interno.
5. Autorizzazione al rilascio e successiva osservazione, senza attivare C5.


## C4b(k) — preflight pinned con metadati CI sintetici (08/11/2026)

Aggiunto `deploy/oracle/v165_pinned_preflight_lab.py` e relativo test offline. Questo è un **componente di laboratorio**, non una libreria di autorizzazione LIVE: verifica la forma stretta di un **fixture CI fittizio** (due workflow differenti, push su main, HEAD identico e success), confronta i 14 Git blob preparatori al commit bloccato `3819fe1450980c046533e400d283b25f37a67bd3`, poi costruisce soltanto in memoria un manifest SHA256 dei 12 file esistenti e 2 moduli nuovi. Reimpiega la preview validata per nove riferimenti nav.js v165, banner comune e cache PWA; la data Europe/Rome è **simulata**, non l'ora di un rilascio. Test negativi: target alterato, main moved, workflow duplicato, CI pull_request/dispatch/rossa, tree modificato, file extra, timestamp senza zona e DST.

**Limitazioni:** due CI finte verdi non equivalgono a run reali! Non consulta GitHub, Tailscale, OCI o la VPS; non genera backup o restore SQLite; non attesta il LIVE v1.64 né gli hash precedenti per rollback; non conserva manifest in produzione. La CLI ammette solo `--check-fixture-offline`; `actualPushMainCiVerified=false`, `installedLiveV164Attested=false` e `NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION` sono obbligatori anche con tutti i test verdi. Per l'installer futuro servono lettura remota autenticata e doppio controllo HEAD sotto lock, prova LIVE separata, rollback persistente e verificato, restore e consenso operativo.

**CI verificata:** commit `7f85a2a9d301fed3cc6450ee4975457bce31f333`, `tests/test_v165_pinned_preflight_lab.py` **19/19 PASS**, [Price Engine #42496881081](https://github.com/mirkoworz/remura/actions/runs/42496881081) **SUCCESS** (incluso il nuovo step e tutti i test v1.65 precedenti), [Insights #42496881083](https://github.com/mirkoworz/remura/actions/runs/42496881083) **SUCCESS**. Totale storico dei cinque moduli di test v1.65: **42+18+18+17+19 = 114 test offline**; la loro riuscita NON è prova di CI push/main per un futuro commit LIVE, backup off-host o autorizzazione.

## C4b(k) — laboratorio rollback persistente su filesystem sintetico (08/11/2026)

Nuovo modulo **isolato** `deploy/oracle/v165_rollback_bundle_lab.py`, con CLI soltanto `--rehearse-fixture-offline`. All'interno di una `TemporaryDirectory` privata, crea **12 file originali inventati v1.64** e **14 file candidati inventati v1.65** (12 sostituiti + 2 nuovi). Salva copie dei 12 originali e `manifest.json` con SHA256 per-file, serializzazione deterministica, modalità `0600` per i file e `fsync` su file/directory nel runner Linux; un SHA256 del manifest è conservato separatamente **solo nella memoria dello stesso test**. Il bundle dura per l'intera transazione e viene eliminato uscendo dal laboratorio. Non è un backup off-host e il digest non è una firma, né prova contro un attaccante che possa modificare sia manifest sia digest.

Prima di ripristinare, la prova verifica **l'intero** set di backup e i byte delle copie originali, i tipi di file, gli hash previsti e lo stato dei file di destinazione; rifiuta symlink, contenuti alterati, file extra, modifiche non attese, snapshot/manifest manomessi e percorsi non in allowlist. Il rollback sintetico ripristina i 12 file e rimuove i due moduli nuovi; il fault injection verifica stop prima dell'installazione, installazione parziale, installazione completa e interruzione a metà del rollback con successiva ripetizione idempotente. In presenza di corruzione non dichiara recupero riuscito. L'algoritmo di laboratorio **non offre alcun percorso configurabile** e non può installare/restartare servizi o toccare la VPS; nessuna lettura SQLite, nessun aggiornamento dell'autoupdater e nessuna nuova API provider.

**CI verificata:** [commit `90cabea`](https://github.com/mirkoworz/remura/commit/90cabea995cc21c336e86dac33cb596299f5b047), `tests/test_v165_rollback_bundle_lab.py` **22/22 PASS**, [Price Engine #42497495687](https://github.com/mirkoworz/remura/actions/runs/42497495687) **SUCCESS**, [Insights #42497495685](https://github.com/mirkoworz/remura/actions/runs/42497495685) **SUCCESS**. Le cinque suite preesistenti restano verdi nel medesimo Price Engine: **42+18+18+17+19+22 = 136 test offline** nelle sei suite v1.65.

**NO-GO invariato:** questo test non attesta un rollback di `/opt/remura`, backup/restore SQLite off-host, provenienza SHA v1.64 LIVE, chiusura del lock autoupdater, servizi, ingress/ACL, fatturazione post-trial, timestamp reale della barra superiore o autorizzazione. Anche se il laboratorio simula un recupero, un futuro installer dovrà avere evidenze indipendenti, gestione delle eccezioni e dei confini filesystem/permessi/TOCTOU, una copia rollback LIVE verificabile su disco adeguato, gestione sicura delle transazioni parziali e riconciliazione updater separata. **Non promuovere il modulo a installer operativo.**

**Prossimo passo sicuro:** laboratorio separato per baseline v1.64 e transizione autoupdater esclusivamente con fixture, prove che un rollback non implichi riconciliazione e che `main`/CI siano revalidati sotto lock soltanto nel futuro percorso autorizzato. Poi gate C4b(l) veri con consenso; nessuna attivazione C5.

## C4b(k) — laboratorio autoupdater e rollback inverso sintetici (08/11/2026)

**Modello separato, mai operativo:** `deploy/oracle/v165_autoupdater_state_lab.py` con CLI **solo** `--rehearse-state-offline`, insieme a `tests/test_v165_autoupdater_state_lab.py`. È costruito attorno alle interfacce già esaminate di `release_v164.py`, `reconcile_v164.py`, `v165_release_protocol_draft.py`, `v165_pinned_preflight_lab.py` e `v165_rollback_bundle_lab.py`, senza eseguire i moduli di rilascio reale. Il programma crea una directory temporanea privata su GitHub runner contenente 12 file **fittizi v1.64**, poi installa 12+2 file **fittizi v1.65**, un `mock-updater-state.json` e un lock di prova. Non legge né accede a `/opt/remura`, non apre SQLite reale, non chiama GitHub/Tailscale, non esegue `systemctl` o modifica servizi/autoupdater.

**Gate simulati e invarianti:** il manifest di codice viene verificato indipendentemente dal campo `installedSha` dello stato; un aggiornamento del codice **non** riconcilia lo stato automaticamente. Una fase separata di riconciliazione è ammessa nel laboratorio esclusivamente quando i 14 file inventati coincidono byte-per-byte con il candidato, il bundle temporaneo di rollback è valido, il lock della fixture è dichiarato acquisito, l'updater e la salute sintetici sono OK, lo stato baseline fittizio è immutato, e il *secondo* HEAD `main` simulato coincide con target e due CI finte `push/main` verdi. Il check non prova alcun lock LIVE né CI push/main reale: `OLD_FAKE_SHA = a×40` e `TARGET_FAKE_SHA = 1×40` sono volutamente inventati e distinti dal main GitHub reale.

**Esiti dei fault injection:** stop dopo installazione lascia la riconciliazione pending; rollback **prima** di riconciliazione conserva lo stato iniziale; rollback **dopo** la riconciliazione crea una discrepanza marcata `FAKE_INVERSE_RECONCILE_REQUIRED_NO_AUTO_FIX` e **non** riscrive lo stato in modo silenzioso. Cambiamento HEAD, CI `pull_request`, updater occupato, lock mancante, health/backup mock mancanti, file candidati modificati, `failedSha` non vuoto, file di stato assente/symlink, schema diverso o modalità non-offline bloccano la transizione. Non vengono conservati byte reali né attestazioni private nel repository; tutti i file sono eliminati con `TemporaryDirectory`.

**CI verificata:** commit [`c843d3b`](https://github.com/mirkoworz/remura/commit/c843d3b26a244aa992cf49b7f9a6824124f15831), **25/25 nuovi test PASS**, [Price Engine #42497976299](https://github.com/mirkoworz/remura/actions/runs/42497976299) **SUCCESS** (incluse tutte le suite v1.65 precedenti), [Insights #42497976315](https://github.com/mirkoworz/remura/actions/runs/42497976315) **SUCCESS**. Sette suite v1.65: **42+18+18+17+19+22+25 = 161 test OFFLINE**.

**Limitazione rigorosa / NO-GO:** la riuscita di un rehearsal NON equivale all'attestazione dello SHA realmente installato in LIVE, al controllo di una reale chiave di lock autoupdater, alla continuità del collector, alla salute di servizio né alla correttezza di un eventuale rollback inverso. Nessun `--apply` disponibile. Il reale inverso di riconciliazione andrà progettato e autorizzato separatamente, con manifest di rollback sigillato e verificato, prova del ripristino database, gate C4b(l) su risorse e costi/ACL e singolo coordinamento deploy. Il codice applicativo LIVE resta v1.64, senza attivare `REMURA_STORAGE_DIAG_ENABLED` e senza dare GO a C5.

**Prossima preparazione sicura:** modellare un runbook di fault recovery manuale e un pacchetto di evidenze **da raccogliere in ambiente reale solo previa autorizzazione**: classificazione stato installed/staged/rollback e quale singolo operatore può intervenire sulla VPS. Prima di ogni nuova modifica rileggere HEAD branch e PR; nessun merge o installazione fino a nuova autorizzazione dedicata.

## C4b(k) — albero decisionale di incident recovery (OFFLINE, 08/11/2026)

**Nuovo laboratorio a sola classificazione, non esecutore di recupero:** `deploy/oracle/v165_incident_decision_lab.py` con CLI esclusivamente `--decision-fixtures-offline`. 15 profili predefiniti di eventi **inventati**, con campi strict `mode/phase/code/updater/rollbackBundle/sqliteRestore/health/lock`. Ogni elemento esige una testimonianza *synthetic* e nessuna evidenza dell'ambiente reale è letta o accettata dalla CLI. Il modulo non importa client di rete, filesystem, processi o database, non accetta path/JSON esterni, non genera un installer, non avvia alcun rollback né modifica updater. La funzione pure `decide` produce un **gate di revisione umana**, mai un comando da eseguire.

**Piano di gestione guasti:** baseline v1.64, staging, sostituzione parziale, 14 file candidati presenti ma updater ancora v1.64, riconciliazione solo sintetica, ripristino in corso, ripristino v1.64 prima di riconciliare, ripristino dopo aver riconciliato (inverso separato necessario), backup corrotto, restore SQLite fallito, lock occupato, health fallita, prove sconosciute, updater sporco e combinazioni contraddittorie. Le condizioni di corruzione/restore/lock/health prevalgono e causano HALT. `UNKNOWN` non è mai zero o un esito verde. Anche un codice apparentemente corretto, con riconciliazione fittizia completa, **non** produce GO: `automaticRollbackPermitted=false`, `automaticReconciliationPermitted=false`, `operatorAuthorized=false`, `operationalDecision=NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION`.

**Evidenze future obbligatorie, non raccolte in questa chat:** SHA effettivo LIVE e hash dei file installati; manifest rollback realmente sigillato; backup coerente SQLite/WAL con restore-test, *più* prova di recupero off-host; lock esclusivo reale e continuità collector; ingress 127.0.0.1, ACL Tailscale e reverse proxy; stato billing Oracle post-trial, quota/disco/inode effettivi; SHA target `main` e due vere CI push/main verdi; health, versione e timestamp Italia reali su tutte le 9 pagine, cache PWA; piano di riconciliazione inversa indipendente; autorizzazione separata di un unico operatore. Queste prove devono essere raccolte in sede di gate operativo privato e **mai** inserite come credenziali, raw SQLite o dati sensibili su GitHub pubblico.

**Prova verificata:** commit [`121a07a`](https://github.com/mirkoworz/remura/commit/121a07aa7e9a45445ced16141146b625c67b54e4), test `tests/test_v165_incident_decision_lab.py` **31/31 PASS** (inclusa matrice completa fittizia phase×code×updater e mapping dal laboratorio autoupdater precedente), [Price Engine #42498454145](https://github.com/mirkoworz/remura/actions/runs/42498454145) **SUCCESS**, [Insights #42498454265](https://github.com/mirkoworz/remura/actions/runs/42498454265) **SUCCESS**. Otto suite v1.65, totale **42+18+18+17+19+22+25+31 = 192 test OFFLINE**. Nessun workflow nuovo né ulteriore chiamata provider; GitHub Actions normali, gratuità reale non attestata.

**NO-GO invariato:** niente merge, rilascio LIVE, servizi, flag diagnostica o raccolta C5. Lo stato reale VPS non è stato osservato; la v1.64 LIVE resta soltanto l'ultima versione **documentata**. C4b(l) non può essere dichiarato verde da CI. Prossima fase in sicurezza: rivedere la copertura di errore incrociata e progettare un **pacchetto di evidenze di preflight privato, sola lettura**, senza contattare Oracle né attivare scanner, e definire autorizzazione separata prima di qualsiasi misurazione/backup reali.

## C4b(k) — specifica evidence packet privato, solo OFFLINE (08/11/2026)

Il nuovo `deploy/oracle/v165_preflight_evidence_lab.py` modella un **piano delle future prove**, non un collettore attivo. CLI unica `--plan-evidence-offline`, senza percorsi, token, JSON esterni, contatti VPS, servizi, filesystem, SQLite, provider o scritture. La tabella di **12 gate esatti** è vincolata a `v165_incident_decision_lab.REQUIRED_LIVE_EVIDENCE`; ogni gate specifica una classe di raccolta, custodia solo privata e controllo umano. Ricevute sintetiche in input consentite esclusivamente con 2 valori `ABSENT`/`SYNTHETIC_RECEIPT_ONLY` e campo `gateId` in ordine identico. Qualsiasi `REAL_VERIFIED`, attributo extra (per esempio chiave, URL, misura, timestamp, percorso), ID sconosciuto/duplicato, evidenza fuori ordine o schema diverso viene rifiutato con STOP. Anche con 12 ricevute finte, `missingRealEvidenceCount=12`, `actualRealEvidenceState=NOT_ATTESTED`, `releaseAuthorized=false`, `operationalDecision=NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION`.

**Separazione delle attività:** SHA LIVE, controllo file e ingress/ACL richiedono futuri accertamenti tecnici read-only con consenso dedicato; backup coerente SQLite, restore-test, recupero off-host, lock/rollback e riconciliazione inversa sono **azioni future controllate con scritture**, mai descritte come sola lettura; billing/Always Free richiede verifica in console privata; health, banner reale su nove pagine e cache PWA richiedono riscontri **solo dopo una release separatamente approvata**; consenso di rilascio è un gate distinto. Il report nel repository pubblico contiene esclusivamente lo schema e **nessuna prova**, hash LIVE, dato personale, segreto, token, database o indirizzo. Custodia futura proposta in contesto privato sotto revisione del singolo operatore; nessun trasferimento configurato.

**Risultati:** commit [`b639784`](https://github.com/mirkoworz/remura/commit/b63978404dfcb869fbf8ef4a06fcf78ac56048f2), `tests/test_v165_preflight_evidence_lab.py` **30/30 PASS**, [Price Engine #42498958037](https://github.com/mirkoworz/remura/actions/runs/42498958037) e [Insights #42498958132](https://github.com/mirkoworz/remura/actions/runs/42498958132) entrambe **SUCCESS**. Nove suite: **42+18+18+17+19+22+25+31+30=222 test offline**, tutte verdi nel workflow Price Engine. Nessun nuovo workflow cron/servizio/provider. Non certifica consumo o quote realmente gratuiti; impiega soltanto runner standard CI.

**Gate bloccati:** C4b(k) preparazione, C4b(l) misure operative e C5 raccolta prospettica restano **NO-GO**. SHA installato Oracle v1.64, billing post-trial, ACL, dimensione/inode, backup/restore off-host e autoupdater LIVE **non attestati**. Non mergiare PR #89/#97/#98, non fare deploy, non abilitare il flag storage; la versione LIVE resta v1.64 documentata, non osservata dalla VPS in questa operazione.

**Prossima fase sicura:** audit trasversale dei 12 gate per eliminare sovrapposizioni e pianificare diagnostica read-only privata futura, senza accedervi prima dell'autorizzazione separata. Quando sarà autorizzato il preflight operativo, distinguere una **prima fase sola lettura** da una successiva prova controllata di backup/restore e da un eventuale rilascio, ciascuna con consenso proprio.

## C4b(k) — preflight computazionale fittizio, sola lettura NON attiva (08/11/2026)

Preparato `deploy/oracle/v165_readonly_preflight_fixture.py` con CLI **unicamente** `--check-synthetic-readonly` e `tests/test_v165_readonly_preflight_fixture.py`. Non è un collector operativo: non legge disco, non apre file, non usa rete, processi, SQLite, Oracle, Tailscale, fatturazione o credenziali; non accetta alcun percorso, hostname, input JSON o dato LIVE. Valuta esclusivamente un dizionario di **numeri inventati**, con schema rigido, contatori limitati e indicatore `OFFLINE_READONLY_PREFLIGHT_FIXTURE_ONLY`.

Calcola un **fabbisogno di spazio simulato**, `4×(DB+WAL+SHM)+3×dimensione codice candidata+512 MiB`, e verifica separatamente il numero di inode liberi della fixture (riserva di progetto pari a 256), la freschezza fittizia dei metadati (soglia progettuale 300 s), l'identità simulata codice/updater, l'accesso dichiarato privato **solo su fixture**, il rischio di fatturazione simulato e l'ipotetico doppio CI push/main. `None` nei numeri non equivale a zero e genera `UNKNOWN`; cap e tipi rigidi impediscono booleani, overflow e valori negativi. Uno scenario con disco sufficiente è classificato soltanto `MOCK_CAPACITY_PLAUSIBLE_NOT_LIVE_PROOF`, mai GO. Il riassunto espone solo indicatori sintetici, non percorsi, timestamp di sistema, IP, identificatori o metadati reali.

I dodici gate del piano di evidenze restano **12/12 non attestati** anche quando tutti i flag fittizi risultano favorevoli. Non confondere i 256 inode e i 300 secondi con limiti effettivi della VPS; sono esclusivamente criteri di progettazione da rivedere in preflight autorizzato. Allo stesso modo le cifre di riserva non attestano davvero filesystem, quota, possibilità di recovery e capienza su Oracle. Un backup/restore coerente SQLite e un ripristino off-host non possono diventare read-only: richiedono attività scriventi autorizzate e separate.

**CI verificata:** commit [`f681385`](https://github.com/mirkoworz/remura/commit/f681385c5fae6d1b400b6da0152b17db4de8b630), `test_v165_readonly_preflight_fixture.py` **38/38 PASS**, [Price Engine #42499487328](https://github.com/mirkoworz/remura/actions/runs/42499487328) **SUCCESS**, [Insights #42499487301](https://github.com/mirkoworz/remura/actions/runs/42499487301) **SUCCESS**. Dieci suite v1.65: **42+18+18+17+19+22+25+31+30+38 = 260 test OFFLINE**, nessun workflow aggiuntivo e nessun costo provider attivato. I consumi/quote GitHub e OCI reali restano da certificare indipendentemente.

**NO-GO invariato:** main e LIVE non modificati, PR #89/#97/#98 DRAFT, diagnostica OFF, C4b(l) misure vere e C5 raccolta prospettica ancora bloccati. Prossimo passo responsabile: audit incrociato dei contratti e specifica di **raccolta read-only effettivamente autorizzabile**, con limiti stretti e nessuna fuga dei metadati privati; la futura accensione richiederà consenso separato e successiva attestazione quota/billing Oracle Always Free. Evitare allungamento del laboratorio senza una concreta riduzione dei gate reali.

## C4b(k) — collegamento alle automazioni PRIVATE già esistenti (08/11/2026)

**Cambio di metodo:** prima di progettare altri mock o nuove infrastrutture abbiamo verificato i sorgenti di cinque workflow **già disponibili** nel repository privato `mirkoworz/remura-collector`. Esistono strumenti di sola lettura per health/autoupdater/risorse via Tailscale, costo Oracle Usage API (35 giorni UTC chiusi), storage e Compute Oracle home/non-home. Non sono stati avviati run né interrogate le API: abbiamo effettuato soltanto la revisione del codice su GitHub. L'inventario dettagliato e i link privati per le verifiche future sono in **[OPERATIONAL-V165-READONLY-GATE.md](OPERATIONAL-V165-READONLY-GATE.md)**.

**Gap reali che non vanno mascherati dai workflow:** la diagnostica espone soltanto uno SHA installato abbreviato (campo dell'API, non verifica file indipendente), `resources` espone RAM e uso disco root ma **non inode**; inventario OCI dei volumi non misura `df` nella VM; costo Usage API pari a zero, se letto, non certificherebbe Always Free o fattura corrente; Tailscale non dimostra da solo ACL effettiva; nessuna di queste operazioni prova backup SQLite ripristinato off-host o release authorization. I 12 gate rimangono non attestati indipendentemente dalle 260 prove offline precedenti.

**Stato:** `main` verificato `5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74` (identità VPS non attestata), PR #89/#97/#98 DRAFT, nessun deploy, merge, avvio di workflow, consumo API Oracle aggiuntivo o accesso VPS. La variabile che abilita la diagnostica, la cronologia dei workflow privati e i consumi di minuti correnti non sono stati letti da questa sessione. **C4b(l) e C5 NO-GO**. Prossimo passo: consultazione delle prove private pregresse già disponibili e, solo se necessario e separatamente autorizzato, esecuzione mirata dei task di sola lettura esistenti. Niente duplicazione di scanner né altre suite simulate prive di beneficio operativo.

## C4b(k) — evidenze storiche REALI dalle Actions private (08/11/2026)

Lettura **sola GitHub REST** (nessun dispatch) dell'elenco di run già esistenti del repository privato `mirkoworz/remura-collector`, con verifica dei job effettivamente completati e di output già sanitizzati. Ultimi controlli osservati: health/autoupdater/disco/RAM del **06/11**; COST OCI, inventario volumi, Compute e limiti A1 del **06/11**; inventario regioni non-home e check autenticazione del **07/11**. Un run storico verde non garantisce che la capacità, la sicurezza o la fatturazione siano ancora uguali. L'uso attuale e le fatture non vengono attestati dalla sola Usage API; la disponibilità A1 nominale non equivale a host capacity o a un volume Always Free autorizzato.

**Limitazione di privacy:** i valori numerici e i prefissi SHA ricavati dai log privati sono stati discussi soltanto nel contesto dell'operatore e **non inseriti nel repository pubblico**. Lo stato dettagliato, il perimetro e le limitazioni sono indicizzati in [`OPERATIONAL-V165-READONLY-GATE.md`](OPERATIONAL-V165-READONLY-GATE.md), sezione 5. Rimangono NON ATTESTATI in modo indipendente SHA completo realmente installato, ACL, billing/trial/quote corrente, free bytes/inode della VPS, backup con restore off-host e controllo autoupdater/collector in un rilascio. La verifica di autenticazione non è una prova di rotazione completa delle chiavi.

**No-GO invariato:** nessun nuovo workflow, OCI API request, VPS GET, modifica o restart, nessun merge/release, storage diag OFF, C4b(l) e C5 ancora bloccati. È un consolidamento **delle prove pregresse**, non un nuovo test di produzione. La CI precedente del codice v1.65 resta 260/260 OFFLINE, non è stata rieseguita per questa modifica di soli documenti.

## C4b(k) — chiusura duplicazione scanner inode e cautela SHA v1.64 (08/11/2026)

Ricontrollato il codice v1.65 DRAFT su PR #98: `scripts/storage_inventory_v165.py` implementa già `os.fstatvfs(fd)` con `availableBytes` e `availableInodes`; la cache prevede il passaggio in memoria al solo endpoint `/private-api/resources` dietro flag `REMURA_STORAGE_DIAG_ENABLED=1` (OFF di default). **Nessuna seconda implementazione necessaria**. I dati non provengono ancora dalla VPS LIVE e il componente non va abilitato fino alla release separatamente autorizzata. Il file `OPERATIONAL-V165-READONLY-GATE.md`, sezione 6, distingue il codice disponibile dalla prova operativa mancante.

L'utility v1.64 `reconcile_v164.py --check` è read-only in teoria, ma richiede root, un particolare precedente `installedSha`, controllo servizio/backup e accesso rete GitHub: non usarla come sostituto automatico di un test generale di checksum LIVE. La modalità `--apply` modifica esplicitamente lo stato e resta esclusa. Resta necessario un futuro controllo SHA indipendente, con baseline e lock verificati, senza toccare autoupdater. **12/12 gate integrati ancora NO-GO**. Nessuna modifica codice, flag, VPS, OCI o provider; ultimo checkpoint codice verificato 260 test offline del commit `f681385` (CI Price #42499487328 e Insights #42499487301). La modifica odierna è solo documentale; non attribuirle una nuova CI.

## C4b(k) — verificatore reale file v1.64 indipendente (08/11/2026)

Aggiunto **solo sul ramo DRAFT della PR #98** `deploy/oracle/v165_v164_live_code_readonly.py` (non installato in LIVE), con manifest statico di 15 Git blob hash verificato sul commit di rilascio v1.64 `883336a4e956a9e50c94dcfebf8d7ba78910fb65`. Nessuna dipendenza da autoupdater: routine locale su file regolari bounded e dirfds `O_NOFOLLOW`, nessun accesso a stato, database, servizi, rete o secrets. Il solo `nav.js` ammette una sostituzione controllata della data reale del banner, escludendo esplicitamente lo stamp preparatorio e modifiche non concordate. Per una futura esecuzione reale servono due flag intenzionali e, **indipendentemente**, approvazione umana e connettività privata revisionata: non eseguire adesso. L'esito non attesta `installedSha` updater o altri gate della release; resta NO-GO.

**Test del codice verificati:** 30/30 nuovi su fixture locali temporanee + 260 pregressi = **290/290 offline**. Commit [`e48e7bd`](https://github.com/mirkoworz/remura/commit/e48e7bd4ddecd297f8c1b7da832c46443b32d3b2), fix fail-closed di preparazione [`33aeb9a`](https://github.com/mirkoworz/remura/commit/33aeb9a4805104d663489e3a5e28dd12db47f28a); [Price Engine #42508534836](https://github.com/mirkoworz/remura/actions/runs/42508534836) **SUCCESS**, [Insights #42508534878](https://github.com/mirkoworz/remura/actions/runs/42508534878) **SUCCESS**. La CI sul primo commit aveva 1 test rosso: corretto prima del checkpoint. Nessun merge/release/flag attivo, nessun controllo locale sulla VPS. Dettagli e limitazioni in [`OPERATIONAL-V165-READONLY-GATE.md`](OPERATIONAL-V165-READONLY-GATE.md), sezione 7.

## C4b(k) — proposta trasporto privato manuale per SHA v1.64 (08/11/2026)

Il workflow privato attuale Tailscale **serve soltanto HTTPS/443**; manca un accesso SSH autorizzato e dedicato, e non è sicuro ampliare il tag diagnostico già utilizzato. Predisposto **solo come template non attivo** `deploy/oracle/templates/v165-private-ssh-audit-REVIEW-ONLY.yml`, da sottoporre a revisione/autorizzazione prima di un'eventuale installazione nel repo privato. Il modello usa Tailscale con tag nuovo separato, environment protetto che **deve essere configurato e verificato** (nome da solo non basta), `workflow_dispatch` su `main` privato e gate variabile OFF; fa uno scan dei 15 file v1.64 da sorgente Git pinned tramite `python3 -I -` via SSH stdin, **senza script persistente sulla VPS**. Richiede utente non-root senza sudo/scritture REMURA e chiave host SSH verificata fuori banda; non sono ancora predisposti o attestati questi requisiti. Un futuro accesso SSH, anche se dedicato, non equivale alla precedente diagnostica read-only HTTPS e va autorizzato distintamente.

Aggiunto `deploy/oracle/v165_ssh_stdout_receipt.py` per rifiutare un successo fittizio dell'output: schema esatto, source SHA, 15 file, campi approvazione LIVE tutti falsi, JSON unico senza campi doppi/extra, massimo 2 KiB. Non mostra risposte grezze, segreti o dati server nei log. Nuova suite `tests/test_v165_ssh_stdout_receipt.py`: **29/29 PASS**; totale **319/319 OFFLINE** in 12 suite, [Price Engine #42509499728](https://github.com/mirkoworz/remura/actions/runs/42509499728) e [Insights #42509499735](https://github.com/mirkoworz/remura/actions/runs/42509499735) verdi sul codice [`8f0553d`](https://github.com/mirkoworz/remura/commit/8f0553dc7ae80ffd7829996470e30314a6f2985c). Non è stato attivato o installato nessun workflow SSH. Dettagli, prerequisiti e limiti in [`OPERATIONAL-V165-READONLY-GATE.md`](OPERATIONAL-V165-READONLY-GATE.md), sezione 8.

**NO-GO:** codice e automazione privati non eseguiti, nessuna prova SHA LIVE, no Tailscale ACL review, niente chiavi/servizi/OCI/collector modificati, niente release o C5. La futura attivazione richiede altra approvazione esplicita; mantenere release PR #98 DRAFT e `main` invariato. La protezione del workflow non sostituisce gli altri gate di billing/Always Free, SQLite backup off-host e rollback.


## C4b(k) — hardening del template SSH NON attivo (08/11/2026)

Dalla lettura del workflow privato su GitHub: la diagnostica Tailscale esistente raggiunge soltanto i GET HTTPS/443, non un processo locale e non un hash indipendente dei 15 file LIVE. Riutilizzare i GET esistenti per prove parziali quando autorizzati e' la via piu' semplice; non chiamare la SHA abbreviata updater verifica indipendente. Non creare nuove API di comando remoto e non allargare tag:remura-ci-read a SSH.

Il modello di futuro audit privato resta **solo** sotto deploy/oracle/templates, mai Actions attive. Rafforzamenti: token OIDC con permessi limitati al job e revisione environment obbligatoria; blob SHA separato del ricevitore e scanner pinned; SSH senza configurazioni/proxy/client socket ereditati; stream stdout limitato a 2049 byte, parser fail-closed fino a 2048, file temporaneo solo sul runner e pulizia finale, nessun log di output grezzo. Quattro test statici aggiuntivi da sottoporre a CI: la CI non certifica la sessione reale.

Prima di un eventuale run reale servono approvazione dedicata, environment con reviewer effettivi, ACL effettive per una nuova identita' Tailscale su solo host TCP/22, server SSH non pubblico, chiave host verificata indipendentemente, utente non-root senza sudo/scrittura, forced-command restrittivo e verifica che i 15 file siano leggibili senza privilegi. Pin a SHA immutabili le Action esterne (attualmente @v4 e @v5), che sono ancora tag. Il comando da stdin non lascia script sul server ma puo' aggiornare atime/log OS. Anche un esito positivo non verifica autoupdater, inode, backup/restore off-host, fatturazione o release.

**NO-GO:** 319/319 e' il checkpoint CI precedente; nuovi test da verificare. Nessun SSH/OCI/VPS avviato, nessuna risorsa attivata, LIVE ancora documentata v1.64 e non attestata, 12 gate reali mancanti, C4b(l) e C5 bloccati.

**Chiusura verifica CI codice del modello, 08/11/2026:** [Price Engine #42512887999](https://github.com/mirkoworz/remura/actions/runs/42512887999) e [Insights #42512887987](https://github.com/mirkoworz/remura/actions/runs/42512887987) entrambe SUCCESS al commit di test `4e898a7a83edcba03ca958ee50bee3aa41b3695b`. I log Price confermano **33/33** test trasporto e **323/323** test v1.65 offline su 12 suite (319 precedente + 4). Il modello resta non attivo, nessun riscontro dei file LIVE, 12 gate reali NO-GO; CI verde non autorizza preflight VPS o release.


## C4b(k) — pin immutabili Action esterne (08/11/2026; NON ATTIVO)

Nel template di futuro audit SSH sotto deploy/oracle/templates (mai workflow eseguibile) le dipendenze esterne sono state fissate a commit GitHub ufficialmente risolti: actions/checkout v5.0.1 `93cb6efe18208431cddfb8368fd83d5badbf9bfd`; tailscale/github-action v4.4.0 `064b10558093f38325e838ddea35486bdc6b1d5c`. L'action Tailscale di quel commit dichiara supporto OIDC e client versione predefinita 1.104.4, che abbiamo reso esplicita. Cache Tailscale disabilitata per il controllo one-shot; runner ubuntu-24.04. Quattro nuovi test statici di pin/versione/runner, da verificare in CI.

Rischio residuo: il pin SHA dell'**Action** non equivale al checksum del binario Tailscale scaricato al runtime; `sha256sum` e' ancora da ottenere da fonte affidabile e validare prima di qualsiasi attivazione. Restano da attestare manual approvals effettive dell'environment, identita' Tailscale dedicata/ACL/host, utente non-root senza sudo, known_hosts, costo/quote e tutte le evidenze Oracle/SQLite. Niente run remoto o LIVE; NO-GO rilascio e C5.

**Esito CI del pin verificato:** codice test [af14b7b](https://github.com/mirkoworz/remura/commit/af14b7bfdce51d4c938c54aa3dd2c9e8e7d28b6b), nuova suite trasporto **37/37 PASS** (33 precedenti + 4 nuovi), totale **327/327 PASS** sulle 12 suite v1.65 offline. [Price Engine #42513435833](https://github.com/mirkoworz/remura/actions/runs/42513435833) e [Insights #42513435757](https://github.com/mirkoworz/remura/actions/runs/42513435757) entrambe **SUCCESS**, confermato tramite log del runner Price. Questo non abilita il template, non costituisce verifica del tarball, di Tailscale/OIDC LIVE o dell'accesso alla VPS; NO-GO invariato.


## C4b(k) — archiviazione Tailscale, controllo hash prima di OIDC (08/11/2026; NON ATTIVO)

Esaminato il codice upstream dell'Action Tailscale v4.4.0 fissata: su Linux legge automaticamente `.sha256` ufficiale se l'input `sha256sum` non e' impostato e confronta il tarball prima di estrarlo; un hash dal medesimo server non rappresenta pero' un pin indipendente revisionato. Per evitare la fiducia automatica durante un audit sensibile, il template SSH **ancora non installato** ora richiede `REMURA_V165_TS_TARBALL_SHA256` da future variabili private e passa il valore all'input `sha256sum`. Prima del collegamento verifica forma stretta SHA256, non-zero, Linux/X64; con valore assente/invalido e' STOP prima dell'azione OIDC. Quattro test aggiuntivi offline verificano errori, piattaforma e valore sintetico formato-correttamente (che **non** vale come hash autentico).

**Il digest reale dell'archivio `tailscale_1.104.4_amd64.tgz` non e' stato ottenuto o approvato.** Va verificato separatamente dalla fonte ufficiale e custodito in configurazione privata con protezioni/reviewer, insieme a policy origine OIDC, ACL tailnet, utente non-root, chiave host e tutte le altre prove. Nessuna credenziale, nuovo job privato, accesso Oracle/VPS o spesa cloud aggiunta, NO-GO v1.65 e C5.

**CI verificata dopo il controllo SHA256:** sul commit codice `1c8dc1acdcc963f0dd927f20a115b658c208fdee`, la suite SSH/read-only trasporto e' **41/41 PASS** (37 + 4 nuovi), totale v1.65 **331/331 PASS** su dodici suite offline; [Price Engine #42514473795](https://github.com/mirkoworz/remura/actions/runs/42514473795) e [Insights #42514473836](https://github.com/mirkoworz/remura/actions/runs/42514473836) **SUCCESS**, i quattro nuovi test confermati nei log. Non e' stata verificata la SHA reale del tarball, ne' la rete Tailscale/SSH, la VPS, le quote o il rilascio: **NO-GO invariato**.

**Controllo HEAD main, stesso checkpoint:** GitHub segnala `main=8c1907a03123dc766cc434d14ae13a9ac93aec3c`, avanzato di **un commit** rispetto al pin documentato `5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74`. Il confronto GitHub mostra **31 file cambiati, tutti sotto `data/myfxbook/`**, senza differenze di codice fuori `data/`. E' un refresh dati, NON un commit di release, e non attesta la LIVE: il riferimento del simulatore v1.65 rimane fissato alla baseline storica e NON va riscritto in automatico. Prima del release-preflight reale serviranno riconciliazione del target corrente e verifica SHA LIVE separatamente. Nessuna azione su `main` eseguita da questo filone.
