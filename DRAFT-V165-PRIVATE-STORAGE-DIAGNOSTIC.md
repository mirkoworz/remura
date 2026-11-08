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

