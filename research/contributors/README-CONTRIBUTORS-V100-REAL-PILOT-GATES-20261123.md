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
