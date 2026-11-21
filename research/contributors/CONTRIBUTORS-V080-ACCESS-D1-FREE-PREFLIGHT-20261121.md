# REMURA Contributors v0.80 LAB — Piano di verifica Access + D1 senza costi

**Aggiornamento: 21 novembre 2026, ore 17:22 CET (Europe/Rome)**  
**SOLO PIANIFICAZIONE — ZERO CALL CLOUDFLARE, ZERO SECRET, ZERO DEPLOY.**

## Dati che servono prima di autorizzare il primo staging privato
1. **Cloudflare D1:** elenco completo delle metriche `rowsRead` e `rowsWritten` *dell'attuale giornata UTC*, e riferimento al piano effettivo. I 4 database/6,56 MB osservati il 21 novembre non dimostrano le letture e scritture effettive della giornata. Il run https://github.com/mirkoworz/remura/actions/runs/44919682812 resta `UNKNOWN_NO_GRAPHQL_DATA`.
2. **Cloudflare Zero Trust:** confermare da console il *piano realmente attivo*, il numero di posti inclusi e quelli già utilizzati. L'API `GET /accounts/{account_id}/access/users` è di sola lettura e restituisce pagine di utenti con `access_seat`, ma quel booleano indica chi ha autenticato con Access e non è una fattura né prova sufficiente dei posti acquistati/disponibili. Documentazione: https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/users/methods/list/
3. **Policy Access:** verificare che il futuro hostname sia chiuso per default, con allowlist esplicita per un account di test; non bastano il link privato o la separazione grafica tra OWNER e CONTRIBUTOR.
4. **Entrypoint Worker:** compilazione isolata, verifica `ctx.access` diretto, niente bypass tramite Assets/Service Binding, binding del *solo* D1 staging con dati sintetici e chiavi fuori GitHub.
5. **Verifica da Safari iPhone:** login, logout, sessione effettivamente invalidata, revoca, refresh, più schede, risposta persa, invio livello, ricevuta, coda OWNER e audit.
6. **Budget:** Workers Free, D1 quotidiano, storage e Access seat sono semafori distinti. Nessuno può trasformare un campo `UNKNOWN` in una quota libera.

## Access: dove guardare quando il controllo sarà autorizzato
- Cloudflare Dashboard → **Zero Trust → Settings → Billing / Cloudflare One plan**, per accertare piano e posti consumati (le etichette possono variare).
- Zero Trust → **Team & Resources → Users → Your users**, per verificare l'inventario autorizzato senza esportare email in GitHub.
- Per un futuro tool di sola lettura, le permission API documentate includono `Access: Users Read` o `Zero Trust Read`; **nessun token è stato creato o utilizzato** in v0.80.
- Cloudflare avverte che *Remove* di un utente invalida sessioni e libera un posto, ma senza una policy di blocco quell'utente può autenticarsi ancora; *Revoke* termina le sessioni ma non libera necessariamente il posto. Fonte: https://developers.cloudflare.com/cloudflare-one/faq/getting-started-faq/

## D1: perché due giorni non bastano per un GO
- Il dataset `d1AnalyticsAdaptiveGroups` appare solo quando una richiesta arriva al motore SQL. L'assenza di gruppi il 21 novembre **non prova zero consumo**; confrontarlo col 20 può aiutare a diagnosticare, non può attribuire il valore storico alla data attuale.
- La documentazione dice che dashboard e API GraphQL condividono lo stesso dataset di origine; una seconda visualizzazione non equivale a una fonte indipendente.
- Fonte: https://developers.cloudflare.com/d1/observability/metrics-analytics/
- La v0.80 non esegue nemmeno una richiesta GraphQL: usa solo risposte simulate o dati forniti esplicitamente, e pubblica aggregati senza database ID.

## Nuovi artefatti v0.80
- `access_seat_inventory_v080_lab.py`: verifica paginazione completa Access, utenti unici e flag `access_seat`; non restituisce nome, email, token, IP, uid o account ID. Rifiuta un inventario parziale/falso e non prova i posti fatturabili.
- `d1_two_day_visibility_v080_lab.py`: controllo righe GraphQL aggregate di oggi e ieri, validazione di giorno/identità contatore, distinzione tra una riga con valore zero e un elenco vuoto. Nessun contatto Cloudflare.
- `staging_preflight_v080_lab.py`: dossier unico; tutti i semafori manuali restano vincolanti e la decisione è sempre `NO_GO` fino a un percorso di autorizzazione distinto.
- Test nuovi in GitHub, **92/92 PASS**, https://github.com/mirkoworz/remura/actions/runs/44923942230 . Nessun test storico rieseguito.
- La UI iPhone resta **v0.78 LAB**, perché questo è un aggiornamento di sicurezza/infrastruttura. I banner di quelle pagine restano in cima.
- Nessun deploy, binding, migrazione, token, acquisto, merge `main`, modifica Oracle o azione su utenti reali.

## Reversibilità e prossimi passi
- Quando i contatori e i posti Free saranno noti, sottoporre **una sola proposta precisa di staging** (hostname, Access allowlist, D1 fixture nuovo, backup, budget e rollback) all'approvazione dell'OWNER.
- Fino a quel momento continuare solo con codice e test offline. Un nuovo run GitHub sintetico non è una nuova misura Cloudflare.
- Non caricare schermate con email, token o dettagli account nel repository `mirkoworz/remura`, attualmente pubblico.
