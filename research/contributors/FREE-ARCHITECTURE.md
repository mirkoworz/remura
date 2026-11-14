# REMURA Contributors — architettura candidata v0.15 LAB
Verifica documentale 14/11/2026 — NO-GO deploy, nessuna risorsa creata.

## Candidato preferito per staging
Worker nuovo, D1 nuovo, Access su singolo Worker (tutto traffico inclusi preview). Google come IdP per account personali; policy con email esatte e login Google richiesto, non dominio gmail.com, non Everyone, nessun bypass, nessuna modifica globale Access o altro Worker. Nessuna membership account Cloudflare, nessun accesso VPS, broker o private API. Preferire HTML direttamente dal Worker senza Static Assets/router o Service Binding perché ctx.access ha limiti documentati.
- Access autentica a monte; Worker deve negare se contesto assente o audience diversa. Identità esclusivamente autenticata dalla piattaforma (o JWT verificato con libreria), mai header arbitrari o email dal body.
- Access sub non equivale a Google sub: identificatore per email/account Zero Trust, cambia se utente rimosso e riaggiunto. Richiedere binding owner di identità stabile effettivamente verificata, nessuna riassegnazione automatica, verifica revoca su ogni operazione. Non assumere disponibilità Google sub tramite ctx.access; se manca evidenza sufficiente preferire GIS diretto con verifica Google sub e libreria. Non implementare login reale ora.
- Esporre solo raccolta e ricevute proprie. Revisione/analisi owner separate; futuro import autenticato read-only, nessun token infrastruttura nel Worker. D1 dedicato, prepared statements, indici, limiti, audit, no log sensibili, CSRF, sessioni/revoca, restore fail closed. Prova deny su ogni route e preview prima di inviti.
- Alternativa Worker + GIS diretto: maggior controllo su Google sub, maggiore carico di verifica token e gestione sessioni. Opzione Access da preferire solo dopo verifica identità, isolamento e CPU in staging. Nessuna scelta irreversibile.

## Limiti ufficiali Free consultati
Workers 100000 invocazioni/giorno account, 10 ms CPU per HTTP, 128 MB RAM. D1 5000000 righe lette e 100000 scritte al giorno, 5 GB complessivi, 10 DB, 500 MB per DB, Time Travel 7 giorni. Free D1 si ferma al limite, quote condivise, reset UTC. Zero Trust Free fino a 50 utenti secondo offerta. workers.dev adatto a hobby/staging, non SLA business-critical. Indici e query di manutenzione contano. Nessun piano account attestato.

## Budget candidato (target, non misura né riserva)
Tre utenti, nessun polling, massimo 40 contributi/giorno (20 per ciascun amico), review manuale, import owner su richiesta (max 4 sessioni/giorno), pagine limitate. Target prudenziale 500 invocazioni/giorno, 50000 rows_read, 5000 rows_written inclusi indici, 8 MiB storage pilota; nessun cron aggiuntivo. Non assumere che limiti app garantiscano hard cap invocazioni esterne o righe. Misurare CPU e meta D1 in staging, senza retry automatico; sospendere se account raggiunge 70% o evidenza assente/scaduta. Verificare piano Free e limiti reali account, utilizzo aggregato incluso D, numero DB/Workers/seat, quote GitHub Actions e eventuali obblighi di billing. Non usare snapshot precedente come prova corrente. Nessun upgrade automatico. Nessuna credenziale o risorsa attivata.

## Riferimenti ufficiali
https://developers.cloudflare.com/workers/platform/limits/
https://developers.cloudflare.com/d1/platform/pricing/
https://developers.cloudflare.com/d1/platform/limits/
https://www.cloudflare.com/it-it/sase/products/access/
https://developers.cloudflare.com/workers/configuration/cloudflare-access/
https://developers.cloudflare.com/workers/configuration/routing/workers-dev/
https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/
https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/application-token/
https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
https://developers.google.com/identity/gsi/web/guides/verify-google-id-token

## Gate
NO-GO deploy. Restano CI v0.14, account evidence aggiornata, review identity adapter e schema D1, test locali e staging autorizzato, restore/revoca, privacy e mapping. Nessun cambiamento A/B/C/D.
