# REMURA — TEST WEBHOOK RELEASE GATE v0.8.32 (BOOTSTRAP LIVE; ROLLBACK TEST MANUALE PRONTO)
**Aggiornamento: 13/11/2026, ore 21:09 CET**  
**Bootstrap inerte TEST realmente distribuito, gateway completo NON distribuito. PR #102 OPEN/DRAFT; Worker Production v0.8.5 non modificato.**

## Checkpoint v0.8.32 — rollback TEST preparato, non eseguito
- Workflow `.github/workflows/remura-tv-rollback-test-manual.yml` su `main`: azione esclusivamente manuale, owner `mirkoworz`, branch main, conferma a scelta `ROLLBACK_TEST_TO_BOOTSTRAP_OFF`, codice pinned `ac68fabf95a26ec9c62f4e2cd270661c32622578`. Concurrency serializzata con precedente workflow bootstrap. Creato e non avviato; **nessun deploy su Cloudflare in questa fase**.
- Preflight `worker_rollback_preflight_v1.py` usa due GET autenticati per riconoscere bootstrap senza binding o gateway TEST con D1 TEST, limiter e `INGEST_ENABLED=false`, rifiutando configurazioni diverse. [GitHub CI #43498033946](https://github.com/mirkoworz/remura/actions/runs/43498033946) verde, 6 test mock aggiunti. Non è prova di rollback live.
- Se autorizzato in futuro, il workflow distribuisce solo bootstrap inerte con `preview_urls:false` e richiede verifica metadata a zero binding. Il rollback **non supporta ancora** uno stato `INGEST_ENABLED=true` con Secret TEST: dovrà essere ampliato e testato **prima** di qualunque webhook reale e fase di emergenza.
- Prossima fase: preparare il separato deploy gateway TEST `INGEST_ENABLED=false` e verificarne la compatibilità live del rate limiter, poi consenso ulteriore per una singola prova TradingView. Non eseguire da solo né `main` né PR.
  
## Checkpoint v0.8.31 — verifica LIVE postdeploy + preparazione gateway OFF
- **Control-plane reale**: [GitHub run #43496120098](https://github.com/mirkoworz/remura/actions/runs/43496120098) SUCCESS, GET API della versione esatta del bootstrap `f5a43b49-f07f-404b-a9dd-4606a22afa3c`, zero binding sia nella versione sia nelle impostazioni Worker TEST; **NON** prova 100% del traffico o `/health` pubblico. Nessun webhook.
- **Futuro gateway TEST**: l'esempio `wrangler.webhook-test.EXAMPLE.json` è ancora intenzionalmente **non deployabile** (UUID e namespace segnaposto). Ora richiede `preview_urls:false`, `workers_dev:true`, `INGEST_ENABLED:false`, binding **solo D1 TEST** e limiter 20/60. [Wrangler dry-run #43496797754](https://github.com/mirkoworz/remura/actions/runs/43496797754) SUCCESS; nessun deploy.
- **Autenticazione D1 reale in sola lettura**: `gateway_off_candidate_v1.py` usa i token esistenti per controllare UUID distinti UE MAIN/TEST e generare in memoria un candidato coerente. [Run #43496787646](https://github.com/mirkoworz/remura/actions/runs/43496787646) SUCCESS, 10 mock test PASS, nessun UUID, namespace o Secret nei log; il namespace proposto **non è stato verificato contro altri limiter dell'account**.
- **Rollback**: `off_gateway_rollback_guard_v1.py` vieta main D1, ingest ON, Secrets inattesi, namespace differente e binding non conosciuti; 12 test mock PASS [CI #43497283571](https://github.com/mirkoworz/remura/actions/runs/43497283571). È **soltanto il guard offline**: prima di distribuire gateway OFF servirà un vero workflow manuale di rollback con preflight autenticato e codice bootstrap pinned. Il vecchio workflow `bootstrap-test-only-manual.yml` rifiuterebbe un Worker che ha binding D1/limiter: NON usarlo come rollback senza aggiornamento.
- **Consensi da mantenere separati**: (i) eventuale distribuzione gateway TEST `INGEST_ENABLED=false` con D1 TEST/limiter e rollback pronto; (ii) eventuale inserimento Secret TEST + `INGEST_ENABLED=true` + prova webhook reale da TradingView. Non autorizzare (ii) implicitamente tramite (i).
- **Rischi irrisolti**: CPU Workers Free 10 ms/invocazione, traffico anonimo, disponibilità/costo effettivo limiter sul Free e quota aggregata account; rate limit per-location approssimativo non sostituisce protezione edge. Nessun dato mercato vero ancora raccolto da questa pipeline.
- Documentazione ufficiale: https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/ , https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/ , https://developers.cloudflare.com/workers/authorization/workers/ .

## Checkpoint v0.8.30 — bootstrap LIVE riuscito (13/11/2026 ore 20:45 CET)
- [GitHub run #43495068875](https://github.com/mirkoworz/remura/actions/runs/43495068875) SUCCESS, con input manuale confermato, controlli offline, GET autenticato che ha letto **zero binding del TEST prima del deploy**, dry-run e successivo deploy Wrangler esclusivamente `remura-tv-webhook-test` con sorgente inerte pinned `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`.
- Cloudflare `Uploaded` e `Deployed` realmente riusciti; ID versione `f5a43b49-f07f-404b-a9dd-4606a22afa3c`. URL workers.dev attivo `https://remura-tv-webhook-test.mirkoworz.workers.dev`. Test codice: `GET /health` risponde `accepting:false`, tutte le altre richieste incluse `POST /ingest` HTTP 503; **GET live esterno /health non ancora confermato separatamente**.
- Avviso Wrangler: `preview_urls` non specificato → preview URL abilitati automaticamente. Valutare disattivazione per prossimo deploy e verificare prima che la configurazione del Worker TEST sia separata. **Non è autorizzata ingestione, collegamento D1 o attivazione TradingView**.
- Il token dedicato ha superato lettura metadata e deploy del Worker selezionato, senza evidenza di privilegi sul Worker Production; il perimetro per-worker deriva dagli screenshot dei permessi Cloudflare `Specified Workers`, non da tentativi distruttivi su altri Worker.
- **Due gate rimasti distinti:** (1) installare eventualmente gateway TEST `INGEST_ENABLED=false` con D1 TEST, Secret TEST e limiter dopo nuovo consenso; (2) abilitare temporaneamente ingest + alert TradingView per primo evento dopo altra autorizzazione e protezioni complete. Monitorare Free. Non cancellare dati TEST.

## Checkpoint bootstrap a privilegi minimi — 13/11/2026, ore 16:33 CET
- **Nuova informazione documentale Cloudflare (Sep 2026):** la creazione di un Worker richiede ruolo `Admin` di prodotto Workers. Un token `Editor` limitato a **un singolo Worker** può fare deploy soltanto se quel Worker **esiste già**: https://developers.cloudflare.com/workers/authorization/workers/. NON autorizzare un token Workers Admin product-wide per automatizzare l'innocuo primo bootstrap del TEST.
- **Nuova sequenza raccomandata:** con consenso specifico, proprietario crea **una volta** dalla dashboard il solo `remura-tv-webhook-test` caricando `gateway-lab/bootstrap_test_worker.mjs`, che NON ha DB/Secret/limiter né gestione webhook: `GET /health` indica `accepting:false`, il resto restituisce HTTP 503. Solo dopo il Worker esistente, valutare un token dedicato con ruolo `Editor` limitato esattamente a `remura-tv-webhook-test`. Non assegnare privilegi al Worker Production `remura-tv-ingest-lab`.
- **CI v0.8.25:** [Actions #43453466241](https://github.com/mirkoworz/remura/actions/runs/43453466241) SUCCESS: test Node di comportamento non operativo e compilazione Wrangler `deploy --dry-run` con configurazione sintetica `workers_dev:false`, senza login né API Cloudflare. Questo NON dimostra lo stato live, i costi CPU o l'esistenza del Worker TEST.
- **Gate invariati:** vero binding `TELEMETRY_DB → remura-tv-lab-test`, limite `INGEST_RATE_LIMITER` ed effettiva disponibilità Free, Secret TEST distinto, `INGEST_ENABLED=false` nel gateway completo. **Nessuno** di questi va predisposto collegando il database principale per il bootstrap.
- La creazione del Worker in dashboard è una modifica reale Cloudflare e richiede consenso nuovo; successiva sostituzione del codice con gateway completo e attivazione alert sono **altre** decisioni separate. Non richiedere ancora credenziali o screenshot dei vecchi controlli.
- Procedura completa: [BOOTSTRAP-TEST-WORKER-v0.8.25.md](./BOOTSTRAP-TEST-WORKER-v0.8.25.md).

## Checkpoint piano Workers Free — 13/11/2026, ore 15:55 CET
- Screenshot reale dell'utente Cloudflare → **Workers plans**: `Free $0` indicato come **Current plan**, Paid `$5/month + usage` disponibile ma non selezionato. **Verificato l'effettivo piano Workers Free** per l'account alla data del controllo; non richiedere di nuovo uno screenshot del piano.
- Per i soli Workers Free: 100.000 richieste/giorno/account, 10 ms CPU per richiesta, massimo 100 Worker (documentazione ufficiale 2026). La conferma Workers Free **non prova l'assenza di altri prodotti a pagamento né una fattura a zero**. Restano non accertati CPU reale, consumo aggregato di tutti i Worker, eventuali fatture e binding limiter del Worker TEST.
- Modificare solo il piano Workers è operazione da non fare: **NO upgrade** senza nuova richiesta e consenso utente. Nessuna necessità attuale di passare a Paid per una compilazione TEST o piccoli volumi teorici.
- Il rate limiter per Workers è approssimativo, attivo solo dopo l'arrivo della richiesta al codice, e non protegge da abuso anonimo sul conteggio account; la documentazione non dimostra né quota né disponibilità reale del binding per questo nuovo Worker. Serve preflight prima di abilitarne l'ingestione.
- **Prossimo gate indipendente**: preparare credenziali minime Workers *per il solo Worker TEST* e binding confermati senza sostituire quelli già configurati del Worker Production. Il primo deploy è autorizzabile **solo OFF**, separatamente dal consenso a eventuali webhook TradingView reali.

## Nuova prova non distruttiva (v0.8.23)
- [Wrangler compile-only #43443677850](https://github.com/mirkoworz/remura/actions/runs/43443677850) SUCCESS: 5 test isolati più compilazione reale `wrangler@4.157.0 deploy --dry-run`; pacchetto 11,76 KiB (gzip 4,06 KiB). Non è avvenuto upload né deploy. Config TEST temporanea con D1 e rate limiter sintetici; account, Secrets, Worker Production e dati D1 non toccati.
- Un primo test di eccezione del manifest aveva fallito e viene registrato correttamente; fix `1c6a783f` ha reso la prova fail-closed. **Questo non è un preflight finale di autorizzazione al deploy**.
- Numero teorico di heartbeat EURUSD M5 = 288/24 h, pari a 0,288% delle 100k richieste giornaliere Free se fosse l'unico utilizzo. Non compresi ritrasmissioni, altri Worker e richieste anonime. **Piano Cloudflare, CPU e fatture effettive NON ancora verificati.**
- Al prossimo rilascio reale, NON caricare la configurazione sintetica del dry-run: occorre generare separatamente il file di Worker TEST da identità D1 verificata nell'account, Secret separato, limiter univoco e autorizzazione esplicita. **Nessun token dev'essere incollato in chat.**

## Evidenze accertate
- Cloudflare Worker **Production** `remura-tv-ingest-lab` è legato a D1 **PRINCIPALE**: `TELEMETRY_DB → remura-tv-lab`; confermato da screenshot dell'utente. **Mai usarlo come banco di prova**.
- Cloudflare D1 inventory GET autenticato [Actions #43441281362](https://github.com/mirkoworz/remura/actions/runs/43441281362) **SUCCESS**: D1 `remura-tv-lab` e `remura-tv-lab-test` con UUID distinti e giurisdizione UE. La lettura NON ha stampato/conservato UUID; 12 test offline PASS. La disponibilità del DB TEST non equivale a permesso di deploy Worker.
- Manifest `wrangler.webhook-test.EXAMPLE.json` intenzionalmente non distribuibile: Worker name `remura-tv-webhook-test`, solo `TELEMETRY_DB → remura-tv-lab-test`, `INGEST_ENABLED=false`, UUID e namespace limiter segnaposto. È una **bozza**, non la configurazione Cloudflare.
- Sorgente gateway GitHub v0.8.6: se flag OFF o manca limiter/D1/secret, l'endpoint ingest risponde **503 disabled**; test Node con FakeD1; non è una verifica del Worker distribuito. `test_d1_test_target_preflight_v1.py` controlla identity e no-POST; `worker.test.mjs` simula kill-switch ON → OFF, senza cancellare alcun record TEST.
- API Cloudflare Worker Settings con token D1 READ ha già restituito `403` sul control-plane: non riutilizzare per tentativi identici e non attribuire questa causa al BIC del sito pubblico. Non è attualmente disponibile un token autorizzato al deploy.
- Cloudflare Free **limiti pubblicati**: Workers **100.000 richieste/giorno/account**, **10 ms CPU/invocazione**; D1 Free **10 DB/account, 500 MB/DB, 5 GB/account**. **Workers Free confermato da screenshot del proprietario 13/11/2026**; restano non verificati fatture/account billing aggregato e CPU per invocazione sul nuovo Worker. Aggiungere un Worker non prova che il costo sarà zero, e la quota account è condivisa da altri servizi.
- Rate Limiting binding Cloudflare: `namespace_id` deve essere una stringa di intero positivo univoco per l'account; `simple.limit=20`, `simple.period=60`; quota **approssimativa per Cloudflare location**, non un tetto globale né protezione di richieste anonime che arrivano prima del codice. Namespace reale e disponibilità/costi del binding **NON confermati**.

## Gate necessari, nell'ordine
1. **GO/NO-GO costo + accessi**: piano Workers Free già verificato. Prima del deploy completo, scegliere il percorso a minimo privilegio: **bootstrap manuale owner-only del Worker TEST inerte** (dopo consenso), poi token `Editor` limitato al **solo Worker TEST già creato**. Non usare product-level Workers Admin nella CI; non riutilizzare i token D1/Analytics per fare deploy. Restano da verificare costi/limiti delle integrazioni, billing e CPU reali. Nessun automatismo deploy sul ramo DRAFT.
2. **Binding preparato fuori dal repository**: ottenere soltanto da Cloudflare il vero UUID D1 TEST, verificarne corrispondenza con il nome TEST, configurare `INGEST_RATE_LIMITER` con namespace univoco, e generare segreto webhook **separato** dal Worker Production. Non aggiungere a GitHub file con segreti, token in URL, UUID sensibili o output API integrali. L'esempio con placeholder non va caricato.
3. **Primo deploy richiede consenso ESPRESSO distinto**: nuovo Worker `remura-tv-webhook-test` con `INGEST_ENABLED=false`, nessuna route custom, binding a `remura-tv-lab-test`, MAI toccare `remura-tv-ingest-lab`. Non abilitare TradingView alert. Verificare via Cloudflare Dashboard versione, binding, limiter e l'endpoint `/health` **da un canale affidabile**: `accepting:false`. Una risposta 403 da GitHub verso `workers.dev` resta inconcludente, non ripetere uguale.
4. **Secondo consenso per invio LIVE**: solo dopo identità e limiti confermati, abilitare temporaneamente ingest sul Worker TEST e configurare alert nel Pine TradingView, assicurando token fuori dal codice (niente log/chats). Permettere 1–pochi eventi pilota da TradingView, mai esecuzioni di ordini. Accertare esito consegna alert, presenza `BAR_EVENT/HEARTBEAT` e `received_at_ms` in D1 TEST con query read-only, latenza, errori Workers/CPU e rispetto del budget. Se Cloudflare applica BIC o protezioni edge che bloccano TradingView, **STOP**; non allargare globalmente Access/WAF per aggirare.
5. **Rollback**: portare `INGEST_ENABLED=false` **sul solo Worker TEST**, confermare `/health.accepting=false` o accertare dalla Dashboard flag OFF + versione deployed; invii successivi devono tornare `503 disabled` e nuove scritture D1 TEST devono cessare. **Non** eliminare il record sintetico già presente o i nuovi eventi di prova senza autorizzazione separata. Se necessario, revocare **solo** segreto di TEST. Eliminazione del Worker TEST, se desiderata, è operazione separata. Non toccare il Worker Production.
6. **Evidenza prima della raccolta prospettica**: il solo successo di un POST non rende validi i proxy TradingView come esecuzioni CME e non produce segnali profittevoli. L'attivazione stabile e i collegamenti ai filoni B/C richiedono un checkpoint separato.

## Stati e sicurezza del rilascio
| Voce | Stato attuale |
| --- | --- |
| D1 TEST identità distinta | VERIFICATO con GET API |
| Sorgente/test di rollback | SOLO SIMULAZIONE OFFLINE |
| Manifest deployabile reale | NO — PLACEHOLDER |
| Rate limiter account | NON VERIFICATO |
| Secret per Worker TEST | NON CREATO |
| Worker bootstrap inerte | COMPILATO E TESTATO OFFLINE, NON DEPLOYATO |
| Permesso Worker EDIT/DEPLOY | NON DISPONIBILE IN QUESTA CHAT; scoped Editor possibile dopo creazione TEST |
| Primo deploy e primo webhook live | NON AUTORIZZATI |
| Piano Workers Free | CONFERMATO con screenshot dashboard 13/11/2026 |
| Fatturazione aggregata account/CPU Worker TEST | NON VERIFICATE |
| Trading automatico | NON AUTORIZZATO |

**STOP GUARANTEE**: nessun GitHub Actions della PR #102 può effettuare deploy, variare `INGEST_ENABLED` su Cloudflare o spedire webhook con gli attuali script di questo filone.

### Fonti tecniche Cloudflare, consultate 13/11/2026
- [Workers Free limits](https://developers.cloudflare.com/workers/platform/limits/)
- [D1 Free limits](https://developers.cloudflare.com/d1/platform/limits/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [Workers Rate Limiting binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)
- [Wrangler D1 bindings](https://developers.cloudflare.com/workers/wrangler/configuration/)
