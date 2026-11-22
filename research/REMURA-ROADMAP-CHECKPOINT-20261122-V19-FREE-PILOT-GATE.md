# REMURA — CHECKPOINT V19 / CONTRIBUTORS FREE PILOT READINESS — 22 novembre 2026 (Europe/Rome)

## Principio inderogabile
L'utente ha confermato su Safari iPhone l'anteprima Shark Anatomy v1.68 e la compilazione/copia bozza Contributors v0.95. V18 ha allineato la v0.96 al contratto D1 e preparato il form privato + bundle senza deploy, 31/31 test GREEN. Questo V19 **NON crea utenti veri, non usa API Cloudflare, non installa/deploya Worker, non modifica D1, Oracle, Pages o main**. Resta LAB. Ereditare tutti i checkpoint da V01 a V18; non rifare collaudi gia' verdi se codice non cambia. V18: research/remura-roadmap-v18-contributors-server-parity-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V18-CONTRIBUTORS-SERVER-PARITY.md, commit 73339cf85b9361ea578e7721803a717add300cbf.

## Verifica ufficiale dei limiti Free, indipendente da REMURA
Consultate pagine Cloudflare ufficiali aggiornate a ottobre/novembre 2026:
- D1 Workers Free: **5.000.000 RIGHE lette/UTC day**, **100.000 RIGHE scritte/UTC day** (i database D1 sono 10 al massimo; spazio totale account 5 GB; cap **500 MB per DB Free**). Fonti: https://developers.cloudflare.com/d1/platform/pricing/ ; https://developers.cloudflare.com/d1/platform/limits/ . Le scritture di indici possono consumare piu' righe. Il consumo D1 si ripristina alle 00:00 UTC.
- Workers Free: **100.000 richieste/UTC day**, **10 ms CPU per invocazione**, **50 subrequest per richiesta**. Fonte: https://developers.cloudflare.com/workers/platform/limits/ .
- Zero Trust / Access Free: supporto per team fino a 50 utenti, ma occorre verificare dal proprio dashboard posti acquistati/assegnati e usati; l'identita' che si autentica consuma un posto. Fonte: https://www.cloudflare.com/it-it/products/access/ e https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/ .
- **Revoca:** 'Remove users' libera il posto ma NON nega di per se' accessi futuri; 'Revoke sessions' termina sessioni ma da solo NON impedisce nuovo login se Access policy resta permissiva. REMURA richiede revoca D1 + esclusione dalle policy + invalidazione sessione + test effettivo di diniego. Fonte ufficiale Cloudflare Seat Management.
- **Stato reale account personale NON CONOSCIUTO:** nessuna lettura D1 GraphQL, nessuna metrica live, nessuna nuova autorizzazione spesa, nessuna creazione/attivazione. Non confondere la quota del piano (confermata) con la quota residua sul proprio account (ignota). Verifica manuale future tramite dashboard read-only, senza query SQL; consumo della sola dashboard da confermare.

## Nuovo sviluppo in GitHub — gate no-network, fa risparmiare
Branch: **research/contributors-v097-free-pilot-readiness-20261122**.
- `research/contributors/contributors_free_readiness_v097_lab.mjs` implementa report(evidence,now) senza fetch, Secret, CLI Cloudflare o scrittura. Valida schema, giorno UTC e freschezza inferiore 24h, piano FREE, utenti Access prenotati per 1-2 collaboratori, Worker requests e CPU, D1 letture/scritture/storage/database count, prova di approvazione owner, revoca D1 e Access, ruoli server, catalogo, JWT Access, persistent receipt/no-blind-retry, sessioni Safari dei due ruoli, billing Free senza paid add-on.
- **Riserva prudenziale REMURA al 75% dei consumi massimi Cloudflare** per richieste Worker, righe D1 e spazio: margine operativo 25% come regola di progetto, non Cloudflare. CPU 10ms va provata anche operativamente: la metrica p95 non garantisce il massimo singolo.
- **Ottimizzazione risparmio v0.97:** puo' valutare un database D1 esistente isolato, invece di crearne uno a forza: l'input anonimo `existingDatabaseIndex` deve riferirsi a uno dei database con dimensioni confermate; controlla che dimensione attuale piu' storage stimato del pilot rimanga sotto il 75% dei 500 MB Free per DB. Se il target manca o e' troppo grande, NO-GO. Evita di mischiare dati reali e fixture.
- `research/contributors/REMURA-CONTRIBUTORS-V097-EVIDENCE-BLANK.json`: manifest senza nomi/email/account ID, cifre o token: tutti i consumi nulli (UNKNOWN, non zero) e attestazioni false. Il risultato attuale e' NO-GO.
- `research/contributors/test_contributors_free_readiness_v097_lab.mjs`: 21 nuovi test mirati: limiti documentati, status NO-GO quando vuoto, falsi goLive sempre respinti anche con evidenza ipotetica GREEN, UTC day, Access seats, CPU, D1 righe/storage/totali/per-DB, riuso D1, Access e D1 revocation, forecast, billing zero.
- `research/contributors/README-CONTRIBUTORS-V097-FREE-PILOT-GATE.md`: runbook semplice da iPhone per vedere nel dashboard Cloudflare senza chiamate API, SQL o click che modifichino account.
- `.github/workflows/remura-contributors-v097-free-readiness.yml`: CI solo branch/path, Node 22, 4min max, permissions contents read, non usa Secret/Cloudflare.
- **Collaudo definitivo** [GitHub Actions run 45073929053](https://github.com/mirkoworz/remura/actions/runs/45073929053), SUCCESS sul commit e1f1adbddd4c2f145172955e59cfa262d450b66d. Log realmente letti: `# tests 21`, `# pass 21`, `# fail 0`, `REMURA_CONTRIBUTORS_V097=21_21_FREE_GATE_PASS`. I fallimenti intermedi al commit 691c4607 e prima sono stati risolti con test che imposta davvero un forecast oltre 375MB. **Non ripetere quei test senza nuovo cambiamento.**
- Nota: nell'ultima commit del branch esiste anche solo una documentazione README; nessun cambiamento eseguibile rispetto al CI GREEN.

## Gate esplicito: NON equivale a autorizzazione
Il codice `report()` restituisce sempre `goLive:false` e `deployAuthorized:false`, anche se un manifest di prova ha tutti i campi true. La valutazione `EVIDENCE_READY_FOR_INDEPENDENT_REVIEW` NON verifica l'autenticita' di un account, NON attesta un deploy Safari e NON concede nuovi permessi. In produzione e' obbligatorio un consenso esplicito separato, identity/Access + roles D1 + revoca testata con utenti reali e staging privato. Il codice LAB non deve diventare un pulsante di deploy.

## Stato progetto invariato
- Main nella sessione V18 era SHA `9758bdcbf1c55b1c63ad66bcf6716872cdc906e4`. Non e' stato modificato in V19: solo branch separato e roadmap.
- PR #105 Contributors e #106 TradingView aperte DRAFT e non mergiate al V18.
- Contributors v0.96 privato con preflight + bundle in branch `research/contributors-v096-protected-preflight-20261122`, HEAD `f3aea5137dcfcb9b911b4a022a57f816f4d283a5`, 20/20 verde; UI iPhone bozza v0.96 in `feature/contributors-v096-server-contract-iphone-20261122`, commit `b98d574b75918b0188bedfc4457ae8540ff9c459`, 11/11 verde. Non ripetere suites vecchie.
- Shark Cockpit v1.68 LAB, 14 contratti futures CFTC, 6 movers (stesso martedi'), favoriti e storico fino a 12 report, anatomy long/short. Utente conferma Safari, ma aggiornamenti CFTC reali e first-seen indipendenti non sono dimostrati; CVD edge/alpha ancora no-go.
- TradingView CVD TEST holdout V2 inizia 23/11/2026 00:00 UTC (01:00 CET); nessun worker/receiver live attestato da V19, e non retrodatare mai i dati.
- Mac Codex: Oracle collector, v1.65 staged, backup/antirollback ed Experience splash Toro-Orso 3D restano al loro filone; Ampere Radar Milano Free separato.
- Cloudflare D1 test GraphQL precedentemente autorizzati una tantum erano esauriti, nessun altro chiamato in V19; Access seats uso reale ancora sconosciuto.

## Priorita' V20 pratica
1. **Solo con autorizzazione dedicata**: verifica account Cloudflare in sola lettura di Metrics Workers, D1 Row Metrics + DB sizes, Access seats/free plan e Billing. Preferire dashboard e conti aggregati per non sprecare chiamate GraphQL e non esporre Secret. Il gate continua NO-GO fino alle prove reali.
2. Staging privato isolato con riuso del LAB se fisicamente isolato e attestato, altrimenti uno nuovo (solo se Free, con consenso): Access JWT lato Worker, catalogo verificato, OWNER + 1–2 contributors, ruoli e proprietà lato D1, ricevute durevoli, divieto di reinvii ciechi e test di revoca con sessioni Safari reali.
3. Registrare il primo accesso e la prima ricevuta di proposta solo una volta con token autorizzato, e verificarli con snapshot; non pubblicare dati privati su raw.githack o sul repo pubblico.
4. Solo dopo tutto questo valutare merge/deploy controllato del portale e sincronizzazione con REMURA Experience/Collector. Nessuna spesa senza esplicito consenso.
5. Non ripetere test, check o backup gia' conclusi; incrementare numero versione e timestamp Europe/Rome su ogni pagina reale modificata; non confondere LAB con produzione.

**RISULTATO:** V19 aggiunge un gate gratuito documentato e 21 test GREEN, chiarisce limiti Free e revoca, evita DB aggiuntivo non necessario; il pilot reale rimane NO-GO finche' account/identita'/budget non attestati.
