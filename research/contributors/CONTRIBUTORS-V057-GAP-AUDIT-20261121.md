# REMURA Contributors v0.57 — audit pratico dei permessi e percorsi mancanti
**21/11/2026, 08:20 CET — design e lettura del sorgente, NON una nuova versione operativa.**

## Origine verificata
Branch Contributors originario: research/contributors-offline-20261114 @ 21338d4a405b0a3053e5a51322f8643c428ac757. Nessuna modifica a quel ramo e nessuna ripetizione dei collaudi storici o delle verifiche D1.

File letti da quel branch:
- contributors_worker_candidate.mjs (blob 77b07a75bfb1458e08588a815c5f2772c04aafe9)
- http_access_candidate.mjs (blob eeca1d27f202f10473116504fc9bf8d65934805d)
- d1_access_candidate.mjs (blob e5dd70b5a0243130a1a95bee4ea4cb6266b08b68)
- contributors_candidate_client.mjs (blob 873f84930b32c7f5292d62ce5df4e7f36d8a6869)
- contributors_candidate.html (blob 2b56f681c6789967813f065f7bd17fb762654f9a)
- d1_lab_schema.sql (blob 81db063ef5c7cd35c180a9dca884151a89be4414)
- access_policy_v1.py (blob 3fb5e5ba5de0b870561ee7661924d2bd0df2ab2b)

Questi artefatti sono LAB/candidati; l'analisi del codice **non** dimostra autenticazione reale né sicurezza di un deployment. Non usare i soli controlli lato browser come ACL.

## Già presente nel candidato LAB (non in produzione)
1. Pagina separata Contributors con intestazione versione/data/ora, modulo per nuovi livelli, ricevute personali e flusso di revisione OWNER. La UI distingue le sezioni, ma il vero permesso dipende dal server.
2. Worker candidato chiuso salvo precise variabili LAB_ONLY, origine HTTPS configurata e route allowlisted, non pubblicato.
3. Contratto HTTP con POST JSON, evidenze same-origin, header CSRF, limite corpo, rate limiter e intento one-time per le mutazioni; risposta non confermata senza retry automatico.
4. Access binding di test e query D1 candidate con controlli ruolo/subject e singola sessione primary. La query ricevute filtra il soggetto; queue/review richiedono OWNER.
5. Tabella lab_entries immutabile tramite trigger UPDATE/DELETE e revisione owner append-only. Il contratto prezzi osservati, periodi, metodologie e note è definito.

## GAP reali da chiudere PRIMA di aprire agli amici
**A. Correzione dei propri livelli:** il candidato espone /api/submit per creare, non un endpoint proprio per correggere. La tabella lab_entries blocca UPDATE/DELETE. Non risolvere eliminando il trigger: progettare invece **AMENDMENT append-only** che si riferisce all'ID precedente, lega SUBJECT ORIGINALE lato SQL e richiede un nuovo consenso owner. Finché manca, la UI deve indicare che si possono INVIARE nuovi livelli e non correggere quelli già presentati.

**B. Vedere REMURA senza scriverla:** i soli /api/profile, /api/catalog e /api/receipts non rappresentano una vista completa dell'analisi REMURA. Prevedere read-only projections server-side autorizzate, con sezioni Price/COT/Sentiment/Science filtrate per provenienza; dati PENDING/ABANDONED mai mostrati. Mai esporre database, Secrets o amministrazione mediante navigazione UI.

**C. Inviti reali e revoca:** l'access_policy_v1.py usa LabIdentity, example.invalid e slot sintetici friend-a/friend-b. Non è onboarding reale. Prima degli inviti: autenticazione con provider reale, piano owner inviti/revoca verificato, audit, session TTL, per-request re-check e collaudi contro modifica dei ruoli durante scrittura.

**D. Revisione/Telegram:** le approvazioni sono operazioni OWNER distinte; NON inoltrare automaticamente livelli grezzi a Telegram. Più avanti una consegna opzionale e revocabile solo dopo approvazione, con consenso e no Secret in chat.

**E. UI iPhone:** Safari Mac collaudato per Experience, non Safari fisico iPhone per Contributor editing/login/offline. Nessuna equivalenza dedotta.

## Contratto proposto per correzione append-only — NON implementato
1. Richiesta di correzione con nuovo request_id, ID del livello originale, nuovo payload completo (ancora prezzo, data UTC, note <= 280, periodo/metodo) e motivazione opzionale. Il subject NON proviene dal body.
2. Il server verifica in transazione che il livello originale appartenga esattamente al subject della sessione e non sia revocato; un livello dell'altro amico è sempre invisibile e non modificabile.
3. Inserimento di un nuovo record in catena di emendamenti, original_id e SHA256 del predecessore, con proprio timestamp UTC e idempotency key; originale sempre immutabile.
4. La modifica resta UNREVIEWED e non sovrascrive una vista già APPROVED. L'owner deve decidere esplicitamente la sostituzione, con procedura che impedisca due sostituti approvati simultaneamente.
5. Doppio invio e risposta incerta: verifica dell'idempotency key, mai ripetizione automatica della mutazione. Rate-limit, limiti Free e minimizzazione PII.
6. Revoca contributor fra controllo e commit: guard SQL/operazione deve rilevarla nel medesimo punto di linearizzazione, o bloccare.
7. Audit e vista read-only: il contributor vede solo le proprie correzioni; l'owner può vedere audit completo; viewer futuro non scrive.

## Test negativi da realizzare solo in una futura fixture dedicata
- Utente A tenta emendare entry di B; owner-only review da A; replay di request_id con payload diverso; revoca durante transazione; alterazione original_id e subject; edit di livello approvato senza nuova approvazione; concorrenza di due emendamenti, idempotenza; clock futuro/regressivo; note invalide; lettura di record altrui; fuga di dettagli SQL; aumento delle query e costi oltre quota.
- Non creare schema D1 aggiuntivo o deploy finché contratto, test e limiti Free non sono verificati.

## Decisione di priorità operativa
1. Concludere gate v0.57 per **visione autorizzata + inserimento soltanto dei propri livelli** usando i moduli candidati già esistenti; non confondere 'login demo' con accesso reale.
2. Progettare l'emendamento come filone v0.58 LAB separato, con verifica formale delle transizioni e migrazione solo dopo autorizzazione.
3. Integrare pagine/Experience solo quando la disponibilità dei dati e la custodia dell'autorità sono credibili; splash 3D toro/orso e ringraziamento SMF restano invariati.
4. Valutare prezzi, limiti reali Cloudflare Free e sicurezza dell'identità prima di aprire un ambiente esterno; attualmente nessun costo/preview/deploy autorizzato.

**Risultato: gap analizzati sul codice, non test nuovi Contributors, non release e non registrazione di utenti reali.**
