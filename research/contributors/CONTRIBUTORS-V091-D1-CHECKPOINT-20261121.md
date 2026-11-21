# REMURA Contributors v0.91 LAB — CHECKPOINT D1 DIAGNOSTIC

**21 novembre 2026 · Europe/Rome · Versione 0.91 LAB.**

## GitHub effettivo
- Repository pubblico: mirkoworz/remura.
- Branch: research/contributors-d1-diagnostic-v091-20261121.
- Baseline: Contributors v0.90 SHA e1693bb9b12b53bcd3af87b5b720abd6c63f2e55.
- Script nuovo: research/contributors/cloudflare_d1_diagnostic_v091_lab.py, Git blob f5568f365232a943d6b53b6c8581cd158f21188e.
- Script pinned query v0.86: research/contributors/readonly_probe_plan_v086_lab.py, blob bfc0315067c2adb5436e6166a6af88761adfd615; fixture GraphQL blob cf804bf39721fcd2f791722d07bcb1e07a1391ae; query SHA-256 483e14a113af7841fb69bdfdb7ea3fa3ee616b74f4f28b9cbc509b29d022754a.
- Codice CI testato commit 0b07d4783fc4fceea80de4a7deb7197cf17cf8bb. GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44937483269 **SUCCESS**; log verificato: Ran 25 tests, OK, REMURA_CONTRIBUTORS_V091_D1_DIAGNOSTIC=25_25_PASS. SOLO 25 test nuovi, nessuna suite pregressa ripetuta.
- Prima di questo checkpoint, HEAD branch 377db44824829b51484d8e1d1cd0b6e44141898d. main rimasto 26896d642ea311f23dfa7f30ea1c8599c8c099e3.
- Nessuna esecuzione Cloudflare reale durante i commit v0.91. Verificato che il file di consenso V091-ONE-TIME-OWNER-CONSENT.txt NON ESISTE; nessun workflow provider è partito.

## Capacità aggiunta
La nuova diagnostica ha due modalità:
1. --offline-plan: 0 richieste HTTP, 0 Secret, stato OFFLINE_NOT_AUTHORIZED, decision NO_GO.
2. --execute-one-time: SOLO in futuro dopo autorizzazione SPECIFICA; richiede due flag esatti e gli attuali Secret GitHub REMURA_CF_ACCOUNT_ID e REMURA_CF_ANALYTICS_READ_TOKEN con Account Analytics Read. Non usa D1 Write/Edit, D1 SQL, Access Users, Oracle, webhook né trading.

Il codice interroga prima il giorno UTC corrente e, SOLO se il dataset è vuoto, una seconda volta il giorno UTC precedente. Tetto 2 POST HTTPS totali su api.cloudflare.com/client/v4/graphql, timeout 15 secondi/call, risposta massima 100.000 byte/call, nessun redirect o retry. Query byte-pinned, nessun body grezzo, ID account/database o token in output. Solo fasce percentuali D1 read/write del giorno corrente oppure stati TODAY_EMPTY_PREVIOUS_PRESENT / BOTH_DAYS_EMPTY_NOT_ZERO / ERROR_UNATTESTED. UNKNOWN non equivale a zero. Metriche adattive non sono fatturazione esatta. In ogni caso staging_allowed=false, access_seats_verified=false, free_plan_verified=false.

## Trigger eseguibile in futuro SENZA main
Inizialmente predisposto un workflow manuale su research branch, poi RIMOSSO perché GitHub richiede workflow_dispatch sul default branch (https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). In sostituzione predisposto .github/workflows/remura-v091-consent-trigger.yml.

Nessuno schedule o workflow_dispatch. Si attiva soltanto se, DOPO una mia specifica autorizzazione nel dialogo, viene creato per la PRIMA volta sul solo branch un file:
research/contributors/V091-ONE-TIME-OWNER-CONSENT.txt

Contenuto esatto di una riga:
REMURA_V091_OWNER_CONSENT_FOR_D1_ONLY:YYYY-MM-DD
con YYYY-MM-DD uguale al giorno UTC del futuro run e newline finale.

Commit message esatto:
chore(remura): OWNER_APPROVES_D1_ONE_TIME_V091

Ulteriori controlli: il job verifica che il file sia NEW in head_commit.added, che sia il giorno UTC corrente, che i tre file di sicurezza abbiano Git hash immutati e che il repository/branch siano esatti. SOLO dopo carica i Secret read-only nel passo che effettua al massimo due richieste. Il file di consenso NON è stato creato. La possibilità tecnica del trigger è codice preparato, non un workflow già collaudato dal vivo o un'autorizzazione implicita da un generico "andiamo avanti".

## Free e reali punti di blocco
- Monitor schedulato main .github/workflows/remura-cloudflare-budget-daily.yml intatto. Il run del 21/11 44919682812 è FAILED, con REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA e REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED. Il GREEN del 20/11 44772218921 non certifica oggi.
- Posti Access Free e pianificazione costi account UNKNOWN, anche se conosciamo i limiti nominali D1 Free 5M reads/day, 100k writes/day, 10 DB, 5GB account e 500MB per DB. Cloudflare D1 docs https://developers.cloudflare.com/d1/observability/metrics-analytics/ .
- L'analisi provider va autorizzata separatamente, dopo verifica margine Free. Una query D1 NON verifica seats Access, il piano effettivo, login/logout/revoca, sicurezza Worker o spese.
- Pilot reale di 1-2 collaboratori ancora NO-GO. Le 4 pagine private v0.78 LAB non sono in deploy; v0.90 POST guard 34/34 PASS; v0.89 demo iPhone 30/30 PASS; v0.88 Free Guard 22/22 PASS. Scrittura solo propri livelli, OWNER approva, original e amendment separati, RESERVED no auto-retry, audit append-only, futuro Telegram solo livelli approvati.

## Roadmap integrale preservata
1. Contributors: consenso specifico D1 sola lettura (max 2 GraphQL POST una tantum) -> verifica seats Free in dashboard privata -> staging isolato e reversibile autorizzato, Access deny-default, JWT e ruoli D1 lato server, Safari fisico e rollback -> pilot 1-2 collaboratori.
2. TradingView v0.8.186 LAB: protocollo V2 congelato; sviluppo 16–22 novembre, holdout 1 23–29 novembre UTC, holdout 2 30 novembre–6 dicembre UTC, confronto CVD vs price-only 60 minuti preregistrato. Dati live prospettici, ancoraggio indipendente e performance NON ATTESTATI. Vietate ricostruzioni tardive o proclami di edge.
3. Shark Science v0.4 LAB COT/retail sentiment/Delta-CVD proxy/assorbimento/Effort Result; matching stessa decisione e clock first-seen da provare. Non riscrivere moduli già esistenti.
4. Experience v0.30 LAB splash toro/orso 3D, esplosione, pinna REMURA e SMF, rimozione foto; Safari reale futuro.
5. Private Capture v0.15 LAB solo sintetico e non attivo; Oracle collector attivo, autoupdater fermo, v1.65 signed root-owned staged NON installare. Ampere Radar v0.36 capacity Milano e Telegram operativo, backup reale e Squalincome in roadmap.
6. Nessun Mac, deploy, merge main, token reale o spesa introdotti; non ripetere test/verifiche concluse. In chat lunga fare passaggio con commit/branch/run/roadmap.

**RISULTATO: Contributors v0.91 LAB preparato, 25/25 NUOVI TEST PASS; provider non contattato, nessuna autorizzazione reale ricevuta, staging NO-GO.**
