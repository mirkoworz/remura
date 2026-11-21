# REMURA Contributors v0.67 LAB — CHECKPOINT iPHONE RECOVERY
**21 novembre 2026, 12:02 CET (Europe/Rome)**

## GitHub provenance e isolamento
- Repo: `mirkoworz/remura`; nuovo branch `research/contributors-recovery-v067-20261121`.
- Base originale intatta: `research/contributors-fullstack-v066-20261121` a `0b40ddddf25a15478ab618e038aa4c4406c53ac8`.
- Nessun merge su `main`, nessun PR, nessun deploy, nessun database reale, nessuna chiave o identità reale, nessuna modifica Oracle.
- I cinque nuovi file sono stati caricati su GitHub e confrontati con `git hash-object` dei byte usati per i test:
  - `recovery_portal_v067_lab.mjs`: `eebc54e5f65e73e1cc690b803442973bf217c995`.
  - `contributors_recovery_v067_lab.html`: `43d20b369c5613b02cdd762b760de6c1c3aa9b28`.
  - `contributors_owner_recovery_v067_lab.html`: `4cf790f0112accf2f7c38b4dd68e337c138dc4d5`.
  - `contributors_recovery_v067_lab.css`: `4e7dfd6944681810917552c77aa41425704ceaa0`.
  - `test_recovery_portal_v067_lab.mjs`: `2c95ed979b65e755bdbad6193033ada43811449f`.
- Il primo elemento visibile di ciascuna pagina contiene `REMURA Contributors v0.67 LAB · 21/11/2026 11:57 CET · OFFLINE`, orario italiano letto al momento della preparazione dei file.

## Implementato — SOLO LAB
1. Due nuove schermate responsive con CSP offline `connect-src 'none'`: recupero del collaboratore e scrivania OWNER separata.
2. Riutilizzo *per import* del lettore `ReconciliationClientV065` per i cinque stati `NO_ATTEMPT`, `UNRESOLVED`, `COMMITTED_UNREVIEWED`, `COMMITTED_REVIEWED`, `CLOSED`.
3. Tutti e cinque sono **non autorizzanti**. Nessuno stato né ricevuta rimuove il blocco dei nuovi invii. Anche `CLOSED` e `NO_ATTEMPT` non equivalgono a via libera.
4. Lettura delle ricevute tramite `AmendmentClientV063.read('/api/amendment/mine',{after:0})`, che usa il controllo identità del backend originale. Validazione esatta del wire format e proiezione minima `id/source_entry_id/status/received_utc`: prezzi e note non vengono visualizzati. Il client non può trasmettere identità arbitrarie.
5. Lettore OWNER v0.67 separato per `/owner/amendment/reconcile-queue`, con validazione `no-store`, `same-origin`, CSRF, paginazione dopo ultimo ID e rigetto di campi extra, stati CLOSED o ordinamenti inconsistenti.
6. Cancella-vista e invalidazione di risposte asincrone ritardate; niente `localStorage`, `sessionStorage` o `fetch()` autonomo; nessun controller che invii modifiche.
7. La cancellazione locale **non è** logout del provider Cloudflare Access: necessaria una futura integrazione autenticata.

## Test nuovi e limiti
- Comando eseguito localmente (solo suite nuova): `cd research/contributors && node --test test_recovery_portal_v067_lab.mjs`.
- Ambiente: Node 22.16.0, DOM simulato con nodi sintetici, fetch iniettato con risposte `Response` sintetiche; **33/33 PASS**, zero fail.
- Nei test locali sono state ricreate copie **byte-identiche** dei client v0.63 e v0.65 già presenti nel repository; le loro impronte Git sono rispettivamente `da696aa1d7d7d7bcb7b701ab30a3e9ecfb057b56` e `6c062cc9c602411a442fe2c3e1eebd974311f9c5`. Le copie originali GitHub NON sono state modificate.
- Casi nuovi: tutti e cinque gli stati, blocco invio, privacy, risposta malformata, perdita di rete, HTTP same-origin/no-store, distinzione OWNER/CONTRIBUTOR, paginazione, chiusura vista durante una risposta lenta, refresh, scritture duplicate escluse dall'interfaccia.
- Verifica layout supplementare: rendering statico Chromium headless a larghezze 320/375/390/768 CSS px, **4/4 senza overflow orizzontale** e con intestazione iniziale corretta; per vincoli di navigazione dell'ambiente la prova ha utilizzato HTML/CSS isolati e **non ha verificato il caricamento del modulo JS nel browser**.
- NON sono state ripetute le 45 prove v0.66, le 79 v0.65 o altri collaudi già conclusi.
- Nessuna prova su Safari iPhone fisico, Cloudflare Access reale o D1 reale: **NO-GO portale amici in produzione**.
- Due scritture backend persistenti (prenotazione e insert) sono ancora separate e non atomiche; un esito incerto resta gestione OWNER manuale.

## Stato operativo
- IMPLEMENTATO: controller/HTML/CSS/pagine personal + OWNER, nuovi test.
- TESTATO LOCALMENTE: 33/33 unit/HTTP-mock/DOM e 4/4 rendering statico Chromium mobile.
- VERIFICATO SU GITHUB: 5 nuovi file, SHA Git corrispondenti al workspace locale.
- TESTATO SUL CLOUD: **NO**.
- ATTIVO IN PRODUZIONE: **NO**.
- COSTI: **nessuna nuova spesa, nessun runner hosted, nessun nuovo servizio**. I contatori del piano Free non sono stati consultati: margine residuo NON attestato.

## Roadmap aggiornata
- **P0 / v0.67**: checkpoint LAB implementato; restano test browser JS con server/DOM reali e iPhone Safari fisico, oltre al controllo corretto del logout provider.
- **P1 / v0.68**: piano operativo accesso privato `Cloudflare Access + Worker + D1`, CSP `connect-src` limitato al proprio origin, role enforcement server, fetcher autorizzato, contatori reali Workers/D1/Access, quota GitHub e gate di deploy/staging. Non attivare senza autorizzazione separata.
- **P2 / PORTALE AMICI**: MVP consultazione REMURA in sola lettura + creazione/correzione dei soli livelli propri; iniziare con pochi invitati autorizzati, mai accesso ai livelli altrui e approvazione solo OWNER.
- **P3 / EXPERIENCE v0.30**: splash 3D toro/orso, esplosione, REMURA pinna, SMF e ringraziamento; prova iPhone Safari e custodia anti-rollback indipendente ancora non certificate.
- **P4 / TRADINGVIEW v0.8.181 e SHARK SCIENCE v0.4**: parametri holdout congelati, H1 23–29/11 UTC, H2 30/11–06/12 UTC; baseline price-only, costi, nessun edge istituzionale dichiarato.
- **P5 / CLOUD-ORACLE-PRIVATE CAPTURE**: collector Oracle invariato, v1.65 NO-GO, Ampere Radar v0.36 operativo non alterato, Private Capture v0.15 hosted STOP; conservare backup, Squalincome, sicurezza e integrazioni senza nuovi interventi sui server.
- **P6 / TELEGRAM CONTRIBUTORS**: possibile solo in seguito e dopo politiche privacy/approvazione; nessun invio reale di livelli.

**Decisione:** v0.67 LAB pronta per revisione, **non** attivare identità o servizi reali. La prossima attività utile è progettare il passaggio protetto v0.68, non aggiungere ulteriori suite storiche.
