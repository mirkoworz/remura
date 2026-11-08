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
