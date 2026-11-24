# REMURA C — v1.00 LAB · checkpoint operativo e unico pilot minimo
**23 novembre 2026 · Europe/Rome · STAGING NON ATTIVO · NO MERGE**

## Stato verificato sul codice
- Head della v0.99 al checkpoint: `a374abecee4d414b82f547f2aa39550b8634a50d`.
- 11/11 v0.99 eseguiti su GitHub Actions run 45252246730: GET sintetici, **non** Access reale.
- Nuovo modulo `private_worker_pilot_profile_integrity_v100_lab.mjs`: profilo CONTRIB con `can_recover=true` o capacità non booleane ora nega **anche GET** di HTML/JS, anziché affidarsi soltanto alle verifiche POST. Riuso dello **stesso** `profileRead`; zero letture D1 aggiuntive attribuite a questo specifico wrapper, **non** zero costo complessivo delle altre composizioni.
- Solo 4 nuovi casi mirati, GitHub Actions 45255017949 **SUCCESS**, workflow v1.00; le 11 prove v0.99 non sono state ripetute.
- Nessun `export default fetch`, nessun nuovo Worker attivo, Access/DB reali non verificati.

## Blocco di sicurezza esterno da risolvere PRIMA di qualunque deploy
1. **Billing Free**: aprire nella propria dashboard Billing/Subscriptions e confermare piano, add-on e costo totale effettivo; Access Free 1/50, Workers e D1 osservati il 23/11 sono solo screenshot temporanei, non certificazione dei costi. Mantenere il buffer 25% quando applicabile.
2. **Topologia Access**: inventariare tutte le destinazioni effettive (Worker, preview, custom domain e workers.dev) e policy effettive, comprese bypass/service token. Preferire Access applicato al Worker intero, non solo a un percorso esposto; default deny. Non attivare nulla in questa fase.
3. **Autenticazione runtime**: Cloudflare `ctx.access` è disponibile soltanto sulla richiesta **direttamente autenticata** dal Worker. Il router interno Workers Static Assets non inoltra `ctx.access` al Worker applicativo; non far dipendere la prova di autenticazione da asset binding o service binding. Verificare `ctx.access.aud`, `getIdentity()`, `account_id`, `user_uuid`, `service_token_status` e `email` **reali** prima di supporre che coincidano con le fixture.
4. **SESSIONE / REVOCHE**: sessione Access e ruolo/autorizzazioni nel D1 sono due barriere indipendenti. Escludere l'identità dalle policy, revocare il ruolo nel D1 e revocare le sessioni Access. Il solo logout, la sola eliminazione seat o la sola revoca token **non** sono prove di blocco del login futuro.
5. **Protezione contenuti**: un CONTRIBUTOR legge le pagine pubbliche REMURA e solo i suoi endpoint protetti; nessuna API privilegiata di prezzi, amministrazione, segreti o modifica COT deve attraversare la superficie protetta dei CONTRIBUTOR. Provare HTTP reali, non la sola assenza di pulsanti.

Documentazione Cloudflare ufficiale verificata il 23/11:
- https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/

## Sequenza minima: 1 OWNER + 1 CONTRIBUTOR (soltanto dopo nuova autorizzazione specifica)
**Gate 0 — sola lettura**: fatturazione Free, quote e topologia Worker/Access/D1. Nessuna query GraphQL non autorizzata. Se costo o binding incerto = STOP.

**Gate 1 — cambi autorizzati separatamente**: un solo staging isolato, una singola identità di test CONTRIBUTOR e OWNER distinto, D1 di staging isolato e feature flag esplicito. Backup e revoca pronti prima del primo test. Nessuna produzione.

**Gate 2 — login e lettura**: login/logout da Safari iPhone, risposta autenticata OWNER, CONTRIBUTOR e ANON; 403 backend reali per pagine e JS OWNER ai CONTRIBUTOR; controlli cache `no-store` e `nosniff`. Un HTTP 200 imprevisto = STOP.

**Gate 3 — unica proposta di prova**: CONTRIBUTORS invia un solo livello controllato, vede ricevuta persistente e soltanto i propri record. OWNER vede coda/audit, approva/rifiuta; vietate auto-approvazione, sovrascrittura e retry cieco di POST incerti. Un errore = STOP.

**Gate 4 — revoca completa**: D1 revocato, politica Access negata, token/sessioni revocati; test vecchia scheda GET/POST 403 e nuovo login negato dopo la finestra di propagazione. Se non verificato = STOP.

**Gate 5 — quote e rollback**: misurare CPU Workers e righe D1 del singolo percorso, verificare Billing e rollback completo. Solo dopo si valuta il secondo CONTRIBUTOR.

## Release integration warning
Con base main `4f8d8a707789eec29686a1568c4b8441e4c7d684`, il ramo C risulta divergente (**504 commit avanti, 31 indietro**, confronto GitHub 23/11). **NON fondere direttamente** e NON trascinare nel rilascio la storia di 504 commit. Una futura integrazione va selezionata tramite allowlist di moduli, audit dei loro import e build su ramo release creato da main SOLO previo consenso a merge/deploy. PR #105 resta Draft.

**NO-GO reale confermato**. Questa nota è un checkpoint operativo, non un'autorizzazione ad attivare la rete.

## Evidenza Billing UI — 23/11/2026 21:06–21:07 CET (Europe/Rome)
Osservazione visiva dell'OWNER in **Cloudflare Billing → Subscriptions**, tab *Subscribed* e *Available*, da iPhone. Il repository registra **solo un riepilogo non personale**, non gli screenshot e non i metodi di pagamento.

- **Subscribed:** `Workers Free — Active`; `Teams Free Base — Renews on Dec 15, 2026`.
- **Available:** `Workers Paid` ($5/mese + usage) e `Workers for Platforms` ($25/mese + usage), con pulsante `Add`: **non risultano sottoscritti** nello screenshot; non sono stati attivati.
- **Accertato:** nessun abbonamento Workers Paid/Workers for Platforms visibile fra gli abbonamenti sottoscritti. La scheda mostra che l'account utilizza i due piani Free elencati.
- **Non accertato:** importi `Billable usage`, `Invoices`, `Spend limits`, eventuali consumi di altri prodotti e fatturazione effettiva totale. Presenza di piani Free **non prova** che tutte le possibili voci di utilizzo siano a €0.

**Gate 0**: `FREE_SUBSCRIPTIONS_VISIBLE`, `BILLABLE_USAGE_UNKNOWN`, `NO_GO_REAL_PILOT`. Prossimo controllo indispensabile e **solo lettura**: aprire `Billable usage` e verificare le voci di costo/importo del periodo, senza premere `Upgrade`, `Add` o cambiare impostazioni. Il controllo non autorizza modifiche Access, Worker/D1, creazione utenti, SQL, merge o deploy.

## Evidenza parziale Billable usage — 23/11/2026 21:08 CET
Osservazione visiva da due schermate Safari dell'OWNER in **Cloudflare Billing → Billable usage**, selezione **Current Month**, grafici **Daily**. Queste immagini mostrano una porzione della pagina, non un totale complessivo di fatturazione; nessun dato personale e nessuna schermata sono salvati nel repository.

- **Argo traffic**: dicitura esatta `Cumulative total this month: 0 B`, grafico giornaliero piatto a 0 B.
- **Spectrum**: dicitura esatta `Cumulative total this month: 0 B bytes`, grafico giornaliero piatto a 0 B.
- **Significato limitato**: risultano 0 byte nelle **due specifiche metriche** Argo e Spectrum osservate. I byte trasferiti non sono l'importo in euro né provano utilizzo gratuito di **Workers, D1, Zero Trust Access o altri prodotti**.
- **Stato costi complessivi**: **UNKNOWN**; negli screenshot non è visibile un totale fatturabile, né un eventuale elenco completo delle altre voci. Non sostituire `UNKNOWN` con 0 €.

**Gate aggiornato**: `SUBSCRIPTIONS_FREE_VISIBLE` + `ARGO_BYTES_0` + `SPECTRUM_BYTES_0`; `TOTAL_BILLABLE_USAGE_UNKNOWN`, `REAL_PILOT_NO_GO`. Unica verifica manuale ancora utile e autorizzata in sola lettura: cercare nella parte superiore di `Billable usage` o in `Invoices` il totale monetario/altre voci del periodo di fatturazione (non serve inviare dati di carta o personali). Nessun upgrade, aggiunta prodotto, deploy, Cloudflare API, D1 SQL o utente reale autorizzato.

## Verifica documentale del contratto Cloudflare Access — 23/11/2026
Fonti ufficiali:
- https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/application-token/

**Confermato sul contratto del provider, NON sulla nostra configurazione runtime**:
- `ctx.access` arriva soltanto al Worker chiamato direttamente dopo l'autenticazione Access; non attraversa Service Bindings, RPC né il router interno Workers Static Assets. Il progetto v1.00 dipende da `ctx.access` e da `ctx.access.getIdentity()`: un futuro build con `assets` nel Wrangler manifest può bloccare la funzione anche con Access attivo.
- L'oggetto di identità documentato espone `email`, `user_uuid`, `account_id`, `service_token_id`, `service_token_status`. Questo è coerente con i nomi verificati nel modulo `access_binding_candidate.mjs`, **ma il valore e la presenza dei campi su un login reale restano non verificati**.
- La politica Access va controllata anche su `workers.dev`, preview, custom domain e override più specifici; policy configurate come bypass possono annullare l'assunzione di tutela.
- Il futuro manifest di staging deve escludere il router Static Assets e dichiarare ESPLICITAMENTE Access Worker-level, D1 di staging e nomi reali di AUD/account, con segreti solo nel provider. Il codice attuale rimane intenzionalmente inerte e NON è un bundle da distribuire.

**Decisione**: niente altro ciclo di prove sintetiche per la stessa proprietà. Il prossimo gate che può confermare l'interoperabilità è il test autentico su un URL di staging isolato, dopo consenso specifico. `CLOUDFLARE_RUNTIME_NOT_VERIFIED`.

## Blocco operativo: gate OFFLINE nel router — 23/11/2026
**Evidenza nel codice esistente, NON test live:**
- `private_worker_router_v096_lab.mjs` e `private_worker_pilot_owner_guard_v098_lab.mjs` richiedono letteralmente `env.PRIVATE_WORKER_V078 === 'OFFLINE_FIXTURE_ONLY'`, tanto per GET quanto per POST.
- `private_worker_pilot_profile_integrity_v100_lab.mjs` usa tali router senza cambiare quel flag. Quindi v1.00 **non è ancora una configurazione staging realmente attivabile**: è sbagliato trattare il solo cambio Wrangler/Secret come sufficiente.
- L'entrypoint `staging_identity_worker.mjs` già presente con un altro gate `IDENTITY_ONLY` è un probe di sola identità distinto, **non** un frontend Contributors completo e non prova la composizione v1.00.
- **Azione tecnica futura obbligatoria:** definire una modalità `STAGING_AUTHENTICATED` separata dall'harness offline, legarla a validazione Access diretta e ambiente isolato, negare tutte le rotte in assenza di campi/provider verificati, e rendere espliciti i passaggi di approvazione per POST e revoca. La modifica deve essere testata su un Worker reale solo dopo nuova autorizzazione; non sovrascrivere il gate attuale in modo non auditato.
- Non attivare `OFFLINE_FIXTURE_ONLY` sul Worker reale per simulare un permesso di deploy. Nessun cambio runtime o Cloudflare effettuato ora.

**Decisione C**: la sicurezza offline è pronta come composizione, la **deployability controllata è un blocco reale ancora aperto**, da chiudere prima del Gate 1. Evitiamo altre suite sintetiche che non provano Access. Il checkpoint D separato **PR #113 Draft** rappresenta invece una release UI candidata; non abilita login Contributors.

## Incremento v1.01: GET autenticato isolato, POST interamente chiuse
**23 novembre 2026 · Europe/Rome.** Nuovo codice `private_worker_staging_readonly_v101_lab.mjs` su questo stesso ramo C; nessuna modifica dei vecchi router v0.96/v0.98/v1.00.
- Candidato di **Worker diretto** `privateReadOnlyStagingV101`, privo di `export default fetch` e di configurazione Wrangler/deploy. Accetta solo GET di **quattro pagine private esistenti e dei loro asset allowlisted**; ogni POST, PUT, PATCH, DELETE, OPTIONS e URL non previsto è respinto con HTTP 403.
- Gate necessari: `PRIVATE_WORKER_V078=STAGING_AUTHENTICATED_READONLY`, `STAGING_ENABLED=D1_CANDIDATE`, `CONTRIBUTORS_STAGE_READONLY=EXPLICIT_STAGING_ONLY`, `STAGING_ORIGIN` HTTPS esatto, binding `CONTRIBUTORS_DB`, `ctx.access` diretto con audience prevista. **Le stringhe di configurazione non sono una prova di autorizzazione OWNER**.
- Integrazione runtime candidata con gli **esistenti** `accessBinding`, `profile` e `privateAssetFilesV096`: Access verifica dati identità/consistenza HMAC, D1 fornisce ruolo fresco per ogni GET (revoca D1 blocca la GET successiva). Non legge ruolo da header o storage browser.
- Il modulo nuovo **non** modifica il flusso di invio/ricevute/approvazione: i gestori delle POST v0.96/v0.98 e a valle rimangono `OFFLINE_FIXTURE_ONLY`. Questo è intenzionale: il percorso reale di scrittura richiede un rilascio di sicurezza separato.
- Nuovi test isolati `test_private_worker_staging_readonly_v101_lab.mjs`: **7/7, GitHub Actions 45260701997 SUCCESS**. Verifica ruoli, asset, GET/POST, origine, Access assente, capability contraddittorie e revoca sintetica. **Non misura autentici JWT/sessioni Access, né l'ownership persistente sul D1 reale**.
- Ancora **NO-GO** alla distribuzione reale: manca il build Wrangler auditato con nessuna sezione `assets`, il binding D1 staging isolato verificato, le vere policy Access e il collaudo Safari con un'identità OWNER e una CONTRIBUTOR. I file HTML privati riusati riportano ancora il banner LAB e vanno coordinati con un timbro v1.01 e un testo di stato veritiero **prima** di un'attivazione pubblica/privata.

Percorso di prova minima futura, **solo dopo autorizzazione distinta**: un solo Worker staging privato Access protetto, GET OWNER e CONTRIBUTOR + denial incrociati + revoca; **zero invii e zero approvazioni** nella prima sessione. Solo dopo si può valutare separatamente l'abilitazione delle POST con ricevuta persistente e audit.


## 23/11/2026, 22:22 CET — v1.02 candidate Worker entrypoint (NO DEPLOY)
- Creato `staging_readonly_entry_v102_lab.mjs`: **entrypoint reale compatibile con Workers ES Modules**, che usa la composizione GET-only v1.01 e respinge a monte ogni metodo diverso da GET. Richiede configurazione staging esplicita, Access diretto autenticato, audience/account/HMAC presenti e binding D1.
- Creato `wrangler-v102-STAGING-TEMPLATE.toml` **intenzionalmente non distribuibile**, con `workers_dev=false`, `preview_urls=false`, nessuna route, nessun `assets` e database_id invalido `REPLACE_ONLY_AFTER_SEPARATE_APPROVAL`.
- Nessun URL/utente/Access/Worker/D1 realmente creato o modificato, nessun Secret incluso.
- CI nuova `45268908051`: **SUCCESS, tre test aggiuntivi** su gate senza identità, metodi di scrittura e manifest chiuso. Le sette prove v1.01 restano attestate da `45260701997` e non sono state ripetute.
- **FUTURO GATE MANUALE OBBLIGATORIO**, dopo autorizzazione specifica: OWNER conferma policy Access sul Worker, identità OWNER + CONTRIBUTOR distinte, dominio/route diretto, database staging isolato, autorizza eventuale build/deploy, prova Safari login/logout e blocchi HTTP. Fino allora v1.02 `INERT_LAB/NO_GO`.
- Le richieste POST per proposte livelli, ricevute, approvazione, audit e revoca restano disabilitate; non vendere questa build come pilot completo.


## Incremento v1.03 — interfaccia di staging realmente non interattiva
**Checkpoint: 23 novembre 2026, 23:05 CET (Europe/Rome).** Non pubblicato.
- Trovato un problema concreto prima di un pilot: `private_assets_v096_lab.mjs` conteneva ancora **4 pulsanti type=submit in 2 pagine livelli**, oltre a JS client che poteva tentare POST (nonostante il Worker GET-only respingesse tutto).
- Creato `private_worker_staging_saferead_v103_lab.mjs`: dopo autenticazione Access e autorizzazione ruolo tramite `privateReadOnlyStagingV101` + D1 fresco, restituisce pagine HTML di consultazione senza **alcun** `<form>`, `<script>`, `<button>` o `<input>`. Banner visibile **v1.03 / 23/11/2026 23:05 CET** in ogni pagina. Restano i CSS autorizzati; richieste `*.js` e `*.mjs` sempre 403. Le pagine di altri ruoli restano negate dal router verificato.
- Collegato il nuovo wrapper al **candidato entrypoint esistente** `staging_readonly_entry_v102_lab.mjs`; template Wrangler inattivo, binding database ancora placeholder deliberatamente non valido, nessuna route pubblicata.
- **CI `45276468567` SUCCESS**: sei nuovi controlli su pagina senza form/script, propagazione deny Access/D1, blocco JS, CSS autenticato, divieto POST e collegamento all'entrypoint; tre controlli precedenti dell'entrypoint ritestati **solo perché l'entrypoint è stato modificato** (9/9).
- Il wrapper riusa la verifica esistente: `extraD1Reads=0` rispetto a v1.01; **non significa zero letture totali** né costo totale verificato.
- Non è il portale completo per proporre livelli: questo è **esclusivamente un gate di identità/lettura**. Il contributo reale, ricevuta/approvazione/audit/revoca end-to-end richiedono un'implementazione POST separata e test provider.
- **NO-GO**: Access e D1 reali, account e user UUID, policy e billing, verifica Safari staging e rollback non autorizzati / non verificati.

Per la fase successiva è richiesta un'autorizzazione **solo per configurare e collaudare uno staging privato OWNER + 1 CONTRIBUTOR in sola lettura**, senza creazione di utenti veri finché non si conferma la policy. Non confondere questa autorizzazione con un permesso di merge/deploy su REMURA pubblica.

## 24 novembre 2026 — v1.04 CSP fail-closed e controllo Free

- Modulo aggiunto: `private_worker_staging_csp_v104_lab.mjs` e test `test_staging_csp_v104_lab.mjs`. Attualmente integrato nel **candidato** `staging_readonly_entry_v102_lab.mjs`, privo di URL, route e deploy: la catena è `Worker Entry → CSP v1.04 → Safe Read v1.03 → Access/D1 v1.01`.
- Le quattro pagine autorizzate presentano in cima **REMURA Contributors v1.04 LAB · 24/11/2026 00:12 CET (Europe/Rome)**. HTTP 200 solo dopo controlli Access/D1 reali nel codice, non ancora attestati da provider. CSS resta permesso esclusivamente dalla stessa autorizzazione; il wrapper non sblocca endpoint sconosciuti.
- Difesa nel browser: CSP `default-src 'none'; script-src 'none'; connect-src 'none'; form-action 'none'; style-src 'self'; frame-ancestors 'none'`, più `no-store`, `nosniff`, `X-Frame-Options:DENY`, `X-Robots-Tag:noindex`. L'HTML è ricontrollato server-side: marca v1.03 autentica richiesta, tag eseguibili/form e modifiche inattese -> 403. Le pagine riportano versione v1.04 coerente.
- CI su nuovi controlli **45287131225 SUCCESS (5/5)**. L'entrypoint modificato ha richiesto il ricollegamento del test precedente: **45287019706 SUCCESS (9/9)** per presentazione + vecchio entry gate, **45287012266 SUCCESS (3/3)** per gate Worker. La precedente run rossa di v1.03 al solo commit intermedio 959f6bb è stata corretta con aggiornamento del contratto dei test: nessuna suite disattivata.
- L'ulteriore `CSP` non legge D1: `additionalD1Reads=0`. Non confondere questo con consumo D1 totale (il gate sottostante esegue letture).
- **Free monitor:** le fonti ufficiali Cloudflare segnalano che i limiti giornalieri D1 Free sono applicati con errore quando si superano le quote dal 01/09/2026. Workers Free documenta 100.000 richieste/giorno per account; il reale consumo del tuo account, gli Access seats, l'eventuale Billing e i database disponibili non sono ancora letti, quindi il costo effettivo non è certificato. Fonti: https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/ ; https://developers.cloudflare.com/workers/platform/limits/ ; https://developers.cloudflare.com/d1/platform/limits/
- Cloudflare Workers Access documenta `ctx.access` **solo** per Worker direttamente autenticato; Worker Static Assets e service bindings non passano il contesto di identità. La build reale dovrà dimostrare assenza di `assets`, policy Access corretta e identità da due utenti reali senza usare un service token: https://developers.cloudflare.com/workers/configuration/cloudflare-access/

**Restano condizioni NO-GO del pilot:** creare/configurare staging privato soltanto con autorizzazione distinta, verificare Zero Trust Free e posti disponibili, confermare D1 staging isolato (né produzione né fixture), policy Access per OWNER + CONTRIBUTOR, autenticazione Safari, 403 incrociati, revoca e audit reali. Le POST restano tutte negate; niente invio livelli né approvazione da questa versione. Nessun Worker deploy, D1 write, utente o nuova spesa effettuata qui.


## 24 novembre 2026, 06:49 CET — prova reale Zero Trust Free ricevuta

**Evidenza fornita dall'OWNER:** schermata della dashboard Cloudflare, sezione `Settings → Cloudflare One plan`, fotografata su iPhone il 24/11/2026 alle 06:49 italiane.

- `Plan type: Zero Trust Free` — **verificato sullo schermo OWNER**.
- `Seats: 1 of 50 available seats` — **un posto su 50 in uso**; margine nominale **49 posti**, ampiamente sufficiente per un pilot di 1 OWNER + 1–2 CONTRIBUTOR, subordinato alle policy e agli inviti reali. Non sono stati creati nuovi account o posti.
- `Price: $0 / month` — prezzo del **solo piano Cloudflare One Zero Trust** sullo screenshot, non attestazione del costo totale Cloudflare / Workers / D1 / Pages / billing.
- `Role: Super Administrator - All Privileges` — privilegi del dashboard verificati visivamente. **Non riportare né conservare qui l'indirizzo email visibile sullo screenshot.**
- `Set dashboard to read-only: Off` — stato dashboard, non abilitazione di un Worker.
- **Non ancora attestati**: numero e regole delle applicazioni Access, politiche precise dei domini Worker, provider di login, identity UUID e email tag, D1 database staging separato, consumi Workers/D1, fatturazione complessiva, autenticazione Access reale, permessi incrociati e revoca.

**Decisione di roadmap:** il gate `ZERO_TRUST_FREE_PLAN_AND_SEAT_CAPACITY` passa da `UNKNOWN` a **`OWNER_SCREENSHOT_VERIFIED`**. I gate `ACCESS_APP_POLICY`, `STAGING_D1_ISOLATION`, `WORKERS_D1_USAGE_FREE`, `REAL_AUTHENTICATION`, `ROLE_REVOKE_END_TO_END` e `OWNER_APPROVAL_FOR_DEPLOY` restano `NO_GO`.

**Prossima operazione manuale a costo zero:** aprire Zero Trust → Access → Applications **in sola consultazione**, verificare se esiste già un'app legata al dominio staging; non creare app, policy, utenti, Worker o binding e non selezionare piani a pagamento. Acquisire soltanto la vista generale della lista; oscurare email e dati identificativi. Prima di creare qualsiasi risorsa o pubblicare il portale si richiede autorizzazione separata.

## 24 novembre 2026, 06:54 CET — Access Applications: una app di staging esistente

**Evidenza diretta fornita dall'OWNER da iPhone**: screenshot Cloudflare Zero Trust `Access → Applications` del 24/11/2026 ore 06:54 CET.

- L'elenco mostra `Showing 1-1 of 1`: **esiste esattamente un'applicazione visibile**.
- Nome visualizzato (troncato dall'interfaccia): `remura-contributors-staging - Cloudfl...`. Colonna `Destinations`: `remura-contributors-staging` (etichetta link, non ancora URL/dominio accertato).
- Il checkpoint precedente ha già verificato **Zero Trust Free, 1/50 posti, $0/mese per il piano One**.
- **Non creare app duplicate, non cambiare policy e non assegnare o invitare utenti**. L'esistenza nell'elenco non prova che l'app sia correttamente protetta, raggiungibile da Safari, abbinata a un Worker diretto né che il database staging D1 sia isolato.
- Gate `ACCESS_APPLICATION_EXISTS`: **OWNER_SCREENSHOT_VERIFIED**.
- Gate `ACCESS_APPLICATION_EXACT_HOST`, `ACCESS_POLICY_ALLOWLIST`, `WORKER_DIRECT_ACCESS_IDENTITY`, `D1_STAGING_ISOLATED`, `REAL_AUTH_ROLE_REVOCATION` restano **NOT_VERIFIED / NO_GO**.
- Prossimo controllo gratuito **in sola lettura**: aprire la riga dell'app esistente e leggere `Overview/Basic information` e `Policies` (nome completo, dominio pubblico, modalità/self-hosted, elenco e tipo delle regole Allow/Block), senza esporre segreti/identità/email/token e senza fare `Save` o cambiamenti. Conservare nel report solo il minimo indispensabile e non le identità private.
- Nessun deployment Cloudflare, nuovo utente, abbonamento, richiesta D1, merge PR o variazione `main` autorizzato o effettuato in questo passaggio.


## 24 novembre 2026, 06:56 CET — Access Worker scope e policy: evidenza OWNER

Tre screenshot iPhone Cloudflare Zero Trust, **solo consultazione visiva** della stessa applicazione `remura-contributors-staging - Cloudflare Workers` e della policy OWNER. Nessuna modifica o invito è stato autorizzato.

1. **Destinations → Workers**: `Scope = remura-contributors-staging`, `Type = A Worker's production and preview URLs`. La protezione configurata può quindi riguardare sia indirizzi di produzione **sia** preview del medesimo Worker, non soltanto uno staging isolato. La casella aggiuntiva `Destinations: Select...` appare senza selezione; non inferire un host da questa etichetta. Il dominio preciso ed eventuali route/custom domains **non sono visibili**.
2. **Access policies** sull'app: una riga `REMURA Contributor`, action `Allow`, `Rules = 2`, ordine 1. **I selettori di queste due regole non sono visibili.** Non attestare che la policy limiti gli accessi a collaboratori conosciuti.
3. **Authentication**: `Accept all available identity providers = OFF`; unico provider selezionato visualizzato `REMURA Google - google`. `Apply instant authentication = OFF`; `Authenticate with Cloudflare One Client = OFF`. Non sono state eseguite sessioni reali né provati token/JWT.
4. **Policy separata visualizzata**: dettaglio `REMURA Contributors Owner Test` mostra `Include: Emails` con **un singolo indirizzo personale da NON registrare**, più `Require: Login Method = Google · REMURA Google`. La sua sezione `Applications` visualizza la stessa app Worker. **Da riconciliare**: nella lista policy dell'app appare solo `REMURA Contributor`, mentre il dettaglio OWNER indica l'associazione. Non presumere che la regola OWNER sia attiva, ordinata o sufficiente a proteggere l'app fino alla conferma della lista completa.
5. Browser rendering RDP/SSH/VNC = `Off`. I pulsanti `Edit`, `Save`, `Delete` sono visibili, **non azionati**.

**Regola Cloudflare verificata documentalmente**: in policy Access `Include` con più selettori è logica OR, `Require` è AND, e una Allow compatibile concede l'accesso; un Include generico può aprire il Worker più del previsto. Fonti: https://developers.cloudflare.com/cloudflare-one/access-controls/policies/ ; https://developers.cloudflare.com/workers/configuration/cloudflare-access/ .

**Passaggio decisionale**: `WORKER_ACCESS_SCOPE = OWNER_SCREENSHOT_VERIFIED (prod+preview, non isolato)`; `GOOGLE_IDP_SELECTED = OWNER_SCREENSHOT_VERIFIED`; `ACCESS_POLICY_DETAILS = PARTIAL`; `OWNER_POLICY_ATTACHED = UNCONFIRMED`. Rimangono `NO_GO`: rilevazione del selettore Include/Require di `REMURA Contributor`, identity allowlist effettiva, dominio Worker reale, corretta verifica `ctx.access` nel Worker, D1 staging isolato, approvazione spesa/deploy, test Safari e revoca.

**Prossima verifica ammessa in sola lettura:** aprire la voce `REMURA Contributor` nei dettagli delle policy dell'app e visualizzarne i selettori `Include`/`Require` (evitare di pubblicare indirizzi o identità), **senza cambiare o salvare nulla**. Non creare nuove applicazioni, Worker, regole, utenti o abbonamenti.


## 24 novembre 2026, 06:59 CET — conferma policy OWNER separata da CONTRIBUTOR

Nuove schermate Cloudflare Zero Trust fornite dal proprietario (06:59 Europe/Rome) mostrano il dettaglio della policy **`REMURA Contributors Owner Test`**, **non** il dettaglio della policy `REMURA Contributor` elencata nell'app.

**Dati osservati (senza conservare identità o indirizzi personali):**
- `Total rules = 2`, `Used by applications = 1`, `Action = Allow`, `Session duration = 1h`.
- `Include → Emails`: **un solo indirizzo specifico**, deliberatamente omesso in questa nota.
- `Require → Login Method`: `Google · REMURA Google`.
- `Applications`: riferimento visualizzato all'app `remura-contributors-staging - Cloudflare Workers`.
- `Multi-factor authentication (MFA) = Off` nella policy; questo non attesta lo stato MFA del singolo account Google.
- `Isolate application = Off`, `Purpose justification = Off`, `Temporary authentication = Off`.
- Nessun pulsante `Edit`, `Save`, `Delete`, nuovo utente, test login o altro controllo è stato azionato.

**Interpretazione rigorosa:** la policy OWNER è una allowlist specifica che richiede anche il provider Google; non autorizza automaticamente i ruoli lato D1. L'associazione mostrata per la policy OWNER non riconcilia ancora la differenza con la lista policy dell'app, dove era visibile solo `REMURA Contributor`. Lo stato di enforcement reale dell'app rimane da provare e il tipo di destinazione precedente comprende **Worker production e preview URLs**.

**Gate:** `OWNER_POLICY_SELECTOR_DETAILS=OWNER_SCREENSHOT_VERIFIED`; `OWNER_MFA_POLICY=OFF`; `CONTRIBUTOR_POLICY_SELECTOR_DETAILS=UNKNOWN`; `APP_POLICY_ATTACHMENT_AND_ORDER=UNRECONCILED`; `REAL_ACCESS_AUTHENTICATION=NO_GO`; `D1_STAGING_ISOLATION=NO_GO`; `CONTRIBUTOR_WRITABLE_PILOT=NO_GO`.

**Prossima verifica gratuita in sola lettura:** chiudere il dettaglio OWNER (X), tornare a `Access → Applications → remura-contributors-staging → Access policies` e toccare **esattamente `REMURA Contributor`** (non `REMURA Contributors Owner Test`), espandere `Policy details`, verificare `Include`, `Require`, `Exclude` (se presenti) e eventuali regole generiche; oscurare dati identificativi prima dello screenshot. Nessun edit, nessun salvataggio, nessun invito e nessun deploy.


## 24 novembre 2026, 07:03 CET — Reusable versus app-scoped policy

Screenshot OWNER: Zero Trust `Access controls → Policies → Reusable policies` mostra esattamente **una policy riutilizzabile**, chiamata `REMURA Contributors Owner Test`, action `Allow`, `2` regole, `Used by applications = 1`. Il suo dettaglio ripete la allowlist email singola e il requisito del provider Google già verificati; **non è una nuova prova della policy Contributor**.

L'applicazione `remura-contributors-staging - Cloudflare Workers` mostrava nella propria sezione `Access policies` una diversa policy `REMURA Contributor` con action `Allow` e 2 regole. **Possibile spiegazione, da verificare:** quest'ultima è una policy *application-specific* (non riutilizzabile) e quindi non compare nella lista delle `Reusable policies`. Cloudflare documenta due endpoint distinti per policy di app e policy riutilizzabili: https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/applications/subresources/policies/methods/update/ . Non inventare le sue condizioni Include/Require, che restano invisibili.

**Percorso UI corretto, sola lettura:** `Access controls → Applications → remura-contributors-staging → Application details → Access policies → REMURA Contributor`. **Non entrare in `Policies → Reusable policies`**, perché apre soltanto `REMURA Contributors Owner Test`. Se cliccare il nome nell'app reindirizza nuovamente a Owner Test, documentare come `UI_POLICY_IDENTITY_AMBIGUOUS` e fermarsi senza salvataggi; valutare un'eventuale verifica separata e limitata con lettura API autorizzata, mai dedurre la policy da nome/colore.

Nessun utente, deploy, chiamata API Cloudflare, Worker, D1, policy o costo creato da questo checkpoint. Gate `CONTRIBUTOR_POLICY_RULES=NO_GO`, `OWNER_POLICY_DETAILS=VERIFIED`, `WORKER_ACCESS_SCOPE_PROD_AND_PREVIEW=VERIFIED`. Non riportare UUID policy o email personali in roadmap.


## 24 novembre 2026, 07:06 CET — mismatch policy link confermato senza ulteriori test

**Nuovo screenshot OWNER da iPhone**: dopo il percorso dall'applicazione `remura-contributors-staging`, il link mostrato nell'elenco come `REMURA Contributor` apre nuovamente il pannello **`REMURA Contributors Owner Test`**, con la medesima allowlist di una sola email e requisito Google. L'OWNER ha ripetuto il percorso richiesto e non va più mandato a ripeterlo.

**Conclusione rigorosa:** `UI_POLICY_IDENTITY_AMBIGUOUS = CONFIRMED`; l'etichetta dell'elenco potrebbe non corrispondere al titolo effettivo dell'oggetto policy, oppure la piattaforma potrebbe reindirizzare a una policy riutilizzabile diversa. **NON sappiamo** quali regole risultino realmente applicate all'identità CONTRIBUTOR. Non assumere esistenza di una allowlist collaboratori, non assumere che l'accesso Contributor sia configurato e non modificare la policy OWNER.

**Decisione:** sospendere i tentativi ripetuti nella UI; `ACCESS_POLICY_CONTRIBUTOR_VERIFIED = NO_GO` e `REAL_COLLABORATOR_PILOT = NO_GO`. Qualsiasi lettura Cloudflare Access API o cambiamento di policy richiede autorizzazione separata, con campi minimi e nessun token esposto. Il blocco NON impedisce altre verifiche indipendenti in sola lettura.

**Prossimo controllo indipendente**: consultare il solo elenco D1 nel dashboard Cloudflare (senza eseguire query): identificare l'eventuale database staging dedicato, il fixture sintetico e il database lab; non creare, collegare, eliminare o migrare database. Rilevare nome e piano Free evitando identificativi privati. Non inferire il database associato a un Worker dalla sola presenza in elenco.

Nessun deploy/merge/utente/Worker/D1 modificato e nessuna nuova spesa.


## 24 novembre 2026, 07:23 CET — D1 Free: elenco e quote reali OWNER

**Fonte:** screenshot della dashboard Cloudflare `D1 Database`, vista `Daily`, data 24/11/2026; sola lettura e senza query o mutazioni.

- `Total databases: 4 / 10` → 4 database attuali, 6 posti nominali liberi.
- `Rows read: 0 / 5M` e `Rows written: 0 / 100k` **nella giornata indicata al momento dello screenshot**. Non generalizzare a consumi di altri giorni.
- `Total storage: 7.71 MB / 5 GB`. `Metered storage: 74.99 kB-mo` visualizzati come valore separato; non confonderlo con i byte archiviati.
- I 4 database visibili: `remura-contributors-fixture`, `remura-contributors-lab`, `remura-tv-lab-test`, `remura-tv-lab`; la colonna `Queries` della lista mostra 0 per tutti.
- **NESSUN `remura-contributors-staging` dedicato nell'elenco.** La presenza del Worker `remura-contributors-staging` in Access **non** implica l'esistenza dell'omonimo D1, né dimostra che siano presenti binding/staging/credenziali. Distinguere nomi di Worker da nomi D1.
- `remura-contributors-fixture` resta destinato a test sintetici e non va utilizzato con identità reali; `remura-contributors-lab` è LAB storico da proteggere, non dichiararlo staging isolato verificato.
- Si può **valutare** un quinto database D1 staging *separato* nei limiti quantitativi della schermata, ma sono ancora da verificare quota Workers, billing account e limitazioni specifiche; **non crearne uno senza autorizzazione nuova e specifica**.

**Gate aggiornati:** `D1_FREE_CAPACITY=OWNER_SCREENSHOT_VERIFIED`; `D1_CURRENT_LIST=OWNER_SCREENSHOT_VERIFIED`; `DEDICATED_CONTRIBUTORS_STAGING_DB=ABSENT_IN_LIST`; `STAGING_D1_ISOLATION=NO_GO`; `CONTRIBUTOR_ACCESS_POLICY=NO_GO`; `REAL_COLLABORATOR_PILOT=NO_GO`.

**Prossima scelta operativa:** prima riconciliare policy Access `REMURA Contributor` (UI rimanda a Owner Test, già documentato, non chiedere di ripetere); poi autorizzare eventualmente creazione del **solo** database staging isolato, dopo verifica del Free. Vietati merge/deploy, SQL, Worker binding e nuovi utenti in assenza di permesso separato.


## 24 novembre 2026, 07:25 CET — Worker Production DISABLED e assenza binding D1

**Evidenza:** screenshot OWNER del Worker `remura-contributors-staging`, sezione `Settings → Production` (i selettori `Previews Base` NON risultano aperti). Nessuna configurazione è stata modificata.

- **Variabile visibile:** `STAGING_ENABLED = DISABLED`. Questa è una prova che l'ambiente **Production** non ha lo staging abilitato mediante quella variabile. Non inferire il comportamento del codice Worker remoto senza verificare il deployment attivo.
- **Bindings → Production:** la dashboard mostra testualmente `No connected bindings`: non risultano D1, KV, R2 o altri binding connessi **in Production**. Non confondere l'esistenza dei quattro database D1 account (4/10) con un database collegato a questo Worker.
- **Secret presenti come soli nomi:** `ACCESS_ACCOUNT`, `ACCESS_AUD`, `STAGING_ORIGIN`, `TEST_EMAIL`, `TEST_UUID`. I valori restano cifrati, **non sono stati aperti, copiati o letti**. In particolare il valore effettivo di `STAGING_ORIGIN` resta ignoto e non va riportato nel registro; `TEST_EMAIL` e `TEST_UUID` non attestano identità Contributor reali.
- **Requisiti del candidato LAB v1.04:** `PRIVATE_WORKER_V078=STAGING_AUTHENTICATED_READONLY`, `CONTRIBUTORS_STAGE_READONLY=EXPLICIT_STAGING_ONLY`, `STAGING_ENABLED=D1_CANDIDATE`, `IDENTITY_HMAC_KEY` valida, `CONTRIBUTORS_DB` D1 con `prepare`, autenticazione diretta `ctx.access`. Nella lista Production i primi due e la chiave HMAC non risultano visibili; **non significa che non esistano in Previews Base o altrove**. `STAGING_ENABLED=DISABLED` da solo già non soddisfa il gate.
- **Osservabilità → Production:** `Logs Off`, `Traces Off`, `Issues Off` nello screenshot. Non attivare logging dei dati personali senza valutazione e autorizzazione.
- Per il pilot reale **NON modificare Production**, non cambiare `STAGING_ENABLED`, non toccare Secret di test e non collegare direttamente `remura-contributors-lab` o `remura-contributors-fixture`. Serve uno staging D1 separato, policy Contributor riconciliata e un Worker/test in ambiente isolato esplicitamente autorizzato.
- **Gate aggiornati:** `WORKER_PRODUCTION_STAGING_FLAG=DISABLED_VERIFIED`, `WORKER_PRODUCTION_D1_BINDING=ABSENT_VERIFIED`, `WORKER_PREVIEWS_BASE_BINDINGS=NOT_INSPECTED`, `WORKER_ACTIVE_DEPLOYMENT=NOT_VERIFIED`, `WORKER_LAB_V104_CONFIG_SATISFIED=NO_GO`, `ACCESS_CONTRIBUTOR_POLICY=NO_GO`, `REAL_COLLABORATOR_PILOT=NO_GO`.

**Prossimo controllo gratuito in sola lettura (facoltativo):** nella stessa schermata `Settings` selezionare `Previews Base` nella sezione `Bindings` e verificare **solo** se compaiono collegamenti già esistenti, senza aprire Secret o premere `Add binding`/`Save`. L'esistenza di una base preview non significa un ambiente indipendente: non attivare alcuna route o deploy. In alternativa, preparare il piano tecnico isolato mentre si riconcilia Access. Nessuna necessità di ripetere screenshot di Production già acquisito.


## 24 novembre 2026, 07:55 CET — Previews Base bindings: assenti

**Fonte:** screenshot OWNER del Worker `remura-contributors-staging` → `Settings` → sezione `Bindings` con **`Previews Base` esplicitamente selezionato**. Compare `No connected bindings`. Il controllo è stato effettuato senza azionare `Add binding` o modificare impostazioni.

- `WORKER_PREVIEWS_BASE_BINDINGS = ABSENT_OWNER_SCREENSHOT_VERIFIED`.
- Il controllo precedente aveva già attestato `WORKER_PRODUCTION_BINDINGS = ABSENT_OWNER_SCREENSHOT_VERIFIED`.
- La sezione distinta `Runtime variables and secrets` in questo screenshot rimane selezionata su **Production**; non attribuire ai `Previews Base` la variabile Production `STAGING_ENABLED=DISABLED` né i nomi dei Secret di Production. `WORKER_PREVIEWS_BASE_VARIABLES_AND_SECRETS=NOT_INSPECTED`.
- Non esiste dunque un binding D1 visibile in questi due scope del Worker. I 4 database D1 dell'account rimangono indipendenti; nessuno di essi è attestato come collegato al Worker.
- Nessuna interpretazione sulla disponibilità dell'URL preview, sulla policy Access Contributor ancora ambigua o sul deployment effettivamente attivo: **nessun login/ruolo/lettura D1 end-to-end verificato**.

**Decisione:** lo staging Contributors reale resta `NO_GO` finché non vengono chiarite policy Access, Worker isolato e database staging dedicato. Il prossimo avanzamento sensato non è ripetere schermate ma preparare, dopo autorizzazione separata, **un quinto database D1 staging vuoto e isolato**, con limite Free accertato (4/10 database, 7,71 MB/5 GB al 24/11/2026 07:23 CET), senza migrarlo, collegarlo o eseguire SQL. Qualsiasi creazione è ancora **non autorizzata**.

Nessun nuovo utente, deploy, merge, accesso API Cloudflare, binding o spesa in questa fase.


## 24 novembre 2026 — V23: quinto D1 dedicato creato, conferma OWNER
L'OWNER ha confermato in chat la creazione manuale di `remura-contributors-staging` con giurisdizione europea (EU), dopo autorizzazione esplicita limitata al database vuoto sul piano Free. Evidenza `OWNER_REPORTED_D1_CREATED_EU`, non interrogazione API né screenshot post-creazione. Conteggio atteso 5/10 sulla base dei quattro precedentemente attestati; consumo e fatturazione complessiva non ricontrollati. Non creare duplicati. Nessun UUID, email, credenziale o screenshot conservato. Schema candidato v1.05 `staging-readonly-v105-REVIEW-ONLY.sql` già registrato in 0f76172c: tre tabelle profilo/stato, gate iniziali OFF, nessun utente. Non eseguito su D1; compatibilità runtime reale non attestata. Prossimo gate: verifica locale mirata SQL e autorizzazione separata all'inizializzazione del solo nuovo DB, poi policy Access ambigua, binding/config/deploy con consensi distinti. Nessuna modifica a Production, merge, deploy, utenti o spesa autorizzata in questo passaggio.


## 24 novembre 2026, 09:43 CET — D1 staging v1.05 initialized
OWNER screenshots 09:42–09:43 from D1 Console show new `remura-contributors-staging` empty before initialization, execution of authorized v1.05 schema batch with no visible error, then aggregate SELECT across two horizontal views: expected named tables=3, staging trigger count=4, owner rows=0, contributor rows=0, write_enabled=0, read_enabled=0, recovery_enabled=0. All seven aggregate checks match. Evidence `OWNER_SCREENSHOT_D1_SCHEMA_INITIALIZED_CLOSED`; counts do not independently attest trigger bodies or provider runtime authorization. No raw identities, IDs, secrets or screenshots stored. No repeat SQL needed. No binding, Access changes, deploy, merge or user enrollment performed. Next gate: resolve Access policy identity ambiguity by limited read-only inspection only after separate authorization; actual billing and Worker quotas still to be confirmed before activation. D1 pilot remains closed.

## 24/11/2026 09:45–09:58 CET — Access diagnosis deferred by OWNER
OWNER screenshots show no personal API tokens, seven pre-existing account tokens; displayed permission groups Analytics Read, D1 Read, Individual Workers Editor and unrelated broader write permissions are not suitable for narrow Access read diagnosis. OWNER separately authorized temporary dedicated Access read token, confirmed configuration completed after review showing only Access: Apps and Policies Read for account and expiry date 25/11/2026; exact expiry hour not independently attested. Token value retained by OWNER, never provided in chat or repository. OWNER asked to skip installing Scriptable and defer API step; no GET performed (0/3), no credential use, no Access policy modified. Existing ambiguity UI_POLICY_IDENTITY_AMBIGUOUS remains NO-GO for real collaborators. D1 closed state unchanged. Do not request repeated screenshots or create another token without authorization. Verify policy before real pilot, preferably local read-only client when available; let unused token expire or owner revoke separately.

## 24 November 2026 — V24.1: Access policy identity reconciled by OWNER local read-only API
OWNER ran Scriptable locally and supplied redacted results: initial diagnostic 3 GET, separately authorized follow-up 3 GET, both OK; no retry or mutation reported. Follow-up lists exactly one application policy, valid UUID, decision allow, one email Include matching OWNER locally, one login_method Require (specific value unverified), no Exclude. Exactly one reusable policy with the same valid ID and same summarized rules; both names masked as ALTRO_NOME. No distinct contributor policy in returned list. One allowed identity provider listed; allow_all_idps null, not proof of false. Evidence OWNER_REPORTED_LOCAL_API_REDACTED; no independent API access by ChatGPT. UI name ambiguity resolved at ID/rule level for inspected app, actual login and all alternate origins remain unverified. No email, IDs, token, raw response or screenshots stored. GET allowance exhausted (6 total across two batches); no more API requests without new approval. D1 still closed. Next: verify billing and actual Worker deployment/topology, then separately authorize one contributor policy with exact email and approved provider, preserve OWNER policy, isolated binding/config and enrollment separately. No deploy, merge, new user, Cloudflare write or expense authorized. Existing LAB readonly profile correction head 384eaeb4 remains separate from runtime verification.

## 24 November 2026, 11:00 CET — V24.2: reusable Contributor policy created, unattached
OWNER reported zero Workers usage (not independent billing attestation). Separately authorized manual creation only. Pre-save screenshots show REMURA Contributor Pilot, Allow, single exact collaborator email Include, Require Login Methods REMURA Google, custom duration 1h, no Exclude. Post-save screenshot shows two reusable Allow policies, two rules each, application usage counts 0 and 1, names truncated; consistent with new unattached policy and existing OWNER policy preserved. No personal email, ID or screenshot retained in repo. Evidence OWNER_SCREENSHOTS_POLICY_CREATED_UNATTACHED. No app association, deploy, D1 binding/write, enrollment or new expense authorized. Before granting collaborator Access, confirm target Worker active deployment and isolation (including alternate origins), actual Free billing, fail-closed runtime and role separation; association needs distinct approval. No additional API requests. D1 gates remain closed per prior evidence.

## 24 November 2026, 11:01–11:02 CET — V24.3: staging Worker topology evidence
OWNER screenshots: Deployments shows existing deployment eight days old and earlier history referencing v0.18; current source/runtime not independently attested, not evidence v1.04 installed. Domains shows Production workers.dev OFF, Preview workers.dev OFF, no custom domains or routes listed. Access tab shows Worker Access All traffic (login required on production and preview URLs), one OWNER Allow policy with full name REMURA Contributors Owner Test, consistent with earlier redacted API identity reconciliation. Hostname policies take precedence over Worker policies, then account policies per UI; no independent account-wide inventory or runtime test. New contributor reusable policy remains unattached according to prior screenshot. No credential, email, audience, UUID or screenshot stored. No Cloudflare mutations or additional API calls. Keep URLs and enrollment disabled; before association, stage audited current code and D1 binding only with separate approval, account for dashboard changes that may create/deploy versions, preserve rollback and validate real OWNER access before opening collaborator policy. Billing total remains not independently verified.
