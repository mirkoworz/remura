# REMURA Contributors v0.79 LAB — D1 GraphQL UNKNOWN: runbook di diagnosi senza spesa

**21 novembre 2026 · 17:10 CET (Europe/Rome)**

## Stato dell'incidente
- Il report Cloudflare AUTOMATICO su main del **21 novembre 2026** è `INCOMPLETE_OR_CRITICAL` (workflow failed) perché `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, e `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`.
- Log reale, sola lettura: https://github.com/mirkoworz/remura/actions/runs/44919682812
- Non si tratta di un risultato `0` righe, né di una prova di quota esaurita.
- Workers: `OK`, circa **199 richieste stimate**, **0 errori stimati** il 21 novembre UTC.
- D1 metadata: **4 database**, **6.557.696 byte** account complessivi, **6.266.880 byte** il database TEST. Non sono contatori di righe lette o scritte.
- Ultimo monitor D1 Analytics `OK` 20 novembre: https://github.com/mirkoworz/remura/actions/runs/44772218921. Non utilizzare il suo valore per “riempire” le metriche mancanti del 21.

## Perché può accadere
La documentazione ufficiale Cloudflare, aggiornata al **6 novembre 2026**, chiarisce che `d1AnalyticsAdaptiveGroups` registra un dato soltanto se la richiesta raggiunge effettivamente il motore di esecuzione SQL. Le chiamate fallite prima del SQL potrebbero non apparire. L'assenza di righe GraphQL non prova né traffico zero né completamento della misurazione.
Fonte: https://developers.cloudflare.com/d1/observability/metrics-analytics/
L'API GraphQL alimenta anche le metriche della dashboard. Consultare la dashboard non fornisce necessariamente una fonte indipendente.
Le 31 giornate disponibili di retention e le metriche `rowsRead`/`rowsWritten` sono riferimenti informativi; l'uso aggregato rimane stimato e non attestazione di fatturazione.

## Procedura futura SOLO DI LETTURA, quando il proprietario la autorizzerà
1. Aprire il monitor GitHub read-only `REMURA Cloudflare Free Budget DAILY`; NON riavviare senza motivo, né modificare Secret/token/cloud.
2. Se `UNKNOWN_NO_GRAPHQL_DATA`, consultare la dashboard Cloudflare → D1 SQL databases → database già esistente → Metrics → Row Metrics per il giorno UTC corrente e per il precedente, **senza eseguire query SQL apposta**.
3. Per chiarire la disponibilità del dataset, confrontare l'esistenza di gruppi `d1AnalyticsAdaptiveGroups` per oggi e ieri usando solo **lettura GraphQL account**, limitata nel tempo e nel numero di risultati. `0 gruppi` in entrambe le finestre è sempre UNKNOWN; `0` oggi e `>0` ieri resta UNKNOWN oggi.
4. Se la metrica giornaliera corrente è assente, il monitor deve conservare `NO_GO` e non interpretare metadata storage come consumi giornalieri. Non creare nuove operazioni D1 “per accendere i grafici”.
5. Per una futura prova di staging controllare anche piano/Seats Access Free e budget corrente. I report account GraphQL sono stime; nessun tool locale può autorizzare produzione.
6. Se il problema persiste con attività SQL realmente nota, verificare stato Cloudflare e permessi del solo token Analytics Read, senza creare, ruotare o divulgare token in questa fase. Ogni variazione di credenziali richiede autorizzazione distinta.

## Cosa è stato aggiunto alla v0.79 LAB
- `free_quota_evidence_v079_lab.py` è un **classificatore offline** dei log già prodotti. Non accede all'API e non legge `os.environ`; i quattro blocchi sono `d1`, `workers`, `test_storage`, `account_storage`.
- Il classificatore richiede data UTC corrente, origine dichiarata `ADAPTIVE_GRAPHQL_ESTIMATE`, valori numerici non negativi, stesso limite Free di riferimento, margine di sicurezza sotto il **70%** e consenso Access attestato come input. Restituisce `NO_GO` se qualsiasi evidenza manca.
- Anche nel caso sintetico perfetto l'esito massimo è `LAB_REVIEW_ONLY`, `automatic_deploy_allowed: false`. NON è un'autorizzazione a Cloudflare, e non misura fatturazione o Access.
- `diagnostic(today,yesterday)` classifica soltanto la presenza/assenza di dataset GraphQL ricevuti come input sintetico (NON effettua richieste), senza inferire righe lette/scritte.
- `staging_source_lock_v079_lab.py` verifica **14 blob Git originali** (SHA-1 Git: blob di contenuti precisi), inclusi router Worker v0.78, 15 asset incorporati, Access/HMAC/D1, schema SQL v0.76/v0.77, audit e lettore integrity. Rifiuta file modificati/symlink, non fa deploy e non attesta il runtime Cloudflare.
- Il repo `mirkoworz/remura` è pubblico: i log e le fonti committate **non devono contenere identità reali, Secrets o prezzi proprietari**.

## Vincoli Free ufficiali (21/11/2026)
- D1 Workers Free: nominalmente 10 DB, 500 MB/DB, 5 GB account; Workers Free 100.000 invocazioni/giorno; D1 Free circa 5M righe lette/giorno e 100K scritte/giorno. Questi sono limiti documentali e possono essere aggiornati.
- La documentazione Cloudflare dichiara che al superamento dei limiti giornalieri Free D1 **le query vengono respinte**, non che si genera automaticamente una spesa.
- Fonti: https://developers.cloudflare.com/d1/platform/limits/ ; https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/
- Questa fase non ha creato alcuna fatturazione: nessun accesso Cloudflare nuovo e nessuna API reale chiamata.

## Non fare
- NON eseguire query SQL per generare artificialmente attività; NON cambiare il monitor `main`, NON allargare permessi del token, NON attivare staging, deploy, nuovi database, nuovi utenti, modificare Oracle, né dichiarare GREEN se D1 GraphQL è vuoto.
- NON confondere un checksum Git con prova crittografica di autenticità o una suite sintetica con sicurezza reale su Cloudflare.

**Esito attuale: NO-GO per staging reale, ma nessun indizio nel report che i limiti storage o Workers siano prossimi all'esaurimento.**
