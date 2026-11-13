# REMURA TradingView — ROADMAP GATEWAY ONLINE v0.8.29-doc (Worker Production noto v0.8.5, gateway sorgente v0.8.6 offline)
**Aggiornamento roadmap: 13/11/2026, ore 20:43 CET — primo dispatch SKIPPED, conferma in UI resa selezionabile**
**PR #102 DRAFT/OPEN — nessun merge, alert TradingView OFF, nessun ordine.**

## CHECKPOINT v0.8.29 — PRIMO BOOTSTRAP DISPATCH SKIPPED, NESSUN DEPLOY — 13/11/2026, ore 20:43 CET
- [x] L'utente ha avviato manualmente il workflow `REMURA TEST Worker BOOTSTRAP (manual only)` su `main`; screenshot mobile scattato mentre risultava `Queued`. La verifica GitHub successiva [run #43494222257](https://github.com/mirkoworz/remura/actions/runs/43494222257) indica **`completed/skipped`** con job `bootstrap-existing-test-only` **SKIPPED** e **nessuno step eseguito**. Nessun deploy, nessun POST, nessun cambiamento Worker o database.
- [x] Il job ha una condizione preventiva con repository, ref main, actor `mirkoworz` e stringa esatta input `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Repository/actor/branch risultano coerenti nell'esecuzione; il contenuto dell'input non è disponibile nel run e **la causa esatta non è dimostrata**. Il campo compilato a mano potrebbe non aver superato il confronto; classificazione `INPUT_SUSPECTED_NOT_PROVEN`, non errore di Cloudflare né del token.
- [x] Corretto **solo il workflow su `main`** `.github/workflows/remura-tv-bootstrap-test-only-manual.yml` (commit `1892085aaab994bf27fcc77593f64c03580daabc`): input `confirmation` è ora `type: choice` con una sola opzione precompilata `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Rimangono invariati controllo manuale owner, `contents:read`, fonte pinned SHA `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`, test offline, GET-only preflight e **solo bootstrap inerte** del Worker TEST. Nessun altro job di rilascio è stato avviato.
- [ ] Occorre **un nuovo dispatch esplicito dell'utente** dalla pagina GitHub Actions selezionando `main` e l'unica opzione; non tentare di rilanciare il job skipped senza nuovo input. Dopo il run verificare sia i test sia il vero deploy e stato remoto `/health`, evitando la vecchia sonda GitHub 403 identica. **Non è stato autorizzato gateway completo, webhook, ingest ON né utilizzo D1**.
- [x] Secret GitHub `REMURA_CF_TEST_WORKER_EDITOR_TOKEN` già verificato tramite run GET-only #43493628453; non ricrearlo, non richiedere screenshot/token. PR #102 resta OPEN/DRAFT, main monitor budget invariato e Worker Production `remura-tv-ingest-lab` non toccato.

## CHECKPOINT v0.8.28 — TOKEN EDITOR WORKER TEST E METADATA LIVE CONFERMATI — 13/11/2026, ore 20:36 CET
- [x] L'utente ha configurato **Account API Token** `REMURA-TV-TEST-EDITOR`, scope `Specified Workers` → **esclusivamente `remura-tv-webhook-test`**, ruolo `Individual Workers → Editor`, `Admin` disattivato, come screenshot già verificati. Token registrato dall'utente in **GitHub Actions Secret `REMURA_CF_TEST_WORKER_EDITOR_TOKEN`**; nessun valore in chat, documenti o log. Non serve crearne altri né ripetere screenshot.
- [x] Per accertare il funzionamento senza concedere nuova autorità, creato il solo workflow read-only `.github/workflows/remura-tv-test-worker-editor-readonly.yml` su `main`, commit `87f496a4f3e729d96c89f43d5c4198bda1100b1f`: trigger automatico esclusivamente alla **creazione/modifica di questo stesso file** più `workflow_dispatch`, `contents:read`, checkout del **pin `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`**, test offline del guard, poi **un GET autenticato** `/accounts/{id}/workers/scripts/remura-tv-webhook-test/settings`. Nessun deploy, nessun POST, nessuna query D1, nessuna interazione con Production.
- [x] [GitHub run #43493628453](https://github.com/mirkoworz/remura/actions/runs/43493628453) **SUCCESS**: 9 test di sicurezza offline superati; `REMURA_TEST_TOKEN=SECRET_PRESENT_NOT_DISCLOSED`; risposta API sanitizzata `REMURA_BOOTSTRAP_PREFLIGHT=EXISTING_TEST_ONLY_NO_BINDINGS` e `WORKER=remura-tv-webhook-test; BINDINGS=NONE; DEPLOY=NOT_YET`. **LIVE metadata verificati**: Worker TEST esiste ed è privo di binding al momento della GET. Non equivale a prova del codice deployato (Hello World resta ultimo codice dichiarato dall'utente), del routing workers.dev, né a verifica che il token possa scrivere altri Worker; quest'ultima limitazione deriva dalla policy UI visibile.
- [x] Il workflow già preparato `.github/workflows/remura-tv-bootstrap-test-only-manual.yml` resta **non eseguito** e utilizzabile soltanto tramite `workflow_dispatch` su main con stringa esatta `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY` e controllo owner. Conterrà un deploy del SOLO codice `bootstrap_test_worker.mjs` inerte, senza DB/secrets e con `GET /health.accepting=false`, ma richiede **ulteriore conferma esplicita dell'utente prima dell'esecuzione**. Nessun webhook TradingView ancora autorizzato.
- [ ] **Prossimo passo**: consenso distinta sostituzione Hello World con bootstrap inerte via workflow manuale owner-only, poi verificare codice effettivo e `/health` con canale affidabile (precedente sonda pubblica GitHub 403 inconcludente da non ripetere tale e quale). Nessuna attivazione ingest né collegamento al DB principale.
- [x] `main` monitor budget v0.8.14 non modificato, filoni A/B/C intatti, PR #102 DRAFT/OPEN senza merge, Worker Production `remura-tv-ingest-lab` non toccato, Free Workers $0 e D1 EU checkpoint acquisiti.

## CHECKPOINT v0.8.27 — CREAZIONE TEST OWNER E PREPARAZIONE GITHUB EDITOR SCOPED — 13/11/2026, ore 18:35 CET
- [x] L'utente ha confermato **«creato»** dopo la procedura `Start with Hello World → Deploy` per `remura-tv-webhook-test`. È una **dichiarazione del proprietario**; codice effettivamente deployato, nome finale, binding e Access **non ancora letti da API autorizzata**. Si presume solo Hello World innocuo, **non** il bootstrap sicuro già verificato in offline. Non richiedere di creare il Worker nuovamente.
- [x] Su documentazione Cloudflare del 13/11/2026 (ruoli aggiornati 15/09/2026), la policy API `Workers: Editor` limitata a **Specified Workers/Individual Workers → solo `remura-tv-webhook-test`** può aggiornare Worker esistente, ma non crearne/eliminarne altri. Percorso: **Manage Account → Account API Tokens → Create**. Fonte https://developers.cloudflare.com/workers/authorization/workers/ e https://developers.cloudflare.com/changelog/post/2026-09-15-granular-worker-permissions/ . Il token deve essere **account-owned** e non riutilizzare quelli D1/Analytics.
- [x] Nuovi `gateway-lab/bootstrap_settings_guard_v1.py` e 9 test `test_bootstrap_settings_guard_v1.py`: preflight esclusivamente `GET` API settings sul solo Worker TEST con nome fissato, richiede `bindings=[]`, errore fail-closed se sconosciuti/assenti, nessun valore o API response nei log. [CI #43473684646](https://github.com/mirkoworz/remura/actions/runs/43473684646) **SUCCESS** offline. Il preflight LIVE non è stato eseguito: **non esiste ancora il nuovo token in GitHub**.
- [x] Creato SU `main`, isolato dagli altri filoni, il workflow `.github/workflows/remura-tv-bootstrap-test-only-manual.yml`, commit `f89ce27`, **solo `workflow_dispatch` (NO cron, push o PR)**, permessi GitHub `contents:read`, consentito solo a owner `mirkoworz`, input esatto `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Checkout codice **PINNED SHA `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`**; prima esegue test Node e Python; poi GET-only metadata guard; compila il bootstrap inerte senza D1, Secrets o limiter ed esegue deploy soltanto dopo azione manuale owner. Nessun deploy avviato.
- [ ] **Unico setup manuale necessario prima della successiva esecuzione:** creare account-owned Cloudflare API Token `Workers: Editor` scope **Specified Workers/Individual Worker** con l'unico Worker `remura-tv-webhook-test`; nessun permission aggiuntivo product-wide o D1 Write, no Global API Key. Conservare token **esclusivamente** in GitHub Actions secret `REMURA_CF_TEST_WORKER_EDITOR_TOKEN`, mai in chat/screenshot; GitHub `REMURA_CF_ACCOUNT_ID` già presente e NON va rifatto. Se UI mostra solo **All Workers** o concede Admin → STOP, chiedere istruzioni senza scegliere scope eccessivi.
- [ ] Dopo token GitHub creato, verificare scope e invocare manualmente (su `main`) solo workflow bootstrap, con conferma esplicita del proprietario: prima `GET settings` e rifiuto dei binding inattesi, poi deploy codice inerte. Non autorizzare ancora gateway completo, ingest, webhook o SQL D1.
- [x] `main` daily budget v0.8.14 immutato, PR #102 OPEN/DRAFT senza merge, Worker Production `remura-tv-ingest-lab` con D1 principale non modificato, non introdotti costi Paid o ordini. Non dichiarare che il Worker TEST sia già isolato in runtime finché non arriva il preflight LIVE.

## CHECKPOINT v0.8.26 — AUTORIZZAZIONE CREAZIONE TEST, IN ATTESA DELLA UI OWNER — 13/11/2026, ore 17:27 CET
- [x] L'utente ha risposto **«Sì»** alla domanda esplicita di autorizzazione della **sola creazione iniziale** del Worker `remura-tv-webhook-test` con bootstrap inerte, senza D1/Secrets/limiter e senza webhook. Consenso limitato esattamente a questa fase, non al deploy del gateway completo, ingest ON, modifica di `remura-tv-ingest-lab`, trasferimento dati né creazione di token.
- [x] Ricontrollato stato PR #102 OPEN/DRAFT e codice bootstrap `gateway-lab/bootstrap_test_worker.mjs` già validato in precedenza. Documentazione Cloudflare dashboard conferma il percorso Workers & Pages → Create application → Create Worker: https://developers.cloudflare.com/learning-paths/workers/get-started/first-worker/ . L'interfaccia può creare prima un template di esempio; NON dichiarare che l'esempio iniziale sia il bootstrap approvato. Se non è possibile cambiare il codice prima del deploy, guidare l'owner a sostituirlo immediatamente e verificare che nessun POST sia accettato.
- [ ] **Azione proprietario da confermare**: creare solo `remura-tv-webhook-test` nella Dashboard Cloudflare, senza collegare GitHub, D1, Secrets, custom routes, ingest o altri servizi. Preferire il codice inerte al primo deploy se l'interfaccia lo consente; registrare screenshot dopo il salvataggio, senza credenziali. La creazione non è stata eseguita da questa sessione, che dispone di accesso GitHub ma non di scrittura Cloudflare.
- [ ] Solo dopo verifica dell'identità del nuovo Worker esistente: considerare token per-Worker Editor e rate limiter TEST con nuova autorizzazione specifica. **Non confondere il consenso di creazione col permesso di attivare webhook o dati live**.
- [x] Piano Workers Free e D1 distinti acquisiti, il monitor `main` v0.8.14 non modificato, PR #102 sempre DRAFT, nessun deploy/merge effettuato in questo aggiornamento.

## CHECKPOINT v0.8.25 — WORKER BOOTSTRAP INERTE E RUOLI GRANULARI — 13/11/2026, ore 16:34 CET
- [x] Partito solo dal checkpoint v0.8.24 già verificato e PR #102 **OPEN/DRAFT**; nessun vecchio audit o 403 ripetuto; `main` monitor giornaliero v0.8.14, Workers Free $0 e due D1 UE restano checkpoint acquisiti.
- [x] Verificata documentazione Cloudflare aggiornata 13/11/2026: il modello 2026 `Workers: Editor` consente deploy **solo Worker già esistente**; `Workers: Admin` a livello prodotto è necessario per **creare** un Worker via API/Wrangler e non può essere vincolato a un Worker inesistente. Ruoli per-Worker disponibili e applicabili a token/membri. **Cambiata la strategia**: preferire un bootstrap iniziale dell'unico Worker TEST tramite il proprietario in dashboard, dopo autorizzazione, evitando token product-wide Admin nella CI. Fonte https://developers.cloudflare.com/workers/authorization/workers/.
- [x] Creato `gateway-lab/bootstrap_test_worker.mjs` v0.8.25: codice ESM indipendente, **nessun binding D1, Secret, limiter, fetch esterno o log**, GET `/health` → `bootstrap_only/accepting:false`, tutti gli altri metodi/route → `503 disabled`. Anche se l'ambiente avesse flag ON o Secrets errati, non legge env né può ingestire. Il Worker non è stato creato su Cloudflare.
- [x] `gateway-lab/bootstrap_test_worker.test.mjs`: **6 test Node offline** verificano anti-ingest, no letture env/D1, no eco di credenziali, no-store e HTTP 503. Inseriti nel workflow esistente `.github/workflows/remura-tv-telemetry-lab.yml`; [Actions #43452920303](https://github.com/mirkoworz/remura/actions/runs/43452920303) **SUCCESS** e controlli sintattici verdi.
- [x] Esteso `.github/workflows/remura-tv-wrangler-dryrun.yml`: compila con **Wrangler 4.157 `deploy --dry-run`** anche il bootstrap con configurazione temporanea `workers_dev:false`, senza D1/Secrets/limiter né credenziali Cloudflare, oltre al già validato gateway di test sintetico; [Actions #43453466241](https://github.com/mirkoworz/remura/actions/runs/43453466241) **SUCCESS**. È una prova di packaging locale, NON un deploy e non dice nulla sul runtime, routing o billing reale.
- [x] Documenti `gateway-lab/BOOTSTRAP-TEST-WORKER-v0.8.25.md` e `gateway-lab/TEST-WEBHOOK-RELEASE-GATE-v0.8.22.md` (contenuto v0.8.25) spiegano creazione owner-only, eventuale **token Editor limitato al Worker TEST esistente**, gate successivi del gateway completo OFF e webhook reale, rollback e no-cost. Nessun nuovo token creato, nessun permesso aggiunto.
- [ ] Prossimo intervento **manuale e autorizzato**: **solo** creare Worker `remura-tv-webhook-test` con bootstrap inerte e senza D1/Secrets/route, dal dashboard del proprietario. Confermare solo identità e flag spento; **non** associare `remura-tv-lab`. Dopo creazione, preparare un token `Editor` limitato a questo singolo Worker, senza condividere valore in chat; prima chiarire se la UI supporta workers.dev disattivato e limitare il traffico di prova. **Non affermare che il Worker esista già**.
- [ ] Restano da verificare in modo reale: quota rate limiter nella specifica configurazione Free, CPU e fatturazione aggregata, secret dedicato, D1 TEST binding al gateway, endpoint workers.dev (precedente 403 inconcludente), primo POST veramente TradingView e qualità dati; successivi deploy/ingest richiedono consensi distinti, niente ordini.
- [x] Production `remura-tv-ingest-lab` v0.8.5 ancora invariato (binding `TELEMETRY_DB → remura-tv-lab` da screenshot utente); D1 MAIN e record sintetico TEST non modificati; PR #102 DRAFT, nessun merge, nessuna spesa/piano Paid, nessun webhook, filoni A/B/C intatti.

## CHECKPOINT v0.8.24 — PIANO WORKERS FREE REALE VERIFICATO — 13/11/2026, ore 15:54 CET
- [x] Acquisito screenshot utente Cloudflare → Compute → **Workers plans**: piano **Free $0**, pulsante **Current plan** disattivato sulla scheda Free, piano Paid **$5/month + usage** con opzione di upgrade; **Workers Free è il piano attuale dell'account alla data dello screenshot**, non una semplice pagina prezzi generica. Nessun clic su Upgrade o Change.
- [x] **Risolto blocco precedente "piano effettivo sconosciuto"** per Workers. Rimangono non accertati eventuali altri servizi/prodotti a pagamento, situazione delle fatture, disponibilità del Rate Limiting binding nell'account, contatori CPU reali per POST, numero di Worker e consumi condivisi. NON affermare "tutti i servizi Cloudflare sono gratis" né "fattura zero" sulla base della sola schermata Workers.
- [x] Limiti da documentazione ufficiale Cloudflare Workers Free verificata al 13/11/2026: **100.000 request/giorno/account**, **10 ms CPU/invocazione**, **100 Worker/account**; condizioni diverse per risorse esterne. Sforare quote Free può produrre errori/interruzioni e non deve essere presentato come capacità illimitata. Fonte: https://developers.cloudflare.com/workers/platform/limits/ e https://developers.cloudflare.com/workers/platform/pricing/
- [x] Rate Limiting API Cloudflare documentata con `namespace_id` univoco, `simple.limit` e `simple.period`, conteggi approssimativi per località e soggetti a overshoot; la documentazione non costituisce conferma di **binding attivo/reale sul Worker TEST**. https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [x] Monitor GitHub `main` v0.8.14 con avvisi Free già attivo e verificato al checkpoint precedente; **nessuna modifica a main**, nessuna duplicazione dei monitor; la prossima esecuzione cron effettiva va verificata dopo 14/11 ore 08:37 CET.
- [ ] Prossimo gate: autorizzazione separata del primo **solo deploy TEST con ingest OFF**; prima preparare permesso Cloudflare minimo per **nuovo Worker TEST**, vero binding `TELEMETRY_DB → remura-tv-lab-test`, Rate Limiting e Secret TEST distinto, confermandoli senza usare l'URL Worker Production. Non eseguire deploy, POST reali o accendere TradingView da questa chat senza consenso separato. La compilazione `--dry-run` v0.8.23 era sintetica, non prova dei binding live.
- [x] D1 principale e record sintetico TEST immutati, Worker Production invariato, PR #102 DRAFT/OPEN, nessun segreto condiviso, nessun upgrade/servizio a pagamento, nessun trade, filoni A/B/C non toccati.

## CHECKPOINT v0.8.23 — REAL WRANGLER DRY-RUN, ZERO DEPLOY — 13/11/2026, ore 15:34 CET
- [x] Ripresa dal checkpoint v0.8.22 PR #102 DRAFT/OPEN; nessuna sonda pubblica 403 ripetuta, nessun altro test di lettura D1 reale eseguito (identità D1 TEST già verificata).
- [x] Riviste le fonti ufficiali Cloudflare aggiornate al 13/11/2026: Wrangler `deploy --dry-run` compila senza upload; Free Workers 100.000 richieste giornaliere su account e 10 ms CPU/invocazione, max 100 Workers; Rate Limiting binding `namespace_id` stringa intero univoco e `simple.period` solo 10/60, contatori approssimativi per località. **Documentazione dei limiti NON prova piano reale o costi account**. Fonti: https://developers.cloudflare.com/workers/wrangler/commands/workers/ ; https://developers.cloudflare.com/workers/platform/limits/ ; https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [x] Creato `gateway-lab/build_test_worker_dryrun_v1.py`: legge esclusivamente il manifest di esempio con ingest OFF e placeholder, ne materializza in directory temporanea una copia con UUID D1 **fittizio** `00000000-0000-4000-8000-000000000002` e limiter namespace **fittizio** `987654321`; copia sorgente Worker senza credenziali e conferma nome Worker TEST e target `remura-tv-lab-test`. **Non usare mai il bundle temporaneo per un deploy reale**. No real database UUID, no token Cloudflare, no modifiche remote. Aggiunti 5 test sintetici `test_build_test_worker_dryrun_v1.py` (blocchi Production, flag ON, secrets inline, routes, placeholders risolti parzialmente).
- [x] Workflow dedicato `.github/workflows/remura-tv-wrangler-dryrun.yml`, solo PR #102 o push branch LAB e `contents:read`, senza secrets o deploy permissions. Esegue `npx wrangler@4.157.0 deploy --dry-run --config <temporanea> --outdir <temporanea>`, compilazione reale Wrangler con `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` vuoti. Installazione via npm in runner GitHub, **non è una chiamata all'account Cloudflare**.
- [x] Un primo job dry-run [#43443229228](https://github.com/mirkoworz/remura/actions/runs/43443229228) è fallito per classe d'eccezione inattesa nel test sintetico dei placeholder; normalizzato in fail-closed con commit `1c6a783f`, senza intervento sull'ambiente remoto. **Esecuzione successiva [#43443677850](https://github.com/mirkoworz/remura/actions/runs/43443677850) SUCCESS**, 5 test nuovi PASS, manifest bloccato come esempio, Wrangler effettivamente compilato, dimensione package **11.76 KiB** (gzip **4.06 KiB**), `REMURA_WRANGLER_DRYRUN=COMPILED_SYNTHETIC_ONLY`. Il risultato è packaging locale, NON prova di runtime CPU o connettività webhook.
- [x] Stima volumetrica per **un solo pair M5**: 288 chiusure candela/24 h con heartbeat, 0,288% del limite teorico giornaliero 100k Workers Free, **esclusi** eventi aggiuntivi, ritrasmissioni, richieste anonime e altro consumo account. La richiesta regolare è sostenibile sul piano dei conteggi, ma non sono verificati CPU live, piano reale, rischi abuse e billing.
- [ ] Rimangono blocchi per il prossimo deploy: **approvazione esplicita distinta**, permesso Workers Write minimo limitato a `remura-tv-webhook-test`, namespace Rate Limiting reale, Secret separato, UUID DB TEST verificato in fase deploy, controllo dell'effettivo piano Cloudflare, rollback live non ancora eseguito. Il file `wrangler.webhook-test.EXAMPLE.json` **resta non distribuibile**, e nessuna configurazione Workers reale è stata letta/cambiata.
- [x] Worker Production `remura-tv-ingest-lab` e D1 principale non toccati, record sintetico D1 TEST preservato, main con budget v0.8.14, nessun ordine, nessun webhook reale né merge della PR #102; filoni A/B/C intatti.

## CHECKPOINT v0.8.22 — TARGET D1 TEST VERIFICATO E ROLLBACK DI LAB — 13/11/2026 ore 15:21 CET
- [x] Partito da `v0.8.21`, screenshot Worker Production già verificato `TELEMETRY_DB → remura-tv-lab`; NON ripetuti screenshot, vecchia sonda pubblica 403 o audit identici. PR #102 prima di operare DRAFT/OPEN e `main` monitor quotidiano v0.8.14 preservato.
- [x] Creato `gateway-lab/d1_test_target_preflight_v1.py`: preflight una tantum con token D1 READ e **soli 2 GET** (verify + inventario completo D1), controllo nomi, UUID distinti, giurisdizione UE e coerenza con il manifest TEST; **UUID mai scritti sul disco, nei file GitHub o nei log**. Nessuna SQL, nessuna modifica D1 o Worker, nessuna API Workers Settings ri-tentata con token D1 che aveva dato 403. Scopo nuovo: identificazione sicura del TARGET per il futuro Worker TEST, non ripetizione del budget.
- [x] `test_d1_test_target_preflight_v1.py` aggiunti **12 test sintetici** contro alias di UUID, filtro parziale/paginazione, giurisdizione errata, destinazione Production, token mancante, POST e log di dati sensibili. Workflow isolato `.github/workflows/remura-tv-test-target-preflight-readonly.yml`, con permessi `contents:read`, nessuno schedule/deploy. **Esecuzione LIVE [#43441281362](https://github.com/mirkoworz/remura/actions/runs/43441281362) SUCCESS**: `VERIFIED_TEST_DB_IDENTITY_ONLY`, `D1_MAIN_IDENTITY=VERIFIED_EU`, `D1_TEST_IDENTITY=VERIFIED_EU_DIFFERENT_FROM_MAIN`; `TEST_WORKER_MANIFEST=BLOCKED_UNRESOLVED_IDS`, `LIMITER_NAMESPACE=UNASSIGNED`, `WORKER_DEPLOY=NOT_AUTHORIZED`. Test 12/12.
- [x] Aggiunti 2 test Node a `gateway-lab/worker.test.mjs` per **simulare kill-switch**: stato ON memorizza evento **sintetico** in FakeD1, flag OFF produce `/health.accepting=false` e HTTP 503 senza altre scritture o cancellazioni; anche riattivazione flag senza limiter rimane fail-closed. **GitHub [#43441553706](https://github.com/mirkoworz/remura/actions/runs/43441553706) SUCCESS**: CI Python root 69, mock D1 11, test manifest 12 e gateway Node superati. Questa è **simulazione offline**, non rollback reale Cloudflare.
- [x] Nuovo documento `gateway-lab/TEST-WEBHOOK-RELEASE-GATE-v0.8.22.md`: separa due consensi espliciti (deploy nuovo Worker TEST inizialmente OFF, poi eventuale ON/test webhook TradingView), criteri di GO/NO-GO, monitor Free, procedure di emergenza e preservazione database TEST. **Nessun nuovo Worker è stato creato**, nessuna chiave/secret nuova, nessuna spesa e nessun ordine attivati.
- [x] Limiti ufficiali Workers Free 100.000 richieste/giorno/account e 10 ms CPU/invocazione; D1 Free 10 DB, 500 MB/DB, 5 GB/account. Disponibilità reale / stato fatturazione account **ancora non verificati**. Rate Limiting binding è **approssimativo per località**, non un tetto globale, e controlla gli eventi solo dopo l'invocazione Worker; namespace univoco e disponibilità effettiva **da verificare**. Fonti: https://developers.cloudflare.com/workers/platform/limits/ , https://developers.cloudflare.com/d1/platform/limits/ , https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [ ] Prossimo intervento: confermare disponibilità reale del rate limiting/costo e permesso minimo Workers per il SOLO nuovo Worker TEST; poi sottoporre per autorizzazione la distribuzione `INGEST_ENABLED=false`. Il manifest in GitHub è SOLO esempio con placeholder, non pronto per il deploy. **NON distribuire o inviare webhook senza consenso distinto**.
- [x] Filoni A/B/C e monitor `main` intatti, PR #102 DRAFT, Worker Production vecchio v0.8.5 invariato, record sintetico D1 TEST conservato; nessun risultato di mercato reale o capacità predittiva dimostrata.

## CHECKPOINT v0.8.21 — TARGET D1 DEL WORKER PRODUCTION CERTIFICATO DA SCHERMATA — 13/11/2026 ore 15:11 CET
- [x] Screenshot utente iPhone ruotato in orizzontale: Worker `remura-tv-ingest-lab`, ambiente **Production**, sezione Settings → **Bindings**: riga completa **Type `D1 database` | Name `TELEMETRY_DB` | Value `remura-tv-lab`**. Confermata destinazione del binding sul **DB PRINCIPALE**, non quello TEST. Questo è un dato della **configurazione UI**, non un test del percorso webhook o della ricezione effettiva.
- [x] Chiuso il requisito manuale precedente sui nomi binding senza richiedere altri screenshot. Secret Production visto in precedente immagine come nome parziale `WEBHOOK_TOKE...`, valore encrypted; NON riesaminare/ricreare il secret, né affermare nome completo verificato da screenshot.
- [x] Il Worker Production NON va riutilizzato per il primo webhook di prova: mantenere separato un eventuale `remura-tv-webhook-test` legato **solo** al `remura-tv-lab-test`, con `INGEST_ENABLED=false` prima dell'autorizzazione. Manifest template e guard di v0.8.18 ancora non distribuibili, nessun UUID o token inserito.
- [x] Nella porzione di tabella Production è mostrato **un D1 binding** e **nessun Rate Limiting binding visibile**. Non affermare che rate limiter sia configurato né che la sua mancanza sia prova dell'intero runtime. Sorgente gateway GitHub v0.8.6 richiede `INGEST_RATE_LIMITER` in modalità ingest ON, altrimenti rimane fail-closed: non consentire tentativi senza verifica effettiva. La documentazione Cloudflare consente configurazione `ratelimits` con namespace_id stringa positiva, `simple.limit`, `simple.period=10|60`; limite approssimativo per location, non protezione assoluta dell'account. Fonte: https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [ ] Prossimo passo: rendere pronto **in modo reversibile e senza deploy** il percorso del Worker TEST (binding D1 TEST, limiter, segreto separato, test isolato, costo Free, rollback) e chiedere consenso soltanto per distribuire/abilitare successivamente. Non modificare `main` o il Worker Production; non fare read/write sul database.
- [x] PR #102 sempre DRAFT OPEN all'ultima verifica, monitor daily main v0.8.14 intatto; nessuna modifica Cloudflare, nessuna spesa attivata, nessun alert TradingView, nessun ordine e filoni A/B/C non interferiti.

## CHECKPOINT v0.8.20 — SEGRETO PRODUCTION NOME PARZIALE — 13/11/2026 ore 15:09 CET
- [x] Acquisito nuovo screenshot iPhone in orizzontale, Worker `remura-tv-ingest-lab` → **Production** → Settings → Runtime variables and secrets. **Tipo `Secret`**, **nome visibile `WEBHOOK_TOKE...`**, **valore `Value encrypted`**. Nome visibile coerente col precedente `WEBHOOK_TOKEN_SHA256`, ma **troncato: NON conferma esattamente nome completo, contenuto, autenticazione o abilitazione dell'ingestione**.
- [x] Non esposti né richiesti valori segreti. Nessuna nuova operazione Cloudflare / GitHub da parte dell'utente, nessun token o costo nuovo.
- [ ] Informazione nuova indispensabile: schermata **Bindings** con colonne **Name / Type**, possibilmente nome D1 `TELEMETRY_DB` e database associato quando visibile, evitando qualsiasi valore sensibile; screenshot precedente mostrava solo tipo `D1 database`, non nome. Non richiedere nuovamente screenshot del Secret o Domains/Access.
- [ ] Binding `INGEST_RATE_LIMITER` e valore `INGEST_ENABLED` restano NON verificati nell'ultima configurazione runtime; screenshot parziale NON dimostra assenza di elementi oltre inquadratura. Nessun deploy, webhook o ingest finché preflight/consenso separato.
- [x] PR #102 DRAFT, nessun merge, ultimo monitor `main` v0.8.14 invariato, record sintetico D1 TEST preservato. Le prove full-chain attuali restano esclusivamente offline/sintetiche.

## CHECKPOINT v0.8.19 — WORKER PRODUCTION SETTINGS, SCREENSHOT UTENTE — 13/11/2026 ore 15:03 CET
- [x] Nuovo screenshot reale Cloudflare dashboard `remura-tv-ingest-lab` → **Settings** → tab **Production**. In `Runtime variables and secrets` visibile **un elemento di tipo Secret**; in `Bindings` visibile **un elemento di tipo D1 database**. In `Observability` spunta su `Include Invocation logs` nell'area visibile. Nessuna modifica effettuata.
- [x] **Non attribuire nomi che NON compaiono nell'immagine**: visualizzata soltanto colonna `Type` per Secret e D1. Non possiamo associare con certezza il Secret a `WEBHOOK_TOKEN_SHA256` né il binding D1 a `TELEMETRY_DB` o al database specifico. I checkpoint precedenti documentano la loro configurazione; **questa immagine non li riconferma nominalmente**. La colonna nome sembra fuori inquadratura sulla visualizzazione iPhone.
- [x] Nella porzione di schermata visibile **non risulta alcuna riga Rate Limiting** e non è visibile alcuna variabile plaintext `INGEST_ENABLED`; **non dire che siano assenti dall'intera configurazione** finché non si controllano nomi, ambienti e binding supportati dalla UI.
- [x] Confermata esistenza di impostazioni Production e binding D1/Secret dall'interfaccia proprietario **senza nuovi token**. Il workflow API Workers Settings aveva già prodotto `INCONCLUSIVE_HTTP_403` sul token D1 Read: non ripeterlo identico.
- [ ] **Unica informazione manuale residua per questa vista:** mostrare la colonna `Name` e `Type` nello stesso screenshot, senza aprire valori: modalità orizzontale/zoom-out Safari o scorrimento laterale tabella. Non richiedere screenshot Access/Domains già acquisiti, né segreti.
- [ ] Prima del webhook live serviranno verifica affidabile binding limiter/costo Free, ambiente TEST isolato (manifest v0.8.18 ancora INCOMPLETO/NO DEPLOY), flag ingest OFF fino al consenso per primo test e test end-to-end reale. Nessun ordine.
- [x] PR #102 ancora DRAFT OPEN all'ultimo controllo, Worker runtime non modificato, monitor main v0.8.14 invariato, nessuna modifica ai database, filoni A/B/C o configurazione Cloudflare.

## CHECKPOINT v0.8.18 — WORKER SETTINGS AUTH GET 403 E TEST WEBHOOK SICURO — 13/11/2026 ore 13:57 CET
- [x] Verificata documentazione **Cloudflare GET /accounts/{account}/workers/scripts/{script}/settings**, che richiede permessi Worker Scripts Read oppure Worker Metadata Read-Only; **NON** implica che il token D1 Read possieda tali permessi. Endpoint diverso da hostname pubblico `workers.dev`. [API Cloudflare](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/script_and_version_settings/methods/get/).
- [x] Nuovo `gateway-lab/worker_metadata_probe_v1.py`: tenta **solo due GET autenticati** (verify token + metadata del solo Worker `remura-tv-ingest-lab`); valore segreti, bind D1 UUID, environment values, corpo risposte e token **mai pubblicati**. Schema sanitize: `INGEST_FLAG`, stato binding D1/secret/rate limiter, ma non simula stato del codice realmente deployato.
- [x] Nuova workflow `.github/workflows/remura-tv-worker-settings-readonly.yml` (branch DRAFT, nessuno schedule, permessi `contents:read`), con **11 test esclusivamente sintetici verdi**. [Run #43428754941](https://github.com/mirkoworz/remura/actions/runs/43428754941) SUCCESS come **esecuzione del controllo**, risultato **`REMURA_WORKER_SETTINGS=INCONCLUSIVE_HTTP_403`** dalla API autenticata: **NON** letti i metadata Worker. Non confondere verde della Actions con permesso ottenuto, configurazione verificata o ingest OFF. Il precedente 403 sulla URL pubblica resta un controllo distinto e inconcludente. Non ripetere identico con lo stesso token.
- [x] Preparato `gateway-lab/wrangler.webhook-test.EXAMPLE.json`, configurazione **non deployabile** per un nuovo Worker isolato `remura-tv-webhook-test`, D1 `remura-tv-lab-test`, `INGEST_ENABLED=false`, con UUID e namespace rate limiter lasciati intenzionalmente come placeholder. **No Secrets nel repo**, e nessun Worker nuovo creato su Cloudflare.
- [x] `predeploy_test_manifest_guard_v1.py` + `test_manifest_guard_v1.py`: blocca in offline qualsiasi destinazione al database principale, `INGEST_ENABLED=true`, variabili secret in chiaro, routes inattese, limiter assente/indebolito, IDs invalidi. [CI #43429329813](https://github.com/mirkoworz/remura/actions/runs/43429329813) **SUCCESS** (69 test laboratorio + 11 D1 reader + nuovi test manifest + Node simulato); stato manifest `EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS`, non “ready for deploy”. Nessun deploy/webhook, nessuna scrittura D1.
- [ ] Per finire preflight configurazione: preferire **un'unica lettura manuale dalla UI delle sole righe Binding / Variables and Secrets, con valori segreti chiusi**, al posto di generare nuovi token. La disponibilità del binding Rate Limiting potrebbe non essere visibile da dashboard; stato limiter quindi da confermare separatamente prima del deploy. Il vecchio screenshot Domains & Routes è già acquisito, NON ripetere.
- [ ] Per primo webhook reale: preflight completo, verifica effettiva account Free e disponibilità rate limiter; eventuale Worker TEST isolato prima **OFF**, poi abilitazione per un test controllato SOLO dopo autorizzazione dell'utente; nessun dato nel DB principale durante il test.
- [x] PR #102 OPEN/DRAFT, Worker online v0.8.5 non aggiornato, main budget v0.8.14 invariato, record sintetico TEST conservato, filoni A/B/C non toccati. **Nessuna nuova credenziale o spesa**.

## CHECKPOINT v0.8.17 — CLOUDFARE DOMAINS / ROUTES DA SCHERMATE UTENTE — 13/11/2026 ore 13:44 CET
- [x] **Nuova verifica manuale, diversa dalla sonda pubblica GitHub**: screenshot Cloudflare Workers & Pages → `remura-tv-ingest-lab` → Settings → Domains & Routes, inviati il 13/11/2026 alle 13:44 CET. Vista `Worker URL` **Production**, hostname pubblico `remura-tv-ingest-lab.mirkoworz.workers.dev`, testo **`Anyone with this URL can visit`** e pulsante **`Enable Access`**. Questi elementi indicano **Access non attivato per quel collegamento Production nella vista corrente**, **non** garantiscono l'assenza di altre policy di accesso a livello account/hostname.
- [x] Sezione Custom Domains and Routes: **No custom domains**; nessuna custom route elencata. È presente anche una URL **Preview** distinta; NON utilizzare il percorso Preview per webhook senza valutare sicurezza e routing.
- [x] Non è stato cliccato alcun controllo mutativo: **no Enable Access, Add Route, Add Domain**, nessun cambio di infrastruttura, secrets, database o Worker.
- [x] Aggiornata diagnosi `INCONCLUSIVE_EDGE_403`: il precedente 403/403 GitHub è **ancora inconcludente**, ma non deve più essere attribuito senza prove al login di Cloudflare Access per l'URL Production. Cloudflare documenta un **Browser Integrity Check (BIC) obbligatorio sull'hostname workers.dev**, che può respingere client automatizzati prima che il Worker venga invocato; è **un'ipotesi tecnica, NON la diagnosi verificata del vecchio 403**. [Documentazione Workers.dev](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/), [Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/).
- [ ] Prossima verifica necessaria **non duplicata**: binding/versione/settings Worker reali con canale autenticato read-only e permessi minimi. Evitare nuove richieste dal runner GitHub che replichino GET `/health` e `/` con lo stesso comportamento già classificato inconcludente.
- [ ] Il fatto che l'URL sia pubblico **non equivale ad ingest abilitato**; ultimo runtime noto v0.8.5, Pine alert OFF, primo webhook reale NON inviato. Prima di abilitarlo servono rate limiter, protezione anti-abuso e consenso distinto, idealmente primo test su D1 TEST.
- [x] PR #102 DRAFT/OPEN, main budget v0.8.14 invariato, Filoni A/B/C non coinvolti. **Nessuna operazione manuale ulteriore richiesta all'utente in questo checkpoint**.

## CHECKPOINT v0.8.16 — SIMULAZIONE FULL CHAIN E READER MAIN D1 OFFLINE — 13/11/2026, ore 13:11 CET
- [x] Nessun repeat dei vecchi audit Cloudflare: ripreso dal checkpoint v0.8.15 e PR #102 verificata OPEN/DRAFT. Esaminati esclusivamente Pine v0.8.1, gateway v0.8.6, bridge v0.8.15 e workflow CI pertinenti. `main` resta monitor giornaliero v0.8.14 con pinned commit precedente; Worker online non modificato, ingest OFF ultimo checkpoint.
- [x] Implementato `gateway-lab/offline_webhook_roundtrip.mjs`: **POST soltanto verso l'oggetto Worker in memoria Node**, con token sintetico e IP simulato, D1 FakeD1; prova 403 per IP/token errati, 200 accepted, duplicato idempotente, evento in ritardo non prospettico e heartbeat. Emette 3 sole righe completamente sintetiche e marcate `SYNTHETIC_LOCAL_NODE_WORKER_FAKE_D1`. Nessun accesso di rete o Cloudflare.
- [x] `test_offline_webhook_roundtrip_v1.py`: riceve tali righe, attraversa `remura_tv_bridge_preview_v1.py`, controlla coerenza contratto, classificazione eventi/heartbeat, etichetta LATE, rifiuti su campi D1 incoerenti, duplicati in conflitto quarantinati e nessun LONG/SHORT o ordine.
- [x] `gateway-lab/d1_preview_reader_v1.py`: predisposto lettore **SELECT esclusiva** su `remura-tv-lab` (solo PROSPETTICO, non TEST), account e giurisdizione UE obbligatori, finestra <= 24h, limite <= 100, sentinella `LIMIT+1` per rifiutare risposte troncate, schema D1 rigido e output analitico senza raw_json. Non possiede un CLI e **non viene chiamato con credenziali reali**; parametro `explicit_live_approval` è guardia tecnica supplementare, NON sostituisce approvazione utente.
- [x] `gateway-lab/test_d1_preview_reader_v1.py`: test di rete **interamente mocked**, verificano assenza di chiamate se non autorizzato, solo query SELECT, destinazione corretta, risposte Cloudflare incomplete e record invalidi. Non ha letto il DB principale reale.
- [x] [GitHub CI #43422541291](https://github.com/mirkoworz/remura/actions/runs/43422541291) **SUCCESS** (69 test Python laboratorio + 11 regressioni lettore, Node gateway test e controlli sintattici). CI non esegue alcuna connessione D1 principale né webhook. Workflow `.github/workflows/remura-tv-telemetry-lab.yml` ora v0.8.16, GitHub contents:read, solo branch PR.
- [x] Nuova guida `gateway-lab/WEBHOOK-LIVE-GATE-v0.8.16.md` con vincoli e gates: 403/403 GitHub inconcludente, possibile Cloudflare Access che richiede login (da verificare, NON accertato), read-only Worker settings richiede permesso Workers Metadata Read Only/Workers Scripts Read che gli attuali token non garantiscono; rate limiting approssimativo e costo reale sull'account Free sconosciuto. Non ripetere sonda pubblica identica, non richiedere segreti in chat.
- [ ] Prossimo passo sicuro: **configurazione autenticata read-only del solo Worker** (Access, routing, binding, versione) attraverso connettore/permessi minimi, solo quando possibile senza nuova esposizione segreti; nessun deploy, modifica Access o ingest. I quattro IP TradingView e la 2FA erano già verificati.
- [ ] Solo dopo preflight Worker + limite costo Free + consenso distinto: endpoint temporaneo isolato su D1 TEST, prova Webhook reale originato da TradingView, validazione 3 secondi/record, quindi eventuale passaggio al D1 prospettico. Nessun ordine automatico.
- [ ] Integrazione filoni B/C e notifiche richiedono validazione prospettica /out-of-sample e decisione architetturale separata. I volumi FXCM TradingView sono **proxy**, non esecuzioni istituzionali.
- [x] Filoni A/B/C, database principali, record sintetico TEST, secrets, Worker runtime e monitor quotidiano `main` intatti. **Zero servizio a pagamento attivato**.

## CHECKPOINT v0.8.15 — PRIMO ADATTATORE D1 → REMURA SOLO OFFLINE — 13/11/2026, ore 13:00 CET
- [x] Esaminato soltanto contratto Pine v0.8.1, ricevitore gateway v0.8.6, schema D1 e misuratore prospettico v0.8.3 gia presenti; **nessun test o configurazione Cloudflare precedente ripetuto**. Il Pine e il gateway hanno componenti di emissione/validazione ma **nessun webhook end-to-end LIVE ancora autorizzato**.
- [x] Nuovo `tradingview/delta-peaks/remura_tv_bridge_preview_v1.py` v0.8.15: accetta **solo un export JSONL preparato offline** con le 9 colonne dello schema `tv_flow_events`, usa `validate_telemetry_v1.validate_payload`, verifica coerenza tra metadati D1 e JSON originale, unicita chiave, timeliness sul timestamp **del gateway**, provenienza FXCM/proxy, flags ER/PEAK/RT/DAY, disponibilita footprint, ATR e POC, senza chiedere/leggere segreti.
- [x] Uscita JSON locale `remura.tv.observation.preview.v1` con etichette osservazionali, ragioni di dati mancanti e stato `OBSERVATION_ONLY | PARTIAL_OBSERVATION | LATE_NOT_PROSPECTIVE`. Il verdetto resta sempre `NESSUN_SEGNALE_OPERATIVO`, `orders_enabled:false`, `proof_of_institutional_activity:false`, `statistical_edge_validated:false`. **Non e il collegamento live REMURA app e non dimostra edge o profitti**.
- [x] Duplicati identici scartati; record con stessa chiave ma payload differente **interamente in quarantena**; record sintetici TEST, stime presentate come contratti CME, colonne incoerenti, timestamp falsi o payload JSON invalidi rifiutati. L'adattatore non scrive in D1, Cloudflare, Oracle, Firestore o altri filoni.
- [x] Test sintetici `test_remura_tv_bridge_preview_v1.py` e controllo di sintassi aggiunti al workflow **gia esistente** di PR #102. [Run GitHub #43421390844](https://github.com/mirkoworz/remura/actions/runs/43421390844) **SUCCESS** per test offline Python, simulazione gateway Node e syntax; **nessuna richiesta Cloudflare, nessun webhook**. Commit modulo `ba4cf512`, test `f0dda600`, gestione conflitti `70af2d3b`, regressioni `371645d3`, CI `4fdc9594`.
- [ ] Per primo **webhook reale**: preflight autenticato configurazione Worker e protezione edge (non rifare sonda GitHub 403 inconcludente); confermare disponibilita/costo limiter Free; test controllato su D1 TEST o canale isolato; solo con autorizzazione distinta deploy/abilitazione e TradingView `alert()` v0.8.1. Monitorare consegna TradingView e latenza 3s, nessun ordine.
- [ ] Per **analisi automatica REMURA**: implementare lettore D1 GET/SELECT a credenziali minime con politiche di accesso e quota, processo idempotente eventi → adattatore → validazione outcome/benchmark, UI filone C e notifiche solo dopo coordinamento esplicito con B/C. Nessuna scrittura verso B/C da questa PR.
- [ ] Per verdetti statisticamente utili: raccogliere campione prospettico completo (heartbeat M5 per misurare anche barre senza evento), false positive, esiti out-of-sample e risk/costi di negoziazione; **non trasformare etichette di osservazione in raccomandazioni di entrata**.
- [x] Rimane monitor giornaliero `main` v0.8.14 con run SUCCESS e pin SHA testato; PR #102 DRAFT OPEN, Worker online v0.8.5 ingest OFF ultimo checkpoint, sorgente v0.8.6 offline, record sintetico TEST immutato, altri filoni A/B/C intatti, nessun servizio a pagamento.

## CHECKPOINT v0.8.14 — INVENTARIO D1 LIVE E MONITOR GIORNALIERO VERDE — 13/11/2026, ore 12:52 CET
- [x] **Laboratorio PR #102:** GitHub Actions [#43414271846](https://github.com/mirkoworz/remura/actions/runs/43414271846), commit verificato `08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8`: job offline-safety SUCCESS con **85/85 test** (20 D1 Analytics, 17 Workers, 13 D1 TEST, 18 D1 account storage, 17 summary), job API LIVE **read-only SUCCESS**. `REMURA_D1_ACCOUNT_STORAGE=OK`: **2 database D1, 57.344 byte aggregati**, massimo **28.672 byte/DB**, D1 TEST **28.672 byte**; quota account 5GB di riferimento. Dati `file_size` **metadati reali**; consumi giornalieri Analytics **stime** (D1 1 read/0 write, Workers 123 requests/0 errors).
- [x] Sulla base della prova reale e dell'assenso a proseguire, aggiornato **solo** `.github/workflows/remura-cloudflare-budget-daily.yml` su `main` alla **v0.8.14**, con `permissions: contents: read`, ref codice immutabile `08ee9d8f...`, 85 test offline e quarta sonda GET-only account D1. Mai abilitati ingest, webhook, SQL write, Worker deploy, merge PR o ordini.
- [x] **Errore intercettato e corretto:** primo commit workflow `bd16c6fd` produsse YAML non valido; [run #43420321670](https://github.com/mirkoworz/remura/actions/runs/43420321670) FAILURE senza job avviati. Ricostruito il file dalla v0.8.13 funzionante, senza riusare il patching difettoso, e pubblicato fix su `main` [commit `f40da371`](https://github.com/mirkoworz/remura/commit/f40da371a0abe9cb007ec98fa3401904e23ac5a3).
- [x] **Run finale main** [#43420383076](https://github.com/mirkoworz/remura/actions/runs/43420383076) SUCCESS e log effettivo `REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE`; 85/85 test, D1 account storage OK, **2 D1 / 57.344 byte**, Workers **133 richieste stimate**, 0 errori stimati, D1 **1 read/0 write stimate**, D1 TEST 28.672 byte. Nessun token stampato. Workflow prezzi e insights in main SUCCESS; [GitHub Pages #43420381151](https://github.com/mirkoworz/remura/actions/runs/43420381151) SUCCESS verificato. Rebuild Pages conseguente al push: **non equivale a Worker Cloudflare deploy**.
- [x] WARNING a 70% (annotazione Actions); CRITICAL a 90% o UNKNOWN causa failure, comprese nuove metriche D1 account. Le email/notifiche push **non sono verificate** e dipendono da preferenze GitHub. Non promettere avvisi telefonici.
- [ ] **Primo evento cron reale** atteso il **14/11/2026 verso le 08:37 CET**; prima esecuzione `push` non dimostra l'attivazione di `schedule`. Verificare evento e risultato domani senza ripetere oggi i test manuali.
- [ ] Ancora da verificare: Cloudflare billing/costi realmente maturati, piano effettivo, CPU totale Workers, Worker pubblicamente protetto oltre l'inconclusivo 403, rate limiting binding, e modalità affidabile di notifica warning/failure. Mai considerare metriche Analytics adaptive come billing esatto.
- [x] PR #102 sempre DRAFT/OPEN, due database UE non modificati, record sintetico TEST preservato, Worker runtime v0.8.5 e sorgente gateway v0.8.6 senza deploy, ingest OFF ultimo checkpoint, filoni A/B/C intatti.

## CHECKPOINT D1 ACCOUNT STORAGE READ-ONLY PREPARATO — 13/11/2026, ore 12:06 CET
- [x] Verificati solo PR #102 OPEN/DRAFT, roadmap v0.8.13 e scheduler in main v0.8.13; **nessun audit ripetuto, nessun deploy, merge o cambiamento su main**.
- [x] Nuovo `gateway-lab/cloudflare_d1_account_storage_guard.py` **v0.8.14** nel SOLO branch DRAFT: API GET di token verify, elenco D1 account con `page=1&per_page=100` e GET `file_size` di ogni database. Nessuna query SQL, POST, token in output, Cloudflare write o lettura delle tabelle. Riutilizza esclusivamente `REMURA_CF_D1_READ_TOKEN` e `REMURA_CF_ACCOUNT_ID` già presenti.
- [x] Controlli fail-closed contro elenco incompleto/paginazione mancante, UUID duplicati, metadata mancanti, assenza dei due D1 REMURA previsti o giurisdizione non UE per tali database. **UNKNOWN non è zero.** Inventario vincolato a max 100 elementi, senza assumere che il piano reale sia Free.
- [x] Soglie comparative Free su 10 DB/account, 500.000.000 byte/DB, 5.000.000.000 byte/account; WARNING a 70%, CRITICAL a 90%. `file_size` è metadata reale API ma **non contatore di fatturazione esatto**. Fonte: documentazione ufficiale D1 API e limits Cloudflare consultata il 13/11/2026.
- [x] Aggiunti test **esclusivamente sintetici/offline** `test_cloudflare_d1_account_storage_guard.py`, report esteso con campo D1 account e nuovi test summary. Workflow di LAB `.github/workflows/remura-tv-account-analytics-readonly.yml` modificato per tentare la quarta sonda **solo nel branch DRAFT**. Commit codice `b826817c`, test `c765ca63`, summary `54773f10`, test summary `5abeffb4`, workflow `119280ac`. Test e chiamata remota **da verificare su run GitHub Actions**, non dichiararli verdi prima del riscontro.
- [x] Raffinamento dello script per giurisdizione facoltativa dei **soli DB estranei a REMURA**, preservando il controllo EU obbligatorio sui due D1 REMURA; [commit `cb7f4663`](https://github.com/mirkoworz/remura/commit/cb7f4663bbce0e9e8ec8097d8682decae57ae34a). Aggiunto caso di test [commit `08ee9d8f`](https://github.com/mirkoworz/remura/commit/08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8). Esecuzione remota CI non ancora verificata da questa sessione. **Nessun nuovo dato live dichiarato.**
- [x] Verificata CI e nuovo inventario D1 LIVE nella run #43414271846: 85 test, lettura GET metadata 2 D1 e 57.344 byte. Casi incompleti restano UNKNOWN; nessuna nuova credenziale.
- [x] Aggiornato il solo workflow giornaliero su `main` dopo risultato positivo, commit `f40da371`, ref ora puntato in modo esplicito a `08ee9d8f` (85 test, live read-only); prima esecuzione `schedule` ancora attesa 14/11/2026 08:37 CET.
- [ ] Notifiche: in `main`, WARNING è attualmente annotazione GitHub; CRITICAL/UNKNOWN causa job failure. Le notifiche email/web dipendono dalle impostazioni GitHub dell'utente e NON sono state provate o attivate da REMURA; nessun canale a pagamento aggiunto.
- [x] Worker runtime v0.8.5 e `INGEST_ENABLED` non modificati; webhook TradingView/heartbeat OFF, PR DRAFT/OPEN, record sintetico TEST conservato; filoni A/B/C intatti.

## CHECKPOINT MONITOR GIORNALIERO ATTIVO IN MAIN — 13/11/2026, ore 11:15 CET
- [x] Utente ha autorizzato esplicitamente un **minimo workflow quotidiano di sola lettura** in `main`, isolato dalla PR #102; nessun merge della PR o deploy Cloudflare.
- [x] Creato solo `.github/workflows/remura-cloudflare-budget-daily.yml` su `main`, **REMURA v0.8.13**, [commit `3443c1e5`](https://github.com/mirkoworz/remura/commit/3443c1e521849c6e956d31d4028ce1ef06963db1). Esecuzione programmata **08:37 Europe/Rome ogni giorno**, con `workflow_dispatch` e `push` limitato alla modifica del solo file workflow. GitHub può ritardare o saltare esecuzioni sotto carico; non dichiarare consegna garantita.
- [x] Workflow con `permissions: contents:read`, checkout `persist-credentials:false` di codice read-only da **commit fisso e immutabile** `1e3c38b772df01b0e66679f0e727ffcdbf83c80a`, timeout 5 min. Nessun `git push`, SQL D1 Write, deploy Worker, webhook, merge o ordini; token GitHub Secrets mai stampati.
- [x] Esegue ogni volta **63 test offline**, poi metriche effettivamente interpellate via Account Analytics Read (Workers e D1 giornalieri) + D1 Read (metadati solo DB TEST); genera `GITHUB_STEP_SUMMARY` con valori disponibili/UNKNOWN. Mancanza secrets o stato non verificabile = job failure; `WARNING` a 70%, `CRITICAL` a 90% delle soglie calcolate. P99 CPU non fatturazione esatta.
- [x] [Prima esecuzione su `main` #43407561296](https://github.com/mirkoworz/remura/actions/runs/43407561296) SUCCESS, `REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE`; stime 13/11/2026: **111 richieste Workers, 0 errori, D1 1 read/0 write**, dimensione reale D1 TEST **28.672 byte**. NON contatori billing esatti né prova di tutte le risorse account senza spese.
- [x] Il commit `main` ha attivato anche workflow esistenti (GitHub Pages build/deployment, price checks, insights checks); tutti osservati **SUCCESS**. Nessun file UI/applicativo modificato: il rebuild automatico di GitHub Pages è effetto collaterale del commit `main`, NON un deploy Worker o merge della PR #102.
- [ ] Prima esecuzione da `schedule` attesa **14/11/2026, verso le 08:37 Europe/Rome**; l'esito cron non è ancora verificabile. Il semplice risultato SUCCESS del push non prova che l'evento `schedule` venga attivato domani. Monitor consultabile tramite GitHub Actions; nessuna email/Telegram di allerta automaticamente configurata.
- [ ] Versioni future di script PR #102 **non entreranno** nel monitor schedulato senza un nuovo pin SHA testato e intervento deliberato su `main`.
- [ ] Restano non verificati: piano/costi billing esatti, Workers edge 403/403 da runner GitHub, protezione rate limiter reale, spazio aggregato tutti D1. Ingest OFF da ultimo checkpoint attendibile; non autorizzare webhook/ordini da stato monitor verde.
- [x] PR #102 resta OPEN/DRAFT, branch di ricerca indipendente, nessun tocco ai filoni A/B/C.

## CHECKPOINT MONITOR UNIFICATO FREE D1 + WORKERS — 13/11/2026 ore 10:12 CET
- [x] Fonti ufficiali Cloudflare: `workersInvocationsAdaptive` GraphQL con `sum.requests`, `sum.errors`, `quantiles.cpuTimeP99`, richiedendo solo il token **Account Analytics Read** esistente. Il dato è adattivo/stimato, non fatturazione esatta. Workers Free 100.000 req/die e 10ms CPU per singola invocazione.
- [x] Implementato `cloudflare_workers_usage_guard.py` v0.2: riepilogo account-wide da mezzanotte UTC, campione max 1.000 righe; risposta vuota/troncata non può essere presentata come zero/sicura; P99 mancante viene riportato come sconosciuto, non zero. Nessuna credenziale nei log.
- [x] **Prima prova reale Workers** [run #43398573498](https://github.com/mirkoworz/remura/actions/runs/43398573498): 100 richieste stimate, 0 errori stimati, 1 Worker rappresentato dai gruppi ritornati, massimo P99 osservato 3.080µs. **Non dimostra un consumo esatto/account completo né la conformità CPU di tutte le chiamate**.
- [x] **Monitor combinato** workflow `.github/workflows/remura-tv-account-analytics-readonly.yml` v0.4: query D1 Analytics + Workers Analytics + file_size D1 TEST; scrive resoconto sanitized nel `GITHUB_STEP_SUMMARY`. Protezione da valori assenti e nessun logging secret.
- [x] [Run #43399020915](https://github.com/mirkoworz/remura/actions/runs/43399020915): **63/63 test offline** (20 account D1 + 17 Workers + 13 D1 TEST storage + 13 report); job remoto SUCCESS: stime D1 `1 read, 0 write`, Workers `101 richieste, 0 errori`, DB TEST `28.672 byte`, `REMURA_BUDGET_REPORT=GENERATED_NO_SECRETS`.
- [x] Ulteriore prova verde dopo fix `cpuTimeP99=None` senza inventare zero: [run #43399187515](https://github.com/mirkoworz/remura/actions/runs/43399187515).
- [x] README `gateway-lab/README.md` aggiornato a v0.8.12-doc. Sorgente Worker v0.8.6 solo GitHub, runtime online v0.8.5, ingest non abilitato da noi.
- [ ] **Non schedulato giornalmente**: il workflow nel branch DRAFT funziona su push mirati e `workflow_dispatch`. GitHub `schedule` sul branch research non viene eseguito: serve un orchestratore minimo separato nel ramo default solo con permessi `contents:read` e senza deploy, da autorizzare esplicitamente, oppure una schedulazione esterna idonea.
- [ ] Rimangono non verificati: fatturazione e piano Cloudflare reali, protezione edge/403 del Worker, spazio complessivo D1 e disponibilità/costi rate limiting binding Free. Nessuna modifica a `main`, nessun webhook, ordine, SQL write, merge PR #102 o filoni A/B/C.

## CHECKPOINT ANALYTICS ACCOUNT-WIDE REALI RIUSCITE — 13/11/2026 ore 10:01 CET
- [x] Utente ha confermato inserimento nel GitHub Secret `REMURA_CF_ANALYTICS_READ_TOKEN` del token Cloudflare separato **Account Analytics → Read**. Non vengono richieste modifiche ai precedenti token D1 Read.
- [x] GitHub Action [run 43397743147](https://github.com/mirkoworz/remura/actions/runs/43397743147) rilanciata automaticamente tramite commit isolato alla workflow del branch DRAFT: offline-safety SUCCESS, `account-analytics-readonly` SUCCESS.
- [x] Output autentico GraphQL del **13/11/2026 UTC**: `REMURA_CF_ACCOUNT_QUOTA=OK`, `D1_ACCOUNT_ROWS_READ_ESTIMATE=1`, `D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0`; limiti gratuiti di riferimento 5.000.000 read e 100.000 write/die. **Stime Analytics adattive, non contatori billing esatti** e potenzialmente incomplete/ritardate.
- [x] Token Analytics funzionante; nessuna query SQL di scrittura, mutazione API, deploy Worker, merce o ordine. README gateway aggiornato **v0.8.11-doc**, 13/11/2026 ore 10:01.
- [ ] Stato gateway pubblico dal runner GitHub resta `INCONCLUSIVE_EDGE_403`: 403/403 non prova disabilitazione né attivazione. Prima di ogni test webhook servono verifica da account, protezione edge e misure effettive Workers.
- [ ] Restano sconosciuti: consumo giornaliero Workers/CPU, dati billing esatti, spazio combinato dei due D1, disponibilità/costo Rate Limiting binding sul piano Free. Non dichiarare l'account completamente sicuro per i costi solo da D1 Analytics.
- [ ] Monitoring giornaliero vero **non ancora schedulato**. Workflow su branch research con `push` e `workflow_dispatch`; GitHub `schedule` userebbe main e va progettato separatamente con autorizzazione.
- [x] PR #102 verificata OPEN/DRAFT: mantenere no merge/no deploy/no activation; altri filoni A/B/C non modificati.

## CHECKPOINT PUBBLICO 403 + QUOTE GIORNALIERE PREPARATE — 13/11/2026 ore 06:57 CET
- [x] PR #102 ancora **OPEN/DRAFT**, commit isolati sul branch `research/tradingview-delta-peaks-20261111`; Worker pubblico runtime v0.8.5 non modificato, sorgente v0.8.6 solo GitHub, ingest OFF da ultimo stato confermato dall'utente (nuova verifica pubblica inconcludente).
- [x] `worker_public_failclosed_audit.py` v0.3 e [workflow GitHub](https://github.com/mirkoworz/remura/actions/runs/43374850790): esegue **solo GET** `/health` e `/`, mai POST o URL contenente token. 17 test offline verdi.
- [x] Esito reale dal runner GitHub: **HTTP 403/403**, `REMURA_TV_PUBLIC_FAILCLOSED=INCONCLUSIVE_EDGE_403`. Importante: il job verde indica che il caso 403 è stato classificato correttamente, NON che `accepting=false` sia stato verificato da GitHub. Senza nuovo controllo dall'account non dichiarare il Worker provato OFF.
- [x] Fonte Cloudflare GraphQL: il consumo D1 account-wide `rowsRead`/`rowsWritten` richiede **Account Analytics → Read**; il token D1 Read separato non basta. Metriche analytics adattive, non prove esatte della fatturazione. Non autorizzare scritture o nuovi privilegi.
- [x] `cloudflare_account_quota_guard.py` v0.1: query GraphQL **read-only**, giorno UTC, max 10 gruppi DB su Free, soglie 70% WARNING e 90% CRITICAL per 5.000.000 read / 100.000 write giornaliere. `NO_DATA` non equivale a 0.
- [x] [Workflow Account Analytics](https://github.com/mirkoworz/remura/actions/runs/43375218853): **20/20 test offline verdi**, job remoto `REMURA_CF_ACCOUNT_QUOTA=SKIPPED_MISSING_ANALYTICS_READ_TOKEN`, cioè nessun dato account-wide raccolto. Nessuna chiamata GraphQL remota.
- [ ] Per automatizzare il bilancio quotidiano serve un token **separato** e minimo Cloudflare Account Analytics Read salvato in GitHub Secret `REMURA_CF_ANALYTICS_READ_TOKEN`. Richiedere all'utente solo al momento opportuno; mai chiedere valore/screenshot token in chat. Non modificare `REMURA_CF_D1_READ_TOKEN`.
- [ ] In assenza di nuovo token, usare solo prova effettiva spazio D1 TEST (28.672 byte, 0,0057% del limite), non inventare utilizzo giornaliero Workers/D1 o costo realizzato.
- [ ] Se necessario controllare da sessione autenticata `/health` e `/` senza aprire `/ingest`, per chiarire 403 edge. Worker pubblico non testato end-to-end e webhook TradingView/heartbeat OFF.
- [x] `gateway-lab/README.md` aggiornato a v0.8.10-doc; nessun deploy, merge, ordine, o modifica ai filoni A/B/C. Nessun nuovo servizio a pagamento.

## CHECKPOINT D1 FREE STORAGE REALE AUTOMATIZZATO — 13/11/2026 ore 06:45 CET
- [x] Confermata fonte ufficiale Cloudflare per **GET metadati D1** con permesso D1 Read e campo `file_size`. Token GitHub esistente `REMURA_CF_D1_READ_TOKEN` riutilizzato, nessuna nuova credenziale.
- [x] Script `gateway-lab/cloudflare_d1_storage_guard.py` v0.1: solo D1 `remura-tv-lab-test` nella giurisdizione EU, 3 richieste **GET** (verify token, list DB TEST, get metadata TEST); nessun SQL sulla D1 prospettica e nessuna write.
- [x] Soglie automatiche storage sul singolo DB TEST: OK sotto 70%, WARNING da 70%, CRITICAL da 90% sul limite conservativo **500.000.000 byte** per DB Free. Le soglie sono guardie locali, non alert di notifica.
- [x] Workflow [run #43373867720](https://github.com/mirkoworz/remura/actions/runs/43373867720) **SUCCESS**: `REMURA_D1_READONLY_AUDIT=record_verified`, `REMURA_D1_TEST_STORAGE=OK`, `REMURA_D1_TEST_STORAGE_BYTES=28672`, quota TEST misurata **0,0057%**.
- [x] Test offline **47/47**: 21 read-only + 13 cleanup sintetico in SQLite memory + 13 storage metadata. GitHub Actions non fa merge/deploy.
- [x] README gateway aggiornato a v0.8.9-doc, 13/11/2026 ore 06:44.
- [ ] **Non ancora misurati:** consumo aggregato dei due database, quota D1 giornaliera letture/scritture, chiamate Worker/CPU e funzionalità/costo effettivo rate limiting binding sull'account Free. Non inventare `0%` o "tutto gratis" senza dashboard.
- [ ] Non aggiungere `schedule` nel branch DRAFT come se funzionasse: GitHub cron esegue workflow dal branch default; attuale audit parte solo su push selettivi/manuale.
- [ ] Il prossimo test pratico di ricezione richiederà preflight quota edge, rate-limiter binding e autorizzazione distinta. Ingest OFF, PR #102 DRAFT/OPEN, nessun alert/ordine.

## CHECKPOINT 2FA + LIMITER v0.8.6 OFFLINE — 13/11/2026, ore 06:38 CET
- [x] Utente conferma **2FA TradingView attiva** (13/11/2026); non ripetere richiesta né chiedere codici.
- [x] Verificata limitazione `workers.dev`: appartiene alla zona Cloudflare gestita, regole WAF del proprio dominio **non si applicano automaticamente**. Rate Limiting Workers disponibile a livello API binding, ma soglie **approssimative per Cloudflare location**, non garantiscono limite globale; costi/disponibilità account Free ancora da verificare.
- [x] Preparata SOLO nel branch PR #102 sorgente **gateway v0.8.6**, ancora NON distribuita: richiede `INGEST_RATE_LIMITER.limit()` presente prima di qualunque ingest; se assente, risponde 503, `/health.accepting=false` anche qualora INGEST_ENABLED=true.
- [x] Blocco rate limit applicato dopo controllo IP/token e prima di D1; oltre soglia 429, errore limiter 503; nessuna scrittura in Cloudflare, nessun deploy.
- [x] Aggiornati test Node con regressioni per missing binding, risposta health, rejection/throw, no write e IP non autorizzato. [CI](https://github.com/mirkoworz/remura/actions/runs/43373136227) verde sul commit del gateway+test, senza webhook live.
- [x] Guida gateway aggiornata a **v0.8.8-doc** con esempio NON attivo di binding e costi da verificare.
- [ ] Preflight prima del vero utilizzo: verifica effettiva tariffazione/rate-limit binding nel tuo account Free, identificatore namespace univoco, possibilità di configurazione sicura con risorse già in uso, test end-to-end autorizzati, protezione traffico anonimo su workers.dev, quote/latency/CPU reali.
- [ ] Non aggiungere `INGEST_ENABLED=true`, non distribuire il Worker v0.8.6, non toccare altri Worker, D1 principale, filoni A/B/C. PR #102 deve rimanere DRAFT.

## CHECKPOINT AUDIT IP TRADINGVIEW E QUOTE — 12/11/2026 ore 23:43 CET
- [x] Confrontate le quattro IPv4 allowlisted nel `worker.mjs` v0.8.5 con la [guida webhook TradingView](https://it.tradingview.com/support/solutions/43000529348/): corrispondono all'elenco ufficiale (12/11/2026).
- [x] Confermati da TradingView: webhook richiede 2FA, solo porte 80/443, timeout 3 secondi, IPv6 non supportato. Nessun webhook effettivo provato; tempo di risposta Worker+D1 ancora sconosciuto.
- [x] Confermate fonti [Workers Free](https://developers.cloudflare.com/workers/platform/limits/) (100k richieste/giorno, 10ms CPU/request) e [D1 Free](https://developers.cloudflare.com/d1/platform/limits/) (10 DB, 500MB/DB, 5GB/account, 5M read/100k write giornalieri).
- [ ] Verifiche **ancora necessarie**: 2FA TradingView effettivamente ON, rate limit edge/proxy, quote account aggiornate a due DB e CPU/latency reali. Non confondere riscontro documental con un test live.
- [x] Aggiornato il README gateway v0.8.7-doc. Worker runtime resta v0.8.5, ingest OFF, nessun deploy né merge PR #102.

## CHECKPOINT CLEANUP OFFLINE + D1 LIVE READ-ONLY — 12/11/2026 ore 23:41 CET
- [x] Sicurezza account e modalità: [PR #102](https://github.com/mirkoworz/remura/pull/102) verificata OPEN/DRAFT, nessun merge, nessun deploy dei Worker né modifica ai filoni A/B/C.
- [x] `cloudflare_d1_readonly_audit.py` v0.4: SELECT solo su D1 `remura-tv-lab-test` UE e verifica aggiuntiva del `raw_json` **esattamente sintetico**, timeframe e tipo evento. Nessuna API di scrittura.
- [x] `synthetic_cleanup_plan_v1.py`: genera soltanto un piano di eliminazione della singola chiave `REMURA_SYNTHETIC_WRITE_20261112` con guardie su simbolo, versione, timeframe, tipo evento, is_timely e JSON esatto. **Non esegue SQL né accede alla rete**.
- [x] `test_synthetic_cleanup_plan_v1.py`: **13 simulazioni su SQLite in memoria**. Insieme ai **21 test offline read-only** (totale **34**) eseguiti con successo nel workflow di verifica.
- [x] GitHub Actions [run #43321908263](https://github.com/mirkoworz/remura/actions/runs/43321908263): job offline-safety SUCCESS, job Cloudflare D1 Read SUCCESS; log `REMURA_D1_READONLY_AUDIT=record_verified` su `remura-tv-lab-test`, UE, SELECT. Nessuna scrittura remota.
- [x] Guida `gateway-lab/README.md` aggiornata con stato effettivo Cloudflare e separazione TEST/PROSPETTICO; sezione storica che sosteneva DB/Worker mai creati corretta.
- [ ] Cleanup reale del singolo record sintetico **non autorizzato né eseguito**; evitiamo di creare un token D1 Write ampio per cancellare una sola riga. Il record rimane esclusivamente nel DB TEST e non contamina `remura-tv-lab`. Potrà essere rimosso con un'unica DELETE manuale circoscritta o con procedura one-shot più avanti, dopo approvazione.
- [ ] Priorità successiva: verificare protezioni edge/IP TradingView, rate limit e quota Free, poi pianificare prova webhook end-to-end **solo con consenso esplicito** e tenendo `INGEST_ENABLED` OFF sino ad allora. Nessun alert o ordine live.

## CHECKPOINT TOKEN CORRETTO E AUDIT D1 REALE VERDE — 12/11/2026 ore 23:34 CET
- [x] Utente ha corretto una lettera nel GitHub Secret `REMURA_CF_D1_READ_TOKEN` senza pubblicare il valore in chat/repo.
- [x] Rilanciati solo i job falliti con GitHub Actions [run 43319409168, tentativo 2](https://github.com/mirkoworz/remura/actions/runs/43319409168): `offline-safety` SUCCESS e `cloudflare-readonly` SUCCESS.
- [x] Log reale del job Cloudflare `131541499082`: `REMURA_D1_READONLY_AUDIT=record_verified`; `DATABASE=remura-tv-lab-test; JURISDICTION=EU; HTTP=READ_ONLY; SQL=SELECT`. Confermata autenticazione API ed esistenza del record sintetico atteso; nessuna scrittura/cancellazione remota.
- [x] Token Account D1 READ funziona dalla GitHub Action. L'ID account verifica guardia hash attesa; il database principale `remura-tv-lab` **non è stato interrogato né modificato da questo workflow**.
- [ ] Pulizia del record sintetico richiede autorizzazione separata e un meccanismo con privilegio di scrittura limitato, oppure intervento manuale; non usare il token D1 Read per nuove funzioni scriventi.
- [ ] Eventuale successivo audit automatico periodico solo dopo scelta esplicita della frequenza. Worker ingress principale continua fail-closed; TradingView alerts/heartbeat OFF; PR #102 resta DRAFT/OPEN.

## CHECKPOINT AUTOMAZIONE CLOUDFLARE CON AUTENTICAZIONE 401 — 12/11/2026 ore 23:24 CET
- [x] Utente ha confermato aggiunta GitHub Actions Secrets `REMURA_CF_D1_READ_TOKEN` e `REMURA_CF_ACCOUNT_ID` (nessun valore segreto ricevuto in chat).
- [x] Avviato workflow D1 read-only su branch di ricerca: [run #43318523658](https://github.com/mirkoworz/remura/actions/runs/43318523658). I test offline verdi e il job API raggiunge Cloudflare, ma Cloudflare ha risposto HTTP **401** a GET /d1/database; nessuna SELECT D1 completata.
- [x] Aggiunto preflight GET /accounts/{account_id}/tokens/verify senza log sensibili; [run #43318951287](https://github.com/mirkoworz/remura/actions/runs/43318951287): **401 anche in verifica account token**.
- [x] Aggiunta protezione che blocca Account ID diversi da REMURA tramite digest SHA-256 e richiede il formato account-token `cfat_` introdotto nel 2026 (trim whitespace). Suite offline estesa a **18 test**.
- [x] [Run #43319409168](https://github.com/mirkoworz/remura/actions/runs/43319409168): offline-safety **SUCCESS**, live API bloccata prima della rete con `unexpected_account_api_token_format`. Ciò indica che il contenuto attuale del GitHub Secret non rispetta il formato previsto del token Account 2026; **non se ne conosce il valore e non va esposto**.
- [ ] Azione manuale minima: controllare e sostituire nel solo GitHub Secret `REMURA_CF_D1_READ_TOKEN` il valore **integrale** del token account Cloudflare (nuovo prefisso `cfat_`), senza includere nome, etichette, spazi o screenshot. Se smarrito, ruotarlo dal pannello Cloudflare senza condividere il nuovo valore. Non cambiare gli altri secrets.
- [ ] Alla conferma utente, riavviare audit con commit innocuo sul workflow; dichiarare successo solo dopo API attiva e SELECT D1 TEST verificata. Non cancellare dati né toccare Worker/filoni A/B/C o webhook.

## CHECKPOINT API D1 READ-ONLY — 12/11/2026, ore 17:48 CET
- [x] Integrazione automatizzabile via API D1 Cloudflare, senza nuovo deploy Worker né modifiche D1: script `gateway-lab/cloudflare_d1_readonly_audit.py` v0.1, limitato per codice a `remura-tv-lab-test` (EU) e SELECT sulla chiave sintetica.
- [x] Aggiunti **11 test offline** in `gateway-lab/test_cloudflare_d1_readonly_audit.py`, nessuna chiamata di rete nelle regressioni.
- [x] Creato workflow isolato `.github/workflows/remura-tv-cloudflare-d1-readonly.yml` limitato ai push del branch #102, più workflow_dispatch per uso futuro; GitHub permissions contents:read, senza deploy/cancellazioni, solo token `REMURA_CF_D1_READ_TOKEN` e account ID `REMURA_CF_ACCOUNT_ID` dai GitHub Secrets.
- [x] GitHub Actions [run 43262606971](https://github.com/mirkoworz/remura/actions/runs/43262606971) **SUCCESS**: job offline-safety verde. Job cloudflare-readonly terminato senza chiamate remote: **SKIPPED_MISSING_SECRETS**, non confondere il verde con un D1 live audit.
- [ ] One-time manuale: token API Cloudflare `Account > D1 > Read` sul solo account REMURA, salvato in **GitHub Actions Secrets** senza mostrarlo in chat, e ID account in secondo secret. NON creare D1 Edit né Workers Edit.
- [ ] Dopo secrets, nuovo commit al file di workflow su branch DRAFT per attivare il job remoto; verificare API read-only. Successivamente progettare cleanup con permessi di scrittura temporanei e autorizzazione separata.
- [ ] `remura-tv-write-test` deve mantenere Hello World come codice pubblicato; la diagnostica temporanea è stata abbandonata senza Deploy secondo l'utente. Nessun webhook, nessuna scrittura automatica aggiunta.

## CHECKPOINT WRITE PROBE SU D1 TEST — 12/11/2026, ore 17:38 CET
- [x] Worker temporaneo isolato `remura-tv-write-test` distribuito con Hello World, binding D1 Production `TELEMETRY_DB` → `remura-tv-lab-test` confermato da screenshot. Preview configurata per usare lo stesso database di test.
- [x] Editor Preview con codice sintetico di `INSERT OR IGNORE` su chiave `REMURA_SYNTHETIC_WRITE_20261112` e successivo `SELECT COUNT(*)`; secondo screenshot utente risposta `{"status":"d1_write_ok","record_found":1,"new_rows":0,"synthetic":true}`.
- [x] Confermata **lettura del record di test dal Worker Preview**, senza duplicazione nell'ultima richiesta. `new_rows:0` significa che l'ultima invocazione non ha creato una nuova riga; la presenza del record è coerente con precedente invocazione Preview. **Non attribuire con certezza il momento della prima scrittura** senza ulteriore verifica.
- [ ] Priorità: **rimuovere la modifica temporanea non autenticata dall'editor e uscire senza Deploy/Save**, mantenendo Hello World pubblico.
- [ ] Confermare nella console D1 TEST mediante SELECT sulla chiave la presenza e i metadati `LAB:TEST_ONLY`, poi eliminare solo tale riga di prova con consenso e verifica; controllare che D1 principale rimanga senza eventi.
- [ ] Non abilitare `INGEST_ENABLED=true`, heartbeat TradingView o ordini; non modificare altri Worker/filoni A/B/C. PR #102 resta DRAFT/OPEN senza merge.

## CHECKPOINT D1 TEST SCHEMA VERIFICATO — 12/11/2026, ore 15:51 CET
- [x] Creato manualmente dall'utente database D1 isolato `remura-tv-lab-test`, giurisdizione **The European Union**, region **Eastern Europe**, read replication Disabled (screenshot).
- [x] Esecuzione SQL su D1 Studio: una tabella `tv_flow_events` e due indici `idx_tv_flow_events_received`, `idx_tv_flow_events_symbol_close`, lanciando un comando per volta.
- [x] Controllo `sqlite_master` restituisce esattamente 3 righe: tabella + due indici (screenshot 12/11/2026).
- [x] Ultime quote D1 mostrate dall'utente prima della creazione: 1/10 database, 28,67 kB/5GB, 0/5M letture e 0/100k scritture (aggregati dashboard arrotondati). **Non è una misura dopo la creazione**.
- [ ] Test reale di scrittura dal Worker **non ancora svolto**; nessun evento prospettico TradingView confermato. Evitare endpoint diagnostici pubblici e garantire che il database di prova, non quello principale, sia l'unico target.
- [ ] Prossima azione: predisporre Worker di prova separato con binding D1 test e provare solo in preview controllata. Non modificare worker produttivo `remura-tv-ingest-lab`; ricezione `INGEST_ENABLED` resta disattivata. Nessuna PR merge, nessun ordine automatico.

## CHECKPOINT PROVA D1 IN PREVIEW — 12/11/2026, ore 13:22 CET
- [x] Utente ha creato localmente su iPhone un token forte e digest SHA-256; i valori NON sono stati condivisi in chat o nel repository. Dalla UI Cloudflare risulta un secret in Production. La correttezza del valore non è ancora verificata end-to-end.
- [x] Dopo aggiunta secret e deploy isolato del Worker, controlli LIVE: GET `/health` → `{"status":"lab_only","accepting":false}`; GET `/` → `{"status":"disabled"}`. Ingestion ancora OFF; nessun alert TradingView.
- [x] Console D1 `remura-tv-lab`: `SELECT COUNT(*) AS totale_eventi FROM tv_flow_events` → **0** eventi alle 13:01 CET del 12/11/2026 (screenshot utente). Questo prova lettura nella Console D1, non una scrittura Worker.
- [x] Editor Cloudflare: patch `ignoreBOM:false` presente; prova temporanea GET `/__lab_d1_probe` **solo in Preview** con `SELECT COUNT(*)` ha restituito `{"status":"d1_ok"}` secondo l'utente. Verifica accesso di lettura D1 dal Worker nella sessione Preview, **non conferma la scrittura né necessariamente l'identità dell'ambiente DB Production**.
- [x] Codice della diagnostica `/__lab_d1_probe` rimosso dall'editor e screenshot verificato; utente ha chiuso l'editor. Nessun deploy della diagnostica autorizzato o riferito.
- [x] PR #102 verificata DRAFT/OPEN tramite GitHub prima di questo aggiornamento, senza merge.
- [ ] **Prossimo passaggio**: prova scrittura D1 solo su database isolato di staging/Preview, oppure altra procedura esplicitamente approvata, senza contaminare `remura-tv-lab`. La documentazione Cloudflare segnala che Preview con binding D1 allo stesso database ID condivide i dati: non assumere isolamento automatico. Prima verificare quota Free reale e binding Previews Base.
- [ ] Non abilitare `INGEST_ENABLED=true`, webhook TradingView, heartbeat o ordini; non toccare filoni A/B/C o gli altri Worker.

## CHECKPOINT WORKER LIVE MA FAIL-CLOSED — 12/11/2026 10:55 CET
- [x] Due screenshot utente confermano Worker `remura-tv-ingest-lab.mirkoworz.workers.dev` con ricevitore REMURA v0.8.5 distribuito.
- [x] GET `/health` restituisce esattamente `{"status":"lab_only","accepting":false}`:
  Worker raggiungibile e flag ingestion OFF.
- [x] GET `/` restituisce `{"status":"disabled"}`: protezione predefinita fail-closed confermata live.
- [x] Binding Cloudflare D1 `TELEMETRY_DB` → `remura-tv-lab` confermato in precedenza dalla UI; schema tabella + due indici confermati con query di lettura, giurisdizione UE verificata.
- [ ] **Non ancora provata** una lettura/scrittura D1 effettuata DAL Worker, né una consegna webhook:
  `/health` e `/` non interrogano D1. Non dichiarare pipeline funzionante end-to-end.
- [ ] Prima di permettere acquisizione: predisporre segreto forte sul Worker senza inviarlo in chat/GitHub,
  controllo IP, test sintetico senza dati di mercato, riscontro D1 e quota CPU;
  fino ad allora `INGEST_ENABLED` deve restare assente/false.
- [ ] Alert Pine/TradingView e heartbeat restano disattivati, nessun dato prospettico reale.
- [ ] Filoni A/B/C intatti, nessun merge/deploy REMURA app né ordine di trading.


**PR #102 DRAFT/OPEN — NESSUN MERGE O WEBHOOK TRADINGVIEW.**

## CHECKPOINT PATCH EDITOR CLOUDFARE — 12/11/2026 10:52 CET
- [x] Utente ha copiato nell'editor Cloudflare il receiver del branch di ricerca.
  Screenshot del Worker `remura-tv-ingest-lab` mostra errore del
  typechecker `ts(2345)` in `new TextDecoder("utf-8", { fatal: true })`,
  perché il tipo `TextDecoderConstructorOptions` di Workers richiede
  la proprietà `ignoreBOM`.
- [x] [Receiver PATCH v0.8.5](gateway-lab/worker.mjs): sostituito con
  `new TextDecoder("utf-8", { fatal: true, ignoreBOM: false })`.
  Nessuna modifica al contratto JSON Pine `0.8.1-lab`,
  all'autenticazione o al fail-closed.
- [x] Utente ha aggiornato il decoder, confermato l'assenza di errori
  nell'editor e distribuito il Worker; health e disabled verificati con screenshot.
  La patch di tipo è quindi verificata nel codice distribuito.
- [x] Ricevitore v0.8.5 distribuito in produzione del SOLO Worker isolato,
  ma `INGEST_ENABLED` è OFF (risposte health e root). Segreti/config
  autenticazione e accesso reale D1 non ancora verificati: non attivare eventi.
- [ ] Risultato CI GitHub per commit patch da verificare.



**PR #102 DRAFT/OPEN — NO MERGE, NO ORDINI, NO WEBHOOK TRADINGVIEW.**

## CHECKPOINT WORKER CLOUDFARE — 12/11/2026 10:43 CET
- [x] L'utente ha creato e distribuito un Worker Cloudflare separato:
  `remura-tv-ingest-lab`, e ha aperto l'editor. Screenshot mostra soltanto
  il programma standard **Hello World**, non il receiver REMURA.
- [x] Nessun collegamento D1, secret, alert o invio dati è stato verificato;
  il Worker Hello World è pubblicato e non memorizza dati di mercato.
- [x] Confermate le istruzioni ufficiali Cloudflare per collegare un D1:
  pagina del Worker → tab `Bindings` → `Add binding` → `D1 database`.
- [x] **Binding D1 salvato e verificato dallo screenshot Cloudflare**:
  Worker `remura-tv-ingest-lab` → tipo D1 database → variabile
  `TELEMETRY_DB` → valore `remura-tv-lab`; confermato in Settings / Bindings.
  Non toccati `mirko-news-calendar` o `telegram-mirko-bridge`.
- [ ] **Prossimo step**: installare nell'editor SOLO il codice
  `tradingview/delta-peaks/gateway-lab/worker.mjs` dal branch della PR #102,
  con `INGEST_ENABLED` **assente** (runtime variables ancora vuote nello
  screenshot). Il ricevitore deve restare `fail-closed` e `/health` deve
  rispondere `{"status":"lab_only","accepting":false}`; il root endpoint
  dovrebbe restituire 503 (`disabled`). Codice Hello World attuale non
  memorizza dati; evitare webhook/segreti fino a test successivo.
- [ ] Eseguire test HTTP non distruttivi del Worker in isolamento e verificare
  le quote, poi affrontare autenticazione e attivazione controllata.
- [ ] Dopo binding verificato, sostituire Hello World con
  `gateway-lab/worker.mjs` SOLO in stato **INGEST_ENABLED assente/false**.
  Testare endpoint read-only /health, configurare sicurezza e
  secret in passaggi distinti; nessuna acquisizione reale senza autorizzazione.
- [ ] Ricontrollare limite Free dopo deployment del receiver, e test
  locali senza dataset reale.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT D1 UE CONFERMATO — 11/11/2026 18:37 CET
- [x] Screenshot Cloudflare D1 Settings del database ricreato dall'utente:
  **Jurisdiction = The European Union**, **Region = Eastern Europe**,
  **Read replication = Disabled**. Verificata la giurisdizione europea dopo
  sostituzione del precedente DB senza giurisdizione.
- [x] **Nome D1 verificato nella foto della Console: `remura-tv-lab`.**
  Il suffisso `-eu` non è necessario: la giurisdizione UE è già confermata
  dalla schermata Settings. Nessuna nuova creazione/rinomina necessaria.
- [x] **SQL schema D1 eseguito dall'utente nel database `remura-tv-lab`**:
  screenshot Console mostra le tre istruzioni `CREATE TABLE IF NOT EXISTS`
  e `CREATE INDEX IF NOT EXISTS` e il messaggio
  `This query successfully executed` (11/11/2026).
- [x] **Schema D1 verificato mediante query readback in Cloudflare Console**:
  screenshot con risultato SQL di `sqlite_master` mostra esattamente
  la tabella `tv_flow_events` e gli indici `idx_tv_flow_events_received`
  e `idx_tv_flow_events_symbol_close` nel DB `remura-tv-lab`.
  La tabella è pronta, ma nessun invio dati TradingView è ancora attivo.
- [ ] Passaggio successivo: creare un Worker **dedicato e isolato**, senza
  toccare `mirko-news-calendar` o `telegram-mirko-bridge`; verificare
  la modalità di creazione nell'interfaccia prima di distribuirlo.
  Codice receiver `gateway-lab/worker.mjs` è fail-closed, richiede D1,
  secret hash e abilitazione esplicita; nessun webhook Live prima dei test.
- [ ] Gateway/Worker non distribuito, nessun secret, webhook o
  heartbeat attivato. Dati reali non ancora raccolti.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT D1 CREATO DALL'UTENTE — 11/11/2026 18:31 CET
- [x] Screenshot D1 Database Overview dell'utente: database appena
  inizializzato, **0 tabelle**, **0 query**, **0 righe lette**, **0 righe
  scritte**, **12,29 kB** storage base. Da verificare nome effettivo
  `remura-tv-lab` e giurisdizione/location: NON sono visibili
  nel ritaglio dello screenshot. Non dichiarare nome verificato.
- [x] I due Workers preesistenti rimangono intatti.
- [ ] Prossimo passaggio manuale nel database **solo dopo verifica nome**:
  tab `Console`, applicare **solo** SQL non distruttivo
  [schema D1 LAB](gateway-lab/schema.sql) (CREATE TABLE/INDEX IF NOT EXISTS).
  Verificare poi `Number of Tables: 1`; nessun evento memorizzato.
- [ ] Non creare Worker/alert/secret, non abilitare webhook o heartbeat
  finché non sono completati i controlli successivi e autorizzati.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO ORDINI.**

## CHECKPOINT CLOUDFARE FREE ACCOUNT — 11/11/2026, 18:24 CET
- [x] Screenshot forniti dall'utente della dashboard Workers & Pages:
  **204/100.000 richieste oggi** e **301/200.000 eventi Observability oggi**.
  Workers già presenti: `mirko-news-calendar`, `telegram-mirko-bridge`.
  **Non modificare o riutilizzare questi Workers.**
- [x] Screenshot forniti dall'utente della dashboard D1:
  **0/10 database**, **0/5M letture giornaliere**, **0/100k scritture giornaliere**,
  **0B/5GB spazio totale**. Anche la vista mensile mostra 0 DB, 0 letture,
  0 scritture, 0B spazio, alla data 11/11/2026.
- [x] Le quote reali account Cloudflare per Workers+D1 sono state
  verificate **al momento degli screenshot**; limiti futuri e CPU
  dell'eventuale Worker LAB ancora da misurare. Il modello di budget
  resta prudenziale.
- [ ] **Prossima azione esclusivamente manuale dall'iPhone:** creare
  nel piano Free un D1 dedicato `remura-tv-lab`, previa verifica
  dettagli nella schermata `Create Database`. Preferire giurisdizione
  UE, se disponibile; WEUR location hint non equivale a vincolo legale UE.
  NON attivare Worker/alert/webhook, non applicare schema SQL prima
  della conferma della creazione D1.
- [ ] Verificare ID e configurazione del nuovo database **senza
  pubblicare segreti**. Configurazione, schema, Worker e webhook rimangono
  attività successive isolate e autorizzate.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO LIVE, NO ORDINI.**

## CHECKPOINT v0.8.4 (11/11/2026 18:05 CET)
- [x] Aggiunti [QUOTA GUARD gratuito](quota_budget_v1.py) e
  [7 prove automatiche](test_quota_budget_v1.py), per proteggere
  costi/storage durante il futuro pilota `FXCM:EURUSD` M5.
- [x] Stimati limiti con **guardrail interni** 10% richieste e scritture Free
  giornaliere, 65% spazio DB da 500 MB; 20KB/evento, overhead 1.4×,
  ritentativi 1.1×. Un simbolo M5/30gg rientra nel modello; due simboli
  M5/30gg superano lo spazio **prudenziale**, due/14gg rientrano.
  Sono stime massime, non consumo reale account.
- [x] Totale suite automatica prevista: **62 test sintetici**
  (16 schema + 18 esiti + 7 quota + 21 gateway Node).
  Run verde sul codice [#43064598345](https://github.com/mirkoworz/remura/actions/runs/43064598345)
  HEAD `fc6ce03b1e730b3cbf252b799cd38d4bca8c1d74`; test
  confermati sul runner, nessun endpoint realmente collaudato.
- [x] Inventario riutilizzo: in `main` sono presenti configurazione Firebase
  Web e piano Firestore privato Capital.com; non sono una destinazione
  webhook autenticata pronta, né attestano quota disponibile.
  Prima scelta: gateway Cloudflare/D1 di laboratorio isolato; valutare
  accesso REMURA C a dati riassuntivi solo dopo coordinamento.
- [x] Aggiornata [guida gateway](gateway-lab/README.md) con limiti,
  modello risparmio e motivi dell'isolamento.
- [ ] Non sono verificabili da GitHub: **utilizzo reale del tuo account
  Cloudflare**, CPU Worker per request, durata reale D1, consegna alert.
  Occorre il dashboard/account, consenso per deploy isolato e
  successivo test sintetico prima di attivare TradingView.
- [ ] Alert TradingView v0.8.1 resta **telemetryEnabled=false** e
  **heartbeat=false**. Nessun dato prospettico reale raccolto da
  questo filone. Per avviare con affidabilità occorrerà
  prova di consegna e heartbeat di tutte le barre M5.
- [ ] Restano fuori da questo filone A/B/C, merge, deploy e ordini.



**PR #102 DRAFT, OPEN — NESSUN MERGE, DEPLOY, WEBHOOK O ORDINE.**

## CHECKPOINT v0.8.3 — 11/11/2026 18:01 CET
- [x] Verificate oggi le condizioni Workers Free e D1 Free alle fonti
  ufficiali Cloudflare: **100.000 richieste Worker/giorno, 10ms CPU/request;
  D1 5M righe lette/giorno, 100.000 righe scritte/giorno,
  500 MB per database e 5 GB/account, max 10 database Free**.
  Le quote sono condivise; **utilizzo reale account Cloudflare NON VERIFICATO**
  e nessun login/account o deploy è stato effettuato.
- [x] Conservati v0.7 funzionante e Pine v0.8.1 confermato funzionante
  dall'utente; nessuna nuova prova Pine necessaria in questa fase.
- [x] Gateway v0.8.2 Cloudflare/D1 e autenticazione/anti-duplicato rimangono
  **soltanto sorgenti offline**. Prove GitHub CI eseguite, nessun URL webhook
  o database realmente creato.
- [x] Creato [OUTCOME AUDIT v0.8.3](outcome_audit_v1.py) e
  [18 regressioni sintetiche](test_outcome_audit_v1.py); aggiornato
  [protocollo](PROTOCOLLO-PROSPETTICO-V08.md).
  Misura **15/30/60 minuti (3/6/12 M5)** su snapshot chiusi con ricezione
  prospettica entro 120s, OHLC/ATR, MFE/MAE, retest RIFIUTO/ROTTURA/
  INDEFINITO, coorti ER e sostituzioni livello senza look-ahead.
- [x] Mancanza di barre M5, timestamp ricezione, ATR o cambio anchor
  produce **esito mancante**. Livelli riclassificati si valutano con
  identità di nascita, non col rank finale. Nessun esito reale finora.
- [x] Confronto baseline descrittivo solo se abbiamo barre `HEARTBEAT`
  complete della stessa data/fascia UTC prefissata: 00–08 / 08–16 / 16–24.
  Nessuna inferenza di profitto: benchmark a segno permutato, intervalli
  di confidenza e walk-forward OOS **ancora da implementare**.
- [x] Aggiornata CI Python per includere 16+18=34 regressioni sintetiche
  e aggiunte alle 21 regressioni Node del gateway = **55 test**;
  risultato verde [run #43063528207](https://github.com/mirkoworz/remura/actions/runs/43063528207)
  sul commit `b27f2f38c4e9f6c5d06bba2b81a339b1da75477b`.
  Riconfermare sull'ultimo HEAD dopo la modifica roadmap.
- [ ] Verificare quanto già utilizza l'**account Cloudflare** dell'utente:
  nessun plugin Cloudflare disponibile, serve controllo via dashboard
  prima di creare risorse.
- [ ] Approvazione esplicita **solo prima** di creare Worker/D1 o abilitare
  alert/webhook; prima effettuare preflight piano Free e misurare costo/CPU.
- [ ] In futuro: test ricezione sintetica isolata e quote, monitor buchi,
  eventuale heartbeat BAR M5 dopo consenso, esportazione dei record veri;
  solo allora valutare prospetticamente ER/RT.
- [ ] Filoni A/B/C, REMURA live e trading automatico rimangono intatti.



**PR #102 DRAFT, OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT CONFERMATO — 11/11/2026 17:52 CET
- [x] **Pine v0.8.1 compila e funziona in TradingView**, conferma esplicita dell'utente il 11/11/2026 dopo l'ultima prova. Non richiedere nuovamente questo controllo; il payload runtime e la consegna webhook **NON** sono ancora testati.
- [x] Verificati i requisiti TradingView: webhook JSON `application/json`, 2FA, timeout remoto 3 secondi, quattro IP pubblicati ufficialmente, porte 80/443; chiamate possono essere perse.
- [x] [Creato GATEWAY LAB v0.8.2](gateway-lab/README.md) Workers + D1 come codice offline: [receiver](gateway-lab/worker.mjs), [schema](gateway-lab/schema.sql) e [21 test sintetici](gateway-lab/worker.test.mjs), senza token, webhook URL, account cloud o deploy.
- [x] Sicurezza fail-closed, IP allowlist + hash token solo configurabile fuori repository, schema JSON versione, body limit 20KB, controllo tempi, deduplica tramite D1, limite best-effort 20 record/min, nessun accesso remoto ai dati né routing a B/C.
- [x] Aggiornata GitHub Actions `.github/workflows/remura-tv-telemetry-lab.yml` per eseguire **16 test Python + 21 test Worker Node** (no network/no third-party dependencies); run verde [43062097541](https://github.com/mirkoworz/remura/actions/runs/43062097541) per SHA `633ae6cae73934f5746dedb79a848a41c6c881b7`. Le successive esecuzioni su nuove modifiche vanno verificate di nuovo.
- [x] Confronto quote ufficiali Cloudflare Workers Free: 100k richieste/giorno, 10ms CPU; D1 Free: 5M righe lette/giorno, 100k righe scritte/giorno; quote condivise con eventuali altre risorse. Nessun costo o risorsa cloud nuovi.
- [ ] Verificare **CI finale** dopo ultime modifiche alla documentazione/test, senza confondere i mock locali con un endpoint reale.
- [ ] **NON AUTORIZZATO:** creare Worker/D1, impostare segreti, attivare Cloudflare o TradingView webhook: prima verifica quote e decisione esplicita dell'utente.
- [ ] Prima attivazione futura: prova endpoint isolato e payload sintetico; verificare che consegna, token/allowlist, latenza <3s e storage siano corretti. Tutto senza REMURA live.
- [ ] Per studio prospettico completo serviranno **tutte le barre M5** (heartbeat TradingView inizialmente OFF), monitoraggio gap, ER/RT 3/6/12 barre, falsi positivi, replacement drift e benchmark; attivare soltanto nella finestra di ricerca concordata.
- [ ] Nessuna modifica ai filoni A/B/C, nessun trade o promessa statistica; confrontare livelli WEEK/MONTH con metodo del collaboratore dopo acquisizione prospettica.



**PR #102 DRAFT, OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT v0.8.1 — 11/11/2026 16:26 CET (SOLO OFFLINE)
- [x] Verificata PR #102 DRAFT/OPEN, branch `research/tradingview-delta-peaks-20261111`, v0.7, manuale, schema e piano webhook; v0.7 resta conservata senza modifiche.
- [x] Creato [REMURA v0.8.1 TELEMETRY](REMURA-ALL-IN-ONE-Premium-v0.8-TELEMETRY.pine) come nuovo script **separato**, `telemetryEnabled=false` e heartbeat OFF di default; `alert()` JSON solo a candela chiusa/realtime.
- [x] Un solo JSON per M5 confermata, per non perdere eventi simultanei con frequenza once_per_bar_close; include OHLC+prev_close+ATR, delta, ER, footprint, snapshot livelli, origine dei livelli, punteggi DAY, nuovi livelli/sostituzioni e flags per quattro tipi di retest.
- [x] Conservati 4 `alertcondition()` legacy, una `request.footprint()` e una `tv.requestVolumeDelta()` (verifica statica).
- [x] [PROTOCOLLO PROSPETTICO](PROTOCOLLO-PROSPETTICO-V08.md): regole **congelate prima degli esiti** per ER e RT 3/6/12 M5, falsi positivi, benchmark e replacement drift; dati **simulati non validi** come prove di efficacia.
- [x] Creati [validatore Python](validate_telemetry_v1.py) e [16 test sintetici](test_telemetry_v1.py) senza dipendenze terze.
- [x] Aggiunto workflow GitHub Actions *solo su file di questo laboratorio* `.github/workflows/remura-tv-telemetry-lab.yml`, sola lettura, no segreti, no deploy, per regressioni Python; runner GitHub standard pubblico gratuito secondo documentazione ufficiale.
- [x] Verifica pubblica quote: Workers Free 100.000 richieste/giorno e 10ms CPU/req; D1 Free 5 milioni righe lette/giorno, 100.000 scritte/giorno, 5GB account **e 500MB/database**; oltre quota il Free blocca operazioni. Nessuna nuova risorsa creata.
- [x] **CI verificata VERDE**: run [43048503823](https://github.com/mirkoworz/remura/actions/runs/43048503823) per HEAD `aaae10c4e6d59951e0b0bb0d4a2c07be27ead5a3`: regressioni sintetiche Python + `py_compile` completati con successo. NON è una compilazione Pine.
- [x] **Pine v0.8.1 COMPILATO in TradingView**, funzionamento confermato esplicitamente dall'utente il 11/11/2026; verifica ancora da fare sul JSON generato a runtime e webhook, senza creare alert.
- [ ] Gateway di test: definire autenticazione sicura compatibile TV, con IP allowlist, body/rate limit, D1/KV retention e deduplica; verificare il consumo di risorse condivise prima di un qualsiasi deploy.
- [ ] Misurazione reale **NON AVVIATA**: può iniziare solo dopo receiver autorizzato, conservazione eventi real-time, e feed M5 prospettico per barre senza eventi.

### Blocco rigoroso prima del collegamento REMURA B/C
Le misurazioni a 15/30/60 minuti devono includere **ogni evento**, non soltanto vincitori.
Finché non emergono confronti out-of-sample credibili, REMURA non deve trasformare
ER+, ER-, POC o RT in ordini o probabilità di successo. Filoni A/B/C non modificati.
Il Free Trial Oracle con scadenza prevista 15/11/2026 è seguito dal Filone A.




## CHECKPOINT CONFERMATO — 11/11/2026, ore 13:55 CET

- [x] **L'utente conferma che la v0.7 funziona** nel Pine Editor/TradingView su FXCM:EURUSD M5, incluse le linee giornaliere. **È una conferma di funzionamento UI, non di correttezza statistica del metodo.**
- [x] Pubblicato il [MANUALE DI STUDIO v0.7](MANUALE-V07-ORDER-FLOW.md): spiegazione puntuale della tabella, regole, sorgenti e protocollo manuale sui livelli/ritorni. CVD eventuale del grafico nativo resta separato dal Pine.
- [x] Creato il [PIANO WEBHOOK TradingView → REMURA](PIANO-WEBHOOK-REMURA.md): JSON dinamico con `alert()`, eventi chiusi, gateway HTTPS e archivio senza attivazione live. PR #102 resta DRAFT.
- [ ] **Prima implementazione successiva**: verificare schema eventi/bar-close, generazione JSON offline, ricezione in test (nessun segreto in GitHub), non attivare ordini o webhook live prima di sicurezza e consenso.
- [ ] Misurazione prospettica su ER e retest DAY a 15/30/60 minuti, benchmark e fallimenti; considerare anche riclassifica dei livelli TOP3 durante la sessione.
- [ ] Verificare una seconda volta su TradingView modalità `HL2` vs `POC FOOTPRINT`, cambio giorno e disponibilità PREVIOUS DAY/MONTH, non sovrapporre retrospettiva al live.

**Prossimo filone TradingView**: v0.8 TELEMETRY JSON verso gateway di test isolato, poi scoring REMURA B/C solo dopo qualità dati validata. Nessun merge, deploy, acquisto o operazione di trading autorizzata. Il periodo Oracle Free Trial previsto in scadenza 15/11/2026 resta responsabilità del Filone A, quindi la nuova architettura deve tollerare un'eventuale assenza VPS.

## NUOVO CHECKPOINT — v0.7 DAY DELTA PEAKS (11/11/2026 13:19 CET)

- [x] Creato [REMURA-ALL-IN-ONE-Premium-v0.7.pine](REMURA-ALL-IN-ONE-Premium-v0.7.pine), lasciando v0.6 intatta.
- [x] **Top3 DAY** su `abs(delta intrabar)` di barre confermate: linee viola, arancione e azzurra dinamiche, filtro minimo 1.5x, nessuna modifica alle metriche ER esistenti.
- [x] **PREVIOUS DAY** massimo in grigio puntinato e reset di giornata al `timeframe.change("1D")`.
- [x] **Retest**: prima intersezione confermata del range High-Low su livelli gia' creati, soltanto da candele successive; marcatori RT, conteggi e quarta condizione di alert.
- [x] **Vista COMPLETO** ampliata ai tre DAY, precedente giorno, conteggi di retest e storico eventi. Conservo le viste isolate RADAR/FOOTPRINT.
- [x] Test strutturali di codice e cardinalita' di chiamate: un solo Footprint, un solo Delta intrabar, una tabella, 4 condizioni di alert.
- [x] **Compilazione e funzionamento v0.7 confermati verbalmente dall’utente** su `FXCM:EURUSD` M5; mancano test quantitativi e verifica completa dei singoli contatori/edge case.
- [ ] Controllare il cambio sessione/giorno, storico parziale, POC N/D e possibili livelli coincidenti.
- [ ] Registrare prospetticamente ogni retest e valutare reazione successiva a 3/6/12 barre senza modificare parametri a posteriori.
- [ ] Confrontare i livelli DAY/WEEK/MONTH coi video di riferimento; distinguere picco di barra da delta cumulativo del periodo.

**Regole scientifiche**: livelli selezionati solo dopo chiusura; la loro classificazione puo' cambiare con nuovi massimi, percio' in analisi prospettica salvare sempre il momento in cui un livello e' nato e quello in cui e' stato sostituito. Le linee non sono ordini istituzionali osservati. Costi addizionali zero, PR #102 DRAFT, no merge/deploy.

## CHECKPOINT v0.6 — ALL-IN-ONE Premium (11/11/2026, ore 12:58 CET)

- [x] Verificato che la precedente v0.5 conteneva gia' i calcoli WEEK/CURRENT MONTH/PREVIOUS MONTH, ma erano leggibili in tabella solo dalla vista RADAR.
- [x] Creato **[REMURA-ALL-IN-ONE-Premium-v0.6.pine](REMURA-ALL-IN-ONE-Premium-v0.6.pine)** separato, senza sostituire i file testati.
- [x] Aggiunta vista default `COMPLETO` con delta intrabar e footprint, Sforzo/Risultato, POC/VAH/VAL, imb, 3 livelli e 3 eventi.
- [x] Conservate viste `FOOTPRINT` e `RADAR`, disegno dei tre livelli, marcatori ER e 3 alert confermati.
- [x] Verificati riferimenti statici: **1 request.footprint**, **1 requestVolumeDelta**, **1 table**, 4 marcatori e 3 alert.
- [ ] Prova **reale di compilazione v0.6** in TradingView EURUSD FXCM M5 e verifica della vista COMPLETO, delle linee e delle altre due viste.
- [ ] Validare visivamente il PREVIOUS MONTH con sufficiente profondita' storica (puo' essere parziale).
- [ ] Stabilire il protocollo di misurazione prospettica ER a 3, 6, 12 barre M5, senza cambiare retroattivamente le soglie o usare dati futuri.
- [ ] Confrontare definizione dei livelli coi video del metodo del collaboratore.

**Vincoli**: no merge/deploy e nessuna modifica ai filoni A/B/C. Nessun nuovo costo; Premium gia' posseduto dall'utente. Il Footprint Forex resta classificazione intrabar del feed, non dati ordini istituzionali CME. Prossima fase statistica senza promettere profitti.

## Nuovo checkpoint visuale v0.5 — 11/11/2026 12:48 CET

- [x] **FOOTPRINT v0.5 visibile e dati nativi presenti** su `FXCM:EURUSD` M5 (screenshot utente). Indicatore `REMURA Order Flow Radar Premium LAB v0.5` compilato e pannello presente.
- [x] Verifica qualitativa di Buy 92, Sell 109, Delta -17, Delta/Volume circa -8,5%, 0 righe BUY imbalance e 0 righe SELL imbalance su candela LIVE. POC/VAH/VAL visibili: dati provvisori, nessuna interpretazione istituzionale.
- [ ] Verificare **vista RADAR** del medesimo script v0.5 e confronto dei marker ER con v0.4.
- [ ] Verificare variazioni durante la candela e dati della candela chiusa; differenze footprint vs delta stimato.
- [ ] Avviare protocollo di misurazione a 3/6/12 barre (M5), prima ipotesi e benchmark fissati *prima* di interpretare gli esiti.

Nota: nel grafico l'utente ha attivato anche il tipo **Footprint volume nativo**. Le celle colorate appartengono al tipo di grafico TradingView, NON alla tabella disegnata dallo script Pine.

## Checkpoint
- [x] Laboratorio indipendente `tradingview/delta-peaks/`, PR #102 DRAFT.
- [x] **v0.1**: primo indicatore con delta stimato, segnalazioni ER e livelli, verificato in screenshot TradingView.
- [x] **v0.2**: soglia delta su 30 barre precedenti, distanza minima 6 barre, riduzione rumore.
- [x] **v0.3**: formule numeriche Sforzo/Risultato/Efficienza e test visivo su EURUSD FXCM M5.
- [x] **v0.4**: radar con colorazione dinamica delta, intensita' 1–5, picchi arancioni, anomalie viola, stato LIVE/CONFERMATO, storico di 3 picchi confermati, barre colorate solo su richiesta.
- [ ] **Compilazione v0.4** e screenshot del radar durante una barra aperta e alla chiusura.
- [ ] Verificare l'assenza di segnali aggiunti o rimossi rispetto a v0.3 a parametri identici.
- [ ] Verificare gestione di dati NA/zero, ATR non disponibile, storico intrabar limitato, cambio timeframe e ricarica.
- [ ] Confrontare livelli WEEK/CURRENT MONTH/PREVIOUS MONTH con i video del metodo di riferimento.

## Codice v0.4
- **Sforzo**: `abs(deltaBar) / SMA(abs(deltaBar[1]), 30)`.
- **Risultato**: `sign(deltaBar) * (close - open) / ATR(14)`.
- **Efficienza**: `Risultato / Sforzo`.
- **ER**: Sforzo >=3.5, Efficienza <=0.07, gap minimo 6 barre e barra confermata.
- **LIVE**: anteprima aggiornata mentre la candela e' aperta, mai salvata come segnale definitivo.
- **CONFERMATO**: marcatori, allarmi e ultime 3 anomalie/picchi solo a barra chiusa.
- **Livelli**: per ora massimo |delta| della candela in periodo, prezzo hl2, non un livello istituzionale identificato.

## Test Premium riuscito e integrazione v0.5 (11/11/2026, ore 12:40 CET)

- [x] `REMURA-Footprint-Premium-Probe.pine` si compila e produce dati in TradingView su **FXCM:EURUSD M5** (screenshot utente). POC/VAH/VAL e imbalance valorizzati; sulla candela LIVE osservati buy 16, sell 23, delta -7, POC 1.11335, VAH 1.11340, VAL 1.11330, BUY IMB=0, SELL IMB=1.
- [x] Creata **[REMURA-Order-Flow-Radar-Premium-v0.5.pine](REMURA-Order-Flow-Radar-Premium-v0.5.pine)** come nuovo file separato. Condivide in un unico script il radar v0.4 e i campi Footprint Premium, con viste RADAR/FOOTPRINT selezionabili; una sola `request.footprint()`.
- [x] Preservati ER, marcatori, ultimi tre picchi, livelli Week/Monthly e alert solo su barre confermate.
- [ ] **Test compilazione** v0.5 in Pine Editor + screenshot delle viste FOOTPRINT e RADAR; controllare feed N/D e aggiornamento LIVE.
- [ ] Confronto su alcuni eventi della differenza tra delta intrabar stimato e footprint (non forzarne uguaglianza).
- [ ] Valutare se POC/imbalance migliorano la capacità di leggere Sforzo/Risultato in modo prospettico, senza introdurli ancora nei segnali.
- [ ] Definire le metriche di efficacia a 15/30/60 minuti su dati prospettici e procedere alla loro misurazione. Includere falsi positivi e benchmark.

**Limite:** footprint FXCM non identifica esecuzioni CME o banche. v0.5 ancora senza test sul grafico; resta una ricerca separata in PR #102 DRAFT.

## Nuovo filone Premium — test footprint (11/11/2026 11:58 CET)
- [x] Confermata da documentazione TradingView disponibilita' di `request.footprint()` per piano **Premium**.
- [x] Creato **[REMURA-Footprint-Premium-Probe.pine](REMURA-Footprint-Premium-Probe.pine)** su questo ramo: prova isolata di BUY/SELL classificati, delta footprint, POC, VAH/VAL, conteggio imbalance per riga.
- [ ] **Compilare il test** in TradingView su `FXCM:EURUSD` M5 e verificare che non sia tutto N/D; acquisire screenshot.
- [ ] Ripetere, se possibile, su un future CME con dati autorizzati e distinguere volume reale da tick volume forex. **Non acquistare feed senza preventivo e autorizzazione.**
- [ ] Confrontare i delta della v0.4 (requestVolumeDelta con 1m) con il delta footprint nativo (granularita' interna differente), senza sommarli o considerarli uguali.
- [ ] Solo dopo prova positiva: pianificare integrazione POC/imbalance in una **v0.5 del RADAR**, mantenendo toggle e fallback N/D, e successiva misurazione prospettica ER a 15/30/60 minuti.

Il piano Premium e' gia' attivo secondo l'utente; **nessun ulteriore abbonamento** necessario per la funzione Pine Premium. L'accesso a particolari dati futures CME in tempo reale potrebbe richiedere un abbonamento dati distinto. Nessun deploy di REMURA live.

## Registro nuovo
- **11/11/2026 11:58 CET — Footprint Premium PROBE v0.1**: aggiunta una prova nativa autonoma alla PR #102 DRAFT; Radar v0.4 lasciato invariato. Attesa compilazione in TradingView.

## Fase successiva — MISURA
1. Definire ora, prima di osservare i risultati, una metrica per ogni evento ER confermato: prezzo, delta, effort, efficiency, ATR, simbolo, timeframe, istante e origine del feed.
2. Misurare reazioni a **3, 6 e 12 barre M5** (15/30/60 minuti), MFE/MAE e spostamento in ATR, senza classificare ER+ come SELL o ER- come BUY senza test.
3. Confrontare con le normali candele e con picchi non-ER; includere i falsi positivi e la dipendenza da sessioni e notizie.
4. Documentare versione e parametri per evitare ottimizzazioni retrospettive.
5. Dopo: valutare la fedelta' alla metodologia Week e Monthly con esempi verificabili, eventuali modifiche ai livelli e solo poi integrazione REMURA.

## Regole del laboratorio
- Priorita' al gratuito, monitorare quote e limiti TradingView prima di usare alert o webhook.
- Nessuna dichiarazione di ordine istituzionale da tick volume/volume FXCM.
- No merge, deploy, credenziali, webhook o modifiche ai filoni A/B/C.
- Sempre versione e data/ora CET/CEST in testa a script e documenti.
- Compilazione in Pine Editor e comportamento LIVE vanno osservati separatamente dai test di statistica e predittivita'.

## Registro
- v0.1 — 11/11/2026 08:41 CET: prototipo.
- v0.2 — 11/11/2026 08:54 CET: selezione picchi e pulizia.
- v0.3 — 11/11/2026 09:03 CET: metriche ER.
- 11/11/2026 09:39 CET: screenshot di v0.3, compilazione e grafico apparentemente corretti.
- **v0.4 — 11/11/2026 11:26 CET**: Order Flow Radar colorato, LIVE/CHIUSA, intensita' e registro ultimi tre picchi. **In attesa di compilazione sul grafico**.
