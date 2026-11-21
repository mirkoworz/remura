# REMURA Contributors v0.68 LAB — private staging admission checkpoint
**21 novembre 2026 · Europe/Rome · progetto senza deploy**

## Scopo e tracciabilità
- Base v0.67: `01ad759d85b84200522bc6411c888d91d7da8ea4`.
- Branch isolato: `research/contributors-staging-gates-v068-20261121`.
- File nuovi: `staging_admission_v068_lab.mjs`, `test_staging_admission_v068_lab.mjs`.
- Questo modulo è un **contratto puro LAB**, NON middleware Cloudflare collegato, NON autenticazione Access verificata. Il campo `session.trusted` è accettabile solo se impostato dal futuro adapter server dopo verifica indipendente del JWT Access; non deve mai provenire dal browser.
- Endpoint READ consentiti: `/api/amendment/reconcile` con body `{}`, `/api/amendment/mine` con `{after}`, `/owner/amendment/reconcile-queue` con `{after}`. Tutti POST, same-origin, CSRF e JSON; il ruolo viene verificato dal server.
- Tutte le route di inserimento, revisione, approvazione, rilascio e chiusura sono negate da questo gate. `CLOSED` non autorizza a reinviare.
- CSP candidata per un futuro staging privato: `connect-src 'self'`, script e CSS same-origin, `no-store`, niente embedding.
- Quote gratuite: le evidenze vanno raccolte sui contatori effettivi. Anche con tutte le dimensioni verificate, la funzione NON autorizza deploy o spese.

## Checklist prima di richiedere l'autorizzazione allo staging
1. Verificare dal dashboard Cloudflare quote e limiti Access Free (utenti e policy), Workers (richieste e CPU), D1 (letture/scritture/storage) e gli eventuali limiti di fatturazione del piano attuale.
2. Verificare stato dei quattro database esistenti e mantenere fixture e LAB separati. **Non migrare** senza consenso.
3. Definire dominio privato e Access application con policy esplicita di allowlist; l'URL da solo non deve concedere privilegi.
4. Verificare JWT Access lato Worker (firma, `aud`, issuer, scadenza, identità verificata), impedire service-token e bypass delle intestazioni; risolvere il ruolo da dati server trusted.
5. Collegare gli endpoint originali già collaudati v0.65 al middleware, mantenendo D1 `first-primary`, HMAC, generazione e rate limit. Non trattare due scritture come atomiche.
6. Aggiungere logout Access effettivo, invalidazione sessione, blocco cache e risposta tardiva dopo logout.
7. Testare in un ambiente autorizzato Access reale/D1 reale con identità sintetiche; solo successivamente considerare pochi collaboratori veri.
8. Confermare separatamente ogni deploy, migrazione, registrazione reale, attivazione Secret o costo.

## Evidenze e limiti
- Implementazione e suite sono pubblicate su branch LAB GitHub.
- Non dichiarare suite PASS finché il comando `node --test research/contributors/test_staging_admission_v068_lab.mjs` non sia realmente eseguito.
- Non sono stati eseguiti test storici v0.66 o v0.67.
- Stato Cloudflare: **NON TESTATO**; produzione: **NON ATTIVA**; quote gratuite: **NON MISURATE**.
- Priorità: ottenere test locale nuovo e verificare i contatori, poi progettare adapter Access verificato senza deploy.
- Altri filoni Experience, TradingView, Shark Science, Oracle, Ampere, Private Capture, backup, Squalincome e Telegram rimangono congelati/invariati secondo roadmap v0.67.
