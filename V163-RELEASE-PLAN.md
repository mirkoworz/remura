# REMURA v1.63 — Splash Squali: piano rilascio protetto (CANDIDATO, NON LIVE)

**Preparazione:** 05/11/2026 Italia. **Sorgente LIVE attestata:** v1.62, `1568edefabc7bbdb7d06485d2b863b196a4e6155` (verificare di nuovo su Oracle prima di procedere). Branch grafico `feature/splash-shark-remora-20261105` / PR #90; branch release separato `release/v163-shark-splash-20261105`. **Non eseguire deploy, merge o attivazioni contemporaneamente ai Track A/B**. Non modificare i relativi collector o flag.

## Contenuto release

- 15 file installati: `scripts/private_server.py`, `nav.js`, `sw.js`, nove pagine HTML e tre nuovi file `splash.js`, `splash.css`, `splash-mascot.webp`.
- Le nove pagine importano `nav.js?v=163`; banner comune `v1.63` con timestamp preparatorio `05/11/2026 16:00 (Italia, preparazione)`, sostituito **esclusivamente in fase --apply** con la vera ora italiana. La Home importa solo `splash.js/css?v=163`.
- PWA cache con nuovo nome `remura-shell-v77-v1.63-shark-splash`; la cache non conserva `/private-api/`. L'unica richiesta aggiuntiva in avvio è una **GET interna** a `/private-api/health` con timeout 1,1 s. Non legge dati finanziari, non chiama provider.
- Il monitor H1 già attivato al Track A rimane nel suo stato attuale: **nessun obbligo di spegnerlo**, nessuna modifica ai parametri H1, broker, segreti, SQLite o file ambientali.

## Codice protetto

- `deploy/oracle/release_v163.py`: installer derivato da v1.62, base SHA v1.62 e dodici Git blob LIVE pinnati, tre nuovi asset assenti obbligatori, tree/zip sha verificati, compare diff allowlist, Price e Insights CI *push/main* verdi. `--check` è sola lettura; `--apply` controlla nuovamente sotto lock autoupdater, backup SQLite e restore-test, registra rollback codici/hashes, ferma solo il servizio web per la sostituzione atomica, lo riavvia e verifica health; in caso di errore tenta rollback. **Non riconcilia lo stato autoupdater**.
- `deploy/oracle/reconcile_v163.py`: verifica il blob immutabile dell'installer v1.63 `0214b8baf5ed3bdefebb21bbfd08204c8d99dd45` leggendo il commit immutabile `21281734e8e10540e57fef15d0cb728b890f8cd0`; convalida i 15 file installati, banner Italia, manifest rollback, SQLite backup, CI push/main e SHA target. `--check` non scrive; `--apply` aggiorna **soltanto** `autoupdate-state.json` con backup dello stato. Non reinstalla codice né riavvia.
- CI offline: vecchi test v1.62 ancora attivi, `tests/test_release_v163.py`, `tests/test_reconcile_v163.py`, `tests/splash.test.js`, test release consistency e suite Price/Insights; nessun segreto o account trading nei workflow.

## Gate prima dell'installazione (ancora NON eseguiti)

1. PR #90 e PR release devono superare CI proprie e review; controllare main, Track A/B e autoupdater e assenza di modifiche non incluse nell'allowlist. Mai unire in contemporanea due rami di produzione. Sequenza: integrare #90 in main, poi PR release con CI push/main; bloccare ogni autoupdate intermedio finché non è approvata la release unica. Il merge di #90 può impostare stato `manual_required`, non è installazione.
2. Verificare test `push/main` verde Price + Insights sullo SHA *finale* (i test PR non bastano). Controllare pin commit installer prima di usarlo.
3. Entrare sulla VPS con accesso privato già autorizzato. Lanciare soltanto `--check --commit SHA` da **file immutabile** e verificare `PREFLIGHT_V163=OK`. Se la LIVE è diversa, una CI è rossa, SQLite è danneggiato, spazio basso, H1 è alterata, oppure main è cambiato, STOP. Nessun dato sensibile nei log.
4. Solo dopo preflight OK, `--apply --commit SHA`, verificare `BACKUP_SQLITE=VERIFICATO`, `RESTORE_TEST=OK`, `RILASCIO_V163=OK`, rollback archiviato e 15 file installati. Controllare il banner su 9 pagine e la scena squalo/remura su iPhone. La prima schermata iOS nativa non è modificabile.
5. **Riconciliazione separata**: `reconcile_v163.py --check --target SHA` poi `--apply --target SHA`, verificare stato e SHA, e ricontrollare `/private-api/health`. Solo dopo potrà funzionare normalmente l'autoupdater.
6. In caso di problema usare **il rollback dell'installer** con manifesto archivato; nessun merge/rollback codice o modifica autoupdater improvvisata. Se il problema è dopo riconciliazione, recuperare anche il file di stato da backup con procedura verificata prima di ripetere il rilascio.
7. Nuovo audit quote **Oracle, GitHub Actions, Firestore**: la GET locale aumenta il contatore di 1 per avvio; il fatto che sia poco non dimostra un costo effettivo di 0 €.

**Stato:** codice in PR, non LIVE. Nessun annuncio "v1.63 installata" senza prove da Oracle, backup/restore-test e banner reale.
