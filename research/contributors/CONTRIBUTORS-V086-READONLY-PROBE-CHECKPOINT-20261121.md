# REMURA Contributors v0.86 LAB — PIANO DIAGNOSI IN SOLA LETTURA

**Checkpoint 21 novembre 2026 · ore 18:24 CET (Europe/Rome)**

## Provenienza GitHub e risultato verificato
- Repository: `mirkoworz/remura`, pubblico. Branch `research/contributors-readonly-probe-v086-20261121` creato da v0.85 LAB `9cdb52a21b17348b0e731eeb579b2a3997340511`.
- Commit di **codice effettivamente testato**: `ef5f55c8c596c1db7b0cf97025072b49316f7e49`.
- Workflow `.github/workflows/remura-contributors-v086-one-shot-ci.yml`, run https://github.com/mirkoworz/remura/actions/runs/44929738479 **SUCCESS**, log verificato: `Ran 18 tests`, `OK`, `REMURA_V086_READONLY_PLAN=18_18_PASS`. Solo **18/18 test nuovi**, nessun precedente ritestato.
- Primo tentativo `019ef757fbb534593f9ba6d9908d756ef3bcd25e`, run 44929552913, **FAILED**: il guard Python storico non è presente nel branch corrente (è caricato dal monitor da un checkout immutabile separato); corretto con fixture GraphQL **non eseguibile** contenente la query storica attestata per testo. Non nascondere l'errore originario, né interpretare una query salvata come attuale verifica live.
- Il modulo non contiene import `urllib` né credenziali, non chiama provider, non usa Secret e non attiva il monitor.

## Nuovi artefatti
1. `readonly_probe_plan_v086_lab.py` produce solo un piano **non autorizzato** e non eseguibile. Fissa massimo **2 richieste GraphQL POST di sola lettura soltanto in un futuro collaudo esplicitamente autorizzato**, rispettivamente giorno UTC target e precedente. Nessun retry, zero richieste Access API o D1 SQL, zero chiamate effettuate.
2. `monitor_query_reference_v086_lab.graphql`: copia della query GraphQL del guard storico sul commit `08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8`, solo fixture; SHA-256 query canonica `483e14a113af7841fb69bdfdb7ea3fa3ee616b74f4f28b9cbc509b29d022754a`. Hash del blob storico originale `af89df266d25541fc474b4d13536f61d2d77022a`, **non** attestato a runtime sul branch.
3. `test_readonly_probe_plan_v086_lab.py` verifica sorgenti assenti/alterate, formato GET vietato, piano non attivabile, deduzioni NO_GO, 18 casi nuovi.
4. `CONTRIBUTORS-V086-READONLY-PROBE-RUNBOOK-20261121.md`: piano futuro con endpoint, costi chiamata limitati, dati aggregati, sezione Access seats manuale e divieto log PII.
5. Output: `approved_to_execute=false`, `http_calls_performed=0`, `provider_secrets_accessed=false`, `d1_rows_today_attested=false`, `same_day_billing_attested=false`, `decision=NO_GO`.

## Diagnostica realistica Cloudflare
- Workflow giornaliero `.github/workflows/remura-cloudflare-budget-daily.yml` su `main` già schedulato; usa `secrets.REMURA_CF_ACCOUNT_ID`, `REMURA_CF_ANALYTICS_READ_TOKEN`, `REMURA_CF_D1_READ_TOKEN` e checkout pinned del monitor. **Non modificato**.
- L'ultima run del 21/11/2026 https://github.com/mirkoworz/remura/actions/runs/44919682812 ha fallito con `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`; non c'è prova attuale di righe D1 lette/scritte. Una lista vuota non è zero; un run vecchio GREEN non colma il vuoto.
- Metriche storiche: Workers circa 199 richieste stimate, 4 database D1 e storage aggregato 6.557.696 B, TEST 6.266.880 B; Access Free seat account **UNKNOWN**. Non è rendicontazione esatta.
- Prima di svolgere la prova reale servono consenso esplicito, controllo Free attuale, segreti strettamente di lettura con limitazione stampa, eventuali quote chiamate e schema già verificato.
- Per posti e revoca Cloudflare Zero Trust: https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/ . Liberare un seat **non** equivale necessariamente a impedire autenticazioni: sono decisioni/policy distinte. D1 GraphQL: https://developers.cloudflare.com/d1/observability/metrics-analytics/ .

## Roadmap invariata e next action
1. Prossimo passo utile per Contributors non è ripetere test sintetici, ma **ottenere con autorizzazione specifica** prova attuale dashboard Free/Access e due finestre D1 qualora il monitor giornaliero non basti. Nessuna azione live autorizzata da questo checkpoint. Staging, D1 migration, utenti e worker restano NO_GO.
2. Portale: le quattro pagine private candidate rimangono **v0.78 LAB** con versione/data in alto; report readiness v0.80 LAB, ruoli OWNER vs CONTRIBUTOR e scrittura limitata ai propri livelli; original e amendment distinti, RESERVED mai auto-release/retry, audit OWNER append-only, Telegram post-approvazione.
3. TradingView v0.8.186 LAB: richiesta di hash pronta per un futuro anchor esterno, holdout V2 23–29/11 UTC e 30/11–06/12 UTC immutati, nessun valore predittivo dimostrato, nessuna cattura live. Shark Science v0.4 continua scientificamente con COT/sentiment/CVD/ER.
4. Experience v0.30 LAB animazione toro/orso 3D + splash pinna REMURA / SMF, foto da rimuovere e Safari fisico quando possibile. Private Capture v0.15 LAB sintetico non attivo. Oracle collector operativo, autoupdater fermo, v1.65 staged root-owned NON installare. Ampere Radar v0.36 per Oracle Milano e notifiche Telegram operativo. Backup, Squalincome e invio livelli approvati via Telegram preservati.
5. Nessuna spesa nuova; monitorare Free senza interpretare UNKNOWN come zero. Niente Mac per questa fase; non ripetere suite storiche già concluse; passaggio di consegne quando chat troppo pesante.

**Conclusione: v0.86 LAB nuovo test 18/18 PASS; D1 e Access provider non attestati; staging NO_GO.**
