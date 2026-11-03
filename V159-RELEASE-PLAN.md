# REMURA v1.59 — Release manuale protetta (non installata)

**Data:** 3 novembre 2026. **Versione live:** v1.58, ultima conferma diagnostica privata #27, autoupdater installedSha=112da31cb10c34477642e2822c78b267cb88978d. GitHub main può contenere commit successivi solo dati Myfxbook.

## Prototipo
- Telemetria Squalincome post-ingest e periodica, aggregata in SQLite, cap 256 righe, solo timestamp UTC e contatori.
- Nuovo file Python scripts/squalincome_timing.py. Nessuna chiamata cTrader addizionale; nessuna notifica e nessun segnale operativo nuovo.
- Nove pagine con nav.js?v=159, banner v1.59 e stamp reale Europe/Rome in fase --apply; cache PWA v73.

## Gate GitHub
1. PR #76 integrata senza squash/rebase; mantenere commit contenente installer immutabile **dc6c14604d83a932f25c7cf0ca5c9fcc725faef5** perché la riconciliazione ne verifica il blob SHA **b14ee7b1efab67913c276d9728216df9750c289a**.
2. Confermare HEAD main esatto e due CI Price Engine/Insights **push** verdi sul commit di merge. Commit solo dati Myfxbook possono avanzare main senza aggiornare codice installato; ogni check deve fissare lo SHA effettivamente verificato.
3. Controllare diff rispetto a 112da31...: consentire solo file previsti e archivi data/myfxbook. Se cambia installer o altro codice, ripetere audit, aggiornare pin e CI.

## Gate VPS: sequenza separata, non automatica
1. Scaricare release_v159.py da **commit immutabile** e controllare Git blob SHA. Eseguire prima **--check --commit SHA_MAIN** con root. Non modifica file o DB.
2. Preflight: file live esatti della v1.58, tranne timestamp reale unico in nav; nuovo modulo assente; server sano, flag post-ingest ON, stato autoupdater con installedSha v1.58 e stato up_to_date/data_only/manual_required; CI remote green, integrità SQLite e spazio.
3. Solo dopo esito positivo: comando distinto **--apply --commit SHA_MAIN** sotto lock. Backup SQLite coerente + restore-test isolato, bundle rollback SHA256 con 13 originali e nuovo modulo marcato assente, 14 file installati, restart e health. Se fallisce, restore 13 file + rimozione nuova unità e riavvio.
4. Solo dopo rilascio validato: scaricare reconcile_v159.py con blob verificato e avviare **--check --target SHA_MAIN**; controlla 14 file, backup e state. Poi **--apply** separato, crea copia dello stato e cambia solo lo SHA. Niente --init-sha.
5. Diagnostica privata indipendente remura-collector; salvare esito, backup e SHA. Verificare condizioni dati, scanner 34 mercati, qualità H1, volumi, RAM/disco e servizi.
6. Osservare almeno più cicli e confrontare scansioni con e senza ingest: numero record, durata, errori, batch-to-scan. **Non è misura candela→segnale** e non prova maggiore profittabilità.

## Rollback
Bundle in /opt/remura/private/predeploy-backups/rollback-v159-*; manifest lega commit a hash vecchi/nuovi e al fatto che il modulo nuovo non esisteva. Il rollback non modifica lo stato autoupdater né ripristina SQLite: se lo SHA è stato riconciliato, va gestito separatamente. Non cancellare il bundle.

## Costi
Nessun endpoint o provider broker aggiunto. Scrittura SQLite limitata a 256 record. Billing OCI, costi di rete, Firestore e quote reali rimangono N/D finché verificati nei relativi pannelli.
