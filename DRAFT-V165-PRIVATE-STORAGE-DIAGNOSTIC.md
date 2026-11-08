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
  Le dimensioni non sono uno snapshot atomico.
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

