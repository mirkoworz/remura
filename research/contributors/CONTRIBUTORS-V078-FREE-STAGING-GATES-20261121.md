# REMURA Contributors v0.78 LAB — Piano staging gratuito REVERSIBILE (NON ATTIVO)

**21 novembre 2026, ore 17:01 CET — SOLO PIANIFICAZIONE.** Non è un file Wrangler, né una richiesta di creazione risorse.

## 0. Semafori verificabili — TUTTI richiesti prima di qualsiasi autorizzazione al deploy
| Semaforo | Prova necessaria | Stato adesso |
|---|---|---|
| Integrità LAB | Suite v0.78 50/50 GitHub Actions, no 0 failure | GREEN sintetico, run 44922091303 |
| Cloudflare Workers Free | Richieste giornaliere + errori + piano e CPU reali | PARZIALE: stima 199 richieste, 0 errori al 21/11, non fatturazione |
| Cloudflare D1 Free | Numero DB, totale byte, uso giornaliero righe lette/scritte | **NO-GO**: GraphQL D1 mancante il 21/11 |
| Cloudflare Access Free | Piano, seats realmente utilizzati, policy allowlist esplicita | **NO-GO**: dati account Access non verificati |
| Router/Worker | Direct Worker + `ctx.access` dopo autentica, no Workers Static Assets/Service Bindings per l'identità | NO-GO runtime reale non collaudato |
| D1 staging isolato | DB fixture *nuovo* dedicato; snapshot/backup + diff schema, niente migrazioni ai DB storici | NO-GO; non creato |
| Credenziali | Secret HMAC e key rotation, credenziali Cloudflare least-privilege senza commit | NO-GO; non provisionate |
| Safari | Test login/logout e revoca reale, tab doppia, lost response, documentazione prove | NO-GO; nessun dispositivo reale connesso |
| Dati contenuti | Nessuna identità reale o livello riservato nel repository pubblico, audit/livelli isolati | SEMAFORO DA REVALIDARE |

## 1. Verifica quote — 21/11/2026
- GitHub run read-only **FAILED / INCOMPLETE**: https://github.com/mirkoworz/remura/actions/runs/44919682812
- `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`; `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`. Non significa consumo superiore al Free: **non abbiamo il dato**.
- `REMURA_CF_WORKERS_USAGE=OK`, giorno UTC 2026-11-21; `WORKERS_ACCOUNT_REQUESTS_ESTIMATE=199`, `WORKERS_ACCOUNT_ERRORS_ESTIMATE=0`, 2 script monitorati, max reported CPU p99 3.680 microsecondi, **stime GraphQL e non estratto fatturazione**.
- `REMURA_D1_TEST_STORAGE=OK`, DB test 6.266.880 byte, 1,2534% del limite Free singolo di 500.000.000 byte.
- `REMURA_D1_ACCOUNT_STORAGE=OK`, 4 DB, spazio totale 6.557.696 byte, DB più grande 6.266.880 byte; limiti nominali 10 DB e 5.000.000.000 byte totali. I limiti sono soggetti alla revisione della documentazione.
- Per D1 Free, **dal 1 settembre 2026 Cloudflare fa fallire le query quando le righe giornaliere lette o scritte superano la quota**. Pertanto niente staging senza attestazione righe giornaliere: https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/
- Documentazione aggiornabile: https://developers.cloudflare.com/d1/platform/limits/ e https://developers.cloudflare.com/d1/platform/pricing/ e https://developers.cloudflare.com/workers/platform/pricing/
- Access: Free annunciato fino a 50 utenti, ma i **seats effettivamente disponibili** nell'account non sono noti: https://www.cloudflare.com/plans/zero-trust-services/

## 2. Architettura PROPOSTA (non installata)
1. Area di staging con hostname HTTPS separato e policy **DENY-by-default**; un solo account sintetico iniziale e un OWNER. Nessun dato cliente reale.
2. Un **singolo Worker diretto**, stesso origin per HTML/CSS/JS e API. Il ruolo deriva da Access JWT/ctx.access e dai campi immutabili D1 (subject/email_tag HMAC).
3. **Nessun Workers Static Assets router** né Service Binding come mezzo di trasmissione dell'identità: la documentazione Cloudflare dice che `ctx.access` non si propaga automaticamente in questi percorsi. Fonte: https://developers.cloudflare.com/workers/configuration/cloudflare-access/
4. Binding D1 del **solo fixture staging isolato**; `withSession('first-primary')` per qualunque operazione con stato e read-after-write. Non alterare `remura-contributors-lab`, `-fixture`, Oracle né `main`.
5. Chiavi `INTENT_HMAC_KEY` e `IDENTITY_HMAC_KEY` diverse, solo in Secret Store Worker, rotazione documentata; account/identity Cloudflare strict allowlist.
6. Invii livello originale e amendment sono flussi separati. `RESERVED` resta bloccato dopo mancata risposta. OWNER registra soltanto evidenza, **non** modifica o cancella journal; il modulo v0.78 segnala evidenze cambiate.
7. Tutte le risposte private `Cache-Control: no-store`, CSP, same-origin CSRF e rate-limit. Logout via /cdn-cgi/access/logout è una richiesta al provider, non conferma istantanea della revoca; controllare la sessione e JWT sul server: https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/

## 3. Collaudo staged richiesto dopo consenso specifico
- Test utente sintetico: denied senza Access, login corretto, ruolo Contributor non OWNER, revoca immediata delle API, prova D1 primary, ricarica Safari, multi-tab e risposta persa.
- OWNER: queue/storico nuovi livelli, HMAC monouso, prova doppia attestazione concorrente, revoca mentre consulta, stale absence -> receipt found, nullità automatismi.
- Verificare in dashboard i contatori reali **prima e dopo** il collaudo: richieste, righe D1 lette/scritte, storage, seats Access, warning e spese. Se la metrica D1 resta `UNKNOWN`, **NO GO**.
- Disattivare subito qualunque route in caso di anomalia; nessuna registrazione reale a cascata.

## 4. Rollback prima di consentire i collaboratori
- Congelare nuovi invii, mantenere immutable audit; disattivare Access policy/route Worker senza eliminare il DB di test o fingere che il commit `main` sia cambiato.
- Conservare backup e hash del fixture in un contenitore privato autorizzato, non nel repo pubblico.
- Revocare o ruotare i Secret se compromessi; non cancellare logs con audit di integrità.
- Ripristino soltanto con nuova autorizzazione specifica e con budget confermato.

## 5. Cosa NON facciamo ora
Nessun deploy, bundle con default fetch, database nuovo, migrazione, Access enrollment/policy reali, Cloudflare Secret, Worker binding, merge, modifica Oracle, captazione o pubblicazione di dati. La v0.78 rimane LAB e l'attivazione reale è NO-GO.

**Prossima tappa possibile senza Mac:** diagnosticare il monitor read-only GraphQL D1 che oggi non restituisce righe e preparare un fallback account-safe, senza Secret reali, poi chiedere consenso per staging.
