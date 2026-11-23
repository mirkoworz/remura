# REMURA Contributors v0.98 LAB — Pilot iPhone/Safari 1 OWNER + 1–2 CONTRIBUTOR
**Aggiornamento: 23 novembre 2026 · ore 13:34 CET (Europe/Rome).**
**STATO: NO-GO reale — nessun deploy, Access, Workers o D1 attivato.**

## Perché v0.98 è una modifica costruttiva, non la replica dei test passati
Il ramo deriva esattamente da `research/contributors-v097-free-pilot-readiness-20261122`.
La v0.96 ha introdotto un router statico diretto, ma il profilo OWNER con `can_read=true` e
`can_recover=false` poteva ancora ottenere le pagine GET OWNER, perché il nuovo router
controllava ruolo e lettura senza imporre la revoca di recovery prevista dalla v0.92.
Inoltre per alcune POST OWNER (es. `/owner/queue`) il gate v0.74 consentiva READ
con `can_read=true` anche dopo perdita di `can_recover`.

La nuova composizione `private_worker_pilot_owner_guard_v098_lab.mjs`:
- usa il **router v0.96 autentico** e gli stessi delegati Access, D1, livelli e audit;
- chiude ogni GET OWNER quando `can_recover!==true` con una **sola lettura D1 di profilo per GET**;
- introduce prima di ogni POST un controllo severo di origine, CSRF, body <=4096,
  route consentita, ruolo e recovery OWNER; respinge header di ruolo contraffatti;
- respinge qualsiasi POST OWNER con `can_recover!==true`, inclusa la `/api/profile`;
- mantiene gli ulteriori controlli dei delegati originali: ownership persistente, quote,
  intent monouso, audit e divieto di retry cieco degli invii incerti;
- non espone `export default`, non attiva Worker o database e non cambia i file v0.96.

**Costo da verificare**: il POST wrapper inserisce almeno un lookup di profilo
primario D1 aggiuntivo prima dei delegati; misurare su staging isolato, solo con
nuova autorizzazione, prima di considerare il margine Free. Nessuna stima spacciata
per misurazione reale.

## Funzioni e confini del pilot

| Identità | Consentito quando confermato dal server | Non consentito |
|---|---|---|
| OWNER (uno) | Consultazione REMURA, coda, audit, revisione/approvazione livelli altrui, gestione revoche con procedura separata | Auto-approvazione, scrivere COT/Oracle, modificare Secret, deploy dal portale |
| CONTRIBUTOR A (uno) | Consultazione pubblica REMURA in sola lettura; strumenti protetti e propri livelli/ricevute; proposta e correzione propri livelli | Coda OWNER, approvazione, livelli altrui, accesso ai Secret/Oracle o cambi dei mercati |
| CONTRIBUTOR B (facoltativo) | Stesso perimetro isolato di A | Conoscere/modificare livelli o ricevute di A |

La UI `preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html` è locale e non invia.
La UI privata `research/contributors/contributors_levels_v096_lab.html` utilizza
catalogo con mapping server, conferma prima dell'invio, ricevuta e gestione invii incerti,
ma **non è pubblicata**. La sola navigazione verso le pagine pubbliche REMURA
non attesta una sessione Access e **non conferisce scritture**.
È necessario verificare che le sezioni protette del resto di REMURA siano
effettivamente in sola lettura per i collaboratori prima della distribuzione.

## Cancello A — prove di costo, solo dashboard privata in lettura

Non creare o cancellare nulla, non aprire SQL Console, non fare query GraphQL D1,
non effettuare acquisti o nuovi login:
1. In `dash.cloudflare.com` controllare **Billing / Subscriptions**: prezzo
   Zero Trust/Workers effettivo, eventuali componenti a pagamento, nessun upgrade.
2. In **Zero Trust → Team & Resources → Users** e piano Cloudflare One:
   Access Free, posti attivi/usati/disponibili; per il pilot servono 1 OWNER
   e 1–2 CONTRIBUTOR inclusi nei posti disponibili/effettivamente già utilizzati
   (non assumere due nuovi posti se un'identità ne occupa già uno).
3. In **Workers / Analytics**: richieste e CPU dell'intero account per il giorno UTC.
4. In **D1 → Metrics / Row Metrics**: numero DB, dimensioni, righe
   lette/scritte nell'intero account e relativo giorno UTC. Un grafico vuoto
   non equivale a utilizzo zero.
5. Compilare **privatamente** l'evidence della v0.97, mai caricarla su un
   repository pubblico; nel repo rimane solo il modello vuoto.
   Le 2 vecchie chiamate GraphQL del 21/11 NON sono autorizzazioni riutilizzabili.

Il gate v0.97 mantiene almeno il 25% di margine ingegneristico sulle quote Free.
Un esito `EVIDENCE_READY_FOR_INDEPENDENT_REVIEW` **non autorizza** l'attivazione.
Se manca una metrica, scrivere `UNKNOWN` e mantenere `NO-GO`.

## Cancello B — staging privato e Safari (richiede consenso nuovo)

Dopo A, il proprietario autorizza separatamente, e solo allora:
1. Configurare staging HTTPS **isolato**, allowlist Access a negazione predefinita,
   account/capacità D1 dedicati o isolamento provato, senza modificare produzione;
   usare identità differenti, niente email/identificatori in repository pubblico.
2. Login OWNER da Safari iPhone, poi logout/relogin; verificare che solo OWNER
   veda coda, audit e review.
3. Login CONTRIBUTOR A da Safari, prova lettura REMURA, modulo livelli, catalogo
   server, invio livello di prova e **ricevuta server persistente**. Verificare
   che possa consultare solo le proprie ricevute e non abbia pulsanti OWNER.
4. Ripetere con CONTRIBUTOR B, quando previsto; A non può leggere B e viceversa.
   Per ogni richiesta vietata controllare **HTTP 403 reale dal Worker**, non
   soltanto pulsanti nascosti o messaggi nella UI.
5. Da OWNER approvare/rifiutare livello di A; l'autore non può auto-approvarlo.
   Leggere audit append-only, idempotenza e nessun retry di tentativi RESERVED.
6. Revocare A **in tre punti**: identità D1 revocata; policy Access che nega
   nuove autenticazioni; sessioni Access terminate. Provare con tab Safari già
   aperta che GET/POST ora sono 403; poi logout/relogin negato. Eliminare il
   posto Access da solo **non** impedisce un nuovo login.
7. Controllare log/metriche di spesa e isolamento finale; se qualcosa è incerto,
   interrompere il pilot, nessuna seconda scrittura automatica. Piano di rollback
   pronto prima di ogni futura attivazione.

**Attenzione:** è la lista di collaudo futuro, non prove già eseguite.

## Stato delle attestazioni 23/11/2026
- [x] Ramo distinto e composizione v0.98 inerte.
- [x] Scenari unitari aggiunti per la regressione OWNER, permessi e header contraffatti.
- [ ] CI v0.98 verificata su run remoto dopo commit finale.
- [ ] Prezzo/Billing, Access Free e posti reali attestati sulla dashboard personale.
- [ ] CPU, righe lette/scritte D1 e overhead POST reali misurati.
- [ ] JWT Access/provider, test iPhone Safari con identità separate.
- [ ] Doppia revoca, ricevuta duratura, approvazione/audit da staging.
- [ ] Consenso OWNER separato per staging/deploy.

La PR #105 resta Draft e non va integrata; questo ramo non la modifica.
Nessuna scrittura Cloudflare, nessun utente creato, nessun Secret, nessuna modifica
Oracle/collector/produzione/Filoni A e B, nessuna spesa autorizzata.

Riferimenti ufficiali:
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/
