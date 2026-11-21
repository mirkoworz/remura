# REMURA Contributors v0.81 LAB — ROUTE / ROLE / ASSET MANIFEST

**Checkpoint: 21 novembre 2026 · ore 17:55 CET (Europe/Rome)**

## Stato tecnico confermato
- Repo **pubblico**: `mirkoworz/remura`; branch di lavoro esclusivo: `research/contributors-route-manifest-v081-20261121`.
- Branch creato dalla **v0.80 readiness** `568febf044a2390f0de2b01cd58ffc4c0fc089c3` (v0.79 base indiretta `eaa6805b3db8fce29a736d0ab47211c925cda055`). Nessuna modifica a `main`.
- HEAD **testata**: `d04497d1929d6cd25bb5af43d7e0fc59a92c8411`.
- GitHub Actions v0.81 su HEAD: https://github.com/mirkoworz/remura/actions/runs/44927074908
- **20 test NUOVI / 20 PASS / 0 FAIL**; job concluso SUCCESS, log ispezionato: `Ran 20 tests`, `OK`, `REMURA_V081_ROUTE_MANIFEST=20_20_PASS`.
- Un primo run `44927000944` è fallito per un'errata mutazione nel test 04: la stringa usata dal test non corrispondeva al sorgente, quindi il controllo negativo non esercitava la protezione. La fixture è stata corretta; il run intermedio `44927054724` e quello HEAD `44927074908` sono entrambi GREEN. Non risulta un bug nel router originale.
- Non sono state rieseguite le suite storiche Contributors. Nessun nuovo accesso Cloudflare, Secret, deploy, merge, migrazione D1, Oracle o spesa.

## Artefatti aggiunti solo LAB
1. `research/contributors/route_manifest_v081_lab.py`: verifica OFFLINE e fail-closed del router privato v0.78. Prima usa il blocco a 14 Git blob già pinned, poi verifica esattamente le 4 rotte con ruoli CONSTRIBUTOR/OWNER, la mappa delle aree asset, l'esclusione di due asset OWNER per navigazione CONTRIBUTOR e le 17 rotte API del candidato.
2. Controllo preciso del bundle: **4 pagine** e **11 asset distinti**, **15 file totali**, senza aggiunte o assenze. Le pagine contengono già v0.78 LAB e timestamp `21/11/2026 16:56 CET` in cima e l'attributo di ruolo corrispondente.
3. `research/contributors/test_route_manifest_v081_lab.py`: 20 test mirati esclusivi per nuove garanzie (drift della route, role switch, duplicate route e API, owner-only guard, bundle, banner, source lock, CLI NO_GO, alterazione di file in copia isolata).
4. `.github/workflows/remura-contributors-v081-one-shot-ci.yml`: workflow Ubuntu standard gratuito, read-only repository, checkout senza credenziali persistenti, solo Python stdlib, nessun uso di Secret, nessuna chiamata a Cloudflare e nessun deploy.
5. Report finale sempre `decision: NO_GO`, `runtime_policy_attested: false`, `provider_access_attested: false`, `automatic_deploy_allowed: false`. Questo **non** equivale a una firma del deploy, prova Access runtime, attestazione di ruoli reali o collaudo Safari.

## v0.80 preesistente: verificata senza rifare test
- v0.80 preflight su branch `research/contributors-access-d1-preflight-v080-20261121`: run https://github.com/mirkoworz/remura/actions/runs/44923942230 — **92/92 PASS**.
- v0.80 readiness: branch `research/contributors-readiness-v080-20261121`: run https://github.com/mirkoworz/remura/actions/runs/44924395473 — **60/60 PASS**; pagina snapshot iPhone https://github.com/mirkoworz/remura/actions/runs/44924515260 — **20/20 PASS**.
- In totale v0.80 ha **172 nuovi test PASS** (tre suite separate). La pagina di readiness v0.80 esiste come file statico ma non è un portale live.
- Le **quattro pagine di accesso privato rimangono alla v0.78 LAB**. Non sono state modificate in v0.79–v0.81, quindi non riscrivere né incrementare falsamente il loro banner.

## Cloudflare Free e condizioni di STOP
- Ultimo monitor account giornaliero del 21/11: https://github.com/mirkoworz/remura/actions/runs/44919682812 — conclusione FAILED/INCOMPLETE per `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`.
- **D1 rows read/write del 21/11: NON MISURATE**, usare `NO_GO` anziché zero. Il report del 20/11 non è una misura sostitutiva.
- Dati del medesimo run: Workers 199 richieste stimate e 0 errori stimati; inventario D1 4 database, 6.557.696 byte totali, database TEST 6.266.880 byte. Snapshot e stime, non fatturazione.
- **Access Free seats/account plan effettivi UNKNOWN**. Cloudflare specifica che la vista Zero Trust overview mostra posti consumati e disponibili, e che revocare sessioni non libera un posto; rimuovere un utente non equivale a impedirne l'accesso. Riferimento: https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/
- Cloudflare D1 GraphQL `d1AnalyticsAdaptiveGroups` non certifica richieste che non arrivano all'esecuzione SQL. Riferimento: https://developers.cloudflare.com/d1/observability/metrics-analytics/
- Riferimenti limiti Free: https://developers.cloudflare.com/d1/platform/limits/ e https://developers.cloudflare.com/d1/platform/pricing/ . Controllare sul provider prima di ogni passaggio reale.
- Nessun account ID, email, nome, token, chiave, segreto o livello privato è stato versionato in questi nuovi file.

## Roadmap preservata e prossima priorità v0.82
1. Sviluppare **senza eseguire** l'adapter read-only di correlazione delle finestre D1 GraphQL, errori di provider, timeouts e provenienza; usare solo input offline sanitizzati. Non riavviare il monitor Cloudflare e non usare vere credenziali senza autorizzazione separata.
2. Preparare il **dossier operativo** Cloudflare Free per account plan, seats disponibili, policy allowlist, 1–2 collaboratori, Access JWT + same-origin, logout/revoca e Safari fisico. Fino al collaudo: staging = NO_GO, nessuna registrazione.
3. D1 fixture isolato e rollback solo dopo autorizzazione specifica e contatori correnti affidabili. Flussi nuovi livelli originali / amendment separati, RESERVED fail-closed, OWNER review append-only; Telegram soltanto per livelli approvati con consenso.
4. TradingView v0.8.181 LAB: holdout 1 **23–29 novembre 2026 UTC**; holdout 2 **30/11–06/12 UTC**. Mantenere protocollo immutato, nessuna dichiarazione di edge. Shark Science v0.4 COT/sentiment/delta/CVD/assorbimento/Effort Result rimane filone sperimentale.
5. REMURA Experience v0.30 LAB: splash toro/orso 3D, collisione/esplosione, logo pinna e ringraziamento SMF, eliminare foto; Safari reale in futuro.
6. Private Capture v0.15 LAB STOP senza Secret; Oracle collector attivo, autoupdater bloccato, release firmata v1.65 staged senza installazione. Ampere Radar v0.36 con monitor gratuito/Telegram operativo; backup reale, Squalincome e integrazione Telegram Contributors futuri preservati.
7. Monitorare quote Free e passare in nuova chat quando pesante con SHA e CI reali; non richiedere il Mac per filoni gestibili su GitHub.

**Semaforo finale**: v0.81 LAB **GREEN 20/20** su GitHub Actions; **staging reale NO-GO** perché quote D1 giornaliere e Access seats non attestati. Nessuna spesa nuova autorizzata.
